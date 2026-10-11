# -*- coding: utf-8 -*-
'''
@文件    :render_tool.py
@说明    :视频换口播工具 — 上传视频 + 提示词 → 三种变换(换声 / 换数字人 / 换场景)
@时间    :2026/09/30
@作者    :一源AI
@版本    :1.0
@说明    :路线由 params.route 派生(backend create_render 已按字段组合判定):
            - voice_only :保留真人画面,仅用提示词 TTS 重新配音(build_mix_audio_cmd);
            - digital_human:生成数字人按提示词口播,合成到源视频(满屏覆盖)或场景 B(作背景);
            - scene_swap :优先用 AI 抠像网关(gen.route.matting)把真人从任意背景源视频抠出,
                          叠到场景 B;未配置/失败时自动降级绿幕色键(chromakey)。
          复用数字人工具(AudioGenTool / DigitalHumanTool)与合成层(compose),
          失败统一以 ToolResult.metadata.success=False 返回,由 BaseGenService 转 failed。
'''
import asyncio
import os
import shutil
import tempfile
import uuid
from typing import Optional

from app.schemas.base import ToolResult
from app.tools.base import BaseGenTool
from app.tools.audio_tool import AudioGenTool
from app.tools.digital_tool import DigitalHumanTool
from app.tools.matting_tool import MattingTool
from app.settings import config
from app.core.plugin import logger
from app.core import compose
from app.utils.oss import download_to_local, upload_local_file


