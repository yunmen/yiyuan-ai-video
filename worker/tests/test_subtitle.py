# -*- coding: utf-8 -*-
"""字幕烧录编排:文案来源与容错

这里的重点不是「烧得对不对」(那是 compose 层的单测),而是
**任何环节不可用都必须返回 None 保留原片** —— 已付费的生成结果不能被"加个字幕"弄丢。
"""
import asyncio

from app.core import subtitle as subtitle_mod
from app.core.subtitle import build_subtitle_cues

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
