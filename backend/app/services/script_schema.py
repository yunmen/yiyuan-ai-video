# -*- coding: utf-8 -*-
'''
@文件    :script_schema.py
@说明    :词锚点编排(纯函数)— segments / selections / moments 用「词序号」锚定,不写秒
@时间    :2026/09/21 16:30:00
@作者    :一源AI
@版本    :1.0
@说明    :对标 SVML 的 Script 层:作者只写叙事结构(无时间),下游用
          during={selection.X} / at={moment.X} 引用「命名窗口」,
          时间由对齐结果推导 —— 这样改一句台词,时间轴自动重排。

          本项目落地为 params.script:
            {"segments":[{id,role,text,words}], "selections":[...], "moments":[...]}

          关键约束:锚点一律用「词序号」(from_word/to_word/at_word),绝不用秒。
          无词级对齐(P1)之前,时间由 estimate_timing 按词数比例估算兜底,
          P1 落地后把 words 换成真实时间戳即可,上层引用方式不变。
'''
import re
from typing import Any, Dict, List, Optional, Tuple

# 分词:中文按单字、连续字母数字按词、标点与空白作分隔符丢弃。
# 刻意不引入 jieba 等分词依赖 —— 锚点要求「稳定且可复现」,
# 单字切分在任何环境结果一致,后续接真实对齐(P1)时再换成模型词。
_WORD_PATTERN = re.compile(r"[0-9A-Za-z]+|[\u4e00-\u9fff]")

# 结构化文案字段 → 叙事分段(与 prompt_builder 的 structured 同键)
STRUCTURED_TO_SEGMENT: Tuple[Tuple[str, str], ...] = (
    ("title", "hook"),
    ("subtitle", "selling"),
    ("script", "script"),
)

# 分段说话人:口播段是主播原声,其余为旁白(供后续字幕分样式 / 音色选择使用)
SEGMENT_ROLES = {"hook": "NARRATOR", "selling": "NARRATOR", "script": "HOST"}

# 备注里声明锚点的字段名
ANCHOR_FIELD_MAP = {
    "锚点": "selection",
    "选区": "selection",
    "窗口": "selection",
    "瞬时": "moment",
    "卡点": "moment",
}

SCRIPT_VERSION = 1


def split_words(text: Any) -> List[str]:
    """把文案切成词序列(中文单字 / 英文数字连写),标点与空白不计入词序号。"""
    if text is None:
        return []
    return _WORD_PATTERN.findall(str(text))


