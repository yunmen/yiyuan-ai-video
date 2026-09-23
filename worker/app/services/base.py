# -*- coding: utf-8 -*-
'''
@文件    :base.py
@说明    :生成服务基类 — 编排:进度心跳 + 断点检查点 + 调 tool 真实生成 + 汇总用量 + 回调 backend
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :2.2
@说明    :失败按 ARQ 的 job_try 判定 —— 未到最后一次则抛 Retry 交由 ARQ 重试(不回调 failed,
          避免"失败→重试成功"造成前端状态抖动);仅最后一次才回写 failed。
          断点续跑:run 启动时向 backend 拉取上次保存的检查点,传给 tool;tool 在每个阶段完成后
          通过 on_stage 回写检查点。ARQ 自动重试或用户「断点续跑」时,worker 复用检查点跳过
          已完成阶段(如复用已提交的外部任务 ID 继续轮询,避免重复扣费生成)。
'''
import asyncio
from typing import Optional, Type

from arq.worker import Retry

from app.tools.base import BaseGenTool
from app.schemas.base import ToolResult
from app.enums.task import GenTypeEnum
from app.core import subtitle
from app.core.plugin import logger
from app.settings import config
from plugin.notice import notify, fetch_checkpoint, checkpoint_save

# 需要烧字幕的结果类型:image/audio/text 不适用(只有视频有"画面+时间轴"可言)
SUBTITLE_GEN_TYPES = (GenTypeEnum.VIDEO, GenTypeEnum.DIGITAL)


