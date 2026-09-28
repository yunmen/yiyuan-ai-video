# -*- coding: utf-8 -*-
'''
@文件    :video_understand_tool.py
@说明    :对标视频拆解工具(带货视频复刻前置)— 把对标视频逆向拆成结构化分镜 JSON
@时间    :2026/09/27 15:00:00
@作者    :一源AI
@版本    :1.0
@说明    :与 video_tool 的「生成」不同,本工具只做「看懂原片」:
            ① ffmpeg 场景检测 → 分镜表(shots.detect_shots);
            ② 原片台词归集(shots.narrate_shots, 依赖词级 ASR, 关闭时留空);
            ③ 逐镜头取帧点(shots.analysis_targets) → compose 抽帧;
            ④ 多模态逆推每个镜头的画面/运镜描述(build_shot_reverse_prompt + parse_shot_prompts)。
          返回 JSON 字符串,由 BaseGenService 经 result_text 回写,前端轮询展示并可编辑。
          任何一步失败都返回空分镜(success=True),绝不把分析失败当成任务失败。
'''
import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core import compose, gateway, shots
from app.core.plugin import logger
from app.schemas.base import ToolResult
from app.settings import config
from app.tools.base import BaseGenTool
from app.utils.oss import download_to_local
from skills.prompt_library import build_shot_reverse_prompt, parse_shot_prompts

# 逆推送多模态模型的画面宽度(px):看清景别/主体即可,原分辨率放大 token 收益极小
_SHOT_FRAME_WIDTH = 512
# 每个镜头取「开始帧 + 结束帧」两张,只给一帧推不出运镜
_FRAMES_PER_SHOT = 2
# 单镜头逆推 chat 超时(秒)
_CHAT_TIMEOUT = 90
# 探时长超时(秒)
_PROBE_TIMEOUT = 60


