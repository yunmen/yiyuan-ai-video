# -*- coding: utf-8 -*-
"""词级对齐(ASR 回灌)的字幕切分语义钉住

cues_from_words 是纯函数:输入 ASR 词级时间戳 + 句子列表,输出字幕 cue。
它是"字幕能不能卡在发音上"的唯一决定点,必须钉住三种边界:
  ① 句时间 = 首词 start ~ 末词 end;
  ② ASR 词数与文案不一致时,末句吃掉剩余词(不能丢尾巴、不能越界);
  ③ 非法时间戳被剔除,而不是把整句时间算成倒挂。
"""
from app.core.asr import cues_from_words


def _words(*pairs):
    """构造词级时间戳:[(词, start秒, end秒), ...]"""
    return [{"word": w, "start": s, "end": e} for w, s, e in pairs]


def test_sentence_takes_first_to_last_word_time():
    """句时间取首词 start ~ 末词 end —— 这正是词级对齐相对"按词数摊分"的价值"""
    words = _words(("招", 0.0, 0.3), ("牌", 0.3, 0.6), ("龙", 1.2, 1.5), ("虾", 1.5, 1.8))
    cues = cues_from_words(words, [("招牌", 2), ("龙虾", 2)])
    assert [(c.start_ms, c.end_ms) for c in cues] == [(0, 600), (1200, 1800)]
    assert [c.text for c in cues] == ["招牌", "龙虾"]


def test_extra_asr_words_are_absorbed_by_last_sentence():
    """ASR 词数多于文案(语气词/断词)时:末句吃掉剩余词,字幕不丢尾巴"""
    words = _words(
        ("欢", 0.0, 0.2), ("迎", 0.2, 0.4), ("光", 0.4, 0.6),
        ("临", 0.6, 0.8), ("啊", 0.8, 1.0),
    )
    cues = cues_from_words(words, [("欢迎", 2), ("光临", 2)])
    assert len(cues) == 2
    assert cues[-1].end_ms == 1000          # 末句覆盖到最后一个词


def test_fewer_asr_words_still_produces_all_sentences():
    """ASR 词数少于文案时也不能少字幕:按比例切分,每句仍拿到词"""
    words = _words(("甲", 0.0, 0.5), ("乙", 0.5, 1.0))
    cues = cues_from_words(words, [("第一句", 3), ("第二句", 3), ("第三句", 3)])
    assert len(cues) == 3
    assert cues[0].start_ms == 0
    assert cues[-1].end_ms == 1000
    # 时间必须单调不减,不能出现倒挂
    assert all(b.start_ms >= a.start_ms for a, b in zip(cues, cues[1:]))


def test_invalid_timestamps_are_dropped():
    """end ≤ start 的坏词被剔除:否则整句时间倒挂,该句字幕会被丢掉"""
    words = [{"word": "a", "start": 1.0, "end": 0.5}, {"word": "b", "start": 0.0, "end": 0.4}]
    cues = cues_from_words(words, [("ab", 2)])
    assert [(c.start_ms, c.end_ms) for c in cues] == [(0, 400)]


def test_empty_inputs_return_empty():
    assert cues_from_words([], [("任意", 1)]) == []
    assert cues_from_words(_words(("a", 0.0, 1.0)), []) == []
    assert cues_from_words([{"word": "a", "start": 1.0, "end": 0.5}], [("a", 1)]) == []
