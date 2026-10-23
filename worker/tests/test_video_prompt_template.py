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
        tool._poll = AsyncMock(return_value=("https://x/a.mp4", False))

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
        tool._poll = AsyncMock(return_value=("https://x/a.mp4", False))

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
        tool._poll = AsyncMock(return_value=("https://x/a.mp4", False))

        await tool.generate({"prompt": "x", "materials": ["https://x/frame.jpg"]})
        assert RATIO_BY_FIRST_FRAME in captured["system"]

    asyncio.run(run())


def test_edit_mode_uses_dedicated_system_prompt():
    """v2v 视频编辑(复刻)必须用编辑专用系统提示:保持原片体裁,不注入带货营销基调。

    实测踩坑:非广告原片 + 换人物意图,通用「营销导演/卖点/促销/行动号召」系统提示
    会把成片强行写成带货广告 —— 编辑链路的改写目标只是"替换指定元素"。
    注意:纯复刻无文案时,generate 还会调 _optimize_prompt 生成口播文案(复刻脚本兜底),
    所以必须按调用顺序断言,只检查第 1 阶段(prompt 改写)的系统提示。
    """
    async def run():
        tool = _make_tool()
        calls = []  # [(system_prompt, ...)],按调用顺序记录

        async def fake_optimize(prompt, system_prompt=None):
            calls.append(system_prompt)
            return "改写后的prompt"

        tool._optimize_prompt = fake_optimize
        tool.client.post = AsyncMock(return_value={"id": "t1"})
        tool._poll = AsyncMock(return_value=("https://x/a.mp4", False))

        await tool.generate({
            "prompt": "x",
            "gen_mode": "v2v",
            "reference_video": "https://x/ref.mp4",
            "intent": ["person"],
            "material_hint": "1 段参考视频",
        })
        assert calls, "prompt 改写阶段未被调用"
        system = calls[0] or ""
        # 编辑专用基调:编辑指令 + 体裁跟随原片
        assert "视频编辑模型" in system
        assert "体裁" in system
        # 不得再出现通用链路的带货营销基调(编辑提示中的"禁止凭空加入强钩子"是禁令,不算)
        assert "你是短视频营销导演" not in system
        assert "突出卖点与促销信息" not in system
        assert "带货质感" not in system

    asyncio.run(run())


def test_edit_template_requires_quality_contract():
    """编辑模板采用完整契约，不再限制为三百字短指令。"""
    system = build_prompt_optimize_system(edit=True)
    for title in ("本段目标摘要", "修改目标", "保留要求", "目标优先级", "相对时间轴", "声音策略", "参考图职责", "验收要求"):
        assert title in system
    assert "不超过 300 字" not in system
    assert "不得编造秒数" in system


def test_edit_contract_preserves_structured_output_and_tail():
    """整理结构化输出时保留正文与结束标记后的本段约束，不重复契约。"""
    prompt = "本段目标摘要：替换指定人物\n【片段质量契约开始】\n修改目标：新人物\n保留要求：上方示意图静止\n相对时间轴：0至2秒保持原动作\n【片段质量契约结束】\n[本段台词]准确台词"
    result = VideoGenTool._build_edit_contract(prompt, "换人物硬约束", "", "@图片1 绑定人物", ["图"], 2.0, True)
    assert result.count("【片段质量契约开始】") == 1
    for text in ("上方示意图静止", "0至2秒保持原动作", "准确台词", "换人物硬约束", "@图片1 绑定人物"):
        assert text in result


def test_edit_contract_unknown_time_and_audio_off():
    """未知时长不伪造秒数，关闭声音时不残留保留原声指令。"""
    result = VideoGenTool._build_edit_contract("旧版编辑指令", "", "", "", [], None, False)
    assert "旧版编辑指令" in result
    assert "全段随参考片段" in result
    assert "0至" not in result
    assert "声音生成开关关闭" in result
    assert "保留原声" not in result
    assert "@图片1" not in result


def test_edit_payload_always_contains_contract(monkeypatch):
    """直接编辑或改写降级为原文时，实际提交仍有七节契约且不请求付费模型。"""
    from app.core import media_prep
    from app.schemas.base import ToolResult

    monkeypatch.setattr(media_prep, "fit_reference_video", AsyncMock(return_value="https://x/ref.mp4"))
    monkeypatch.setattr(media_prep, "probe_duration", AsyncMock(return_value=13.176))
    tool = _make_tool()
    captured = {}

    async def fake_submit(payload, *args, **kwargs):
        """截获最终请求，隔离真实模型服务。"""
        captured.update(payload)
        return ToolResult(content="https://x/out.mp4", metadata={"success": True})

    tool._submit_and_poll = fake_submit
    asyncio.run(tool.edit_video("替换人物但保留原动作", reference_video="https://x/ref.mp4"))
    prompt = captured["prompt"]
    for title in ("本段目标摘要", "修改目标", "保留要求", "目标优先级", "相对时间轴", "声音策略", "参考图职责", "验收要求"):
        assert title + "：" in prompt
    assert "0至13.176秒" in prompt
    assert "替换人物但保留原动作" in prompt
    assert "仅替换人物图片不自动重新配音" in prompt
