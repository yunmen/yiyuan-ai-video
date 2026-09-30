# -*- coding: utf-8 -*-
"""
词锚点编排(纯函数):分段 / 选区 / 瞬时点 / 时间估算。

核心约束:锚点一律用「词序号」,不用秒 —— 改台词后同一语义窗口仍应被命中。
"""
from app.services.script_schema import (
    build_script,
    build_segments,
    estimate_timing,
    parse_anchor_specs,
    resolve_tracks,
    resolve_window,
    split_words,
)

STRUCTURED = {
    "title": "夏日龙虾节开幕",
    "subtitle": "招牌小龙虾 39 元一份",
    "script": "欢迎来到本店,招牌小龙虾现在特惠,赶紧下单吧",
}


def test_split_words_ignores_punctuation():
    """标点与空白不计入词序号,英文数字连写算一个词"""
    assert split_words("招牌小龙虾,现在特惠!") == ["招", "牌", "小", "龙", "虾", "现", "在", "特", "惠"]
    assert split_words("T90 手机,只要 1999") == ["T90", "手", "机", "只", "要", "1999"]
    assert split_words("") == []
    assert split_words(None) == []


def test_build_segments_skips_empty():
    """空段不生成,避免把空文本喂给模型"""
    segments = build_segments({"title": "标题", "subtitle": "", "script": "口播"})
    assert [s["id"] for s in segments] == ["hook", "script"]
    assert segments[0]["role"] == "NARRATOR"
    assert segments[1]["role"] == "HOST"


def test_default_anchors_cover_each_segment():
    """无显式声明时也有可用锚点:每段一个整段选区 + 一个段首瞬时点"""
    script = build_script(STRUCTURED)
    assert {s["id"] for s in script["selections"]} == {"hook", "selling", "script"}
    assert {m["id"] for m in script["moments"]} == {"hook_start", "selling_start", "script_start"}
    assert all(item.get("source") == "default" for item in script["selections"])


def test_explicit_selection_by_word_range():
    """显式选区:3-7 词,越界裁剪,非法丢弃"""
    script = build_script(STRUCTURED, ["锚点:product=3-7"])
    window = resolve_window(script, "selection:product")
    assert window is not None
    assert window["segment"] == "script"        # 未指定段时取最后一段(口播)
    assert (window["from_word"], window["to_word"]) == (3, 7)
    # 越界:裁剪到最后一个词,不产生悬空窗口
    assert resolve_window(build_script(STRUCTURED, ["锚点:p=0-999"]), "selection:p")["to_word"] <= 20
    # 非法:直接丢弃,不静默落到 0 造成错位
    assert resolve_window(build_script(STRUCTURED, ["锚点:bad=abc"]), "selection:bad") is None


def test_explicit_selection_can_target_segment():
    script = build_script(STRUCTURED, ["锚点:headline=hook:0-2"])
    window = resolve_window(script, "selection:headline")
    assert window["segment"] == "hook"
    assert window["text"] == "".join(split_words(STRUCTURED["title"])[:3])


def test_moment_follows_text_after_rewrite():
    """P0 验收指标:改台词后,同一 moment 仍命中同一个语义窗口。

    秒锚点在改台词后必然错位;词锚点靠文本匹配重新定位,
    词序号变了但命中的仍是「招牌小龙虾」。
    """
    spec = ["瞬时:reveal=招牌小龙虾"]
    before = build_script({"script": "欢迎来到本店,招牌小龙虾现在特惠"}, spec)
    after = build_script({"script": "本店招牌小龙虾限时特惠中,欢迎光临"}, spec)

    w1 = resolve_window(before, "moment:reveal")
    w2 = resolve_window(after, "moment:reveal")
    assert w1["text"] == w2["text"] == "招牌小龙虾"
    assert w1["from_word"] != w2["from_word"]    # 位置变了,语义没变


def test_moment_unmatched_is_dropped():
    """文本未命中就丢弃:宁可没有这个锚点,也不能指着错误的词"""
    script = build_script(STRUCTURED, ["瞬时:reveal=不存在的词"])
    assert resolve_window(script, "moment:reveal") is None


def test_resolve_window_supports_bare_id():
    script = build_script(STRUCTURED, ["锚点:product=3-7"])
    assert resolve_window(script, "product")["id"] == "product"
    assert resolve_window(script, "selection:nope") is None
    assert resolve_window(script, "") is None


def test_resolve_tracks_drops_dangling_reference():
    """轨道引用不存在的锚点 → 丢弃,不留悬空轨"""
    script = build_script(STRUCTURED, ["锚点:product=3-7", "瞬时:reveal=招牌小龙虾"])
    cues = resolve_tracks(script, [
        {"type": "broll", "during": "selection:product", "asset": "product-shot"},
        {"type": "sfx", "at": "moment:reveal", "for_ms": 666},
        {"type": "sfx", "at": "moment:ghost"},           # 悬空引用
    ])
    assert len(cues) == 2
    assert cues[0]["window"]["text"] == "".join(split_words(STRUCTURED["script"])[3:8])
    assert cues[1]["window"]["text"] == "招牌小龙虾"


def test_estimate_timing_splits_by_word_count():
    """估算兜底:按词数占比摊分,锚点时间落在所属段内且不重叠越界"""
    script = build_script(STRUCTURED, ["锚点:product=3-7"])
    timing = estimate_timing(script, 10)
    assert timing["estimated"] is True
    assert timing["duration_ms"] == 10000
    total = sum(s["end_ms"] - s["start_ms"] for s in timing["segments"].values())
    assert total == 10000
    anchor = timing["anchors"]["selection:product"]
    seg = timing["segments"]["script"]
    assert seg["start_ms"] <= anchor["start_ms"] < anchor["end_ms"] <= seg["end_ms"]


def test_estimate_timing_handles_empty():
    assert estimate_timing({}, 5)["segments"] == {}
    assert estimate_timing(build_script(STRUCTURED), 0)["anchors"] == {}


def test_parse_anchor_specs_ignores_unknown_fields():
    segments = build_segments(STRUCTURED)
    selections, moments = parse_anchor_specs(["备注:xxx", "锚点:=", "乱写"], segments)
    assert selections == [] and moments == []
