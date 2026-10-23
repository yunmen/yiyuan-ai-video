# -*- coding: utf-8 -*-
"""
worker 侧词锚点消费:提示词注入 + metadata 导出。

实现与 backend app/services/script_schema.py 同构,一致性由
backend/tests/test_cross_worker_contract.py 钉死。
"""
import asyncio
from unittest.mock import AsyncMock

from app.tools.script_anchor import (
    build_script, estimate_timing, render_anchor_hint, resolve_tracks,
    resolve_window, split_words,
)
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


def test_script_anchor_skill_accepts_plain_text():
    """真实技能入口应把口播字符串转为分段，并按指定秒数生成时间轴。"""
    from app.core.skill_runtime import register_builtin_skills, run_skill

    register_builtin_skills()
    result = asyncio.run(run_skill("script-anchor", "", {
        "script": "欢迎来到本店，赶紧下单吧", "duration": "10",
    }))
    assert result.metadata["ok"] is True
    assert result.content["script"]["segments"][0]["text"] == "欢迎来到本店，赶紧下单吧"
    assert result.content["timing"]["duration_ms"] == 10000


def test_script_anchor_skill_accepts_empty_text():
    """空口播继续返回空脚本，不影响工作流后续步骤。"""
    from app.core.skill_runtime import register_builtin_skills, run_skill

    register_builtin_skills()
    result = asyncio.run(run_skill("script-anchor", "", {"script": ""}))
    assert result.metadata["ok"] is True
    assert result.content["script"] == {}


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
        tool._poll = AsyncMock(return_value=("https://x/a.mp4", False))

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
        tool._poll = AsyncMock(return_value=("https://x/a.mp4", False))

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
        tool._poll = AsyncMock(return_value=("https://x/a.mp4", False))

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


# —— P3-1:真实对齐窗口回灌(estimate_timing 的 segment_spans)——

def test_estimate_timing_prefers_real_segment_spans():
    """P3-1:传入真实段级窗口的段用真实秒,未传入的段仍走词数估算"""
    script = build_script(STRUCTURED, ["瞬时:reveal=赶紧下单"])
    timing = estimate_timing(
        script, 20, segment_spans={"script": {"start_ms": 12000, "end_ms": 20000}},
    )
    assert timing["estimated"] is False           # 至少一段是真实值,不再全估算
    seg = timing["segments"]["script"]
    assert (seg["start_ms"], seg["end_ms"]) == (12000, 20000)
    assert timing["segments"]["hook"]["start_ms"] == 0   # 未回灌段仍按估算从 0 起
    moment = timing["anchors"]["moment:reveal"]          # 锚点窗口被夹在真实段内
    assert 12000 <= moment["start_ms"] < moment["end_ms"] <= 20000


def test_estimate_timing_ignores_invalid_spans():
    """P3-1:非法或零长度的真实窗口被丢弃,该段退回估算,estimated 仍为 True"""
    script = build_script(STRUCTURED)
    timing = estimate_timing(
        script, 10, segment_spans={"script": {"start_ms": 500, "end_ms": 500}},
    )
    assert timing["estimated"] is True
    # 非法窗口被丢弃,该段仍产出合法的估算窗口(不因脏数据丢失整段)
    seg = timing["segments"]["script"]
    assert seg["end_ms"] > seg["start_ms"]
    assert (seg["start_ms"], seg["end_ms"]) != (500, 500)


# —— P3-2:备注轨道声明(tracks):词锚点 → 编排意图 ——

def test_build_script_parses_track_declarations():
    """备注里的 轨道:<type>=<ref> 解析为编排意图;默认选区→during、瞬时→at"""
    script = build_script(STRUCTURED, [
        "锚点:product=3-7", "瞬时:reveal=招牌小龙虾",
        "轨道:broll=selection:product",
        "轨道:sfx=at:moment:reveal",
    ])
    assert script["tracks"] == [
        {"type": "broll", "during": "selection:product", "source": "remark"},
        {"type": "sfx", "at": "moment:reveal", "source": "remark"},
    ]


def test_build_script_drops_dangling_track():
    """引用不存在锚点的轨道被丢弃,不留悬空轨;无声明时 tracks 为空"""
    assert build_script(STRUCTURED, ["轨道:sfx=moment:ghost"])["tracks"] == []
    assert build_script(STRUCTURED)["tracks"] == []


def test_tracks_use_default_anchors():
    """轨道可引用默认锚点(段 id 选区 / {段}_start 瞬时)"""
    script = build_script(STRUCTURED, [
        "轨道:broll=selection:script", "轨道:flash=moment:hook_start",
    ])
    assert script["tracks"] == [
        {"type": "broll", "during": "selection:script", "source": "remark"},
        {"type": "flash", "at": "moment:hook_start", "source": "remark"},
    ]


def test_resolve_tracks_from_declared_tracks():
    """build_script 产出的 tracks 可直接交给 resolve_tracks 解析成词窗口"""
    script = build_script(STRUCTURED, [
        "锚点:product=3-7", "瞬时:reveal=招牌小龙虾",
        "轨道:broll=selection:product", "轨道:sfx=at:moment:reveal",
    ])
    cues = resolve_tracks(script, script["tracks"])
    assert [c["type"] for c in cues] == ["broll", "sfx"]
    assert cues[0]["window"]["text"] == "".join(split_words(STRUCTURED["script"])[3:8])
    assert cues[1]["window"]["text"] == "招牌小龙虾"
