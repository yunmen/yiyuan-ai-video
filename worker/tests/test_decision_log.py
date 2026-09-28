# -*- coding: utf-8 -*-
"""P2-9 决策日志 + 成本快照:每次生成都应记录"用了哪个网关 / 模型 / 分辨率 / 时长 / 估算成本"

费用治理的数据基础:事后可回溯一个任务花了多少生成时长、花在哪些模型上。
只记**成功提交**(网关名由 _with_failover 回填),失败的调用不计入 —— 失败的任务没有"选用"可言。
"""
import asyncio
from unittest.mock import AsyncMock

from app.schemas.base import ToolResult
from app.settings import config
from app.tools.video_tool import VideoGenTool


def _run(coro):
    return asyncio.run(coro)


def _make_tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _stamp_decision(decision):
    """模拟 _submit_and_poll 成功提交:_with_failover 会在成功后回填网关"""
    if decision:
        decision["gateway_name"] = "gw-x"
        decision["gateway_url"] = "http://gw-x/v1"
    return ToolResult(content="https://x/v.mp4", metadata={"success": True})


def test_decision_log_records_successful_submit(monkeypatch):
    """成功提交 → 决策日志记一条,且网关名由 failover 回填

    这里直接桩掉 _submit_and_fix_real_person(image_to_video 的提交入口),
    绕过其中的真人检测等副作用,只验证"决策记录被正确建立与回填"。
    """
    tool = _make_tool()

    async def _fake_fix(payload, label, duration, resolution, ratio, route,
                       checkpoint=None, on_stage=None, *, allow_video_fix=False,
                       no_image_fallback=None, decision=None):
        # 模拟 _with_failover 在成功后回填网关
        if decision:
            decision["gateway_name"] = "gw-x"
            decision["gateway_url"] = "http://gw-x/v1"
        return ToolResult(content="https://x/v.mp4", metadata={"success": True})

    monkeypatch.setattr(tool, "_submit_and_fix_real_person", _fake_fix)
    result = _run(tool.image_to_video("p", duration=5, ratio="9:16", resolution="720p", input_image="x"))
    assert result.content == "https://x/v.mp4"
    assert len(tool._decision_log) == 1
    entry = tool._decision_log[0]
    assert entry["route"] == "i2v"
    assert entry["model"] == config.VIDEO_MODEL_I2V
    assert entry["duration"] == 5
    assert entry["estimated_seconds"] == 5
    assert entry["gateway_name"] == "gw-x"


def test_decision_log_ignores_failed_submit(monkeypatch):
    """提交失败 → 不记入决策日志(失败的任务没有"选用")"""
    tool = _make_tool()

    async def _fail_no_stamp(payload, label, duration, resolution, ratio, route,
                             checkpoint=None, on_stage=None, *, allow_video_fix=False,
                             no_image_fallback=None, decision=None):
        return tool._fail("提交失败", "request_error")

    monkeypatch.setattr(tool, "_submit_and_fix_real_person", _fail_no_stamp)
    result = _run(tool.image_to_video("p", duration=5, ratio="9:16", resolution="720p", input_image="x"))
    assert result.metadata["success"] is False
    assert not tool._decision_log, "失败的提交不应记入决策日志"


def test_attach_decision_log_writes_cost_snapshot():
    """收尾时把决策日志聚合成 cost_snapshot(总时长 / 动作数 / 按模型分类)"""
    tool = _make_tool()
    tool._decision_log = [
        {"route": "edit", "model": "m1", "duration": 10, "estimated_seconds": 10, "gateway_name": "gw"},
        {"route": "edit", "model": "m1", "duration": 5, "estimated_seconds": 5, "gateway_name": "gw"},
        {"route": "t2v", "model": "m2", "duration": 8, "estimated_seconds": 8, "gateway_name": "gw"},
    ]
    result = ToolResult(content="x", metadata={"success": True})
    tool._attach_decision_log(result)
    snap = result.metadata["cost_snapshot"]
    assert snap["total_seconds"] == 23
    assert snap["actions"] == 3
    assert snap["by_model"] == {"m1": 15, "m2": 8}
    assert len(result.metadata["decision_log"]) == 3


def test_attach_decision_log_skips_when_empty():
    """没有任何决策记录时不写入(避免给每条成功任务都塞空字段)"""
    tool = _make_tool()
    tool._decision_log = []
    result = ToolResult(content="x", metadata={"success": True})
    tool._attach_decision_log(result)
    assert "cost_snapshot" not in result.metadata
    assert "decision_log" not in result.metadata
