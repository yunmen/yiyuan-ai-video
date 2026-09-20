# -*- coding: utf-8 -*-
"""回调通知:失败自动重试,重试耗尽不抛异常(避免拖垮任务)"""
import asyncio

from plugin import notice as notice_mod
from app.settings import config


class _FakeResp:
    def __init__(self, code):
        self.status_code = code
        self.text = "mock"


class _FakeClient:
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeClient.calls += 1
        # 前两次失败,第三次成功
        return _FakeResp(200 if _FakeClient.calls >= 3 else 500)


def _patch(monkeypatch):
    _FakeClient.calls = 0
    monkeypatch.setattr(notice_mod.httpx, "AsyncClient", _FakeClient)

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(notice_mod.asyncio, "sleep", _no_sleep)


def test_notify_retries_until_success(monkeypatch):
    _patch(monkeypatch)
    asyncio.run(notice_mod.notify("http://cb", {"task_id": 1, "status": "success"}, "tok"))
    assert _FakeClient.calls == 3


def test_notify_gives_up_without_raising(monkeypatch):
    _patch(monkeypatch)

    async def always_fail(self, url, json=None, headers=None):
        _FakeClient.calls += 1
        return _FakeResp(500)

    monkeypatch.setattr(_FakeClient, "post", always_fail)
    asyncio.run(notice_mod.notify("http://cb", {"task_id": 2, "status": "failed"}, "tok"))
    assert _FakeClient.calls == int(config.NOTIFY_RETRY_ATTEMPTS)
