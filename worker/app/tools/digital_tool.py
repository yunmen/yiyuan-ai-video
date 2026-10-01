# -*- coding: utf-8 -*-
'''
@文件    :digital_tool.py
@说明    :数字人口播生成工具(真实接入)— 数字人形象 + 口播音频 → 口型驱动视频
@时间    :2026/09/21 10:00:00
@作者    :一源AI
@版本    :1.0
@说明    :复用视频工具的「提交 + 轮询 + OSS 转存 + 断点续跑 + 网关故障转移」机制,
          差异只在请求体与模型:
            - 模型走数字人专用配置(DIGITAL_MODEL,管理端 gen.digital_model);
            - 请求体携带数字人形象图(image)与口播音频(audio);
            - 口播文案由 TTS 现场合成音频(或直接使用调用方传入的音频地址)。
          能力路由独立为 digital(管理端 gen.route.digital),未配置时回退媒体/文本网关。
          阶段划分与视频一致:1=口播音频就绪(可复用,避免重复合成);2=已提交外部任务;3=已取回原始直链。
'''
from typing import Optional

import asyncio
import os
import shutil
import tempfile
import uuid

from app.schemas.base import ToolResult
from app.tools.video_tool import VideoGenTool
from app.tools.audio_tool import AudioGenTool
from app.settings import config
from app.core.plugin import logger
from app.core import compose
from app.utils.oss import download_to_local, upload_local_file


