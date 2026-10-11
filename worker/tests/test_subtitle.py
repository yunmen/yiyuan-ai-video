# -*- coding: utf-8 -*-
"""字幕烧录编排:文案来源与容错

这里的重点不是「烧得对不对」(那是 compose 层的单测),而是
**任何环节不可用都必须返回 None 保留原片** —— 已付费的生成结果不能被"加个字幕"弄丢。
"""
import asyncio

from app.core import subtitle as subtitle_mod
from app.core import compose as compose_mod
from app.core.subtitle import build_subtitle_cues
from app.core.compose import build_ass, video_canvas

SCRIPT = {
    "version": "1.0",
    "segments": [
        {"id": "script", "role": "HOST", "text": "第一句口播。第二句口播。",
         "words": ["第", "一", "句", "口", "播", "第", "二", "句", "口", "播"]},
    ],
}


def test_cues_from_script_anchors():
    """优先用 backend 已下发的词锚点脚本(segments[].text 就是原文案)"""
    cues = build_subtitle_cues({"script": SCRIPT}, duration_sec=5)
    assert len(cues) == 2
    assert cues[0].text == "第一句口播。"


def test_cues_fallback_to_structured():
    """没有词锚点脚本时,用原始结构化文案现算(保证老任务也能烧)"""
    cues = build_subtitle_cues({"structured": {"script": "招牌小龙虾现在特惠。赶紧下单。"}}, duration_sec=5)
    assert len(cues) == 2
    assert "小龙虾" in cues[0].text


def test_cues_fallback_to_plain_text():
    """数字人路径:口播文案在 params['text']"""
    cues = build_subtitle_cues({"text": "欢迎来到一源AI。今天聊聊降本。"}, duration_sec=5)
    assert len(cues) == 2


def test_no_text_means_no_cues():
    """没有文案就不烧,不能烧出空白字幕条"""
    assert build_subtitle_cues({}, duration_sec=5) == []
    assert build_subtitle_cues({"structured": {}}, duration_sec=5) == []


def test_cues_fallback_to_prompt_context():
    """老任务重跑时 params 可能缺 script/structured,但 prompt_context 的口播文案可兜底"""
    ctx = (
        "[商家信息](以下为必须逐字照念的台词,不得改写或替换措辞)\n"
        "大标题:夏日龙虾节\n副标题:招牌小龙虾 39 元\n口播文案:欢迎来到本店,小龙虾现在特惠。赶紧下单吧"
    )
    cues = build_subtitle_cues({"prompt_context": ctx}, duration_sec=5)
    # 大标题/副标题/口播三段都应有字幕条目(口播按标点再拆句,故条目数 >= 3)
    assert len(cues) >= 3
    assert any("小龙虾" in c.text for c in cues)


def test_burn_skips_without_ffmpeg(monkeypatch):
    """容器没装 ffmpeg:跳过,保留原片"""
    monkeypatch.setattr(subtitle_mod.compose, "available", lambda: False)
    assert asyncio.run(subtitle_mod.burn_subtitle("http://x/v.mp4", {"text": "你好"}, 5)) is None


def test_burn_skips_without_font(monkeypatch):
    """没有中文字体:跳过(ffmpeg 缺字体不报错,只会烧出豆腐块)"""
    monkeypatch.setattr(subtitle_mod.compose, "available", lambda: True)
    monkeypatch.setattr(subtitle_mod.compose, "resolve_subtitle_font", lambda: None)
    assert asyncio.run(subtitle_mod.burn_subtitle("http://x/v.mp4", {"text": "你好"}, 5)) is None


def test_burn_skips_without_cues(monkeypatch):
    """没有字幕文案:跳过"""
    monkeypatch.setattr(subtitle_mod.compose, "available", lambda: True)
    monkeypatch.setattr(subtitle_mod.compose, "resolve_subtitle_font", lambda: ("TestFont", None))
    assert asyncio.run(subtitle_mod.burn_subtitle("http://x/v.mp4", {}, 5)) is None


