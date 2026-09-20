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
from app.core.plugin import logger
from app.settings import config
from plugin.notice import notify, fetch_checkpoint, checkpoint_save


class BaseGenService:
    """每个生成类型继承此类,只需指定 tool_class / gen_type / is_media"""

    tool_class: Type[BaseGenTool] = BaseGenTool
    gen_type: GenTypeEnum = GenTypeEnum.VIDEO
    is_media: bool = True  # 结果是否以媒体地址(result_video/result_image/result_audio)回写

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

        async def heartbeat() -> None:
            """真实生成耗时较长,后台按固定间隔回写进度,直到主流程结束"""
            progress = max(10, start_progress)
            while not stop.is_set() and progress < 90:
                await asyncio.sleep(config.GEN_PROGRESS_INTERVAL)
                if stop.is_set():
                    break
                try:
                    await notify(
                        notify_url,
                        {"task_id": task_id, "status": "processing", "progress": progress},
                        config.NOTIFY_TOKEN,
                    )
                except Exception as e:  # 进度回写失败不阻断生成
                    logger.warning(f"进度回写失败 task={task_id}: {e}")
                progress += 10

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
            payload = {"task_id": task_id, "status": "success", "progress": 100, "usage": metadata}
            if self.is_media:
                payload["result_video"] = result.content
            else:
                payload["result"] = result.content
            await notify(notify_url, payload, config.NOTIFY_TOKEN)
            logger.info(f"生成完成 task={task_id} type={self.gen_type} result={result.content}")
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
        await notify(
            notify_url,
            {"task_id": task_id, "status": "failed", "fail_reason": error[:255]},
            config.NOTIFY_TOKEN,
        )
