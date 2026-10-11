# -*- coding: utf-8 -*-
'''
@文件    :script_anchor.py
@说明    :词锚点编排(纯函数)— 与 backend app/services/script_schema.py 同构实现
@时间    :2026/09/21 16:40:00
@作者    :一源AI
@版本    :1.0
@说明    :worker 与 backend 是独立部署包,无法共享模块,因此这里镜像一份纯函数实现。
          镜像的风险是两端漂移,由 backend/tests/test_cross_worker_contract.py
          用同一批样例断言两端输出完全一致(分词/分段/锚点解析/时间估算)。
          ⚠️ 改任何一端,必须同步改另一端,否则一致性测试会失败。

          锚点一律用「词序号」(from_word/to_word/at_word),绝不用秒:
          时间由 estimate_timing 按词数估算兜底,P1 接真实对齐后替换即可。
'''
import re
from typing import Any, Dict, List, Optional, Tuple

# 分词:中文按单字、连续字母数字按词、标点与空白作分隔符丢弃(不引入分词依赖,保证可复现)
_WORD_PATTERN = re.compile(r"[0-9A-Za-z]+|[\u4e00-\u9fff]")

# 结构化文案字段 → 叙事分段(与 backend prompt_builder 的 structured 同键)
STRUCTURED_TO_SEGMENT: Tuple[Tuple[str, str], ...] = (
    ("title", "hook"),
    ("subtitle", "selling"),
    ("script", "script"),
)

# 分段说话人:口播段是主播原声,其余为旁白
SEGMENT_ROLES = {"hook": "NARRATOR", "selling": "NARRATOR", "script": "HOST"}

# 备注里声明锚点的字段名
ANCHOR_FIELD_MAP = {
    "锚点": "selection",
    "选区": "selection",
    "窗口": "selection",
    "瞬时": "moment",
    "卡点": "moment",
}

# 备注里声明轨道的字段名(P3-2):轨道引用上面已声明的锚点,合成层据此按锚点卡点
TRACK_FIELD_MAP = {
    "轨道": "track",
    "轨": "track",
    "track": "track",
}

SCRIPT_VERSION = 1


def split_words(text: Any) -> List[str]:
    """把文案切成词序列(中文单字 / 英文数字连写),标点与空白不计入词序号。"""
    if text is None:
        return []
    return _WORD_PATTERN.findall(str(text))


