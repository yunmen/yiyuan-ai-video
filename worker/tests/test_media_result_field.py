# -*- coding: utf-8 -*-
"""媒体类结果回写字段:图片/音频应回写 result_video(供预览),文本回写 result_text。"""
import asyncio

from app.services import base as base_mod
from app.services.image_service import ImageGenService
from app.services.audio_service import AudioGenService
from app.services.text_service import TextGenService
from app.schemas.base import ToolResult


class _Tool:
    async def generate(self, params, checkpoint=None, on_stage=None):
        return ToolResult(content="https://x/out", metadata={"success": True})


def _run(monkeypatch, svc_cls):
    sent = []

    async def fake_fetch(*a, **k):
        return {"checkpoint": {}, "progress": 5}

    async def fake_notify(url, payload, token=None):
        sent.append(payload)

    async def fake_save(*a, **k):
        pass

    monkeypatch.setattr(base_mod, "fetch_checkpoint", fake_fetch)
    monkeypatch.setattr(base_mod, "notify", fake_notify)
    monkeypatch.setattr(base_mod, "checkpoint_save", fake_save)

    class Svc(svc_cls):
        tool_class = _Tool

    asyncio.run(Svc().run(1, "http://cb/api/user/v1/task/callback", {"prompt": "p"}, ctx={"job_try": 1}))
    return sent[-1]


def test_is_media_flags():
    assert ImageGenService.is_media is True
    assert AudioGenService.is_media is True
    assert TextGenService.is_media is False


def test_media_types_write_result_video(monkeypatch):
    for cls in (ImageGenService, AudioGenService):
        payload = _run(monkeypatch, cls)
        assert payload["result_video"] == "https://x/out"
        assert "result" not in payload


def test_text_type_writes_result_text(monkeypatch):
    payload = _run(monkeypatch, TextGenService)
    assert payload["result"] == "https://x/out"
    assert "result_video" not in payload