class RenderTool(BaseGenTool):
    """视频换口播工具 — 换声 / 换数字人 / 换场景 三路线统一入口"""

    name = "render"
    description = "视频换口播(换声/换数字人/换场景)"

    def _fail(self, msg: str, error_type: str = "unknown") -> ToolResult:
        logger.error(f"[RenderTool] {msg}")
        return ToolResult(content=msg, metadata={"success": False, "error_type": error_type, "error": msg})

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        """按 route 分发:voice_only / digital_human / scene_swap"""
        checkpoint = checkpoint or {}
        route = str(params.get("route") or "voice_only").strip()
        if route == "digital_human":
            return await self._digital(params, checkpoint, on_stage)
        if route == "scene_swap":
            return await self._scene_swap(params, checkpoint, on_stage)
        return await self._voice_only(params, checkpoint, on_stage)

    async def _maybe_broll(self, local_video: str, params: dict, task_id: str, workdir: str) -> str:
        """可选 B-roll 层:把素材(broll.asset)叠到成片 [broll.start,broll.end] 时间窗内。

        触发需 broll 为 dict 且含有效 asset 与 start<end;否则原样返回(不阻断主流程)。
        失败/ffmpeg 不可用也回退原片 —— B-roll 是增强层,绝不能让一次已付费生成变失败。
        """
        broll = params.get("broll") if isinstance(params.get("broll"), dict) else None
        if not broll or not compose.available():
            return local_video
        asset = str(broll.get("asset") or "").strip()
        try:
            start = float(broll.get("start") or 0)
            end = float(broll.get("end") or 0)
        except (TypeError, ValueError):
            return local_video
        if not asset or end <= start:
            return local_video
        try:
            local_asset = await asyncio.to_thread(download_to_local, asset, ".mp4")
            if not local_asset:
                return local_video
            out2 = os.path.join(workdir, "broll.mp4")
            result = await compose.run(
                compose.build_broll_cmd(
                    local_video, local_asset, out2,
                    start=start, end=end,
                    fade=float(broll.get("fade") or 0.3),
                    scale=float(broll.get("scale") or 1.0),
                    position=str(broll.get("position") or "center"),
                    # 未显式给 type 时按素材扩展名自动识别(图片/视频),让前端"图片或视频均可"真正成立
                    broll_type=self._infer_broll_type(broll, asset),
                ),
                timeout=600, cwd=workdir,
            )
            if result.get("ok") and os.path.exists(out2):
                logger.info(f"[RenderTool] B-roll 叠加成功 {start:.1f}-{end:.1f}s")
                return out2
            logger.warning(f"[RenderTool] B-roll 叠加失败,保留原片: {result.get('stderr')}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[RenderTool] B-roll 叠加异常,保留原片: {exc}")
        return local_video

    @staticmethod
    def _infer_broll_type(broll: dict, asset: str) -> str:
        """推断 B-roll 素材类型:显式 type 优先,否则按扩展名识别(图片/视频)。

        素材地址常为 OSS URL 且带 ?sign= 查询串,需先剥离查询串再取扩展名,
        否则会把 .mp4?sign=... 误判为非视频而退回 image 分支导致叠加失败。
        """
        explicit = str(broll.get("type") or "").strip().lower()
        if explicit in ("image", "video"):
            return explicit
        # 去掉 OSS 签名等查询串后再取扩展名,避免 ?sign=... 干扰识别
        path = asset.split("?", 1)[0]
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        return "video" if ext in ("mp4", "webm", "mov", "m4v", "avi", "mkv") else "image"

    async def _tts(self, params: dict, task_id: str) -> Optional[str]:
        """口播音频:优先用调用方传入的音频,否则按提示词现场 TTS(支持 voice / voice_reference 换声)"""
        audio = str(params.get("audio") or "").strip()
        if audio:
            return audio
        text = str(params.get("text") or params.get("prompt") or "").strip()
        if not text:
            return None
        tts = await AudioGenTool().text_to_speech(
            text=text,
            voice=params.get("voice"),
            voice_reference=params.get("voice_reference"),
            # 语速:0.5x–2.0x,与数字人路线保持一致;render 三路线(只换声/换场景/数字人)共用本 TTS
            speed=params.get("speed"),
            # 方言:与数字人路线一致,经 audio_tool 透传(extra_body + 可选指令模板)
            dialect=params.get("dialect"),
            task_id=task_id,
            notify_url=params.get("_notify_url"),
        )
        if not (tts.metadata or {}).get("success", True) or not tts.content:
            logger.warning(f"[RenderTool] 口播音频合成失败: {tts.metadata.get('error')}")
            return None
        return str(tts.content).strip()

    async def _voice_only(self, params: dict, checkpoint: Optional[dict], on_stage=None) -> ToolResult:
        """只换声音:保留真人画面,用提示词重新配音(替换音轨)"""
        source = str(params.get("source_video") or "").strip()
        if not source:
            return self._fail("视频换口播缺少源视频", "invalid_request")
        task_id = str(params.get("_task_id") or uuid.uuid4().hex)
        audio = await self._tts(params, task_id)
        if not audio:
            return self._fail("视频换口播需要提供口播提示词(或音频)", "invalid_request")
        if not compose.available():
            return self._fail("视频换口播需要 ffmpeg(容器未安装)", "invalid_request")
        workdir = tempfile.mkdtemp(prefix="render_voice_")
        try:
            local_src = await asyncio.to_thread(download_to_local, source, ".mp4")
            if not local_src:
                return self._fail("源视频下载失败", "request_error")
            out = os.path.join(workdir, "voice_only.mp4")
            result = await compose.run(
                compose.build_mix_audio_cmd(local_src, audio, out), timeout=600, cwd=workdir,
            )
            if not result.get("ok") or not os.path.exists(out):
                return self._fail(f"换声音合成失败: {result.get('stderr')}", "request_error")
            # 可选 B-roll 层:把素材叠到成片指定时间窗
            out = await self._maybe_broll(out, params, task_id, workdir)
            url = await asyncio.to_thread(upload_local_file, out, f"generate/result/render_voice_{task_id}.mp4")
            if not url:
                return self._fail("换声音成片转存失败", "request_error")
            return ToolResult(content=url, metadata={"success": True, "mode": "voice_only", "audio": audio})
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"换声音异常: {exc}", "request_error")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    async def _digital(self, params: dict, checkpoint: Optional[dict], on_stage=None) -> ToolResult:
        """数字人路线:生成数字人按提示词口播,再合成到源视频(满屏覆盖)或场景 B(作背景)"""
        task_id = str(params.get("_task_id") or uuid.uuid4().hex)
        # 复用数字人工具:把 route/digital_id 等 render 私有字段剔除,避免数字人网关收到未知字段。
        # motion 不在此剔除 —— 它是数字人网关自定义参数(parameters.motion)的动作控制意图,
        # 此前被 pop 丢弃导致「换动作」选项永远到不了网关,是个纯粹的死字段。
        digital_params = dict(params)
        for k in ("route", "source_video", "scene"):
            digital_params.pop(k, None)
        # 换场景+数字人组合:scene 作为数字人背景(场景 B)
        scene = str(params.get("scene") or "").strip()
        if scene and not digital_params.get("background"):
            digital_params["background"] = scene
        clip = await DigitalHumanTool().generate(digital_params, checkpoint=checkpoint, on_stage=on_stage)
        if not clip.metadata.get("success"):
            return clip
        # 未指定场景 B:数字人成片满屏覆盖到源视频(数字人进入场景 A 口播)
        if not scene:
            source = str(params.get("source_video") or "").strip()
            if source and compose.available():
                workdir = tempfile.mkdtemp(prefix="render_cover_")
                try:
                    local_src = await asyncio.to_thread(download_to_local, source, ".mp4")
                    local_clip = await asyncio.to_thread(download_to_local, clip.content, ".mp4")
                    if local_src and local_clip:
                        out = os.path.join(workdir, "cover.mp4")
                        result = await compose.run(
                            compose.build_cover_cmd(local_src, local_clip, out, audio_source="overlay"),
                            timeout=600, cwd=workdir,
                        )
                        if result.get("ok") and os.path.exists(out):
                            url = await asyncio.to_thread(
                                upload_local_file, out, f"generate/result/render_cover_{task_id}.mp4"
                            )
                            if url:
                                clip.content = url
                                clip.metadata["cover_applied"] = True
                        else:
                            logger.warning(f"[RenderTool] 满屏覆盖失败,保留数字人原片: {result.get('stderr')}")
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"[RenderTool] 满屏覆盖异常,保留数字人原片: {exc}")
                finally:
                    shutil.rmtree(workdir, ignore_errors=True)
        # 可选 B-roll 层:把素材叠到数字人成片指定时间窗(讲解到商品时切特写)
        if params.get("broll"):
            bw = tempfile.mkdtemp(prefix="render_broll_")
            try:
                local_clip = await asyncio.to_thread(download_to_local, clip.content, ".mp4")
                if local_clip:
                    out2 = await self._maybe_broll(local_clip, params, task_id, bw)
                    if out2 != local_clip and os.path.exists(out2):
                        url = await asyncio.to_thread(
                            upload_local_file, out2, f"generate/result/render_broll_{task_id}.mp4"
                        )
                        if url:
                            clip.content = url
                            clip.metadata["broll_applied"] = True
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[RenderTool] B-roll 叠加异常,保留数字人原片: {exc}")
            finally:
                shutil.rmtree(bw, ignore_errors=True)
        clip.metadata.setdefault("mode", "digital_human")
        return clip

    async def _scene_swap(self, params: dict, checkpoint: Optional[dict], on_stage=None) -> ToolResult:
        """换场景(保留真人):色键抠出绿幕真人 → 叠到场景 B → 用提示词重新配音"""
        source = str(params.get("source_video") or "").strip()
        scene = str(params.get("scene") or "").strip()
        if not source or not scene:
            return self._fail("换场景需要提供源视频与目标场景", "invalid_request")
        task_id = str(params.get("_task_id") or uuid.uuid4().hex)
        if not compose.available():
            return self._fail("换场景需要 ffmpeg(容器未安装)", "invalid_request")
        workdir = tempfile.mkdtemp(prefix="render_swap_")
        try:
            local_src = await asyncio.to_thread(download_to_local, source, ".mp4")
            local_scene = await asyncio.to_thread(download_to_local, scene, ".mp4")
            if not local_src or not local_scene:
                return self._fail("源视频或场景下载失败", "request_error")
            # 第一步:优先 AI 抠像(任意背景保留真人),不可用时降级绿幕色键
            swapped = os.path.join(workdir, "swapped.mp4")
            matte = await MattingTool().matte_video(local_src, task_id, params.get("_notify_url"), workdir)
            if matte.metadata.get("success"):
                # AI 抠像成功:RGBA 前景叠到场景 B(scale2ref 适配 + alpha 自然抠边)
                result = await compose.run(
                    compose.build_matte_overlay_cmd(matte.content, local_scene, swapped),
                    timeout=600, cwd=workdir,
                )
                matting_method = "ai"
            else:
                # 降级绿幕色键(未配置 AI 抠像网关 / 抠像失败),保留「没接 AI 也能出片」
                result = await compose.run(
                    compose.build_scene_swap_cmd(
                        local_src, local_scene, swapped,
                        color=str(params.get("matte_color") or "0x00FF00"),
                    ),
                    timeout=600, cwd=workdir,
                )
                matting_method = "chromakey"
                logger.warning(f"[RenderTool] AI 抠像不可用,降级绿幕色键: {matte.metadata.get('error')}")
            if not result.get("ok") or not os.path.exists(swapped):
                return self._fail(f"换场景合成失败: {result.get('stderr')}", "request_error")
            # 第二步:用提示词重新配音,替换音轨
            audio = await self._tts(params, task_id)
            if not audio:
                return self._fail("换场景需要提供口播提示词(或音频)", "invalid_request")
            out = os.path.join(workdir, "final.mp4")
            result = await compose.run(
                compose.build_mix_audio_cmd(swapped, audio, out), timeout=600, cwd=workdir,
            )
            if not result.get("ok") or not os.path.exists(out):
                return self._fail(f"换场景配音失败: {result.get('stderr')}", "request_error")
            # 可选 B-roll 层:把素材叠到成片指定时间窗
            out = await self._maybe_broll(out, params, task_id, workdir)
            url = await asyncio.to_thread(upload_local_file, out, f"generate/result/render_swap_{task_id}.mp4")
            if not url:
                return self._fail("换场景成片转存失败", "request_error")
            return ToolResult(
                content=url, metadata={"success": True, "mode": "scene_swap", "audio": audio, "matting": matting_method}
            )
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"换场景异常: {exc}", "request_error")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


__all__ = ["RenderTool"]