def test_burn_skips_when_download_fails(monkeypatch):
    """下载失败:跳过(不能因为取不到原片就抛异常)"""
    monkeypatch.setattr(subtitle_mod.compose, "available", lambda: True)
    monkeypatch.setattr(subtitle_mod.compose, "resolve_subtitle_font", lambda: ("TestFont", None))
    monkeypatch.setattr(subtitle_mod, "download_to_local", lambda *a, **k: None)
    assert asyncio.run(subtitle_mod.burn_subtitle("http://x/v.mp4", {"text": "你好"}, 5)) is None


# —— 字幕跟随头部(caption-tracking)——

def test_cues_attach_head_positions():
    """头部轨迹落在字幕时间窗中点附近时,字幕锚点贴到头部上沿中心"""
    # 头部在 t=2.5s,框 [x,y,w,h]=[0.1,0.2,0.2,0.3];锚点 = (x+w/2, y) = (0.2, 0.2)
    head_boxes = [(2.5, 0.1, 0.2, 0.2, 0.3)]
    cues = build_subtitle_cues(
        {"text": "欢迎来到一源AI。今天聊聊降本。"}, duration_sec=5, head_boxes=head_boxes,
    )
    assert len(cues) == 2
    for c in cues:
        assert c.pos is not None
        assert abs(c.pos[0] - 0.2) < 1e-6
        assert abs(c.pos[1] - 0.2) < 1e-6


def test_attach_head_skips_far_cue():
    """头部离字幕时间窗超过 2s:不贴,回退默认底部居中"""
    head_boxes = [(10.0, 0.1, 0.2, 0.2, 0.3)]
    cues = build_subtitle_cues(
        {"text": "第一句。第二句。"}, duration_sec=5, head_boxes=head_boxes,
    )
    assert all(c.pos is None for c in cues)


def test_build_ass_contains_pos():
    """带 pos 的 cue 在 ASS 里用 \\an2\\pos 锚定头部上沿中心"""
    cues = [compose_mod.Cue(start_ms=0, end_ms=1000, text="你好", pos=(0.2, 0.2))]
    ass = build_ass(cues, (1080, 1920))
    # 1080*0.2=216, 1920*0.2=384
    assert "\\pos(216,384)" in ass
    assert "Dialogue:" in ass
    assert "PlayResX: 1080" in ass


def test_video_canvas():
    """画幅 + 清晰度 → 像素尺寸"""
    assert video_canvas("9:16", "1080P") == (1080, 1920)
    assert video_canvas("16:9", "1080P") == (1920, 1080)
    assert video_canvas("1:1", "720P") == (720, 720)
    assert video_canvas("9:16", "unknown") is None


# —— 文案来源逐级回退(task 59 的坑)——
#
# 旧逻辑是 `if structured: script = build_script(structured)` —— 只判断字段非空,
# 不判断能否构建出 segments。build_script 只认 title/subtitle/script 三个键,
# 键名不符(或这三个值为空)时返回空 segments 且**不再往下回退**,
# 于是明明有台词却判「无可用字幕文案」→ 成片无声无字幕却判成功。

def test_unknown_structured_keys_fall_back_to_text():
    """structured 非空但键名不认识 → 必须继续往下退到 text,不能卡死在 structured"""
    cues = build_subtitle_cues(
        {"structured": {"body": "未知键名的文案"}, "text": "招牌小龙虾现在特惠。赶紧下单。"},
        duration_sec=5,
    )
    assert len(cues) == 2
    assert "小龙虾" in cues[0].text


def test_empty_structured_values_fall_back_to_prompt_context():
    """structured 的三个键都在但全是空串 → 继续退到 prompt_context 的口播原文"""
    ctx = "口播文案:欢迎来到本店,小龙虾现在特惠。赶紧下单吧"
    cues = build_subtitle_cues(
        {"structured": {"title": "", "subtitle": "  ", "script": ""}, "prompt_context": ctx},
        duration_sec=5,
    )
    assert cues, "有台词就必须烧出字幕,不能因为 structured 是空壳就跳过"


def test_script_segments_win_over_other_sources():
    """已下发的词锚点脚本优先级最高(它的 segments[].text 就是原文案)"""
    script = {
        "segments": [{"id": "script", "role": "HOST", "text": "脚本原文第一句。", "words": []}],
    }
    cues = build_subtitle_cues(
        {"script": script, "text": "别的台词。", "structured": {"script": "别的台词。"}},
        duration_sec=5,
    )
    assert cues[0].text == "脚本原文第一句。"


