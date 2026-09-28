# -*- coding: utf-8 -*-
"""P1-6 一致性资产:同一任务的替换素材与替换语义,必须被所有生成入口一致使用

这里钉的是一个真实缺陷:「改一句台词重生成」时,局部重跑的编辑分支此前**完全不传 images**,
于是首轮替换进去的商品/人物会被换回原片元素 —— 用户看到的就是"重跑一次,复刻白做了"。
另一处是 replace_intent 只在单段首轮传了:漏传会让重跑段与首轮走不同的画幅策略。
"""
import asyncio
from unittest.mock import AsyncMock

from app.core import subtitle
from app.schemas.base import ToolResult
from app.tools.video_tool import VideoGenTool, _replace_assets


def _run(coro):
    return asyncio.run(coro)


def _make_tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


# --- 资产取法:所有入口共用同一份 ---

def test_replace_assets_drops_videos_and_blanks():
    """视频素材由 reference_video 承载,混进 images 会被上游直接判任务失败"""
    params = {"materials": ["https://x/a.jpg", "https://x/ref.mp4", "", "https://x/b.png", None]}
    assert _replace_assets(params) == ["https://x/a.jpg", "https://x/b.png"]


def test_replace_assets_keeps_order_and_deduplicates():
    """保持原顺序(参考图顺序会影响模型理解),重复项去掉"""
    params = {"materials": ["https://x/a.jpg", "https://x/a.jpg", "https://x/b.jpg"]}
    assert _replace_assets(params) == ["https://x/a.jpg", "https://x/b.jpg"]


def test_replace_assets_empty_inputs():
    assert _replace_assets({}) == []
    assert _replace_assets({"materials": None}) == []


# --- 局部重跑:资产与语义必须与首轮同源 ---

def _regen_params(**extra):
    params = {
        "reference_video": "https://x/ref.mp4",
        "original_video": "https://x/orig.mp4",
        "materials": ["https://x/product.jpg", "https://x/ref.mp4"],
        "intent": ["product"],
        "script": {"segments": [
            {"id": "s0", "text": "老台词", "timing": {"start_ms": 0, "end_ms": 5000}},
        ]},
    }
    params.update(extra)
    return params


def test_regenerate_passes_same_assets_and_intent(monkeypatch):
    """重跑段必须带上与首轮同源的替换素材与替换意图

    images 漏传 → 重跑段照抄原片商品;replace_intent 漏传 → 画幅改走"跟随参考视频",
    与首轮(有意图时强制对齐目标画幅)不一致,拼回原片时画幅对不上。
    """
    tool = _make_tool()
    monkeypatch.setattr(tool, "_trim_video_window", AsyncMock(return_value="https://x/window.mp4"))
    edit = AsyncMock(return_value=ToolResult(content="https://x/seg.mp4", metadata={"success": True}))
    monkeypatch.setattr(tool, "edit_video", edit)
    monkeypatch.setattr(subtitle, "burn_subtitle", AsyncMock(return_value="https://x/burned.mp4"))
    monkeypatch.setattr(tool, "_splice_segment", AsyncMock(return_value="https://x/final.mp4"))

    result = _run(tool.regenerate_segment(_regen_params(), segment_index=0, new_text="新台词"))
    assert result.metadata["success"] is True
    kwargs = edit.call_args.kwargs
    assert kwargs["images"] == ["https://x/product.jpg"], "重跑必须带上同源替换素材(视频素材剔除)"
    assert kwargs["replace_intent"] == ["product"], "重跑必须带上替换意图,否则画幅策略与首轮不一致"


def test_regenerate_without_assets_sends_none(monkeypatch):
    """没有素材的任务不能传空列表:images=None 才是"不替换"的正确表达"""
    tool = _make_tool()
    monkeypatch.setattr(tool, "_trim_video_window", AsyncMock(return_value="https://x/window.mp4"))
    edit = AsyncMock(return_value=ToolResult(content="https://x/seg.mp4", metadata={"success": True}))
    monkeypatch.setattr(tool, "edit_video", edit)
    monkeypatch.setattr(subtitle, "burn_subtitle", AsyncMock(return_value=None))
    monkeypatch.setattr(tool, "_splice_segment", AsyncMock(return_value=None))

    _run(tool.regenerate_segment(
        _regen_params(materials=[], intent=[]), segment_index=0, new_text="新台词",
    ))
    assert edit.call_args.kwargs["images"] is None
    assert edit.call_args.kwargs["replace_intent"] == []
