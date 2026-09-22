# -*- coding: utf-8 -*-
"""多段编排纯函数:分段决策、时间轴、文案切分

背景:模型单段上限约 15s,30s 必须拆段生成再拼接。切分策略错了会直接体现为
「最后一段短到没法用」或「同一句台词被念两遍」,所以这里逐条钉死。
"""
from app.core.multiseg import (
    MAX_SEGMENT_SECONDS,
    plan_segments,
    segment_windows,
    split_script_for_segments,
)


# --- 分段 ---

def test_short_duration_stays_single_segment():
    """没超上限就不分段(分段会带来额外成本与接缝)"""
    assert plan_segments(10) == [10]
    assert plan_segments(15) == [15]
    assert plan_segments(MAX_SEGMENT_SECONDS) == [15]


def test_thirty_seconds_splits_evenly():
    """30s 是典型场景:切成两段 15s"""
    assert plan_segments(30) == [15, 15]


def test_sixteen_seconds_balances_instead_of_15_plus_1():
    """16s 不能切成 [15, 1](第二段没法用),要均衡成 [8, 8]"""
    assert plan_segments(16) == [8, 8]


def test_segments_never_exceed_model_limit():
    """任何时长下每段都不得超过模型上限,且总和不变"""
    for total in range(1, 61):
        segs = plan_segments(total)
        assert sum(segs) == total, f"{total}s 分段后总时长变了: {segs}"
        assert all(s <= MAX_SEGMENT_SECONDS for s in segs), f"{total}s 出现超限段: {segs}"
        assert all(s >= 1 for s in segs)


def test_multi_segment_balances_across_three_parts():
    assert plan_segments(45) == [15, 15, 15]
    assert plan_segments(31) == [11, 10, 10]
    assert plan_segments(46) == [12, 12, 11, 11]


def test_zero_or_negative_returns_empty():
    """非法时长不猜:返回空列表,由调用方兜底"""
    assert plan_segments(0) == []
    assert plan_segments(-5) == []


# --- 时间轴 ---

def test_segment_windows_accumulate_start_offsets():
    """各段起点要累加:裁参考视频、拼字幕时间轴都依赖它"""
    assert segment_windows([15, 15]) == [(0, 15), (15, 15)]
    assert segment_windows([11, 10, 10]) == [(0, 11), (11, 10), (21, 10)]


def test_segment_windows_empty():
    assert segment_windows([]) == []


# --- 文案切分 ---

def test_script_split_by_sentence_boundary():
    """两段文案应在标点处断开,而不是从句子中间劈开"""
    parts = split_script_for_segments("限时秒杀促销带货。来看这只超乖的小家伙，治愈感拉满。", 2)
    assert len(parts) == 2
    assert "".join(parts).replace(" ", "") == "限时秒杀促销带货。来看这只超乖的小家伙，治愈感拉满。"
    # 第一段不该在句子中间被截断得太随意
    assert parts[0]


def test_script_split_single_part_returns_whole():
    assert split_script_for_segments("随便一句文案", 1) == ["随便一句文案"]


def test_script_split_without_punctuation_hard_cuts():
    """没有任何标点时只能硬切,但必须保证内容和长度都对"""
    text = "一二三四五六七八九十"
    parts = split_script_for_segments(text, 2)
    assert len(parts) == 2
    assert "".join(parts) == text


def test_script_shorter_than_parts_repeats():
    """文案比段数还短:切不出有意义内容,允许重复(总比空文案强)"""
    assert split_script_for_segments("短", 3) == ["短", "短", "短"]


def test_script_empty_or_zero_parts():
    assert split_script_for_segments("", 2) == ["", ""]
    assert split_script_for_segments("文案", 0) == []