def test_all_sources_empty_means_no_cues():
    """三个来源都提取不出台词 → 不烧(不能烧出空白字幕条)"""
    assert build_subtitle_cues({"structured": {"body": "键名不认识"}, "prompt_context": "没有口播标签"}, duration_sec=5) == []


# —— P3-1:真实对齐时间轴回灌锚点窗口 ——

def test_anchor_timing_from_real_cues():
    """真实对齐 cue 归属回段后,锚点窗口落在真实秒内,来源标记 real"""
    script = {
        "version": "1.0",
        "segments": [
            {"id": "hook", "role": "NARRATOR", "text": "夏日龙虾节。", "words": list("夏日龙虾节")},
            {"id": "script", "role": "HOST", "text": "招牌小龙虾特惠。", "words": list("招牌小龙虾特惠")},
        ],
        "selections": [{"id": "product", "segment": "script", "from_word": 0, "to_word": 4}],
    }
    cues = [
        compose_mod.Cue(start_ms=0, end_ms=1000, text="夏日龙虾节。"),
        compose_mod.Cue(start_ms=1000, end_ms=3500, text="招牌小龙虾特惠。"),
    ]
    mapping, source = subtitle_mod.anchor_timing({"script": script}, cues, 4)
    assert source == "real"
    win = mapping["selection:product"]
    assert 1000 <= win["start_ms"] < win["end_ms"] <= 3500


def test_anchor_timing_estimate_source_when_cues_are_estimates():
    """纯估算 cue(无真实对齐)来源标记 estimate,数值回退估算,不冒充真实秒"""
    script = dict(SCRIPT)
    script["selections"] = [{"id": "product", "segment": "script", "from_word": 0, "to_word": 2}]
    cues = build_subtitle_cues({"script": script}, duration_sec=5)
    mapping, source = subtitle_mod.anchor_timing({"script": script}, cues, 5)
    assert source == "estimate"
    assert "selection:product" in mapping


def test_anchor_timing_empty_without_cues():
    """没有 cues(或没有文案)时不产出锚点窗口,metadata 不写(行为与改造前一致)"""
    assert subtitle_mod.anchor_timing({"script": SCRIPT}, [], 5) == ({}, "")
    assert subtitle_mod.anchor_timing({}, [], 5) == ({}, "")


# —— P3-3:锚点引用 → 真实时间窗(供合成层卡点)——

_ANCHOR_SCRIPT = {
    "version": "1.0",
    "segments": [
        {"id": "hook", "role": "NARRATOR", "text": "夏日龙虾节。", "words": list("夏日龙虾节")},
        {"id": "script", "role": "HOST", "text": "招牌小龙虾特惠。", "words": list("招牌小龙虾特惠")},
    ],
    "selections": [{"id": "product", "segment": "script", "from_word": 0, "to_word": 4}],
}


def test_anchor_windows_from_real_alignment():
    """有真实对齐:锚点引用解析成落在真实 cue 秒窗内的 [start,end]"""
    cues = [
        compose_mod.Cue(start_ms=0, end_ms=1000, text="夏日龙虾节。"),
        compose_mod.Cue(start_ms=1000, end_ms=3500, text="招牌小龙虾特惠。"),
    ]
    wins = subtitle_mod.anchor_windows({"script": _ANCHOR_SCRIPT}, cues, 4, ["selection:product"])
    assert len(wins) == 1
    s, e = wins[0]
    assert 1.0 <= s < e <= 3.5


def test_anchor_windows_falls_back_to_estimate():
    """无真实对齐(cues 为空)→ 退回 estimate_timing 估算窗,保证无字幕也能卡点"""
    wins = subtitle_mod.anchor_windows({"script": _ANCHOR_SCRIPT}, [], 5, ["selection:product"])
    assert len(wins) == 1
    s, e = wins[0]
    assert 0.0 <= s < e <= 5.0


def test_anchor_windows_skips_unknown_and_empty_refs():
    """未命中/非法引用直接跳过,不臆造位置;空 refs 返回空"""
    assert subtitle_mod.anchor_windows({"script": _ANCHOR_SCRIPT}, [], 5, ["selection:ghost"]) == []
    assert subtitle_mod.anchor_windows({"script": _ANCHOR_SCRIPT}, [], 5, []) == []
