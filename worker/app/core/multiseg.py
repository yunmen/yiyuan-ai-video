# -*- coding: utf-8 -*-
'''
@文件    :multiseg.py
@说明    :多段编排(纯函数部分)— 把超过模型单段上限的时长切成若干段
          背景:Seedance 2.x 单次生成上限约 15s(实测 15.2s),30s 只能拆成多段生成再拼接。
          这里只做「怎么切」的决策,不碰 IO/ffmpeg,便于单测:
            ① 时长怎么分段(均衡,避免出现 15+1 这种没法用的短尾段);
            ② 文案怎么分配(不重复念同一句,且在标点处断,读起来完整);
            ③ 各段在时间轴上的起点(裁参考视频用);
            ④ 有分镜表时**按镜头边界**分段(plan_segments_by_shots)——
               按秒均衡切分会把同一个镜头拆到两段里分别生成,衔接处最容易突变。
@时间    :2026/09/21 22:30:00
@作者    :一源AI
@版本    :1.1
'''
import math
from typing import Any, Dict, List, Tuple

from app.core import shots as shots_module
from app.core.plugin import logger

# 模型单段生成上限(秒):方舟 Seedance 2.x 实测 15.2s,取 15 留余量
MAX_SEGMENT_SECONDS = 15

# 单段时长下限(秒):低于它模型生成不出有意义的内容(编辑链路实测 4s 起)。
# 它只用于**校验**按镜头切分的结果是否可用,不改变原有按秒切分的档位。
MIN_SEGMENT_SECONDS = 4

# 镜头归属到某一段所需的最小重叠时长(秒):低于它就宁可不归,
# 避免把只是"擦边"的镜头描述塞进相邻段,反而让提示词描述错画面。
MIN_OVERLAP_SECONDS = 0.5

# 切分文案时的优选断点(标点优先,读起来才完整)
_SCRIPT_BREAKS = "，,。！？；;、：: "


def plan_segments(total_seconds: int, max_segment: int = MAX_SEGMENT_SECONDS) -> List[int]:
    """把总时长切成若干段,各段**尽量均衡**

    为什么均衡而不是「前几段塞满、最后收尾」:16 秒若切成 [15, 1],
    第二段只有 1 秒既生成不出内容、也没有意义;均衡切是 [8, 8]。
    返回值各段之和恒等于总时长,且每段都不超过 max_segment。
    """
    total = int(total_seconds or 0)
    if total <= 0:
        return []
    if total <= max_segment:
        return [total]
    count = math.ceil(total / max_segment)
    base, rest = divmod(total, count)
    return [base + (1 if i < rest else 0) for i in range(count)]


def segment_windows(durations: List[int]) -> List[Tuple[int, int]]:
    """累计各段起点,返回 [(start, duration), ...](裁参考视频、拼字幕时间轴都要用)"""
    windows: List[Tuple[int, int]] = []
    cursor = 0
    for duration in durations:
        windows.append((cursor, int(duration)))
        cursor += int(duration)
    return windows


