# -*- coding: utf-8 -*-
'''
@文件    :element_detect.py
@说明    :对标视频「原片元素槽位」检测(带货视频复刻增强)。
          把原片里可替换的视觉元素(人物 / 产品 / 场景)按类识别出来,
          供前端让用户把上传的替换图精确绑定到「原片具体哪个元素」,
          避免多人/多物视频里"换错人、换错货"的错位。
          纯增强能力:任何一步失败都返回空列表,绝不阻断复刻。
          视觉识别走 worker 既有命名网关(ai_vision.vision_chat),与参考图识别同源。
@时间    :2026/10/02
@作者    :一源AI
@版本    :1.0
'''
import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

from app.core.plugin import logger
from app.core import compose, shots
from app.utils.oss import download_to_local, upload_local_file
from app.services.ai_vision import vision_chat

# 元素类别与展示名(与替换意图 intent 的维度保持一致)
ELEMENT_KINDS = ("person", "product", "scene")
KIND_LABELS = {"person": "人物", "product": "产品", "scene": "场景"}
# 抽帧数:覆盖原片主要变化即可,过多 token 收益极小
_MAX_FRAMES = 6
_FRAME_WIDTH = 480


# 元素检测提示词:要求模型按帧列出可替换元素,给出类别 + 外观描述 + 首次出现帧序号,
# 并尽量给出「空间定位(bbox)」与「时间跨度(start/end)」,把绑定从"某类角色"精确到
# "原片具体哪个对象、出现在哪段"——多人/多物视频换错人/换错货的治本信息。
# bbox/start/end 为尽力而为的可选字段:模型给不出就返回 null/0,解析层会安全忽略,不影响绑定。
ELEMENT_PROMPT = (
    "这是一段带货/种草视频的若干帧截图(按时间先后排列,帧序号从 0 开始)。\n"
    "请识别视频中可替换的视觉元素,按类别分组列出:**人物(person)、产品(product)、场景(scene)**。\n"
    "对每一个元素给出:\n"
    "  - kind: 类别(person / product / scene)\n"
    "  - label: 一句话外观描述(不超过 24 字,客观具体:如「戴眼镜的男士」「红色易拉罐饮料」「咖啡馆室内」)\n"
    "  - frame_index: 它**首次清晰出现**的帧序号(整数,从 0 开始)\n"
    "  - bbox: 该元素在「首次出现帧」里的归一化包围盒,格式 [x1, y1, x2, y2](四个 0~1 浮点数,"
    "相对整帧宽高,左上角为原点);无法确定时返回 null\n"
    "  - observations: 列出该元素在所有截图中实际可见的记录，每项含 frame_index 和该帧 bbox。不可见帧不要列出。\n"
    "同一主体跨帧再次出现须归入同一元素的 observations；同类但外观不同的主体必须分开，无法确认同一身份时不要强行合并。\n"
    "不要从抽帧推断连续出现时间或填充离场空档；未知 start/end 返回 null。\n"
    '只输出一个 JSON 对象:{"elements":['
    '{"kind":"...","label":"...","frame_index":0,"bbox":[0.1,0.2,0.5,0.8],"start":0,"end":10}, ...]}\n'
    "没有某类元素就不在数组里出现;描述要客观、区分度高(多人时加上衣着/发型/位置差异),便于用户逐一对应。"
)


def _uuid() -> str:
    import uuid as _uuid_mod
    return _uuid_mod.uuid4().hex