class BaseGenService:
    """每个生成类型继承此类,只需指定 tool_class / gen_type / is_media"""

    tool_class: Type[BaseGenTool] = BaseGenTool
    gen_type: GenTypeEnum = GenTypeEnum.VIDEO
    is_media: bool = True  # 结果是否以媒体地址(result_video/result_image/result_audio)回写

    def _should_burn_subtitle(self) -> bool:
        """是否需要在回写前把字幕烧进成片"""
        return self.is_media and self.gen_type in SUBTITLE_GEN_TYPES

    async def run(self, task_id: int, notify_url: str, params: dict, ctx: Optional[dict] = None) -> None:
        # 启动时拉取上次保存的断点检查点,供 tool 续跑
        ckpt = await fetch_checkpoint(notify_url, task_id, config.NOTIFY_TOKEN)
        checkpoint = ckpt.get("checkpoint") or {}
        start_progress = max(5, int(ckpt.get("progress") or 5))

        # 立即回写一次"生成中",让前端进入进度态
        await notify(
            notify_url,
            {"task_id": task_id, "status": "processing", "progress": start_progress},
            config.NOTIFY_TOKEN,
        )

        stop = asyncio.Event()
        # 进度封顶:必须 < 90(成功才给 100),也不能冲到 90+ 让人以为"马上就好"
        progress_ceiling = 88

        async def heartbeat() -> None:
            """真实生成耗时较长,后台按固定间隔回写进度,直到主流程结束。

            进度必须**持续在动**:此前是"每拍 +10、到 80 就再也不动"(约 35 秒就冻住),
            而 23s 的原生视频编辑要十几分钟 —— 用户完全分不清"还在跑"和"已经死了"(实测踩过)。
            这里让步长随进度收敛:前段快速爬到 60 让用户看到"起来了",之后每拍 +1 稳步前进,
            同时把已用时长一并回写,前端可以显示"生成中 12:34"而不是一个不动的百分比。
            """
            progress = max(10, start_progress)
            beats = 0
            while not stop.is_set() and progress < progress_ceiling:
                await asyncio.sleep(config.GEN_PROGRESS_INTERVAL)
                if stop.is_set():
                    break
                try:
                    await notify(
                        notify_url,
                        {
                            "task_id": task_id,
                            "status": "processing",
                            "progress": progress,
                            "usage": {
                                "heartbeat": {
                                    "elapsed_seconds": beats * config.GEN_PROGRESS_INTERVAL,
                                },
                            },
                        },
                        config.NOTIFY_TOKEN,
                    )
                except Exception as e:  # 进度回写失败不阻断生成
                    logger.warning(f"进度回写失败 task={task_id}: {e}")
                beats += 1
                progress = min(progress_ceiling, progress + (10 if progress < 60 else 1))
            if progress >= progress_ceiling:
                logger.info(f"进度已到上限 {progress_ceiling}%,等待模型返回 task={task_id}(已用 {beats * config.GEN_PROGRESS_INTERVAL}s)")

        async def save_checkpoint(stage: int, data: Optional[dict] = None) -> None:
            """阶段完成回调:把断点检查点回写 backend(失败仅记录,不阻断生成)"""
            try:
                await checkpoint_save(
                    notify_url,
                    {"task_id": task_id, "stage": stage, "data": data or {}},
                    config.NOTIFY_TOKEN,
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"断点回写失败 task={task_id} stage={stage}: {e}")

        # 注入 task_id 供工具层命名结果文件(转存 OSS 用)
        gen_params = dict(params or {})
        gen_params.setdefault("_task_id", task_id)
        # P2:注入回调地址,工具层据此读写 backend 的资产缓存(与 checkpoint 同域名)
        gen_params.setdefault("_notify_url", notify_url)

        hb = asyncio.create_task(heartbeat())
        result: Optional[ToolResult] = None
        error: Optional[str] = None
        try:
            tool = self.tool_class()
            result = await tool.generate(gen_params, checkpoint=checkpoint, on_stage=save_checkpoint)
        except Exception as e:  # noqa: BLE001
            error = str(e)
            logger.error(f"生成异常 task={task_id} type={self.gen_type}: {e}")
        finally:
            stop.set()
            await asyncio.gather(hb, return_exceptions=True)

        metadata = (result.metadata if result else {}) or {}
        # 工具以 success=False 表示业务失败(非异常)
        if error is None and not metadata.get("success", True):
            error = str(metadata.get("error") or (getattr(result, "content", "") or "生成失败"))

        # 成功
        if error is None:
            content = result.content
            # 字幕烧录:在回写前把字幕压进成片,失败一律保留原片(已付费的结果不能被"加字幕"弄丢)
            if self._should_burn_subtitle():
                try:
                    duration = float(metadata.get("seconds") or gen_params.get("duration") or 0)
                except (TypeError, ValueError):
                    duration = 0.0
                burned = await subtitle.burn_subtitle(content, gen_params, duration, prefix=str(task_id))
                if burned:
                    content = burned
                    metadata["subtitle_burned"] = True

            payload = {"task_id": task_id, "status": "success", "progress": 100, "usage": metadata}
            if self.is_media:
                payload["result_video"] = content
            else:
                payload["result"] = content
            await notify(notify_url, payload, config.NOTIFY_TOKEN)
            logger.info(f"生成完成 task={task_id} type={self.gen_type} result={content}")
            return

        # 失败:未到最后一次尝试 → 抛 Retry 交由 ARQ 重试(此时不回调 failed,避免状态抖动)
        job_try = int((ctx or {}).get("job_try", 1) or 1)
        max_tries = int(config.ARQ_MAX_RETRIES or 1)
        if job_try < max_tries:
            logger.warning(
                f"生成失败 task={task_id}(第 {job_try}/{max_tries} 次),"
                f"{config.ARQ_RETRY_DELAY}s 后重试: {error}"
            )
            raise Retry(defer=config.ARQ_RETRY_DELAY)

        logger.error(f"生成最终失败 task={task_id}(已尝试 {job_try} 次): {error}")
        # 回写原始报错到 backend(后端落库);C 端展示时由后端脱敏,管理端保留原始值直击重点,
        # 完整报错同时在此落日志供排查。
        await notify(
            notify_url,
            {"task_id": task_id, "status": "failed", "fail_reason": error[:255]},
            config.NOTIFY_TOKEN,
        )
