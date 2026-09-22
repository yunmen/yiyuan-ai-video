# -*- coding: utf-8 -*-
'''
@文件    :align.py
@说明    :时间轴对齐(纯函数) — 用音频里的「真实停顿」替代按词数摊分的估算
@时间    :2026/09/21 19:00:00
@作者    :一源AI
@版本    :1.0
@说明    :为什么需要它:
          estimate_timing 是按词数占比把时长摊开,假设"说话匀速"。真实口播有停顿、
          有快慢,于是字幕会和口播错位 —— 烧上去反而更明显。

          本模块的做法:**不猜测语速,只找停顿**。
          用 ffmpeg 的 silencedetect 找出音频里的静音区间,取补集得到"语音段",
          再把句子按词数占比铺在**语音时间轴**上(跳过静音),最后映射回真实时间。
          于是字幕永远落在"真的在说话"的区间里,不会飘到停顿上。

          这是**句子级**对齐,不是词级:它能解决"字幕错位",但做不到卡拉 OK 逐字高亮,
          后者需要 P1 的词级时间戳(当前被网关额度阻断)。P1 落地后本模块可整体替换。

          全部是纯函数(输入文本/数字,输出 Cue),便于单测钉住语义。
'''
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.core.compose import Cue

# silencedetect 参数
#   noise:低于该音量视为静音。-35dB 对 TTS 口播较合适(太严会漏掉停顿,太松会把呼吸当语音)
#   d    :静音至少持续这么久才算一次停顿,避免把字间微小间隙当成分句点
DEFAULT_NOISE_DB = "-35dB"
DEFAULT_MIN_SILENCE = 0.25
# 短于该时长的"语音段"视为噪声丢弃(口播里几乎不会有 <0.15s 的有意义语音)
MIN_SPEECH_SEC = 0.15

_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?\d+(?:\.\d+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*(-?\d+(?:\.\d+)?)")


def parse_silence_ranges(text: str) -> List[Tuple[float, float]]:
    """解析 ffmpeg silencedetect 输出 → 静音区间列表(秒)

    输出形如:
      [silencedetect @ 0x...] silence_start: 1.021678
      [silencedetect @ 0x...] silence_end: 1.509297 | silence_duration: 0.487619

    配对:遇到 start 记为待闭合;遇到 end 与最近的未闭合 start 闭合。
    末尾若仍在静音(只有 start 没有 end)则丢弃 —— 尾部静音不影响句子分配。
    """
    ranges: List[Tuple[float, float]] = []
    pending: Optional[float] = None
    for line in str(text or "").splitlines():
        start_match = _SILENCE_START_RE.search(line)
        if start_match and pending is None:
            pending = float(start_match.group(1))
            continue
        end_match = _SILENCE_END_RE.search(line)
        if end_match and pending is not None:
            end = float(end_match.group(1))
            if end > pending:
                ranges.append((pending, end))
            pending = None
    return ranges


def speech_segments(
    silences: List[Tuple[float, float]], duration_sec: float, min_speech: float = MIN_SPEECH_SEC,
) -> List[Tuple[float, float]]:
    """静音区间的**补集** = 语音段(秒);过短片段当噪声丢掉"""
    duration = max(0.0, float(duration_sec or 0))
    if duration <= 0:
        return []
    segments: List[Tuple[float, float]] = []
    cursor = 0.0
    for start, end in sorted(silences or []):
        start = max(0.0, min(start, duration))
        end = max(0.0, min(end, duration))
        if start > cursor:
            segments.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        segments.append((cursor, duration))
    return [(a, b) for a, b in segments if (b - a) >= min_speech]


def _speech_index(t: float, segments: List[Tuple[float, float]]) -> int:
    """语音时间轴上的位置落在第几个语音段"""
    acc = 0.0
    for idx, (start, end) in enumerate(segments):
        span = end - start
        if t <= acc + span:
            return idx
        acc += span
    return len(segments) - 1


def map_speech_time(t: float, segments: List[Tuple[float, float]]) -> float:
    """语音时间轴(不含静音的累计时长) → 真实时间(秒)

    超出总语音时长时收敛到最后一段末尾,保证 cue 不越界。
    """
    if not segments:
        return t
    acc = 0.0
    for start, end in segments:
        span = end - start
        if t <= acc + span:
            return start + (t - acc)
        acc += span
    return segments[-1][1]


def align_sentences(
    sentences: List[Tuple[str, int]], segments: List[Tuple[float, float]], duration_sec: float,
) -> List[Cue]:
    """把句子按词数占比铺到语音时间轴上,再映射回真实时间

    入参 sentences 为 (句子文本, 词数) 列表,顺序即口播顺序。
    没有语音段(如纯静音/无音轨)时返回空列表 —— 调用方应回退到估算时间轴。
    """
    if not sentences or not segments:
        return []
    total_speech = sum(b - a for a, b in segments)
    if total_speech <= 0:
        return []
    total_words = sum(words for _, words in sentences) or 1

    cues: List[Cue] = []
    cursor = 0.0
    for text, words in sentences:
        span = total_speech * (words or 1) / total_words
        start = map_speech_time(cursor, segments)
        idx_from = _speech_index(cursor, segments)
        idx_to = _speech_index(cursor + span, segments)
        if idx_to > idx_from:
            # 这句跨越了停顿:截断到本段末尾 —— 字幕应该在"真的说完"时消失,
            # 而不是挂到停顿里(观众会明显觉得字幕比嘴慢)
            end = segments[idx_from][1]
        else:
            end = map_speech_time(cursor + span, segments)
        if end <= start:  # 极端比例下可能倒挂,退化为不截断
            end = map_speech_time(cursor + span, segments)
        cues.append(Cue(start_ms=round(start * 1000), end_ms=round(max(end, start) * 1000), text=text))
        cursor += span
    # 最后一条不超出视频总时长
    duration_ms = round(float(duration_sec or 0) * 1000)
    if cues and duration_ms and cues[-1].end_ms > duration_ms:
        cues[-1].end_ms = duration_ms
    return cues


def build_silence_cmd(
    media: str, noise: str = DEFAULT_NOISE_DB, min_silence: float = DEFAULT_MIN_SILENCE,
    ffmpeg: str = "ffmpeg",
) -> List[str]:
    """构造 silencedetect 命令(只读分析,不产出文件)"""
    return [
        ffmpeg, "-hide_banner", "-i", media,
        "-af", f"silencedetect=noise={noise}:d={min_silence}", "-f", "null", "-",
    ]