def _cut_near(text: str, size: int) -> int:
    """在 size 附近找断点:优先标点之后;退一步向前找,再退一步向后找,最后硬切"""
    if size >= len(text):
        return len(text)
    floor = max(0, size - size // 2)
    for i in range(size, floor, -1):
        if text[i - 1] in _SCRIPT_BREAKS:
            return i
    ceil = min(len(text), size + size // 2)
    for i in range(size, ceil):
        if i > 0 and text[i - 1] in _SCRIPT_BREAKS:
            return i
    return size


def split_script_for_segments(text: str, parts: int) -> List[str]:
    """把文案切成 parts 份,供各段分别使用

    为什么必须切:每段生成都要带自己的文案,若每段都传完整文案,
    模型会把同一句话念 N 遍。
    切分原则:按目标字数就近找**标点**断开,让每段读起来是完整表达。
    """
    text = (text or "").strip()
    if parts <= 0:
        return []
    if not text:
        return [""] * parts
    if parts == 1:
        return [text]
    if len(text) < parts:
        # 文案比段数还短:切不出有意义的内容,只能让每段都用它
        return [text] * parts

    size = math.ceil(len(text) / parts)
    chunks: List[str] = []
    rest = text
    for _ in range(parts - 1):
        cut = _cut_near(rest, size)
        chunks.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    chunks.append(rest)
    return chunks


def _valid_segments(segments: List[int], total: int, min_segment: int, max_segment: int) -> bool:
    """校验分段是否满足上层依赖的不变量

    为什么要这么严:上层用 sum(分段) 当**成片总时长**(拼接结果长度、字幕时间轴基准),
    任何一条不满足都会让成片与建单时长错位 —— 宁可直接回退按秒切分。
    """
    if not segments or sum(segments) != total:
        return False
    return all(min_segment <= seg <= max_segment for seg in segments)


def _absorb_short_segments(segments: List[int], min_segment: int, max_segment: int) -> List[int]:
    """把过短的段并入相邻段(优先并入前一段,不超上限才并)

    正向走一遍处理"中后段过短",反向再走一遍处理"首段过短"(首段没有前一段可并)。
    """
    merged: List[int] = []
    for seg in segments:
        if merged and seg < min_segment and merged[-1] + seg <= max_segment:
            merged[-1] += seg
            continue
        merged.append(seg)
    reversed_out: List[int] = []
    for seg in reversed(merged):
        if reversed_out and seg < min_segment and reversed_out[-1] + seg <= max_segment:
            reversed_out[-1] += seg
            continue
        reversed_out.append(seg)
    return list(reversed(reversed_out))


def _reconcile_total(segments: List[int], total: int, min_segment: int, max_segment: int) -> List[int]:
    """把取整误差补到还有余量的段上,使 sum(segments) == total

    镜头边界是小数,取整后各段之和必然与总时长有零头;不校正就会让成片时长
    与建单时长差几秒(字幕按总时长铺,直接表现为整体错位)。
    补不动(所有段都已顶到上/下限)时原样返回,由 _valid_segments 判定回退。
    """
    if not segments:
        return segments
    diff = total - sum(segments)
    if diff == 0:
        return segments
    idx = len(segments) - 1
    guard = 0
    limit = len(segments) * max(1, abs(diff) + 1)
    while diff != 0 and guard < limit:
        guard += 1
        step = 1 if diff > 0 else -1
        if min_segment <= segments[idx] + step <= max_segment:
            segments[idx] += step
            diff -= step
        idx = (idx - 1) % len(segments)
    return segments


def segment_shot_map(
    segments: List[int], shot_list: List[Dict[str, Any]], min_overlap: float = MIN_OVERLAP_SECONDS,
) -> List[List[int]]:
    """「第几段覆盖了哪几个镜头」(纯函数),与 segments 等长

    用途:多段生成时把**逐镜头逆推**得到的画面描述按段归位(P0-3)。
    归属规则:一个镜头只归给"与它重叠时间最长"的那一段;
    重叠不足 min_overlap 秒(或完全没有重叠)时**不归任何段** ——
    与其把相邻镜头的话硬塞进错误的段,不如让那段沿用原有提示词。

    即便 segments 是按秒切出来的(未按镜头),这里也能算出重叠关系,
    只是重叠往往落在镜头中间,由调用方决定是否使用(见 video_tool 的启用条件)。
    """
    windows = segment_windows(segments)
    result: List[List[int]] = [[] for _ in segments]
    if not windows or not shot_list:
        return result
    for item in shot_list:
        try:
            shot_start = float(item.get("start") or 0)
            shot_end = float(item.get("end") or 0)
            index = int(item.get("index") or 0)
        except (TypeError, ValueError):
            continue
        if shot_end <= shot_start:
            continue
        best_seg, best_overlap = -1, 0.0
        for seg_idx, (seg_start, seg_dur) in enumerate(windows):
            overlap = min(shot_end, seg_start + seg_dur) - max(shot_start, seg_start)
            if overlap > best_overlap:
                best_seg, best_overlap = seg_idx, overlap
        if best_seg < 0 or best_overlap < min_overlap:
            continue
        result[best_seg].append(index)
    return result


def plan_segments_by_shots(
    shot_list: List[Dict[str, Any]], total_seconds: int,
    max_segment: int = MAX_SEGMENT_SECONDS, min_segment: int = MIN_SEGMENT_SECONDS,
) -> List[int]:
    """按**镜头边界**把总时长切成若干段(纯函数);不可用时回退 plan_segments

    与按秒均衡切分的差别:相邻镜头尽量留在同一段里,累加到接近上限才断开 ——
    同一个镜头不会被拆到两段里分别生成。这正是外部「链式首尾帧」方案的核心:
    段边界落在镜头边界上,跨段衔接才接得上。

    约束(与 plan_segments 完全一致,否则上层拼接与字幕时间轴都会错位):
      · 各段之和 == total_seconds;
      · 每段 ∈ [min_segment, max_segment]。
    分镜表为空、镜头时长缺失、出现单个超上限的长镜头、尾部凑不出合法段等情况
    **一律回退 plan_segments**(按秒均衡),绝不产出非法分段。
    """
    total = int(total_seconds or 0)
    fallback = plan_segments(total, max_segment)
    if total <= 0:
        return fallback
    if total <= max_segment:
        return [total]

    # 参考视频往往比目标时长更长:先裁到目标时长,否则镜头时长之和与目标时长对不上
    usable = shots_module.clip_shots(shot_list or [], total)
    durations: List[float] = []
    for item in usable:
        try:
            duration = float(item.get("duration") or 0)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            durations.append(duration)
    if not durations:
        return fallback

    segments: List[int] = []
    current = 0.0
    for duration in durations:
        # 加上这个镜头会超上限就先收口;current=0 时不收口(单个长镜头只能先收下,
        # 由下面的校验判定回退,而不是在这里硬切出一个 0 秒的段)
        if current > 0 and current + duration > max_segment:
            segments.append(int(round(current)))
            current = 0.0
        current += duration
    if current > 0:
        segments.append(int(round(current)))

    segments = _absorb_short_segments(segments, min_segment, max_segment)
    segments = _reconcile_total(segments, total, min_segment, max_segment)
    if not _valid_segments(segments, total, min_segment, max_segment):
        # 回退不静默:日志里说明原因,便于判断是分镜表质量差还是切分策略要调整
        logger.info(
            f"[multiseg] 按镜头切分结果不合法({segments},合计 {sum(segments)}≠{total}s),"
            "回退按秒均衡切分"
        )
        return fallback
    return segments
