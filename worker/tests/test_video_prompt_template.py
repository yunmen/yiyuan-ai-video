# -*- coding: utf-8 -*-
"""
视频链路提示词:模板参数注入 + 素材语义不重复。

- 改写系统提示里的画幅/清晰度必须由本次任务参数注入(不能写死 9:16);
- 结构化上下文已含 [生成模式] 段,不得再拼一次「素材:」行。
"""
import asyncio
from unittest.mock import AsyncMock

from app.tools.prompt_template import (
    RATIO_BY_FIRST_FRAME,
    build_prompt_optimize_system,
    ratio_label,
    resolution_label,
)
from app.tools.video_tool import VideoGenTool


def _make_tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def test_system_prompt_injects_actual_ratio():
    """画幅来自任务参数:改成横版后提示词不能再要求竖版构图"""
    vertical = build_prompt_optimize_system(ratio="9:16", resolution="1080P")
    horizontal = build_prompt_optimize_system(ratio="16:9", resolution="720P")
    assert "竖版 9:16" in vertical and "1080P 高清" in vertical
    assert "横版 16:9" in horizontal and "720P 标清" in horizontal
    assert "9:16" not in horizontal


def test_ratio_label_handles_unknown_and_first_frame():
    """未知画幅原样描述(不谎报成竖版);i2v 场景画幅由首帧决定"""
    assert ratio_label("21:9") == "比例 21:9"
    assert ratio_label(None) == RATIO_BY_FIRST_FRAME
    assert ratio_label("") == RATIO_BY_FIRST_FRAME


def test_resolution_label_handles_unknown():
    assert resolution_label("720p") == "720P 标清"
    assert resolution_label("4K") == "4K"


def test_no_duplicated_material_line_when_context_present():
    """有结构化上下文时,[生成模式] 段已说明素材语义,不再重复拼接"""
    async def run():
        tool = _make_tool()
        captured = {}

        async def fake_optimize(prompt, system_prompt=None):
            captured["prompt"] = prompt
            captured["system"] = system_prompt
            return "改写后的prompt"

        tool._optimize_prompt = fake_optimize
        tool.client.post = AsyncMock(return_value={"id": "t1"})
        tool._poll = AsyncMock(return_value="https://x/a.mp4")

        await tool.generate({
            "prompt": "扁平prompt",
            "prompt_context": "[生成模式]\n参考生视频\n3 张参考画面",
            "material_hint": "3 张参考画面(...)",
            "materials": [],
        })
        assert "素材:" not in captured["prompt"], "素材语义重复出现,会稀释模型注意力"
        return captured

    asyncio.run(run())


def test_material_line_kept_for_legacy_flat_prompt():
    """旧任务没有 prompt_context 时,仍需补上素材语义"""
    async def run():
        tool = _make_tool()
        captured = {}

        async def fake_optimize(prompt, system_prompt=None):
            captured["prompt"] = prompt
            return "改写后的prompt"

        tool._optimize_prompt = fake_optimize
        tool.client.post = AsyncMock(return_value={"id": "t1"})
        tool._poll = AsyncMock(return_value="https://x/a.mp4")

        await tool.generate({"prompt": "扁平prompt", "material_hint": "无素材(纯文案生成)"})
        assert "素材:无素材" in captured["prompt"]

    asyncio.run(run())


def test_i2v_does_not_declare_ratio_in_prompt():
    """图生视频画幅由首帧决定,提示词里指定画幅会与模型实际行为矛盾"""
    async def run():
        tool = _make_tool()
        captured = {}

        async def fake_optimize(prompt, system_prompt=None):
            captured["system"] = system_prompt
            return "改写后的prompt"

        tool._optimize_prompt = fake_optimize
        tool.client.post = AsyncMock(return_value={"id": "t1"})
        tool._poll = AsyncMock(return_value="https://x/a.mp4")

        await tool.generate({"prompt": "x", "materials": ["https://x/frame.jpg"]})
        assert RATIO_BY_FIRST_FRAME in captured["system"]

    asyncio.run(run())
