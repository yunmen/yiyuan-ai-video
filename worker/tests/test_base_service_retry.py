# -*- coding: utf-8 -*-
"""编排服务:成功回调、失败重试(未到最后一次抛 Retry)、最后一次回写 failed"""
import asyncio

import pytest
from arq.worker import Retry

from app.services import base as base_mod
from app.services.base import BaseGenService
from app.schemas.base import ToolResult
from app.settings import config


class _OkTool:
    async def generate(self, params, checkpoint=None, on_stage=None):
        return ToolResult(content="https://x/result.mp4", metadata={"success": True, "seconds": 5})


class _FailTool:
    async def generate(self, params, checkpoint=None, on_stage=None):
        return ToolResult(content="模型报错", metadata={"success": False, "error": "模型报错"})


def _capture_notify(monkeypatch):
    sent = []

    async def fake_notify(url, payload, token=None):
        sent.append(payload)

    monkeypatch.setattr(base_mod, "notify", fake_notify)
    return sent


def test_success_sends_success_callback(monkeypatch):
    sent = _capture_notify(monkeypatch)

    class Svc(BaseGenService):
        tool_class = _OkTool

    asyncio.run(Svc().run(1, "http://cb", {"prompt": "p"}, ctx={"job_try": 1}))
    assert sent[-1]["status"] == "success"
    assert sent[-1]["result_video"] == "https://x/result.mp4"


def test_failure_retries_when_attempts_remain(monkeypatch):
    _capture_notify(monkeypatch)

    class Svc(BaseGenService):
        tool_class = _FailTool

    # 第 1 次失败、还有重试次数 → 抛 Retry 交由 ARQ 重试
    with pytest.raises(Retry):
        asyncio.run(Svc().run(2, "http://cb", {"prompt": "p"}, ctx={"job_try": 1}))


def test_failure_sends_failed_on_last_attempt(monkeypatch):
    sent = _capture_notify(monkeypatch)

    class Svc(BaseGenService):
        tool_class = _FailTool

    # 最后一次尝试 → 回写 failed,不再抛 Retry
    asyncio.run(Svc().run(3, "http://cb", {"prompt": "p"}, ctx={"job_try": int(config.ARQ_MAX_RETRIES)}))
    assert sent[-1]["status"] == "failed"
    assert sent[-1]["fail_reason"] == "模型报错"


def test_tool_exception_is_treated_as_failure(monkeypatch):
    _capture_notify(monkeypatch)

    class _BoomTool:
        async def generate(self, params, checkpoint=None, on_stage=None):
            raise RuntimeError("连接超时")

    class Svc(BaseGenService):
        tool_class = _BoomTool

    with pytest.raises(Retry):
        asyncio.run(Svc().run(4, "http://cb", {"prompt": "p"}, ctx={"job_try": 1}))
