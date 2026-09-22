# -*- coding: utf-8 -*-
'''
@文件    :multiseg.py
@说明    :多段编排(纯函数部分)— 把超过模型单段上限的时长切成若干段
          背景:Seedance 2.x 单次生成上限约 15s(实测 15.2s),30s 只能拆成多段生成再拼接。
          这里只做「怎么切」的决策,不碰 IO/ffmpeg,便于单测:
            ① 时长怎么分段(均衡,避免出现 15+1 这种没法用的短尾段);
            ② 文案怎么分配(不重复念同一句,且在标点处断,读起来完整);
            ③ 各段在时间轴上的起点(裁参考视频用)。
@时间    :2026/09/21 22:30:00
@作者    :一源AI
@版本    :1.0
'''
import math
from typing import List, Tuple

# 模型单段生成上限(秒):方舟 Seedance 2.x 实测 15.2s,取 15 留余量
MAX_SEGMENT_SECONDS = 15

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