def build_segments(structured: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """结构化文案 → 叙事分段(空段不生成,避免把空文本喂给模型)。"""
    structured = structured or {}
    segments: List[Dict[str, Any]] = []
    for key, segment_id in STRUCTURED_TO_SEGMENT:
        text = str(structured.get(key) or "").strip()
        if not text:
            continue
        segments.append({
            "id": segment_id,
            "role": SEGMENT_ROLES.get(segment_id, "HOST"),
            "text": text,
            "words": split_words(text),
        })
    return segments


def _default_anchors(segments: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """默认锚点:每段一个选区(覆盖整段)+ 一个瞬时点(段首词)。

    存在的意义是让「无显式声明」的任务也有可用锚点,
    后续前端/管理端只要往 selections/moments 里加条目即可精确控制。
    """
    selections, moments = [], []
    for seg in segments:
        last = max(0, len(seg["words"]) - 1)
        selections.append({
            "id": seg["id"], "segment": seg["id"], "from_word": 0, "to_word": last,
            "source": "default",
        })
        moments.append({
            "id": f"{seg['id']}_start", "segment": seg["id"], "at_word": 0, "source": "default",
        })
    return selections, moments


def _find_word_subsequence(words: List[str], target: List[str]) -> Optional[int]:
    """在词序列中查找连续子串首次出现的位置(未命中返回 None)。

    moment 用「文本匹配」而非死序号:改台词后同一句卖点仍能被命中,
    这正是词锚点相对秒锚点的核心价值。
    """
    if not target or not words or len(target) > len(words):
        return None
    for i in range(len(words) - len(target) + 1):
        if words[i:i + len(target)] == target:
            return i
    return None


def _split_segment(spec: str, segments: List[Dict[str, Any]]) -> Tuple[Optional[str], str]:
    """锚点声明支持指定段:「script:3-7」;未指定时取最后一个段(口播段优先)。"""
    spec = str(spec or "").strip()
    seg_ids = [s["id"] for s in segments]
    if ":" in spec or "：" in spec:
        idx = min([i for i in (spec.find(":"), spec.find("：")) if i >= 0], default=-1)
        head, tail = spec[:idx].strip(), spec[idx + 1:].strip()
        if head in seg_ids:
            return head, tail
    return (seg_ids[-1] if seg_ids else None), spec


def _segment_words(segments: List[Dict[str, Any]], segment_id: Optional[str]) -> List[str]:
    for seg in segments:
        if seg["id"] == segment_id:
            return seg["words"]
    return []


def _parse_range(
    spec: str, segments: List[Dict[str, Any]], segment_id: Optional[str],
) -> Optional[Tuple[int, int]]:
    """解析选区范围:支持 3-7 / 3~7 / 单数字(单词窗口);越界裁剪,非法返回 None。"""
    words = _segment_words(segments, segment_id)
    if not words:
        return None
    body = re.split(r"[-~—]", str(spec or "").strip(), maxsplit=1)
    try:
        start = int(body[0].strip())
        end = int(body[1].strip()) if len(body) > 1 and body[1].strip() else start
    except (TypeError, ValueError):
        return None
    last = len(words) - 1
    start, end = max(0, min(start, last)), max(0, min(end, last))
    return (start, end) if start <= end else (end, start)


def _parse_at(
    spec: str, segments: List[Dict[str, Any]], segment_id: Optional[str],
) -> Optional[int]:
    """解析瞬时点:数字=第 N 个词;文本=匹配该词串首次出现的位置(未命中返回 None)。"""
    words = _segment_words(segments, segment_id)
    if not words:
        return None
    raw = str(spec or "").strip()
    if re.fullmatch(r"\d+", raw):
        return max(0, min(int(raw), len(words) - 1))
    return _find_word_subsequence(words, split_words(raw))


def parse_anchor_specs(
    items: Optional[List[str]], segments: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """从备注片段解析显式锚点声明,未命中/非法的一律丢弃(不静默落到 0 造成错位)。

    支持写法:
      锚点:product=3-7          → 选区(默认作用于最后一段)
      锚点:product=script:3-7   → 选区(指定段)
      瞬时:reveal=招牌小龙虾     → 瞬时点(文本匹配,改台词后仍命中)
      瞬时:reveal=5             → 瞬时点(第 5 个词)
    """
    selections: List[Dict[str, Any]] = []
    moments: List[Dict[str, Any]] = []
    for raw in items or []:
        text = str(raw or "").strip()
        idx = min([i for i in (text.find(":"), text.find("：")) if i >= 0], default=-1)
        if idx < 0:
            continue
        kind = ANCHOR_FIELD_MAP.get(text[:idx].strip())
        if not kind:
            continue
        body = text[idx + 1:].strip()
        if "=" not in body:
            continue
        name, spec = body.split("=", 1)
        name = name.strip()
        if not name:
            continue
        segment_id, spec = _split_segment(spec, segments)
        if kind == "selection":
            rng = _parse_range(spec, segments, segment_id)
            if rng and segment_id:
                selections.append({
                    "id": name, "segment": segment_id, "from_word": rng[0], "to_word": rng[1],
                    "source": "remark",
                })
        else:
            at = _parse_at(spec, segments, segment_id)
            if at is not None and segment_id:
                # 文本匹配时把整个匹配串记为窗口(at_word 仍是卡点位置,即串首词),
                # 否则窗口只剩首字,下游(字幕/B-roll)拿不到完整语义
                matched = split_words(spec) if not re.fullmatch(r"\d+", str(spec or "").strip()) else []
                to_word = at + len(matched) - 1 if matched else at
                moments.append({
                    "id": name, "segment": segment_id, "at_word": at,
                    "to_word": max(at, to_word), "source": "remark",
                })
    return selections, moments


def _override(base: List[Dict[str, Any]], extra: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """同名锚点以显式声明为准(覆盖默认生成的同 id 锚点)"""
    merged = {item["id"]: item for item in base}
    for item in extra:
        if item.get("id"):
            merged[item["id"]] = item
    return list(merged.values())


def build_script(
    structured: Optional[Dict[str, Any]],
    extras: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """组装词锚点脚本:分段 + 默认锚点 + 备注里的显式锚点。

    返回结构(worker 与 backend 同构):
      {"version":1, "segments":[...], "selections":[...], "moments":[...]}
    """
    segments = build_segments(structured)
    selections, moments = _default_anchors(segments)
    user_selections, user_moments = parse_anchor_specs(extras or [], segments)
    return {
        "version": SCRIPT_VERSION,
        "segments": segments,
        "selections": _override(selections, user_selections),
        "moments": _override(moments, user_moments),
        # 轨道引用预留(P3 合成层落地后填充):{"type":"broll","during":"selection:product"}
        "tracks": [],
    }


def resolve_window(script: Optional[Dict[str, Any]], ref: Optional[str]) -> Optional[Dict[str, Any]]:
    """把引用解析成词窗口(不含任何秒数)。

    ref 支持 "selection:product" / "moment:reveal";裸 id 按「先选区后瞬时」查找。
    返回 {kind,id,segment,from_word,to_word,words,text};未找到返回 None。
    """
    script = script or {}
    raw = str(ref or "").strip()
    if not raw:
        return None
    kind, _, name = raw.partition(":")
    if not name:
        kind, name = "", kind  # 裸 id:两种锚点都试

    def _pick(kind_name: str) -> Optional[Dict]:
        pool = script.get("selections" if kind_name == "selection" else "moments") or []
        for item in pool:
            if item.get("id") == name:
                return item
        return None

    item = _pick(kind) if kind in ("selection", "moment") else (_pick("selection") or _pick("moment"))
    if not item:
        return None
    kind = "selection" if "from_word" in item else "moment"
    words = _segment_words(script.get("segments") or [], item.get("segment"))
    from_word = int(item.get("from_word", item.get("at_word", 0)) or 0)
    to_word = int(item.get("to_word", from_word) or from_word)
    window = words[from_word:to_word + 1]
    return {
        "kind": kind,
        "id": item.get("id"),
        "segment": item.get("segment"),
        "from_word": from_word,
        "to_word": to_word,
        # 卡点位置:瞬时点取串首词(窗口可能覆盖整串,但卡点始终在起点)
        "at_word": int(item.get("at_word", from_word) or from_word),
        "words": window,
        "text": "".join(window),
    }


def resolve_tracks(
    script: Optional[Dict[str, Any]], tracks: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """解析轨道引用:track 用 during/at 引用命名窗口,解析结果仍是「词窗口」。

    无合成层(P3)前,这里只产出编排意图(cue),供提示词与后续合成使用。
    """
    cues: List[Dict[str, Any]] = []
    for track in tracks or []:
        ref = track.get("during") or track.get("at")
        window = resolve_window(script, ref)
        if not window:
            continue  # 引用了不存在的锚点:丢弃,不留悬空轨
        cues.append({
            "type": track.get("type") or "",
            "ref": ref,
            "asset": track.get("asset"),
            "for_ms": track.get("for_ms"),
            "window": window,
        })
    return cues


def estimate_timing(script: Optional[Dict[str, Any]], duration_sec: Any = 5) -> Dict[str, Any]:
    """估算时间窗(兜底):按「词数占比」把总时长摊到各段与各锚点。

    P1(真实词级对齐)落地后,这里替换为真实时间戳即可,
    上层 during/at 的引用方式完全不变 —— 这是先做词锚点的意义。
    """
    script = script or {}
    try:
        total_ms = max(0, int(float(duration_sec or 0) * 1000))
    except (TypeError, ValueError):
        total_ms = 0
    segments = script.get("segments") or []
    total_words = sum(len(s.get("words") or []) for s in segments)
    if not segments or total_words <= 0 or total_ms <= 0:
        return {"duration_ms": total_ms, "segments": {}, "anchors": {}, "estimated": True}

    seg_timing: Dict[str, Dict[str, int]] = {}
    cursor = 0
    for seg in segments:
        count = len(seg.get("words") or [])
        span = round(total_ms * count / total_words)
        seg_timing[seg["id"]] = {"start_ms": cursor, "end_ms": cursor + span}
        cursor += span

    anchors: Dict[str, Dict[str, int]] = {}
    for item in (script.get("selections") or []) + (script.get("moments") or []):
        seg = seg_timing.get(item.get("segment"))
        if not seg:
            continue
        words = _segment_words(segments, item.get("segment"))
        per = (seg["end_ms"] - seg["start_ms"]) / max(1, len(words))
        from_word = int(item.get("from_word", item.get("at_word", 0)) or 0)
        to_word = int(item.get("to_word", from_word) or from_word)
        kind = "selection" if "from_word" in item else "moment"
        anchors[f"{kind}:{item.get('id')}"] = {
            "start_ms": seg["start_ms"] + round(from_word * per),
            # 选区窗口按「词结束」计:最后一个词占满自己的时长
            "end_ms": seg["start_ms"] + round((to_word + 1) * per),
        }
    return {"duration_ms": total_ms, "segments": seg_timing, "anchors": anchors, "estimated": True}