def build_segments(structured: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """结构化文案 → 叙事分段(空段不生成)。"""
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
    """默认锚点:每段一个选区(覆盖整段)+ 一个瞬时点(段首词)"""
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
    """连续词串首次出现的位置(未命中返回 None)。

    moment 用文本匹配而非死序号:改台词后同一句卖点仍能被命中。
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
    """解析选区范围:3-7 / 3~7 / 单数字;越界裁剪,非法返回 None。"""
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
    """解析瞬时点:数字=第 N 个词;文本=匹配词串首次出现位置(未命中返回 None)。"""
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
    """解析备注里的显式锚点声明,未命中/非法一律丢弃(不静默落到 0 造成错位)。"""
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
                # 文本匹配时把整个匹配串记为窗口(at_word 仍是卡点位置,即串首词)
                matched = split_words(spec) if not re.fullmatch(r"\d+", str(spec or "").strip()) else []
                to_word = at + len(matched) - 1 if matched else at
                moments.append({
                    "id": name, "segment": segment_id, "at_word": at,
                    "to_word": max(at, to_word), "source": "remark",
                })
    return selections, moments


def parse_track_specs(
    items: Optional[List[str]],
    selections: List[Dict[str, Any]],
    moments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """解析备注里的轨道声明(P3-2),引用不存在的锚点一律丢弃(不留悬空轨)。

    语法:`轨道:<type>=<ref>`,ref 形如 `selection:product` / `moment:reveal`;
    可用 `during:` / `at:` 前缀强制语义(默认选区→during、瞬时→at)。
    例:`轨道:broll=selection:product`(讲到商品切产品特写)、`轨道:reveal=at:moment:reveal`。
    只产出「编排意图」(类型 + 引用),真实秒由合成层按锚点窗口回灌,故改台词后仍自动跟随。
    """
    ids = {f"selection:{s.get('id')}" for s in selections}
    ids |= {f"moment:{m.get('id')}" for m in moments}
    tracks: List[Dict[str, Any]] = []
    for raw in items or []:
        text = str(raw or "").strip()
        idx = min([i for i in (text.find(":"), text.find("：")) if i >= 0], default=-1)
        if idx < 0 or TRACK_FIELD_MAP.get(text[:idx].strip()) != "track":
            continue
        body = text[idx + 1:].strip()
        if "=" not in body:
            continue
        ttype, ref = body.split("=", 1)
        ttype, ref = ttype.strip(), ref.strip()
        if not ttype or not ref:
            continue
        # 语义前缀 during:/at: 可选;未给出时按锚点类型推断(选中选区→窗口,瞬时→时刻)
        key = ""
        sep = min([i for i in (ref.find(":"), ref.find("：")) if i >= 0], default=-1)
        if sep > 0:
            head, tail = ref[:sep].strip().lower(), ref[sep + 1:].strip()
            if head in ("during", "at") and tail:
                key, ref = head, tail
        if ref not in ids:
            continue  # 悬空引用:丢弃
        if not key:
            key = "during" if ref.startswith("selection:") else "at"
        tracks.append({"type": ttype, key: ref, "source": "remark"})
    return tracks


def _override(base: List[Dict[str, Any]], extra: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """同名锚点以显式声明为准"""
    merged = {item["id"]: item for item in base}
    for item in extra:
        if item.get("id"):
            merged[item["id"]] = item
    return list(merged.values())


def build_script(
    structured: Optional[Dict[str, Any]],
    extras: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """组装词锚点脚本:分段 + 默认锚点 + 备注显式锚点 + 备注轨道声明"""
    segments = build_segments(structured)
    selections, moments = _default_anchors(segments)
    user_selections, user_moments = parse_anchor_specs(extras or [], segments)
    selections = _override(selections, user_selections)
    moments = _override(moments, user_moments)
    return {
        "version": SCRIPT_VERSION,
        "segments": segments,
        "selections": selections,
        "moments": moments,
        # P3-2:备注声明的轨道(引用上面已就绪的锚点);无声明时为 [],行为与改造前一致
        "tracks": parse_track_specs(extras or [], selections, moments),
    }


def resolve_window(script: Optional[Dict[str, Any]], ref: Optional[str]) -> Optional[Dict[str, Any]]:
    """把引用解析成词窗口(不含任何秒数)"""
    script = script or {}
    raw = str(ref or "").strip()
    if not raw:
        return None
    kind, _, name = raw.partition(":")
    if not name:
        kind, name = "", kind

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
    """解析轨道引用(无合成层前只产出编排意图 cue)"""
    cues: List[Dict[str, Any]] = []
    for track in tracks or []:
        ref = track.get("during") or track.get("at")
        window = resolve_window(script, ref)
        if not window:
            continue  # 引用不存在的锚点:丢弃,不留悬空轨
        cues.append({
            "type": track.get("type") or "",
            "ref": ref,
            "asset": track.get("asset"),
            "for_ms": track.get("for_ms"),
            "window": window,
        })
    return cues


def _normalize_span(raw: Any) -> Optional[Dict[str, int]]:
    """归一化外部真实时间窗 {start_ms,end_ms};非法/零长度返回 None(交由估算兜底)。"""
    if not isinstance(raw, dict):
        return None
    try:
        start = int(round(float(raw.get("start_ms"))))
        end = int(round(float(raw.get("end_ms"))))
    except (TypeError, ValueError):
        return None
    if end <= start:
        return None
    return {"start_ms": max(0, start), "end_ms": max(0, end)}


def estimate_timing(
    script: Optional[Dict[str, Any]], duration_sec: Any = 5,
    segment_spans: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """估算时间窗(兜底):按词数占比摊分;段级真实窗口优先于估算。

    segment_spans:P1 真实对齐回灌的段级窗口 {segment_id:{start_ms,end_ms}}
                   (见 subtitle.segment_spans_from_cues)。提供的段用真实秒,
                   未提供/非法的段回退词数估算 —— 局部真实即可局部生效,不影响其余段。
    返回结构不变(segments/anchors/estimated),其中 estimated 表示「是否全为估算」。
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

    # 先归一化外部真实窗口,非法值直接丢弃(不能污染时间轴)
    real: Dict[str, Dict[str, int]] = {}
    for key, raw in (segment_spans or {}).items():
        norm = _normalize_span(raw)
        if norm:
            real[key] = norm

    seg_timing: Dict[str, Dict[str, int]] = {}
    cursor = 0
    for seg in segments:
        count = len(seg.get("words") or [])
        span = round(total_ms * count / total_words)
        # 有真实窗口用真实值(不推进估算游标,保证未回灌段的估算位置可复现)
        seg_timing[seg["id"]] = real.get(seg["id"]) or {"start_ms": cursor, "end_ms": cursor + span}
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
    return {"duration_ms": total_ms, "segments": seg_timing, "anchors": anchors, "estimated": not real}


def render_anchor_hint(script: Optional[Dict[str, Any]]) -> str:
    """把词锚点渲染成提示词可消费的编排说明(只说词,不说秒)。

    默认锚点(整段选区/段首瞬时)与分段文本重复,这里只输出「非整段」的显式锚点,
    避免把整段原文再抄一遍稀释注意力。
    """
    script = script or {}
    segments = script.get("segments") or []
    if not segments:
        return ""
    lines = ["[叙事分段]"]
    for seg in segments:
        words = seg.get("words") or []
        lines.append(f"{seg['id']}({seg.get('role') or 'HOST'}){len(words)}词:{seg.get('text')}")

    extra: List[str] = []
    for item in script.get("selections") or []:
        words = _segment_words(segments, item.get("segment"))
        if not words:
            continue
        covers_all = item.get("from_word") == 0 and item.get("to_word") == len(words) - 1
        if covers_all and item.get("source") == "default":
            continue  # 整段默认选区:与分段重复,不重复输出
        window = resolve_window(script, f"selection:{item.get('id')}")
        if window:
            extra.append(f"重点窗口 {item['id']}:第{window['from_word']}-{window['to_word']}词 → {window['text']}")
    for item in script.get("moments") or []:
        if item.get("source") == "default":
            continue  # 段首默认瞬时点:不输出
        window = resolve_window(script, f"moment:{item.get('id')}")
        if window:
            extra.append(f"卡点 {item['id']}:第{window['from_word']}词 → {window['text']}")

    if extra:
        lines.append("[词锚点]")
        lines.extend(extra)
    return "\n".join(lines)
