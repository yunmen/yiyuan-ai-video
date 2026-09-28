# -*- coding: utf-8 -*-
"""瞬时错误退避重试:方舟 429 限流 / 5xx 内部错误应就地重试,非瞬时错误立即抛。

实测 seedream 图片生成会返 429、seedance 视频生成会偶发 500,旧实现直接判整条任务失败;
这里把 retry 工具与「瞬时/非瞬时」判定钉死,防止有人改成无脑重试或误把 400 当瞬时。
"""
import asyncio

import httpx
import pytest

from app.core.retry import is_transient_error, with_transient_retry


def test_is_transient_ark_429_message():
    """方舟把 429 包成 RuntimeError('方舟返回 429: ...') → 判为瞬时"""
    assert is_transient_error(RuntimeError("方舟返回 429: RPM exceeded"))


def test_is_transient_ark_500_message():
    """方舟 500 内部错误 → 判为瞬时"""
    assert is_transient_error(RuntimeError("方舟返回 500: InternalServiceError"))


def test_is_transient_http_status_error():
    """httpx 显式状态码错误(raise_for_status 抛出)按状态码判定"""
    req = httpx.Request("POST", "http://x")
    assert is_transient_error(httpx.HTTPStatusError("e", request=req, response=httpx.Response(503)))
    assert not is_transient_error(httpx.HTTPStatusError("e", request=req, response=httpx.Response(400)))


def test_is_transient_timeout_and_transport():
    """网络抖动(超时/传输层)→ 瞬时"""
    assert is_transient_error(httpx.TimeoutException("t"))
    assert is_transient_error(httpx.TransportError("t"))


def test_is_not_transient_400_bad_request():
    """400 参数错误不是瞬时,不应重试"""
    assert not is_transient_error(RuntimeError("方舟返回 400: duration not supported"))


def test_retry_succeeds_after_transient_failures():
    """前两次 429、第三次成功 → 返回结果,且总共调用 3 次"""
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("方舟返回 429: RPM")
        return "ok"

    result = asyncio.run(with_transient_retry(factory, retries=3, backoff=0.01, label="t"))
    assert result == "ok"
    assert calls["n"] == 3


def test_retry_exhausts_on_persistent_transient():
    """持续 500 → 重试耗尽后抛出,调用次数 = 1 + retries"""
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        raise RuntimeError("方舟返回 500: InternalServiceError")

    with pytest.raises(RuntimeError):
        asyncio.run(with_transient_retry(factory, retries=2, backoff=0.01, label="t"))
    # 首次 + 2 次重试 = 3 次
    assert calls["n"] == 3


def test_retry_does_not_retry_non_transient():
    """400 等非瞬时错误立即抛出,只调用 1 次"""
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        raise RuntimeError("方舟返回 400: bad request")

    with pytest.raises(RuntimeError):
        asyncio.run(with_transient_retry(factory, retries=3, backoff=0.01, label="t"))
    assert calls["n"] == 1
