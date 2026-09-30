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

    @staticmethod
    def _empty_result(reason: str, duration: Optional[float] = None) -> ToolResult:
        """构造「空分镜」成功结果:拆解是增强能力,任一环节失败都不让任务失败。

        除 result_text 的 JSON 串外,同时把失败原因结构化回写 usage 的
        `deconstruct_reason`(空分镜场景下 shots/shot_prompts 显式给空列表)——
        否则后端只能从一段 JSON 文本里猜失败原因,失败率无法统计,
        前端也难以区分「没检测到镜头」与「逆推整个挂了」。
        """
        payload: Dict[str, Any] = {"shots": [], "reason": reason}
        if duration:
            payload["duration"] = round(float(duration), 2)
        return ToolResult(
            content=json.dumps(payload),
            metadata={
                "success": True,
                "shot_count": 0,
                # 空列表显式回写:语义是「本次拆解没有产出镜头」,而不是「未执行拆解」
                "shots": [],
                "shot_prompts": [],
                "deconstruct_reason": reason,
            },
        )

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
            return self._empty_result("missing_reference")

        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            logger.warning("[VideoUnderstandTool] ffmpeg 不可用,跳过拆解(容器需安装 ffmpeg)")
            return self._empty_result("ffmpeg_unavailable")

        cleanup: List[str] = []
        local = None
        try:
            local = await asyncio.to_thread(download_to_local, reference_video, suffix=".mp4")
            if not local:
                logger.warning("[VideoUnderstandTool] 对标视频下载失败,返回空分镜")
                return self._empty_result("download_failed")

            duration = float(duration_hint) if duration_hint else await _probe_duration_async(local, ffmpeg)
            if duration <= 0:
                # 探不到时长无法构分镜表,回退空分镜(不阻断)
                logger.warning("[VideoUnderstandTool] 无法探知时长,返回空分镜")
                return self._empty_result("unknown_duration")

            # ① 镜头边界检测 → 分镜表
            shot_table = await shots.detect_shots(local, duration)
            if not shot_table:
                logger.info("[VideoUnderstandTool] 未检测到镜头边界,返回空分镜(回退按秒切分由前端决定)")
                return self._empty_result("no_shots", duration)

            # ② 原片台词归集(依赖词级 ASR,关闭时 narration 留空,不报错)
            shot_table = await shots.narrate_shots(local, shot_table)

            # ③ 逐镜头取帧点(开始帧 + 结束帧)
            targets = shots.analysis_targets(shot_table, limit=shots.MAX_ANALYSIS_SHOTS)
            if not targets:
                return self._empty_result("no_targets", duration)

            # ④ 抽帧(本地,不上传 OSS)
            times: List[float] = []
            for row in targets:
                times.extend(row.get("times") or [])
            frames = await self._extract_local_frames(ffmpeg, local, times, cleanup)
            if len(frames) != len(times):
                logger.warning("[VideoUnderstandTool] 抽帧不完整,放弃逐镜头逆推,返回空分镜")
                return self._empty_result("frame_extract_failed", duration)

            # ⑤ 逐镜头多模态逆推(画面/运镜描述)
            # 复刻目标形态(可选):与生成建单同源,保证"理解原片"与"重塑出片"用同一个形态
            fmt = str((params or {}).get("format") or "").strip()
            # 创意档位/钩子强化(可选):同样与生成建单同源 —— 若拆解按"忠实复刻"写描述、
            # 实际按"爆款改造"出片,用户看到的分镜描述就不再是成片的依据。
            creative_level = str((params or {}).get("creative_level") or "").strip()
            hook_boost = str((params or {}).get("hook_boost") or "").strip()
            # 专家模式追加的创作要求(asset_override):同样与生成建单同源,
            # 否则拆解分镜不体现该要求,用户"看了分镜觉得没问题、出片却多了/少了要求"。
            asset_override = str((params or {}).get("asset_override") or "").strip()
            descriptions = await self._reverse_shots(
                targets, frames, intent, fmt=fmt,
                creative_level=creative_level, hook_boost=hook_boost,
                asset_override=asset_override,
            )
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
            # 结构化回写:backend 的 storyboard.persist_from_usage 直接消费 shots/shot_prompts,
            # 把拆解结果沉淀为 tb_episode/tb_shot(可查询/可编辑/可喂给局部重跑),
            # 而不是只活在 result_text 的一段 JSON 里 —— 后者无法做分镜级编辑与统计。
            # 逆推是逐镜头增强,允许部分成功:未逆推出的镜头仍保留结构,description 为空。
            missing = len(storyboard["shots"]) - len(desc_map)
            metadata: Dict[str, Any] = {
                "success": True,
                "shot_count": len(storyboard["shots"]),
                "shots": [
                    {
                        "index": item["index"],
                        "start": item["start"],
                        "end": item["end"],
                        "duration": item["duration"],
                        "narration": str(item.get("narration") or ""),
                    }
                    for item in storyboard["shots"]
                ],
                "shot_prompts": [
                    {"index": item["index"], "prompt": item["description"]}
                    for item in storyboard["shots"] if str(item.get("description") or "").strip()
                ],
                # 成功时为空串:与空分镜分支的 deconstruct_reason 同字段,后端/前端只需判断一个字段
                "deconstruct_reason": "",
                "reference_video": reference_video,
                "duration": round(duration, 2),
            }
            # 「小白方案建议」:用户不调参时,按原片结构 + 一句话目标给出推荐值与一句人话解释,
            # 随 usage 回写。前端只做展示/预填,不要求用户理解"创意档位"这类术语。
            metadata["plan"] = self._suggest_plan(storyboard["shots"], duration, params)
            if missing > 0:
                # 部分镜头没逆推出描述(模型漏项/网关限流)不是失败,但必须让用户知道哪些镜头要自己补
                metadata["deconstruct_note"] = (
                    f"{missing} 个镜头未生成逆推描述(可手动补充或直接生成),"
                    "其余镜头已按原片结构拆解完成"
                )
                logger.warning(
                    f"[VideoUnderstandTool] 逆推部分缺失 task={storyboard.get('reference_video')}: "
                    f"{missing}/{len(storyboard['shots'])} 个镜头无描述"
                )
            return ToolResult(
                content=json.dumps(storyboard, ensure_ascii=False),
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001
            # 拆解是增强能力:异常也返回成功态的空分镜,绝不让任务失败
            logger.error(f"[VideoUnderstandTool] 拆解异常,回退空分镜: {exc}")
            return self._empty_result("exception")
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

    @staticmethod
    def _suggest_plan(
        shot_rows: List[Dict[str, Any]], duration: float, params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """按原片结构与用户目标给出「推荐方案」(只补用户没指定的旋钮)

        面向"只上传素材"的小白:不要求理解档位,由系统给出默认值与一句人话解释。
        刻意保持规则简单可读 —— 结构类改动(形态)只在用户明确说出口时才给,
        否则一律沿用原片结构,避免"用户没说要改短剧,却被改成短剧"。

        返回 {values:{...}, reason:str}:values 里的键只覆盖"用户未指定"的旋钮。
        """
        params = params or {}
        rows = shot_rows or []
        goal = str(params.get("goal") or "").strip()
        narrated = sum(1 for r in rows if str(r.get("narration") or "").strip())
        values: Dict[str, Any] = {}
        # 形态:仅在用户一句话目标里点名了某种结构时才推荐,否则沿用原片
        format_keywords = (
            ("口播", "talking_head"), ("短剧", "short_drama"), ("剧情", "short_drama"),
            ("街采", "street_interview"), ("采访", "street_interview"),
            ("播客", "two_person_podcast"), ("对谈", "two_person_podcast"),
            ("榜单", "ranking_listicle"), ("盘点", "ranking_listicle"), ("排行", "ranking_listicle"),
            ("旁白", "narration_led_demo"), ("演示", "narration_led_demo"), ("教程", "narration_led_demo"),
            ("讲解", "presenter_led_explainer"),
        )
        if not str(params.get("replicate_format") or params.get("format") or "").strip():
            for word, fmt in format_keywords:
                if word in goal:
                    values["format"] = fmt
                    break
        # 主角表现:只有用户明确提到"跳舞/律动/推广/种草"时才给
        if not str(params.get("lead_act") or "").strip():
            if any(w in goal for w in ("跳舞", "律动", "舞蹈")):
                values["lead_act"] = "dance"
            elif any(w in goal for w in ("推广", "种草", "带货")):
                values["lead_act"] = "pitch"
        # 效果类旋钮:用户没指定时给「适度改造 + 强化开头」——
        # 短视频留存高度依赖开头,而完全照搬原片又让复刻失去价值
        if not str(params.get("creative_level") or "").strip():
            values["creative_level"] = "creative"
        if not str(params.get("hook_boost") or "").strip():
            values["hook_boost"] = "strong"
        # 人话解释:让前端能告诉用户"系统为什么这么定",而不是甩一个参数名
        if narrated >= 2:
            base = f"原片有 {len(rows)} 个镜头、{narrated} 段台词,属于讲解型内容"
        elif len(rows) >= 8:
            base = f"原片切了 {len(rows)} 个镜头,节奏偏快"
        else:
            base = f"原片共 {len(rows)} 个镜头" + (f"、时长约 {duration:.0f} 秒" if duration else "")
        extra = "已按你说的方式调整" if goal else "保持原片结构,适度增强开头"
        return {"values": values, "reason": f"{base};{extra}。"}

    async def _reverse_shots(
        self, targets: List[Dict[str, Any]], frames: List[str], intent: List[str],
        fmt: str = "", creative_level: str = "", hook_boost: str = "", asset_override: str = "",
    ) -> Dict[int, str]:
        """逐镜头逆推(P0-3):读原片每个镜头的画面 → 该镜头的画面与运镜描述

        fmt 为复刻目标形态(短剧/口播/街采/…),非空时逆推会按该形态组织画面与运镜,
        而不是照抄原片结构;为空则与历史行为一致。

        creative_level 为创意档位,决定注入哪一组方法论资产:
        空值=沿用改造前的全量注入,faithful=只描述原片事实不主动改写;
        hook_boost=strong 时额外要求首镜产出钩子式描述。

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
        system_prompt = build_shot_reverse_prompt(
            len(targets), intent, _FRAMES_PER_SHOT, fmt=fmt,
            creative_level=creative_level, hook_boost=hook_boost,
            asset_override=asset_override,
        )
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
