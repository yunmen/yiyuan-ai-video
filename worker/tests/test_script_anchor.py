# -*- coding: utf-8 -*-
"""
worker 侧词锚点消费:提示词注入 + metadata 导出。

实现与 backend app/services/script_schema.py 同构,一致性由
backend/tests/test_cross_worker_contract.py 钉死。
"""
import asyncio
from unittest.mock import AsyncMock

from app.tools.script_anchor import build_script, render_anchor_hint, resolve_window
from app.tools.video_tool import VideoGenTool

STRUCTURED = {
    "title": "夏日龙虾节开幕",
    "subtitle": "招牌小龙虾 39 元一份",
    "script": "欢迎来到本店,招牌小龙虾现在特惠,赶紧下单吧",
}


def _make_tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def test_render_hint_lists_segments_without_duplicating_them():
    """渲染分段;默认锚点(整段选区/段首瞬时)与分段重复,不重复输出"""
    hint = render_anchor_hint(build_script(STRUCTURED))
    assert "[叙事分段]" in hint
    assert "hook(NARRATOR)" in hint and "script(HOST)" in hint
    assert "[词锚点]" not in hint          # 无显式锚点时不输出锚点段
    assert "招牌小龙虾 39 元一份" in hint


def test_render_hint_includes_explicit_anchors_only():
    script = build_script(STRUCTURED, ["锚点:product=3-7", "瞬时:reveal=招牌小龙虾"])
    hint = render_anchor_hint(script)
    assert "重点窗口 product" in hint
    assert "卡点 reveal" in hint
    assert "招牌小龙虾" in hint
    assert "第" in hint and "词" in hint     # 只说词序号,不说秒
    assert "ms" not in hint and "秒" not in hint


def test_render_hint_empty_script():
    assert render_anchor_hint({}) == ""
    assert render_anchor_hint(None) == ""


def test_generate_injects_anchor_hint_into_prompt():
    """有 script 时,改写模型应看到叙事分段与词锚点"""
    async def run():
        tool = _make_tool()
        captured = {}

        async def fake_optimize(prompt, system_prompt=None):
            captured["prompt"] = prompt
            return "改写后的prompt"

        tool._optimize_prompt = fake_optimize
        tool.client.post = AsyncMock(return_value={"id": "t1"})
        tool._poll = AsyncMock(return_value="https://x/a.mp4")

        await tool.generate({"prompt": "x", "script": build_script(STRUCTURED)})
        assert "[叙事分段]" in captured["prompt"]
        return captured

    asyncio.run(run())


def test_generate_exports_script_metadata():
    """metadata 导出分段/估算时间(P1 前兜底),随 usage 回写 backend"""
    async def run():
        tool = _make_tool()
        tool._optimize_prompt = AsyncMock(return_value="p")
        tool.client.post = AsyncMock(return_value={"id": "t1"})
        tool._poll = AsyncMock(return_value="https://x/a.mp4")

        result = await tool.generate({
            "prompt": "x", "duration": 10,
            "script": build_script(STRUCTURED, ["瞬时:reveal=招牌小龙虾"]),
        })
        meta = result.metadata.get("script") or {}
        assert [s["id"] for s in meta["segments"]] == ["hook", "selling", "script"]
        assert meta["timing"]["duration_ms"] == 10000
        assert meta["timing"]["estimated"] is True
        assert "moment:reveal" in meta["timing"]["anchors"]

    asyncio.run(run())


def test_generate_without_script_unchanged():
    """旧任务无 script 字段:不注入、不导出,行为完全不变"""
    async def run():
        tool = _make_tool()
        captured = {}

        async def fake_optimize(prompt, system_prompt=None):
            captured["prompt"] = prompt
            return "改写后的prompt"

        tool._optimize_prompt = fake_optimize
        tool.client.post = AsyncMock(return_value={"id": "t1"})
        tool._poll = AsyncMock(return_value="https://x/a.mp4")

        result = await tool.generate({"prompt": "扁平prompt"})
        assert "[叙事分段]" not in captured["prompt"]
        assert "script" not in (result.metadata or {})

    asyncio.run(run())


def test_moment_window_covers_matched_phrase():
    script = build_script(STRUCTURED, ["瞬时:reveal=招牌小龙虾"])
    window = resolve_window(script, "moment:reveal")
    assert window is not None
    assert window["text"] == "招牌小龙虾"
    assert window["at_word"] == window["from_word"]   # 卡点仍在串首词