async def detect_elements(reference_video: str) -> Optional[List[Dict[str, Any]]]:
    """返回元素列表；执行失败返回 None，与成功识别零元素明确区分。"""
    if not reference_video:
        return None
    ffmpeg = compose.ffmpeg_path()
    if not ffmpeg:
        logger.warning("原片元素解析失败：ffmpeg 不可用")
        return None
    cleanup: List[str] = []
    local = None
    try:
        local = await asyncio.to_thread(download_to_local, reference_video, suffix=".mp4")
        if not local:
            logger.warning("原片元素解析失败：视频下载失败")
            return None
        duration = await _probe_duration(local, ffmpeg)
        if duration <= 0:
            return None
        shot_table = await shots.detect_shots(local, duration)
        times = shots.shot_frame_times(shot_table, per_shot=2, limit=12) or _sample_times(duration)
        frames = await _extract_frames(ffmpeg, local, times, cleanup)
        if not frames:
            return None
        # 上传帧到 OSS 得到公开 URL(视觉模型可直接读取);任一张失败则该帧留空,最后整体仍需至少一张可用
        frame_urls: List[Optional[str]] = []
        for p in frames:
            try:
                frame_urls.append(await asyncio.to_thread(
                    upload_local_file, p, f"element_frames/{_uuid()}.jpg"))
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[element_detect] 帧上传失败: {exc}")
                frame_urls.append(None)
        if not any(frame_urls):
            return None
        raw = await _recognize(frame_urls, times)
        match = re.search(r"\{.*\}", raw or "", re.S)
        parsed = json.loads(match.group(0)) if match else None
        if not isinstance(parsed, dict) or not isinstance(parsed.get("elements"), list):
            return None
        elements = _parse_elements(raw, times, frame_urls, duration, shot_table)
        logger.info(f"[element_detect] 原片元素检测完成: {len(elements)} 个")
        return elements
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"原片元素解析失败，异常类型：{type(exc).__name__}")
        return None
    finally:
        for p in cleanup:
            try:
                os.remove(p)
            except OSError:
                pass
        if local and local != reference_video:
            try:
                os.remove(local)
            except OSError:
                pass


