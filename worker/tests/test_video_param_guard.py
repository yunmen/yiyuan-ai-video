# -*- coding: utf-8 -*-
"""提交前的参数守卫:像素门槛解析 + 「换网关也没用」的错误不再故障转移

背景(实测 task 58/59):参考视频像素数不足 407696 → 方舟 400 → 系统仍按候选列表
切到中转站重打一次 → 同样失败。**参数是同一份,换网关必然同样失败**,白打一次、
拖慢约 5s,还把真实错误埋进备选网关的报错里。
"""
import asyncio

from app.core import frame_quality, gateway
from app.settings import config
from app.tools.video_tool import (
    _DEFAULT_MIN_REFERENCE_PIXELS,
    VideoGenTool,
    _is_request_param_error,
)

# 方舟 400 原文(参考视频像素数不足)
PARAM_ERR = (
    "The parameter `content[1]` specified in the request is not valid: "
    "the parameter video pixel count specified in the request must be greater than "
    "or equal to 407696 for model doubao-seedance-2-5 in r2v"
)
AUTH_ERR = "Error code: 401 - Incorrect API key provided"


class _HttpError(RuntimeError):
    """带 status_code 的异常桩:与 openai SDK 的 APIStatusError 同形(_status_of 读它)"""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status_code = status


def _tool(monkeypatch):
    """构造参与故障转移的工具:显式 base_url 会置 _pinned,这里放开以拿到候选列表"""
    tool = VideoGenTool(api_key="test-key", base_url="https://gw-a.example/v1")
    tool._pinned = False
    monkeypatch.setattr(gateway, "resolve_all", lambda capability: [
        {"name": "gw-b", "url": "https://gw-b.example/v1", "key": "k2", "proto": "openai"},
    ])
    return tool


def _run(tool, call):
    """执行故障转移,返回 (结果 or None, 异常 or None, 尝试过的网关)"""
    tried = []

    async def wrapped(gw):
        tried.append(gw["url"])
        return await call(gw)

    try:
        result = asyncio.run(tool._with_failover("video", wrapped, label="视频编辑"))
        return result, None, tried
    except Exception as exc:  # noqa: BLE001 —— 单测里就是要接住抛出
        return None, exc, tried


# --- 参数类错误的识别 ---

def test_param_error_recognized():
    assert _is_request_param_error(_HttpError(400, PARAM_ERR)) is True
    assert _is_request_param_error(_HttpError(422, "must be greater than or equal to 407696")) is True


def test_non_param_errors_are_not_mistaken():
    """换网关确实可能通的几类错误,必须仍走转移"""
    for status, message in (
        (401, AUTH_ERR),                       # 鉴权:换一把 key 有用
        (403, "Access denied"),                # 权限:换网关有用
        (429, "Rate limit reached"),           # 限流
        (500, "Internal server error"),        # 服务端
        (404, "Not Found"),                    # 端点形态不符
    ):
        assert _is_request_param_error(_HttpError(status, message)) is False, f"{status} 不该被挡住"


# --- 故障转移行为 ---

def test_param_error_does_not_switch_gateway(monkeypatch):
    """参数类错误:候选网关尝试次数 = 1,且抛出的是第一站的原始报错"""
    tool = _tool(monkeypatch)

    async def call(gw):
        raise _HttpError(400, PARAM_ERR)

    _result, exc, tried = _run(tool, call)

    assert tried == ["https://gw-a.example/v1"], "参数类错误不该再打第二个网关"
    assert isinstance(exc, _HttpError)
    assert PARAM_ERR in str(exc), "必须保留第一站的原始报错(它才是真正的问题)"


