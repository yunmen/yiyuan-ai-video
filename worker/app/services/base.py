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

# 各阶段完成后的进度基准(与 backend generate_task.TASK_PROFILES 的阶段划分对齐):
#   1 = prompt 改写完成 → 30(后端阶段文案进入「提交生成任务」)
#   2 = 已提交外部任务 → 55(进入「模型生成视频」)
#   3 = 已取回原始结果 → 88(进入「回传成片」,仅剩转存)
# 改造原因:此前进度只按时间从 10 一路爬到 88,与真实阶段完全无关 ——
# 用户看不出"卡在提交"还是"卡在模型",长任务只能看着一个不动的高百分比。
STAGE_PROGRESS = {1: 30, 2: 55, 3: 88}
# 全局封顶:成功才给 100,生成中最高 88(不能冲到 90+ 让人以为"马上就好")
PROGRESS_CEILING = 88
# 收尾阶段(成片已出 → 转存/自检/画幅修正/字幕烧录)可爬到的上限。
# 这一段实测 2~3 分钟且**没有任何阶段推进**,进度会死死定格在 88,用户看到的就是"卡住了";
# 100 留给成功回调,故只放到 97。
FINAL_CEILING = 97
# 停留在阶段上沿超过这么多拍(模型侧长时间未推进)后,允许继续缓慢爬升:
# 既保留"阶段语义",又保证进度一直在动,用户能确认任务还活着而不是卡死。
STAGE_STALL_BEATS = 6


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
        # 当前阶段基准(由 on_stage 回调推进):心跳据此在阶段区间内蠕动,
        # 保证"进度 ↔ 阶段文案"的对应关系真实,而不是纯时间函数。
        stage_base = {"value": max(5, start_progress)}

        async def heartbeat() -> None:
            """真实生成耗时较长,后台按固定间隔回写进度,直到主流程结束。

            进度由两部分共同决定:
              ① 阶段基准(stage_base)—— 由 tool 的 on_stage 回调推进(见 STAGE_PROGRESS);
              ② 阶段内蠕动 —— 每拍 +1,最多爬到「下一阶段基准 - 1」,不越过下一阶段。
            这样进度既持续在动,又真实对应「改写完成 / 已提交 / 已取回」这些节点;
            若模型侧长时间没有阶段推进,停满 STAGE_STALL_BEATS 拍后允许继续缓慢爬升,
            避免进度冻住让人误判任务已死。已用时长一并回写,前端可显示"生成中 12:34"。
            """
            progress = max(5, start_progress)
            beats = 0
            stall = 0
            ceiling_logged = False
            last_base = int(stage_base["value"])
            # 注意:不能因为"进度到顶"就退出心跳 —— 收尾阶段(成片转存/字幕烧录)可能耗时数分钟,
            # 心跳一停,后端与前端就再也收不到任何进展,与真卡死无从区分(task 5 实测:进度定格
            # 87% 静默 5m37s,而任务其实一直在跑)。到顶后继续按同一节奏回写:progress 保持不变、
            # elapsed_seconds 继续增长,前端得以显示"已运行 X 分 X 秒"。
            while not stop.is_set():
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
                if progress >= PROGRESS_CEILING and not ceiling_logged:
                    ceiling_logged = True
                    logger.info(
                        f"进度已到上限 {PROGRESS_CEILING}%,收尾中(转存/烧录)继续保持心跳 "
                        f"task={task_id}(已用 {beats * config.GEN_PROGRESS_INTERVAL}s)"
                    )
                base = int(stage_base["value"])
                if base != last_base:      # 阶段有推进:重置停留计数
                    last_base = base
                    stall = 0
                if base > progress:
                    # 阶段推进 → 进度立刻顶到该阶段基准,不让用户等"慢慢爬上去"
                    progress = base
                    continue
                # 阶段上沿 = 下一阶段基准 - 1;已到最后阶段则用全局封顶
                nxt = [v for v in sorted(STAGE_PROGRESS.values()) if v > base]
                cap = min(PROGRESS_CEILING, nxt[0] - 1) if nxt else PROGRESS_CEILING
                if progress < cap:
                    progress += 1
                elif stall >= STAGE_STALL_BEATS:
                    # 成片已出(stage=3)后的收尾(转存/自检/画幅修正/烧录)没有任何阶段推进,
                    # 进度会定格;此时放行到 FINAL_CEILING,让这几分钟在进度条上有反馈。
                    # 仍在模型生成阶段则维持 88,避免"97% 却还在等生成"的错觉。
                    ceiling = (
                        FINAL_CEILING
                        if last_base >= STAGE_PROGRESS.get(3, PROGRESS_CEILING)
                        else PROGRESS_CEILING
                    )
                    progress = min(ceiling, progress + 1)
                else:
                    stall += 1

        async def save_checkpoint(stage: int, data: Optional[dict] = None) -> None:
            """阶段完成回调:把断点检查点与该阶段真实进度一起回写 backend(失败仅记录,不阻断生成)"""
            progress = STAGE_PROGRESS.get(int(stage or 0))
            if progress:
                stage_base["value"] = progress
            try:
                await checkpoint_save(
                    notify_url,
                    {"task_id": task_id, "stage": stage, "data": data or {}, "progress": progress},
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
            # O7 局部重跑:params 带 _regenerate_segment 时改走 regenerate_segment(而非整条重生成),
            # 复用同一套心跳/检查点/重试/回调机制,只替换目标分段。
            if gen_params.pop("_regenerate_segment", None) and hasattr(tool, "regenerate_segment"):
                result = await tool.regenerate_segment(
                    gen_params, int(gen_params.get("segment_index", 0)),
                    str(gen_params.get("new_text") or ""),
                    checkpoint=checkpoint, on_stage=save_checkpoint,
                )
            else:
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
            if self._should_burn_subtitle() and not metadata.get("subtitle_burned"):
                try:
                    duration = float(metadata.get("seconds") or gen_params.get("duration") or 0)
                except (TypeError, ValueError):
                    duration = 0.0
                # 纵深防御:整段烧录(下载+ASR+ffmpeg+上传)再包一层超时,
                # 任何子步骤意外阻塞都不会让任务永久卡在 processing —— 超时即跳过烧录,照常回写成功。
                try:
                    burned, cues = await asyncio.wait_for(
                        subtitle.burn_subtitle_with_cues(
                            content, gen_params, duration, prefix=str(task_id),
                        ),
                        timeout=600,
                    )
                except asyncio.TimeoutError:
                    logger.error(f"字幕烧录整体超时(600s),跳过烧录保留原片 task={task_id}")
                    burned, cues = None, []
                if burned:
                    content = burned
                    metadata["subtitle_burned"] = True
                    # 把**实际烧进成片**的时间轴随 usage 回写 backend:
                    # 「改一句台词重跑」据此定位真实时间窗 —— 建单时的 timing 只是按词数摊分的估算值。
                    if cues:
                        metadata["subtitle_timing"] = [
                            {"text": c.text, "start_ms": c.start_ms, "end_ms": c.end_ms} for c in cues
                        ]

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
