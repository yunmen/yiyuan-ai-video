# -*- coding: utf-8 -*-
"""编排服务:断点续跑闭环 —— 启动时拉取检查点并透传给工具;工具经 on_stage 回写;
失败重试(同 task_id)时复用已回写检查点,跳过已完成阶段。"""
import asyncio

import pytest
from arq.worker import Retry

from app.services import base as base_mod
from app.services.base import BaseGenService
from app.schemas.base import ToolResult
from app.settings import config


def test_run_passes_fetched_checkpoint_to_tool(monkeypatch):
    """run 启动时拉取的 checkpoint 应原样传给 tool.generate"""
    seen = {}

    class Tool:
        async def generate(self, params, checkpoint=None, on_stage=None):
            seen["checkpoint"] = checkpoint
            return ToolResult(content="https://x/v.mp4", metadata={"success": True})

    async def fake_fetch(notify_url, task_id, token=None):
        return {"checkpoint": {"stage": 2, "external_task_id": "task-abc"}, "progress": 30}

    async def fake_notify(url, payload, token=None):
        pass

    async def fake_save(url, payload, token=None):
        pass

    monkeypatch.setattr(base_mod, "fetch_checkpoint", fake_fetch)
    monkeypatch.setattr(base_mod, "notify", fake_notify)
    monkeypatch.setattr(base_mod, "checkpoint_save", fake_save)

    class Svc(BaseGenService):
        tool_class = Tool

    asyncio.run(Svc().run(7, "http://cb/api/user/v1/task/checkpoint", {"prompt": "p"}, ctx={"job_try": 1}))
    assert seen["checkpoint"] == {"stage": 2, "external_task_id": "task-abc"}


def test_run_retry_reuses_checkpoint_on_next_attempt(monkeypatch):
    """首次失败抛 Retry;下一次(同 task_id)重跑时应带上工具阶段回写的检查点"""
    calls = {"n": 0, "checkpoints": []}
    saved = []

    class Tool:
        async def generate(self, params, checkpoint=None, on_stage=None):
            calls["n"] += 1
            calls["checkpoints"].append(checkpoint)
            if on_stage:
                # 模拟:已提交外部任务并回写阶段2(断点)
                await on_stage(2, {"external_task_id": "ext-1"})
            if calls["n"] == 1:
                return ToolResult(content="提交异常", metadata={"success": False, "error": "提交异常"})
            return ToolResult(content="https://x/v.mp4", metadata={"success": True})

    async def fake_fetch(notify_url, task_id, token=None):
        # 第一次尝试:库中无检查点;重试时:返回上次回写的检查点(模拟 backend 落库后回传)
        if calls["n"] == 0:
            return {"checkpoint": {}, "progress": 5}
        return {"checkpoint": {"stage": 2, "external_task_id": "ext-1"}, "progress": 30}

    async def fake_notify(url, payload, token=None):
        pass

    async def fake_save(url, payload, token=None):
        saved.append(payload)

    monkeypatch.setattr(base_mod, "fetch_checkpoint", fake_fetch)
    monkeypatch.setattr(base_mod, "notify", fake_notify)
    monkeypatch.setattr(base_mod, "checkpoint_save", fake_save)

    class Svc(BaseGenService):
        tool_class = Tool

    svc = Svc()
    # 第一次尝试(未到最后一次)→ 抛 Retry,交由 ARQ 重试
    with pytest.raises(Retry):
        asyncio.run(svc.run(8, "http://cb/api/user/v1/task/checkpoint", {"prompt": "p"}, ctx={"job_try": 1}))
    # 阶段2 检查点已回写 backend
    assert saved and saved[-1]["stage"] == 2
    assert saved[-1]["data"]["external_task_id"] == "ext-1"

    # 第二次尝试(最后一次)→ 拉取到检查点并复用,成功
    asyncio.run(svc.run(8, "http://cb/api/user/v1/task/checkpoint", {"prompt": "p"}, ctx={"job_try": int(config.ARQ_MAX_RETRIES)}))
    assert calls["checkpoints"][1] == {"stage": 2, "external_task_id": "ext-1"}