def test_auth_error_still_fails_over(monkeypatch):
    """鉴权失败仍要换网关重试:换个网关(换 key)确实可能通"""
    tool = _tool(monkeypatch)

    async def call(gw):
        if gw["url"].startswith("https://gw-a"):
            raise _HttpError(401, AUTH_ERR)
        return "ok"

    result, exc, tried = _run(tool, call)

    assert exc is None
    assert result == "ok"
    assert tried == ["https://gw-a.example/v1", "https://gw-b.example/v1"]
    assert tool.base_url == "https://gw-b.example/v1", "转移后当前网关应切到备选"


def test_rate_limit_and_server_error_still_fails_over(monkeypatch):
    for status in (429, 500, 404):
        tool = _tool(monkeypatch)

        async def call(gw, status=status):
            if gw["url"].startswith("https://gw-a"):
                raise _HttpError(status, "temporary")
            return "ok"

        result, exc, tried = _run(tool, call)
        assert result == "ok" and len(tried) == 2, f"{status} 必须仍走故障转移"


def test_without_stop_on_all_candidates_are_tried(monkeypatch):
    """未配置 stop_on 的子类(默认 None)保持原行为:一律转移"""
    tool = _tool(monkeypatch)
    tool.failover_stop_on = None

    async def call(gw):
        raise _HttpError(400, PARAM_ERR)

    _result, exc, tried = _run(tool, call)

    assert len(tried) == 2, "未声明 stop_on 时不应改变既有行为"


# --- 参考视频像素门槛解析 ---

def test_min_reference_pixels_defaults_to_builtin(monkeypatch):
    monkeypatch.setattr(config, "VIDEO_MIN_REFERENCE_PIXELS", "")
    assert VideoGenTool(api_key="k", base_url="https://x/v1")._min_reference_pixels() == _DEFAULT_MIN_REFERENCE_PIXELS


def test_min_reference_pixels_matches_model(monkeypatch):
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "doubao-seedance-2-5-260628")
    monkeypatch.setattr(config, "VIDEO_MIN_REFERENCE_PIXELS", "doubao-seedance-2-5:407696")
    assert VideoGenTool(api_key="k", base_url="https://x/v1")._min_reference_pixels() == 407696


def test_min_reference_pixels_case_insensitive(monkeypatch):
    """模型名大小写不影响命中(模型名写法在各网关并不统一)"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "Doubao-Seedance-2-5-260628")
    monkeypatch.setattr(config, "VIDEO_MIN_REFERENCE_PIXELS", "DOUBAO-SEEDANCE-2-5:407696")
    assert VideoGenTool(api_key="k", base_url="https://x/v1")._min_reference_pixels() == 407696


def test_min_reference_pixels_unknown_model_disables_check(monkeypatch):
    """模型名未命中任何配置 → 关闭校验(拿不到确切门槛就不猜,绝不误杀正常任务)"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "doubao-seedance-2-5-260628")
    monkeypatch.setattr(config, "VIDEO_MIN_REFERENCE_PIXELS", "other-model:999999")
    assert VideoGenTool(api_key="k", base_url="https://x/v1")._min_reference_pixels() == 0


def test_min_reference_pixels_zero_disables_check(monkeypatch):
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "doubao-seedance-2-5-260628")
    monkeypatch.setattr(config, "VIDEO_MIN_REFERENCE_PIXELS", "doubao-seedance-2-5:0")
    assert VideoGenTool(api_key="k", base_url="https://x/v1")._min_reference_pixels() == 0


