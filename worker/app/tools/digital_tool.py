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

from app.schemas.base import ToolResult
from app.tools.video_tool import VideoGenTool
from app.tools.audio_tool import AudioGenTool
from app.settings import config
from app.core.plugin import logger


class DigitalHumanTool(VideoGenTool):
    """数字人口播工具 — 数字人形象 + 口播音频,提交数字人模型并轮询成片。

    失败不抛异常(除网关异常),统一以 ToolResult.metadata.success=False 返回,
    由上层 service 转成 failed 回调(与其它工具一致)。
    """

    name = "digital"
    description = "数字人口播(形象+音频→口型驱动视频)"
    capability = "digital"

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        """数字人口播主流程:校验入参 → 准备口播音频 → 提交数字人模型 → 轮询成片。

        注意:这里刻意不做 prompt 改写 —— 口播文案需要被逐字念出,改写会改变台词。
        """
        checkpoint = checkpoint or {}
        stage = int(checkpoint.get("stage", 0) or 0)

        model = (params.get("model") or config.DIGITAL_MODEL or "").strip()
        if not model:
            return self._fail(
                "数字人口播未配置模型:请在管理端「业务配置」填写 gen.digital_model(数字人模型名)",
                "invalid_request",
            )
        # 方舟原生协议已支持:形象图以 reference_image 下发、口播音频以 audio_url 下发
        # (见 VideoGenTool._ark_body)。此前这里直接拒绝,导致把 gen.route.digital
        # 指向方舟时功能整体不可用 —— 与"能力可用性"目标冲突。

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
                task_id=self.task_prefix,
                # P2:传回调地址,让 TTS 能命中资产缓存(文案未变则零合成调用)
                notify_url=params.get("_notify_url"),
            )
            if not tts.metadata.get("success", True):
                return tts
            audio = str(tts.content or "").strip()
            if not audio:
                return self._fail("数字人口播失败:口播音频合成为空", "invalid_request")
            if on_stage:
                await on_stage(1, {"audio": audio})
            logger.info(f"[DigitalHumanTool] 口播音频就绪 tts={tts.metadata.get('model')} voice={tts.metadata.get('voice')}")

        duration = self._clamp_duration(params.get("duration"))
        ratio = params.get("ratio") or config.VIDEO_RATIO
        resolution = params.get("resolution") or config.VIDEO_RESOLUTION

        # 主视图派生:底图可能是某个派生姿势,主图始终作为参考形象下发,
        # 放在 metadata.parameters(网关自定义参数区)—— 顶层加未知字段会被网关拒。
        reference = str(params.get("reference_image") or "").strip()
        parameters = {"resolution": resolution, "ratio": ratio, "duration": duration}
        if reference and reference != avatar:
            parameters["reference_image"] = reference
        # 背景/场景参考图:用户上传则透传给数字人网关(放在网关自定义参数区,
        # 顶层加未知字段会被网关拒 —— 与 reference_image 同处理)。
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
            result.metadata["mode"] = "digital"
            result.metadata["digital_audio"] = audio
        return result


__all__ = ["DigitalHumanTool"]
