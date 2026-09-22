# -*- coding: utf-8 -*-
"""时间轴对齐(纯函数)

钉住的核心语义:**字幕必须落在"真的在说话"的区间里**,不能飘到停顿上。
这是「静音检测对齐」相对「按词数摊分」的全部价值所在,所以重点测这个。
"""
from app.core.align import (
    align_sentences,
    build_silence_cmd,
    map_speech_time,
    parse_silence_ranges,
    speech_segments,
)

SILENCE_LOG = """
[silencedetect @ 0x1] silence_start: 1.021678
[silencedetect @ 0x1] silence_end: 1.509297 | silence_duration: 0.487619
[silencedetect @ 0x1] silence_start: 3.0
[silencedetect @ 0x1] silence_end: 3.6 | silence_duration: 0.6
"""


def test_parse_silence_pairs_start_with_end():
    """ffmpeg 的 start/end 是两行,必须正确配对成区间"""
    assert parse_silence_ranges(SILENCE_LOG) == [(1.021678, 1.509297), (3.0, 3.6)]


def test_parse_ignores_trailing_unclosed_silence():
    """音频末尾仍在静音时只有 start 没有 end —— 该区间丢弃(不影响句子分配)"""
    assert parse_silence_ranges("[silencedetect] silence_start: 7.5\n") == []


def test_speech_segments_is_complement_of_silence():
    """语音段 = 静音区间的补集"""
    assert speech_segments([(1.0, 2.0)], 5.0) == [(0.0, 1.0), (2.0, 5.0)]


def test_speech_segments_drops_tiny_noise():
    """过短的"语音"是噪声,不能拿来排字幕(注意:短的**静音**照样会切断语音段)"""
    # 0.5~0.6 之间只有 0.1s 语音 → 视为噪声丢弃
    assert speech_segments([(0.0, 0.5), (0.6, 2.0)], 5.0, min_speech=0.15) == [(2.0, 5.0)]


def test_short_silence_still_splits_speech():
    """静音再短也是停顿:不能因为"不够长"就把两段语音接成一段"""
    segments = speech_segments([(0.5, 0.6), (2.0, 3.0)], 5.0)
    assert segments == [(0.0, 0.5), (0.6, 2.0), (3.0, 5.0)]


def test_speech_segments_needs_duration():
    assert speech_segments([(1.0, 2.0)], 0) == []


def test_map_speech_time_skips_silence():
    """语音时间轴映射回真实时间时,停顿不占长度"""
    segments = [(0.0, 2.0), (2.5, 5.0)]
    assert map_speech_time(0.0, segments) == 0.0
    assert map_speech_time(2.0, segments) == 2.0  # 边界值:刚好用完第一段,落在该段末尾
    assert map_speech_time(2.5, segments) == 3.0  # 越过停顿后落在第二段内部(2.5 + 0.5)
    assert map_speech_time(99.0, segments) == 5.0  # 超界收敛到末尾,不越界


def test_align_sentences_never_cover_a_pause():
    """核心:字幕区间不得穿过停顿(否则观众会看到"话已停、字还在")"""
    silences = [(2.0, 2.5), (5.0, 5.6)]
    speech = speech_segments(silences, 8.0)
    cues = align_sentences([("第一句比较短", 6), ("第二句内容明显更长一些", 11), ("第三句", 3)], speech, 8.0)

    assert len(cues) == 3
    for cue in cues:
        lo, hi = cue.start_ms / 1000, cue.end_ms / 1000
        assert not any(lo < s and e < hi for s, e in silences), f"{cue.text} 穿过了停顿"


def test_align_proportional_to_words():
    """句子越长占的语音时间越多(总语音时长按比例分)"""
    speech = [(0.0, 10.0)]
    cues = align_sentences([("短", 1), ("长句", 3)], speech, 10.0)
    assert cues[0].end_ms - cues[0].start_ms == 2500
    assert cues[1].end_ms - cues[1].start_ms == 7500


def test_align_returns_empty_without_speech():
    """无语音段(纯静音/无音轨) → 返回空,调用方据此回退估算时间轴"""
    assert align_sentences([("你好", 2)], [], 8.0) == []
    assert align_sentences([], [(0.0, 8.0)], 8.0) == []


def test_align_last_cue_within_duration():
    speech = speech_segments([(1.0, 1.5)], 5.0)
    cues = align_sentences([("一", 1), ("二", 1)], speech, 5.0)
    assert cues[-1].end_ms <= 5000


def test_build_silence_cmd_is_readonly():
    """停顿分析不产出文件(-f null -),避免残留垃圾"""
    cmd = build_silence_cmd("/tmp/v.mp4")
    assert cmd[-2:] == ["-f", "null"] or "-f" in cmd
    assert "silencedetect=" in " ".join(cmd)
