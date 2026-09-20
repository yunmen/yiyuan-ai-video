# -*- coding: utf-8 -*-
"""视频工具:按素材数量自动选择生成模式(文生/图生/参考生)"""
import asyncio

from app.tools.video_tool import VideoGenTool
from app.schemas.base import ToolResult


def _make_tool():
    # 仅构造客户端,不发起网络请求
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _stub_modes(tool, calls):
    async def fake_t2v(prompt, **kwargs):
        calls.append("t2v")
        return ToolResult(content="https://x/t2v.mp4", metadata={"success": True})

    async def fake_i2v(prompt, **kwargs):
        calls.append("i2v")
        return ToolResult(content="https://x/i2v.mp4", metadata={"success": True})

    async def fake_r2v(prompt, **kwargs):
        calls.append("r2v")
        return ToolResult(content="https://x/r2v.mp4", metadata={"success": True})

    tool.text_to_video = fake_t2v
    tool.image_to_video = fake_i2v
    tool.reference_to_video = fake_r2v


def test_no_material_uses_text_to_video():
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    result = asyncio.run(tool.generate({"prompt": "海边日落", "materials": []}))
    assert calls == ["t2v"]
    assert result.metadata["success"] is True


def test_single_material_uses_image_to_video():
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    asyncio.run(tool.generate({"prompt": "动起来", "materials": ["https://x/a.jpg"]}))
    assert calls == ["i2v"]


def test_multiple_materials_uses_reference_to_video():
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    asyncio.run(tool.generate({"prompt": "合集", "materials": ["https://x/a.jpg", "https://x/b.jpg"]}))
    assert calls == ["r2v"]


def test_duration_clamp():
    tool = _make_tool()
    assert tool._clamp_duration(0) == 3      # 下限
    assert tool._clamp_duration(99) == 15    # 上限
    assert tool._clamp_duration("bad") == 5  # 非法值兜底
