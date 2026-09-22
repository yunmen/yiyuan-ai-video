# -*- coding: utf-8 -*-
"""worker 配置热更新单测:验证后台下发的网关/模型配置能正确覆盖本地 config,且空值不误清空。
双网关:主网关(CHAT_LLM_*,gen.llm_*)用于润色/prompt 改写;视频网关(LLM_BASE_*,gen.worker_llm_*)用于生视频,
视频网关留空时回退主网关。"""
import asyncio

import httpx
import pytest

from app.settings import config
from app.core import runtime_config


def _make_transport(payload: dict):
    RealAsyncClient = httpx.AsyncClient  # 先捕获真实类,避免 monkeypatch 后递归

    def handler(request: httpx.Request) -> httpx.Response:
        # 校验 worker 鉴权头已携带
        assert request.headers.get("X-Worker-Token") == config.NOTIFY_TOKEN
        return httpx.Response(200, json=payload)

    def make(*a, **k):
        return RealAsyncClient(transport=httpx.MockTransport(handler))

    return make


def test_mask_secret_keeps_prefix_and_suffix():
    """密钥脱敏:保留前 6 后 4 —— 既能核对"换没换 key",又不泄漏完整值"""
    masked = runtime_config.mask_secret("CHAT_LLM_API_KEY", "sk-235b8a36fcc9495aba80d20a5db47d0e")
    assert masked == "sk-235****7d0e"
    assert "235b8a36fcc9" not in masked


def test_mask_secret_leaves_normal_config_readable():
    """非密钥配置照常打印,否则排查问题时就看不到模型名/时长档位了"""
    assert runtime_config.mask_secret("VIDEO_DURATIONS", "5,10") == "5,10"
    assert runtime_config.mask_secret("IMAGE_MODEL", "doubao-seedream-4-0") == "doubao-seedream-4-0"
    assert runtime_config.mask_secret("SHORT_TOKEN", "abc") == "***"


def test_refresh_never_logs_plaintext_key(monkeypatch):
    """这条日志此前会把网关密钥明文写进日志文件(真实发生过的泄漏),这里钉死不许再出现"""
    secret = "sk-supersecret1234567890abcdef"
    logged = []
    monkeypatch.setattr(runtime_config.logger, "info", lambda msg="", *a, **k: logged.append(str(msg)))
    original = config.CHAT_LLM_API_KEY
    try:
        monkeypatch.setattr(httpx, "AsyncClient", _make_transport({
            "code": 1, "data": {"gen.llm_api_key": secret},
        }))
        monkeypatch.setattr(config, "CHAT_LLM_API_KEY", "old-value")  # 制造变化才会触发日志
        asyncio.run(runtime_config.refresh_once())
        joined = " ".join(logged)
        assert secret not in joined, f"日志泄漏了明文密钥: {joined}"
        assert "CHAT_LLM_API_KEY=sk-sup" in joined   # 前缀可见,便于核对是否换了 key
    finally:
        config.CHAT_LLM_API_KEY = original


def test_refresh_applies_gateway_and_models(monkeypatch):
    """后台下发主网关+新模型 → 主网关写到 CHAT_LLM_*,视频网关回退主网关"""
    original_chat_url = config.CHAT_LLM_BASE_URL
    original_chat_key = config.CHAT_LLM_API_KEY
    original_video_url = config.LLM_BASE_API_URL
    original_chat_model = config.CHAT_MODEL
    original_t2v = config.VIDEO_MODEL_T2V
    try:
        data = {
            "gen.llm_base_url": "https://gateway.example/v1",
            "gen.llm_api_key": "secret-token",
            "gen.chat_model": "deepseek-chat",
            "gen.video_model_t2v": "doubao-seedance-1.0-pro-250528",
            "gen.text_model": "qwen-max",
        }
        monkeypatch.setattr(httpx, "AsyncClient", _make_transport({"code": 1, "data": data}))

        asyncio.run(runtime_config.refresh_once())

        # 主网关(润色/prompt 改写)写到 CHAT_LLM_*
        assert config.CHAT_LLM_BASE_URL == "https://gateway.example/v1"
        assert config.CHAT_LLM_API_KEY == "secret-token"
        # 视频网关未单独下发 → 回退到主网关
        assert config.LLM_BASE_API_URL == "https://gateway.example/v1"
        assert config.LLM_BASE_API_KEY == "secret-token"
        # 模型/对话模型正常覆盖
        assert config.CHAT_MODEL == "deepseek-chat"
        assert config.VIDEO_MODEL_T2V == "doubao-seedance-1.0-pro-250528"
        assert config.TEXT_MODEL == "qwen-max"
    finally:
        config.CHAT_LLM_BASE_URL = original_chat_url
        config.CHAT_LLM_API_KEY = original_chat_key
        config.LLM_BASE_API_URL = original_video_url
        config.CHAT_MODEL = original_chat_model
        config.VIDEO_MODEL_T2V = original_t2v