async def _probe_duration_async(source: str, ffmpeg: str) -> float:
    """用 ffmpeg -i 解析视频时长(秒);解析不到返回 0.0

    ffmpeg -i 在未指定输出时会以非零退出,但仍会把 `Duration: 00:00:30.12` 打到 stderr,
    因此这里不依赖命令成功与否,只从 stderr 里抓时长。
    """
    result = await compose.run([ffmpeg, "-i", source], timeout=_PROBE_TIMEOUT, truncate=False)
    text = f"{result.get('stderr') or ''}\n{result.get('stdout') or ''}"
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        logger.warning(f"[VideoUnderstandTool] 未能从 ffmpeg 输出解析出时长: {source}")
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _to_data_url(path: str) -> str:
    """本地图片 → base64 data URL(内联进多模态请求,避免为分析再上传一次 OSS)"""
    import base64
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
    with open(path, "rb") as fp:
        b64 = base64.b64encode(fp.read()).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def _vision_messages(system_prompt: str, content: List[dict]) -> List[dict]:
    """组装多模态消息:系统提示 + 「文字 + 内联图片」的用户消息"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]


class VideoUnderstandTool(BaseGenTool):
    """对标视频拆解工具:生成结构化分镜 JSON(增强能力,失败回退空分镜)"""

    name = "video_understand"
    capability = "video"

    def __init__(self, **kwargs):
        # 复用 video 能力的网关配置(拆解与视频同供应商体系),chat 逆推单独解析
        gw = gateway.resolve(self.capability)
        self.api_key = kwargs.get("api_key") or gw.get("key") or config.LLM_BASE_API_KEY
        self.base_url = (kwargs.get("base_url") or gw.get("url") or "").rstrip("/")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate(
        self,
        params: dict,
        checkpoint: Optional[dict] = None,
        on_stage: Any = None,
    ) -> ToolResult:
        reference_video = (params or {}).get("reference_video") or ""
        intent = (params or {}).get("intent") or []
        duration_hint = (params or {}).get("duration")
        if not reference_video:
            logger.warning("[VideoUnderstandTool] 缺少对标视频地址,返回空分镜")
            return ToolResult(content=json.dumps({"shots": [], "reason": "missing_reference"}), metadata={"success": True, "shot_count": 0})

        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            logger.warning("[VideoUnderstandTool] ffmpeg 不可用,跳过拆解(容器需安装 ffmpeg)")
            return ToolResult(content=json.dumps({"shots": [], "reason": "ffmpeg_unavailable"}), metadata={"success": True, "shot_count": 0})

        cleanup: List[str] = []
        local = None
        try:
            local = await asyncio.to_thread(download_to_local, reference_video, suffix=".mp4")
            if not local:
                logger.warning("[VideoUnderstandTool] 对标视频下载失败,返回空分镜")
                return ToolResult(content=json.dumps({"shots": [], "reason": "download_failed"}), metadata={"success": True, "shot_count": 0})

            duration = float(duration_hint) if duration_hint else await _probe_duration_async(local, ffmpeg)
            if duration <= 0:
                # 探不到时长无法构分镜表,回退空分镜(不阻断)
                logger.warning("[VideoUnderstandTool] 无法探知时长,返回空分镜")
                return ToolResult(content=json.dumps({"shots": [], "reason": "unknown_duration"}), metadata={"success": True, "shot_count": 0})

            # ① 镜头边界检测 → 分镜表
            shot_table = await shots.detect_shots(local, duration)
            if not shot_table:
                logger.info("[VideoUnderstandTool] 未检测到镜头边界,返回空分镜(回退按秒切分由前端决定)")
                return ToolResult(content=json.dumps({"shots": [], "duration": duration, "reason": "no_shots"}), metadata={"success": True, "shot_count": 0})

            # ② 原片台词归集(依赖词级 ASR,关闭时 narration 留空,不报错)
            shot_table = await shots.narrate_shots(local, shot_table)

            # ③ 逐镜头取帧点(开始帧 + 结束帧)
            targets = shots.analysis_targets(shot_table, limit=shots.MAX_ANALYSIS_SHOTS)
            if not targets:
                return ToolResult(content=json.dumps({"shots": [], "duration": duration, "reason": "no_targets"}), metadata={"success": True, "shot_count": 0})

            # ④ 抽帧(本地,不上传 OSS)
            times: List[float] = []
            for row in targets:
                times.extend(row.get("times") or [])
            frames = await self._extract_local_frames(ffmpeg, local, times, cleanup)
            if len(frames) != len(times):
                logger.warning("[VideoUnderstandTool] 抽帧不完整,放弃逐镜头逆推,返回空分镜")
                return ToolResult(content=json.dumps({"shots": [], "duration": duration, "reason": "frame_extract_failed"}), metadata={"success": True, "shot_count": 0})

            # ⑤ 逐镜头多模态逆推(画面/运镜描述)
            descriptions = await self._reverse_shots(targets, frames, intent)
            # 把逆推描述并回原分镜表(按 index 对齐)
            desc_map = {idx: desc for idx, desc in descriptions.items()}
            storyboard = {
                "reference_video": reference_video,
                "duration": round(duration, 2),
                "shots": [
                    {
                        "index": item["index"],
                        "start": item["start"],
                        "end": item["end"],
                        "duration": item["duration"],
                        "narration": str(item.get("narration") or ""),
                        "description": desc_map.get(item["index"], ""),
                    }
                    for item in shot_table
                ],
            }
            logger.info(f"[VideoUnderstandTool] 拆解完成: {len(storyboard['shots'])} 个镜头,其中 {len(desc_map)} 个有逆推描述")
            if on_stage is not None:
                try:
                    await on_stage(1, {"stage": "deconstructed"})
                except Exception:  # noqa: BLE001
                    pass
            return ToolResult(
                content=json.dumps(storyboard, ensure_ascii=False),
                metadata={"success": True, "shot_count": len(storyboard["shots"])},
            )
        except Exception as exc:  # noqa: BLE001
            # 拆解是增强能力:异常也返回成功态的空分镜,绝不让任务失败
            logger.error(f"[VideoUnderstandTool] 拆解异常,回退空分镜: {exc}")
            return ToolResult(content=json.dumps({"shots": [], "reason": "exception"}), metadata={"success": True, "shot_count": 0})
        finally:
            for path in cleanup:
                try:
                    os.remove(path)
                except OSError:
                    pass
            if local and local != reference_video:
                try:
                    os.remove(local)
                except OSError:
                    pass

    async def _extract_local_frames(
        self, ffmpeg: str, video: str, times: List[float], cleanup: List[str],
    ) -> List[str]:
        """按时间点抽帧到本地(不上传 OSS),供多模态请求内联图片使用

        数量必须完整:少一张会让「图片顺序 ↔ 镜头序号」错位,因此任何一张失败都返回空列表。
        """
        paths: List[str] = []
        workdir = os.path.dirname(video) or "."
        for idx, at in enumerate(times):
            out = os.path.join(workdir, f"understand_{idx}.jpg")
            result = await compose.run(
                compose.build_extract_frame_cmd(video, out, at, _SHOT_FRAME_WIDTH, ffmpeg), timeout=120,
            )
            if not result.get("ok") or not os.path.exists(out):
                logger.warning(f"[VideoUnderstandTool] 抽帧失败(第 {idx + 1}/{len(times)} 张),放弃逆推")
                return []
            paths.append(out)
            cleanup.append(out)
        return paths

    async def _reverse_shots(
        self, targets: List[Dict[str, Any]], frames: List[str], intent: List[str],
    ) -> Dict[int, str]:
        """逐镜头逆推(P0-3):读原片每个镜头的画面 → 该镜头的画面与运镜描述

        返回 {镜头序号: 描述};任何一步失败返回空字典(逆推是增强能力,不应让拆解失败)。
        """
        if not targets or not frames:
            return {}
        indexes = [row["index"] for row in targets]
        # 组装用户消息:每个镜头一段文字(序号/时长/原片台词)紧跟该镜头的 2 张帧
        content: List[dict] = []
        fi = 0
        for row in targets:
            content.append({
                "type": "text",
                "text": (
                    f"镜头{row['index']}: 时长{row['duration']}秒; "
                    f"原片台词: {row.get('narration') or '(无)'}"
                ),
            })
            for _ in range(_FRAMES_PER_SHOT):
                if fi < len(frames):
                    # detail=low:512px 抽帧已够看清景别/主体,低细节省 token 且兼容性更好
                    content.append({"type": "image_url", "image_url": {"url": _to_data_url(frames[fi]), "detail": "low"}})
                    fi += 1
        system_prompt = build_shot_reverse_prompt(len(targets), intent, _FRAMES_PER_SHOT)
        # 视觉逆推必须走「支持 image_url 的视觉模型」,而非纯文本 chat 模型(否则网关 400 拒收图片)。
        # 未配置 VISION_MODEL 时直接跳过并给出明确日志,避免反复刷 400 错误。
        if not getattr(config, "VISION_MODEL", ""):
            logger.warning(
                "[VideoUnderstandTool] 未配置 VISION_MODEL(视觉模型),跳过逐镜头逆推,将产生无描述的空分镜;"
                "请在 settings 配置支持 image_url 的视觉模型(如 qwen2.5-vl-max),并用 gen.route.vision 指向其网关"
            )
            return {}
        model = config.VISION_MODEL
        candidates = gateway.resolve_all("vision") or [{
            "name": "env",
            "url": (config.LLM_BASE_API_URL or config.CHAT_LLM_BASE_URL).rstrip("/"),
            "key": config.LLM_BASE_API_KEY or config.CHAT_LLM_API_KEY,
            "proto": "openai",
        }]
        last_exc: Optional[Exception] = None
        for gw in candidates:
            try:
                client = AsyncOpenAI(
                    api_key=gw.get("key") or self.api_key,
                    base_url=(gw.get("url") or self.base_url).rstrip("/"),
                )
                resp = await client.chat.completions.create(
                    model=model,
                    messages=_vision_messages(system_prompt, content),
                    timeout=_CHAT_TIMEOUT,
                )
                text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
                if not text:
                    continue
                parsed = parse_shot_prompts(text, indexes)
                if parsed:
                    logger.info(f"[VideoUnderstandTool] 逐镜头逆推完成: {len(parsed)}/{len(indexes)} 个镜头")
                    return parsed
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
        logger.warning(f"[VideoUnderstandTool] 逐镜头逆推失败: {last_exc}")
        return {}