class DigitalHumanTool(VideoGenTool):
    """数字人口播工具 — 数字人形象 + 口播音频,提交数字人模型并轮询成片。

    失败不抛异常(除网关异常),统一以 ToolResult.metadata.success=False 返回,
    由上层 service 转成 failed 回调(与其它工具一致)。

    支持两种形态:
      - 单段(默认):avatar + text/audio → 一条口型驱动视频;
      - 多段脚本(params.segments):逐段生成(每段一个镜头)后 ffmpeg 拼接成一条成片,
        切镜节奏由 Segment 边界驱动(pause-trim-jump-cuts);
      - 画中画(params.overlay):把(多段/单段)成片缩成小窗叠到背景视频之上(presenter-led-explainer)。
    """

    name = "digital"
    description = "数字人口播(形象+音频→口型驱动视频)"
    capability = "digital"

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        """数字人口播主流程。

        单段:校验 → 准备音频 → 提交模型 → 轮询成片。
        多段(params.segments):逐段走单段逻辑 → 拼接 →(可选)画中画叠加。
        注意:这里刻意不做 prompt 改写 —— 口播文案需要被逐字念出,改写会改变台词。
        """
        checkpoint = checkpoint or {}
        segments = params.get("segments") or []
        if segments and isinstance(segments, list):
            return await self._generate_multiseg(params, segments, on_stage)

        clip = await self._generate_clip(params, checkpoint, on_stage)
        if not clip.metadata.get("success"):
            return clip
        # 画中画:把单段成片叠到背景视频上(数字人缩窗,主讲声音独立连接)
        overlay = str(params.get("overlay") or "").strip()
        if overlay:
            piped = await self._apply_pip(clip.content, overlay, params.get("pip") or {}, params.get("_task_id"))
            if piped:
                clip.content = piped
                clip.metadata["pip_applied"] = True
        if clip.metadata.get("success"):
            clip.metadata["mode"] = "digital"
        return clip

    async def _generate_clip(self, params: dict, checkpoint: Optional[dict], on_stage=None) -> ToolResult:
        """单段数字人口播:校验 → 准备口播音频 → 提交模型 → 轮询成片。

        被单段与多段(每段)复用;params 需含 model/avatar/text/audio/voice/voice_reference 等。
        """
        checkpoint = checkpoint or {}
        stage = int(checkpoint.get("stage", 0) or 0)

        model = (params.get("model") or config.DIGITAL_MODEL or "").strip()
        if not model:
            return self._fail(
                "数字人口播未配置模型:请在管理端「业务配置」填写 gen.digital_model(数字人模型名)",
                "invalid_request",
            )

        avatar = str(params.get("avatar") or "").strip()
        if not avatar:
            return self._fail("数字人口播缺少数字人形象素材(avatar)", "invalid_request")

        script = str(params.get("text") or params.get("prompt") or "").strip()
        self.task_prefix = str(params.get("_task_id") or self.task_prefix)

        # 阶段1:准备口播音频 —— 优先复用断点;其次用调用方传入的音频;最后用文案现场合成
        audio = str(params.get("audio") or "").strip()
        if not audio and stage >= 1 and checkpoint.get("audio"):
            audio = str(checkpoint["audio"]).strip()
            logger.info("[DigitalHumanTool] 断点续跑:复用已合成口播音频")
        if not audio:
            if not script:
                return self._fail("数字人口播需要提供口播文案(text)或音频地址(audio)", "invalid_request")
            tts = await AudioGenTool().text_to_speech(
                text=script,
                voice=params.get("voice"),
                # 声纹复用:现成声纹样本地址 → 网关克隆音色,同一角色跨镜头/跨任务复用同一声音
                voice_reference=params.get("voice_reference"),
                task_id=self.task_prefix,
                notify_url=params.get("_notify_url"),
            )
            if not tts.metadata.get("success", True):
                return tts
            audio = str(tts.content or "").strip()
            if not audio:
                return self._fail("数字人口播失败:口播音频合成为空", "invalid_request")
            if on_stage:
                await on_stage(1, {"audio": audio})
            logger.info(
                f"[DigitalHumanTool] 口播音频就绪 tts={tts.metadata.get('model')} "
                f"voice={tts.metadata.get('voice')} voice_ref={bool(params.get('voice_reference'))}"
            )

        duration = self._clamp_duration(params.get("duration"))
        ratio = params.get("ratio") or config.VIDEO_RATIO
        resolution = params.get("resolution") or config.VIDEO_RESOLUTION

        # 主视图派生:底图可能是某个派生姿势,主图始终作为参考形象下发,
        # 放在 metadata.parameters(网关自定义参数区)—— 顶层加未知字段会被网关拒。
        reference = str(params.get("reference_image") or "").strip()
        parameters = {"resolution": resolution, "ratio": ratio, "duration": duration}
        if reference and reference != avatar:
            parameters["reference_image"] = reference
        # 背景/场景参考图:用户上传则透传给数字人网关(放在网关自定义参数区,顶层加未知字段会被网关拒)
        background = str(params.get("background") or "").strip()
        if background:
            parameters["background"] = background
        payload = {
            "model": model,
            "prompt": script or str(params.get("digital_name") or "数字人口播视频"),
            "image": avatar,
            "audio": audio,
            "seconds": str(duration),
            "metadata": {"parameters": parameters},
        }
        logger.info(
            f"[DigitalHumanTool] 提交数字人口播 model={model} duration={duration} "
            f"ratio={ratio} resolution={resolution} pose={params.get('pose') or '主视图'} "
            f"reference={'主图' if parameters.get('reference_image') else '无'}"
        )
        result = await self._submit_and_poll(
            payload, "数字人口播", duration, resolution, ratio, checkpoint=checkpoint, on_stage=on_stage,
        )
        if result.metadata.get("success"):
            result.metadata["digital_audio"] = audio
        return result

    async def _generate_multiseg(self, params: dict, segments: list, on_stage=None) -> ToolResult:
        """多段口播:逐段生成 → 拼接 →(可选)画中画。

        segments: [{text?, audio?, duration?}, ...];每段一个镜头,段边界驱动切镜。
        整段台词合并后写回 params["text"],供上层 BaseGenService 烧字幕(字幕跟随头部)。
        """
        if not compose.available():
            return self._fail("多段数字人口播需要 ffmpeg(容器未安装),无法拼接成片", "invalid_request")
        full_text = "，".join(
            str(s.get("text") or "").strip() for s in segments if str(s.get("text") or "").strip()
        )
        # 整段台词写回,确保字幕烧录能覆盖全部口播(单段已在 _generate_clip 内处理)
        params["text"] = full_text

        clips: list = []
        seg_durations: list = []
        for idx, seg in enumerate(segments):
            seg_params = dict(params)
            seg_params.pop("segments", None)
            seg_params.pop("overlay", None)
            seg_params.pop("pip", None)
            seg_text = str(seg.get("text") or "").strip()
            seg_audio = str(seg.get("audio") or "").strip()
            # 段时长:显式 duration 优先;否则按字数估算(中文约 4.5 字/秒),并夹在模型允许区间
            seg_duration = int(seg.get("duration") or 0) or self._estimate_duration(seg_text)
            seg_params["text"] = seg_text
            seg_params["audio"] = seg_audio
            seg_params["duration"] = seg_duration
            logger.info(f"[DigitalHumanTool] 多段 第{idx + 1}/{len(segments)}段 文案={seg_text[:20]}… duration={seg_duration}")
            clip = await self._generate_clip(seg_params, {}, on_stage)
            if not clip.metadata.get("success"):
                return clip
            clips.append(clip.content)
            seg_durations.append(seg_duration)

        merged = await self._concat_clips(clips)
        if not merged:
            return self._fail("多段数字人口播拼接失败(ffmpeg 执行异常)", "request_error")
        # 画中画:把整条成片缩窗叠到背景视频上
        overlay = str(params.get("overlay") or "").strip()
        if overlay:
            piped = await self._apply_pip(merged, overlay, params.get("pip") or {}, params.get("_task_id"))
            if piped:
                merged = piped
        return ToolResult(
            content=merged,
            metadata={
                "success": True, "mode": "digital", "segments": len(clips),
                "seg_durations": seg_durations, "pip_applied": bool(overlay and merged),
            },
        )

    def _estimate_duration(self, text: str, chars_per_sec: float = 4.5) -> int:
        """按字数估算单段口播时长(秒),夹在模型允许区间 [3, 15]。

        数字人模型单次生成上限约 15s;低于 3s 生成不出有意义内容。
        """
        chars = len(str(text or "").strip())
        if chars <= 0:
            return 8
        secs = max(3, min(15, int(round(chars / chars_per_sec))))
        return self._clamp_duration(secs)

    async def _concat_clips(self, clip_urls: list) -> Optional[str]:
        """把多段成片下载本地 → concat 拼接 → 上传 OSS,返回新 URL;任何失败返回 None。"""
        if not clip_urls:
            return None
        if len(clip_urls) == 1:
            return clip_urls[0]
        workdir = tempfile.mkdtemp(prefix="digital_multiseg_")
        try:
            local_paths: list = []
            for i, url in enumerate(clip_urls):
                local = await asyncio.to_thread(download_to_local, url, ".mp4")
                if not local:
                    logger.warning(f"[DigitalHumanTool] 多段拼接下载失败 第{i + 1}段 {url}")
                    return None
                local_paths.append(local)
            list_name = "concat.txt"
            list_path = os.path.join(workdir, list_name)
            # concat demuxer 要求相对文件名(见 compose.build_concat_cmd 的 Windows 冒号说明)
            with open(list_path, "w", encoding="utf-8") as f:
                f.write(compose.build_concat_list([os.path.basename(p) for p in local_paths]))
            out_path = os.path.join(workdir, "merged.mp4")
            # 段数 ≥ 2 且相邻参数一致时流复制拼接(秒级);xfade 需重编码,这里用硬切(跳切)更符合 talking-head 节奏
            result = await compose.run(
                compose.build_concat_cmd(list_name, out_path), timeout=600, cwd=workdir,
            )
            if not result.get("ok") or not os.path.exists(out_path):
                logger.warning(f"[DigitalHumanTool] 多段拼接失败: {result.get('stderr')}")
                return None
            key = f"generate/result/digital_multiseg_{uuid.uuid4().hex[:8]}.mp4"
            new_url = await asyncio.to_thread(upload_local_file, out_path, key)
            return new_url
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[DigitalHumanTool] 多段拼接异常: {exc}")
            return None
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    async def _apply_pip(self, digital_url: str, bg_url: str, pip: dict, task_id=None) -> Optional[str]:
        """画中画:把数字人成片缩窗叠到背景视频上;失败返回 None(保留原成片)。

        增强能力,绝不为「加画中画」把一次已付费的生成变成失败任务。
        """
        if not compose.available():
            logger.info("[DigitalHumanTool] 跳过画中画:ffmpeg 不可用")
            return None
        workdir = tempfile.mkdtemp(prefix="digital_pip_")
        try:
            local_digital = await asyncio.to_thread(download_to_local, digital_url, ".mp4")
            local_bg = await asyncio.to_thread(download_to_local, bg_url, ".mp4")
            if not local_digital or not local_bg:
                return None
            scale = float(pip.get("scale") or 0.3)
            position = str(pip.get("position") or "br")
            out_path = os.path.join(workdir, "pip.mp4")
            result = await compose.run(
                compose.build_pip_cmd(local_bg, local_digital, out_path, scale=scale, position=position),
                timeout=600, cwd=workdir,
            )
            if not result.get("ok") or not os.path.exists(out_path):
                logger.warning(f"[DigitalHumanTool] 画中画叠加失败,保留原成片: {result.get('stderr')}")
                return None
            key = f"generate/result/digital_pip_{uuid.uuid4().hex[:8]}.mp4"
            return await asyncio.to_thread(upload_local_file, out_path, key)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[DigitalHumanTool] 画中画异常,保留原成片: {exc}")
            return None
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


__all__ = ["DigitalHumanTool"]