def test_refresh_worker_video_gateway_isolated(monkeypatch):
    """双网关:视频网关(gen.worker_llm_*)非空 → 视频走 worker 网关,润色/chat 仍走主网关(A)"""
    original_chat_url = config.CHAT_LLM_BASE_URL
    original_chat_key = config.CHAT_LLM_API_KEY
    original_video_url = config.LLM_BASE_API_URL
    original_video_key = config.LLM_BASE_API_KEY
    try:
        data = {
            "gen.llm_base_url": "https://main.example/v1",
            "gen.llm_api_key": "main-token",
            "gen.worker_llm_base_url": "https://worker.example/v1",
            "gen.worker_llm_api_key": "worker-token",
        }
        monkeypatch.setattr(httpx, "AsyncClient", _make_transport({"code": 1, "data": data}))

        asyncio.run(runtime_config.refresh_once())

        # chat/润色 走主网关 A
        assert config.CHAT_LLM_BASE_URL == "https://main.example/v1"
        assert config.CHAT_LLM_API_KEY == "main-token"
        # 视频走 worker 网关 B
        assert config.LLM_BASE_API_URL == "https://worker.example/v1"
        assert config.LLM_BASE_API_KEY == "worker-token"
    finally:
        config.CHAT_LLM_BASE_URL = original_chat_url
        config.CHAT_LLM_API_KEY = original_chat_key
        config.LLM_BASE_API_URL = original_video_url
        config.LLM_BASE_API_KEY = original_video_key


def test_refresh_worker_video_gateway_falls_back_to_main(monkeypatch):
    """双网关:视频网关留空 → 视频回退主网关(gen.llm_*)"""
    original_chat_url = config.CHAT_LLM_BASE_URL
    original_chat_key = config.CHAT_LLM_API_KEY
    original_video_url = config.LLM_BASE_API_URL
    original_video_key = config.LLM_BASE_API_KEY
    try:
        data = {
            "gen.llm_base_url": "https://main.example/v1",
            "gen.llm_api_key": "main-token",
            "gen.worker_llm_base_url": "",  # 留空
            "gen.worker_llm_api_key": "",
        }
        monkeypatch.setattr(httpx, "AsyncClient", _make_transport({"code": 1, "data": data}))

        asyncio.run(runtime_config.refresh_once())

        assert config.LLM_BASE_API_URL == "https://main.example/v1"
        assert config.LLM_BASE_API_KEY == "main-token"
    finally:
        config.CHAT_LLM_BASE_URL = original_chat_url
        config.CHAT_LLM_API_KEY = original_chat_key
        config.LLM_BASE_API_URL = original_video_url
        config.LLM_BASE_API_KEY = original_video_key


def test_refresh_main_gateway_falls_back_to_worker(monkeypatch):
    """仅配置 worker 视频网关(gen.worker_llm_*) → 主网关回退到它,文本/图片/音频也能用 B(一处配置全局生效)"""
    original_chat_url = config.CHAT_LLM_BASE_URL
    original_chat_key = config.CHAT_LLM_API_KEY
    original_video_url = config.LLM_BASE_API_URL
    original_video_key = config.LLM_BASE_API_KEY
    try:
        data = {
            "gen.llm_base_url": "",   # 主网关留空
            "gen.llm_api_key": "",
            "gen.worker_llm_base_url": "https://worker.example/v1",
            "gen.worker_llm_api_key": "worker-token",
        }
        monkeypatch.setattr(httpx, "AsyncClient", _make_transport({"code": 1, "data": data}))

        asyncio.run(runtime_config.refresh_once())

        assert config.LLM_BASE_API_URL == "https://worker.example/v1"   # 视频走 B
        assert config.LLM_BASE_API_KEY == "worker-token"
        assert config.CHAT_LLM_BASE_URL == "https://worker.example/v1"  # 主网关回退 B
        assert config.CHAT_LLM_API_KEY == "worker-token"
    finally:
        config.CHAT_LLM_BASE_URL = original_chat_url
        config.CHAT_LLM_API_KEY = original_chat_key
        config.LLM_BASE_API_URL = original_video_url
        config.LLM_BASE_API_KEY = original_video_key


def test_refresh_ignores_empty_value(monkeypatch):
    """空值表示回退 env 默认 → 不把主网关误清空"""
    original_chat_url = config.CHAT_LLM_BASE_URL
    original_video_url = config.LLM_BASE_API_URL
    original_t2v = config.VIDEO_MODEL_T2V
    try:
        data = {
            "gen.llm_base_url": "",
            "gen.video_model_t2v": "doubao-seedance-1.0-pro-250528",
        }
        monkeypatch.setattr(httpx, "AsyncClient", _make_transport({"code": 1, "data": data}))

        asyncio.run(runtime_config.refresh_once())

        assert config.CHAT_LLM_BASE_URL == original_chat_url  # 主网关保持原默认
        assert config.LLM_BASE_API_URL == original_video_url  # 视频网关保持原默认
        assert config.VIDEO_MODEL_T2V == "doubao-seedance-1.0-pro-250528"  # 模型正常覆盖
    finally:
        config.CHAT_LLM_BASE_URL = original_chat_url
        config.LLM_BASE_API_URL = original_video_url
        config.VIDEO_MODEL_T2V = original_t2v


def test_refresh_keeps_state_on_failure(monkeypatch):
    """拉取失败(异常) → 保持现状,不抛异常"""
    original = config.CHAT_MODEL

    def boom(*a, **k):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "AsyncClient", boom)
    asyncio.run(runtime_config.refresh_once())
    assert config.CHAT_MODEL == original


def test_refresh_handles_bad_payload(monkeypatch):
    """返回结构异常(非 code==1 / data 非 dict) → 直接返回,保持现状"""
    original = config.CHAT_MODEL

    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda *a, **k: httpx.AsyncClient(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"code": 0, "msg": "no"}))),
    )
    asyncio.run(runtime_config.refresh_once())
    assert config.CHAT_MODEL == original

    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda *a, **k: httpx.AsyncClient(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"code": 1, "data": "not-a-dict"}))),
    )
    asyncio.run(runtime_config.refresh_once())
    assert config.CHAT_MODEL == original
