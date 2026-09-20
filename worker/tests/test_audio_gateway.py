# -*- coding: utf-8 -*-
"""音频网关选择:优先专用音频网关(方舟无 /audio),留空回退媒体网关。"""
from app.tools.audio_tool import AudioGenTool
from app.settings import config


def test_audio_prefers_dedicated_gateway(monkeypatch):
    monkeypatch.setattr(config, "AUDIO_LLM_BASE_URL", "https://audio.example/v1")
    monkeypatch.setattr(config, "AUDIO_LLM_API_KEY", "audio-key")
    monkeypatch.setattr(config, "LLM_BASE_API_URL", "https://ark.example/v3")
    monkeypatch.setattr(config, "LLM_BASE_API_KEY", "ark-key")
    tool = AudioGenTool()
    assert tool.base_url == "https://audio.example/v1"
    assert tool.api_key == "audio-key"


def test_audio_falls_back_to_media_gateway(monkeypatch):
    monkeypatch.setattr(config, "AUDIO_LLM_BASE_URL", "")
    monkeypatch.setattr(config, "AUDIO_LLM_API_KEY", "")
    monkeypatch.setattr(config, "LLM_BASE_API_URL", "https://ark.example/v3")
    monkeypatch.setattr(config, "LLM_BASE_API_KEY", "ark-key")
    tool = AudioGenTool()
    assert tool.base_url == "https://ark.example/v3"
    assert tool.api_key == "ark-key"