def _sample_times(duration: float) -> List[float]:
    """在原片里均匀取若干抽帧时间点(秒);过短的视频至少取 3 个点"""
    n = max(3, min(_MAX_FRAMES, max(3, int(duration // 5) + 1)))
    n = min(n, _MAX_FRAMES)
    if duration <= 0:
        return [0.0]
    return [round(duration * (i + 0.5) / n, 2) for i in range(n)]


async def _probe_duration(source: str, ffmpeg: str) -> float:
    """用 ffmpeg -i 解析时长(秒);解析不到返回 0.0(逻辑同 video_understand_tool)"""
    result = await compose.run([ffmpeg, "-i", source], timeout=60, truncate=False)
    text = f"{result.get('stderr') or ''}\n{result.get('stdout') or ''}"
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


async def _extract_frames(ffmpeg: str, video: str, times: List[float], cleanup: List[str]) -> List[str]:
    """按时间点抽帧到本地(不上传),供内联/上传使用;任一张失败返回空列表(避免时序错位)"""
    paths: List[str] = []
    workdir = os.path.dirname(video) or "."
    for idx, at in enumerate(times):
        out = os.path.join(workdir, f"element_{_uuid()}_{idx}.jpg")
        cleanup.append(out)
        result = await compose.run(
            compose.build_extract_frame_cmd(video, out, at, _FRAME_WIDTH, ffmpeg), timeout=120,
        )
        if not result.get("ok") or not os.path.exists(out):
            logger.warning(f"[element_detect] 抽帧失败(第 {idx + 1}/{len(times)} 张)")
            return []
        paths.append(out)
        cleanup.append(out)
    return paths


async def _recognize(frame_urls: List[Optional[str]], times: List[float]) -> str:
    """把帧喂给视觉模型,列出原片可替换元素;失败返回空串"""
    urls = [u for u in frame_urls if u]
    if not urls:
        return ""
    content: List[dict] = [{"type": "text", "text": ELEMENT_PROMPT}]
    for i, u in enumerate(frame_urls):
        if not u:
            continue
        content.append({"type": "text", "text": f"帧{i}(约 {times[i]:.1f}s):"})
        content.append({"type": "image_url", "image_url": {"url": u}})
    try:
        return await vision_chat({
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.3,
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[element_detect] 视觉识别失败(不影响复刻): {exc}")
        return ""


def _parse_bbox(e: Dict[str, Any]) -> Dict[str, Any]:
    """解析可选的归一化包围盒 [x1,y1,x2,y2](0~1)。仅当模型可靠返回 4 个合法浮点数才纳入,
    否则忽略——定位是增强项,绝不为不可靠坐标牺牲绑定可用性。"""
    b = e.get("bbox")
    if not isinstance(b, (list, tuple)) or len(b) != 4:
        return {}
    try:
        nums = [float(x) for x in b]
    except (TypeError, ValueError):
        return {}
    if not all(0.0 <= v <= 1.0 for v in nums) or nums[0] >= nums[2] or nums[1] >= nums[3]:
        return {}
    return {"bbox": [round(v, 4) for v in nums]}


def _parse_span(e: Dict[str, Any], duration: float) -> Dict[str, Any]:
    """解析可选的出现时间跨度 [start,end](秒)。任一缺失/非法则整体忽略,由 time 字段兜底为首次出现时刻。
    合法值夹取到 [0, duration],避免模型臆造超出视频时长的范围。"""
    raw_s = e.get("start")
    raw_e = e.get("end")
    if raw_s is None or raw_e is None:
        return {}
    try:
        s = float(raw_s) if raw_s is not None else 0.0
        en = float(raw_e) if raw_e is not None else (duration or 0.0)
    except (TypeError, ValueError):
        return {}
    s = max(0.0, min(s, duration or s))
    en = max(s, min(en, duration or en))
    if not s < en or round(s, 3) >= round(en, 3):
        return {}
    return {"start": round(s, 3), "end": round(en, 3)}


def _parse_elements(text: str, times: List[float], frame_urls: List[Optional[str]], duration: float, shot_table=None) -> List[Dict[str, Any]]:
    """解析视觉模型返回的 JSON,归一化为带时空定位的元素槽位列表;任何异常返回空列表"""
    if not text:
        return []
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        obj = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return []
    els = obj.get("elements") if isinstance(obj, dict) else None
    if not isinstance(els, list):
        return []
    out: List[Dict[str, Any]] = []
    for n, e in enumerate(els):
        if not isinstance(e, dict):
            continue
        kind = str(e.get("kind") or "").strip().lower()
        if kind not in ELEMENT_KINDS:
            continue
        label = str(e.get("label") or "").strip().replace("\n", " ")[:40]
        if not label:
            continue
        try:
            fi = max(0, min(int(e.get("frame_index") or 0), len(times) - 1))
        except (TypeError, ValueError):
            fi = 0
        item: Dict[str, Any] = {
            "id": f"e{n}",
            "kind": kind,
            "label": label,
            "time": round(times[fi], 1),
            "thumbnail": frame_urls[fi] or "",
        }
        # 实例级定位(可选增强):bbox 空间定位 + start/end 时间跨度,让绑定精确到原片具体对象/时段
        item.update(_parse_bbox(e))
        item.update(_parse_span(e, duration))
        # 仅记录实际送入模型且被识别可见的帧；镜头范围是定位上下文，不是连续可见的证明。
        observations = []
        seen = set()
        raw_observations = e.get("observations")
        for observation in (raw_observations[:12] if isinstance(raw_observations, list) else []):
            if not isinstance(observation, dict):
                continue
            index = observation.get("frame_index")
            if type(index) is not int or not 0 <= index < len(times) or not frame_urls[index] or index in seen:
                continue
            seen.add(index)
            point = {"time": times[index], **_parse_bbox(observation)}
            for shot in shot_table or []:
                start = float(shot.get("start") or 0)
                end = start + float(shot.get("duration") or 0)
                if start <= times[index] < end:
                    point.update(shot_index=int(shot["index"]), shot_start=start, shot_end=end)
                    break
            observations.append(point)
        if observations:
            item["observations"] = sorted(observations, key=lambda point: point["time"])
        out.append(item)
    return out
