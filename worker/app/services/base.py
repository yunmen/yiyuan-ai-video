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
from app.core import metrics
from app.core.plugin import logger
from app.settings import config
from plugin.notice import notify, fetch_checkpoint, checkpoint_save

# 需要烧字幕的结果类型:image/audio/text 不适用(只有视频有"画面+时间轴"可言)
SUBTITLE_GEN_TYPES = (GenTypeEnum.VIDEO, GenTypeEnum.DIGITAL, GenTypeEnum.RENDER)

# 音乐网关「权限/未开通」类报错特征(实测 fun-music-v1:403 Access denied)。
# 这类失败重试无用,必须在日志里直接给出可执行的修复方向,否则会持续 403 而无人处理。
_ACCESS_DENIED_HINTS = ("403", "access denied", "permission", "forbidden", "unauthorized")


def _is_access_denied(text: str) -> bool:
    """报错文本是否为「网关未开通该模型权限」(配置问题,而非偶发抖动)"""
    lowered = str(text or "").lower()
    return any(hint in lowered for hint in _ACCESS_DENIED_HINTS)

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

    async def _apply_bgm(
        self, video_url: str, gen_params: dict, task_id: int, metadata: Optional[dict] = None,
    ) -> str:
        """把背景音乐混进成片音轨;任何环节失败返回原 video_url(保留原片)。

        流程:生成 BGM(音乐模型,纯乐器)→ 下载成片与 BGM 到本地 →
        compose.build_bgm_cmd 做 amix 混音(原声 + BGM 压到人声之下)→ 转存 OSS。
        这是增强能力,绝不为「加 BGM」把一次已付费的生成变成失败任务。

        成败都要**留痕**(metadata.bgm_applied / bgm_skip_reason):
        此前 BGM 失败只在 worker 日志里出现一行(实测 task 59:fun-music-v1 报 403
        Access denied),backend/管理端/用户全无感知,排查时只能靠猜。
        """
        import os
        import shutil
        import tempfile

        from app.core import compose
        from app.tools.audio_tool import AudioGenTool
        from app.utils.oss import download_to_local, upload_local_file

        try:
            music = await AudioGenTool().generate_music(
                prompt=config.BGM_PROMPT, is_instrumental=True, task_id=str(task_id),
            )
            if not (music.metadata or {}).get("success", True) or not music.content:
                reason = str((music.metadata or {}).get("error") or "音乐网关未返回结果")
                self._mark_bgm_skipped(
                    metadata, f"背景音乐生成失败(model={config.MUSIC_MODEL}),已保留无配乐原片",
                )
                # 403 多为网关未开通该模型权限(属配置问题,不是偶发抖动),
                # 必须把可执行的修复方向写进日志,否则这类失败会一直重复出现且无人察觉。
                hint = (
                    "请在该网关开通此音乐模型权限,或将 BGM_ENABLE 关闭后重试"
                    if _is_access_denied(reason) else "稍后自动重试或检查音乐网关配置"
                )
                logger.warning(
                    f"[BGM] 背景音乐生成失败(model={config.MUSIC_MODEL}),跳过铺底 "
                    f"task={task_id}: {reason}。{hint}"
                )
                return video_url
            workdir = tempfile.mkdtemp(prefix="bgm_")
            try:
                local_video = await asyncio.to_thread(download_to_local, video_url, ".mp4")
                local_bgm = await asyncio.to_thread(download_to_local, music.content, ".mp4")
                if not local_video or not local_bgm:
                    self._mark_bgm_skipped(metadata, "背景音乐下载失败,已保留无配乐原片")
                    return video_url
                # ducking(人声段压低 BGM):任务级覆盖 > 全局配置。
                # 检测成片音轨的人声段(与字幕对齐同源的 silencedetect),人声段把 BGM 压到 duck_level,
                # 其余保持 BGM_VOLUME;检测失败则不做 ducking(整轨 BGM 仍铺底),绝不阻断铺底。
                ducking = gen_params.get("ducking")
                ducking = config.BGM_DUCK if ducking is None else bool(ducking)
                duck_level = gen_params.get("duck_level")
                duck_level = float(duck_level) if isinstance(duck_level, (int, float)) else config.BGM_DUCK_LEVEL
                duck_intervals = None
                if ducking:
                    try:
                        from app.core.subtitle import detect_speech_segments
                        duration = compose.probe_duration(local_video)
                        if duration > 0:
                            speech = await detect_speech_segments(local_video, duration)
                            if speech:
                                pad = max(0.0, float(config.BGM_DUCK_PAD))
                                duck_intervals = [(max(0.0, s - pad), e + pad) for (s, e) in speech]
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"[BGM] 人声段检测失败,跳过 ducking: {exc}")
                out = os.path.join(workdir, "with_bgm.mp4")
                result = await compose.run(
                    compose.build_bgm_cmd(
                        local_video, local_bgm, out, config.BGM_VOLUME, duck_intervals, duck_level,
                    ),
                    timeout=600,
                )
                if not result.get("ok") or not os.path.exists(out):
                    logger.warning(f"[BGM] 混音失败,跳过铺底 task={task_id}: {result.get('stderr')}")
                    self._mark_bgm_skipped(metadata, "背景音乐混音失败,已保留无配乐原片")
                    return video_url
                url = await asyncio.to_thread(
                    upload_local_file, out, f"generate/result/{task_id}_bgm.mp4",
                )
                if url:
                    if metadata is not None:
                        metadata["bgm_applied"] = True
                    logger.info(f"[BGM] 背景音乐铺底完成 task={task_id}")
                    return url
                self._mark_bgm_skipped(metadata, "背景音乐成片转存 OSS 失败,已保留无配乐原片")
                return video_url
            finally:
                shutil.rmtree(workdir, ignore_errors=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[BGM] 铺底异常,跳过保留原片 task={task_id}: {exc}")
            self._mark_bgm_skipped(metadata, "背景音乐铺底异常,已保留无配乐原片")
            return video_url

    @staticmethod
    def _mark_bgm_skipped(metadata: Optional[dict], reason: str) -> None:
        """BGM 未铺底时留痕:与字幕一同样式,让 backend/管理端可见(此前只有 worker 日志知道)"""
        if metadata is None:
            return
        metadata["bgm_applied"] = False
        metadata["bgm_skip_reason"] = reason
        # 计数:BGM 失败多为网关未授权(403),批量出现应直接关掉或换网关
        metrics.incr("bgm.skipped", detail=reason[:120])

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
                else:
                    # 烧录没成功必须**留痕**,不能静默:否则成片无字幕这件事只有 worker 日志知道,
                    # backend/管理端/用户侧全无感知,排查时只能靠猜(实测 task 59 就是这样:
                    # 日志一行"跳过字幕烧录",成片却已判成功交付)。
                    # 这里只标记不阻断 —— 已付费的成片不该因"加字幕"失败被丢,
                    # 阻断与否由上游按业务需要决定(前端可据此提示"本次未烧录字幕")。
                    metadata["subtitle_burned"] = False
                    metadata["subtitle_skip_reason"] = "字幕烧录失败或超时,已保留无字幕原片"
                    # 计数:字幕是"每单都该有"的能力,批量跳过说明字体/网关/ASR 出了共性问题
                    metrics.incr("subtitle.skipped", detail=f"task={task_id}")
                    logger.warning(
                        f"字幕未烧入成片(保留原片) task={task_id} type={self.gen_type} "
                        f"subtitle_skip_reason={metadata['subtitle_skip_reason']}"
                    )
                    # 把**实际烧进成片**的时间轴随 usage 回写 backend:
                    # 「改一句台词重跑」据此定位真实时间窗 —— 建单时的 timing 只是按词数摊分的估算值。
                    if cues:
                        metadata["subtitle_timing"] = [
                            {"text": c.text, "start_ms": c.start_ms, "end_ms": c.end_ms} for c in cues
                        ]

            # 背景音乐铺底(可配置,默认关):在字幕烧录之后把 BGM 混进成片音轨。
            # 仅视频类型需要;任一环节失败一律保留原片(已付费结果不能被「加 BGM」弄丢)。
            if config.BGM_ENABLE and self.gen_type == GenTypeEnum.VIDEO and not metadata.get("bgm_applied"):
                content = await self._apply_bgm(content, gen_params, task_id, metadata)

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
        # 同时回写**结构化失败码**:用户看得懂的文案只能说明"失败了",前端要靠它才能给出
        # 可执行的下一步(换素材 / 去数字人 / 直接重试),而不是让用户自己猜。
        await notify(
            notify_url,
            {
                "task_id": task_id,
                "status": "failed",
                "fail_reason": error[:255],
                "fail_code": str(metadata.get("error_type") or "").strip()[:64],
            },
            config.NOTIFY_TOKEN,
        )