def test_min_reference_pixels_skips_malformed_parts(monkeypatch):
    """写错的那一项跳过而不是整串失效(运营改配置时极易写出缺冒号的项)"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "doubao-seedance-2-5-260628")
    monkeypatch.setattr(
        config, "VIDEO_MIN_REFERENCE_PIXELS", "no-colon; :123; doubao-seedance-2-5: abc; doubao-seedance-2-5:500000",
    )
    assert VideoGenTool(api_key="k", base_url="https://x/v1")._min_reference_pixels() == 500000


# --- 成片兜底校验开关 ---

def test_output_degenerate_check_switch(monkeypatch):
    """开关用字符串承载:"0" 必须能真的关掉(bool("0") 为真的坑)"""
    monkeypatch.setattr(config, "VIDEO_OUTPUT_DEGENERATE_CHECK", "1")
    assert VideoGenTool._output_degenerate_check_enabled() is True
    monkeypatch.setattr(config, "VIDEO_OUTPUT_DEGENERATE_CHECK", "0")
    assert VideoGenTool._output_degenerate_check_enabled() is False
    monkeypatch.setattr(config, "VIDEO_OUTPUT_DEGENERATE_CHECK", "false")
    assert VideoGenTool._output_degenerate_check_enabled() is False


# --- 成片兜底校验(工具层接线)---

RAW_URL = "https://cdn/raw.mp4"
OUT_URL = "https://oss/result.mp4"      # 与 RAW_URL 不同 → 视为转存成功
DEGENERATE_REASON = "画面 85% 的像素为高饱和纯色,是彩条/测试图一类无实际内容的画面"


def _offline_pipeline(monkeypatch, tool, reason):
    """提交/轮询/转存/成片检测全部打桩:用例绝不发真实请求、绝不写 OSS"""
    calls = {"detect": 0}

    async def fake_prepare(payload):
        return payload

    async def fake_failover(capability, call, label="", prefer_current=True, decision=None):
        return {"id": "t1"}

    async def fake_poll(*a, **k):
        return RAW_URL, False

    async def fake_persist(urls, prefix=None):
        return [OUT_URL]

    async def fake_detect(video, **kwargs):
        calls["detect"] += 1
        return reason

    monkeypatch.setattr(tool, "_prepare_media", fake_prepare)
    monkeypatch.setattr(tool, "_with_failover", fake_failover)
    monkeypatch.setattr(tool, "_poll", fake_poll)
    monkeypatch.setattr("app.tools.video_tool.persist_url_list", fake_persist)
    monkeypatch.setattr(frame_quality, "detect_degenerate_video", fake_detect)
    return calls


def _payload():
    return {
        "model": "doubao-seedance-2-5-260628",
        "prompt": "复刻",
        "metadata": {"parameters": {"resolution": "720p", "ratio": "9:16", "duration": 5}},
    }


def _submit(tool):
    return asyncio.run(tool._submit_and_poll(_payload(), "视频编辑", 5, "720p", "9:16", route="edit"))


def test_degenerate_output_fails_and_refunds(monkeypatch):
    """成片是彩条 → 判失败并说清额度会返还:交付废片还计全额费用,比失败更糟"""
    tool = VideoGenTool(api_key="test-key", base_url="https://gw-a.example/v1")
    _offline_pipeline(monkeypatch, tool, DEGENERATE_REASON)

    result = _submit(tool)

    assert result.metadata["success"] is False
    assert result.metadata["error_type"] == "invalid_output"
    assert "返还额度" in result.metadata["error"], "失败必须说清额度已返还,否则用户以为白扣"


def test_normal_output_is_delivered(monkeypatch):
    """检测未命中 → 正常交付(兜底校验绝不能把正常成片拦下)"""
    tool = VideoGenTool(api_key="test-key", base_url="https://gw-a.example/v1")
    _offline_pipeline(monkeypatch, tool, None)

    result = _submit(tool)

    assert result.metadata["success"] is True
    assert result.content == OUT_URL


def test_switch_off_skips_output_check(monkeypatch):
    """开关关闭时不下载成片(省一次带宽),即便真有坏片也照常交付"""
    tool = VideoGenTool(api_key="test-key", base_url="https://gw-a.example/v1")
    calls = _offline_pipeline(monkeypatch, tool, DEGENERATE_REASON)
    monkeypatch.setattr(config, "VIDEO_OUTPUT_DEGENERATE_CHECK", "0")

    result = _submit(tool)

    assert result.metadata["success"] is True
    assert calls["detect"] == 0, "关闭后不该再下载成片做检测"
