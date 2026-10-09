# -*- coding: utf-8 -*-
"""翻译服务契约测试:网关缺失兜底原样返回 + 正常翻译返回同序列表(不依赖真实模型)。"""
from app.services import ai_translate as ai_translate


def test_translate_no_gateway_returns_original():
    """chat 网关未配置 → fallback=True,原样返回输入(本地化变体仍按原语言出片,不阻断)。"""
    import asyncio
    from unittest.mock import patch

    with patch("app.services.ai_translate.gateway.resolve", return_value={}):
        r = asyncio.run(ai_translate.translate(["你好", "世界"], "en"))
    assert r["fallback"] is True
    assert r["translated"] == ["你好", "世界"]
    assert r["src_chars"] == r["dst_chars"]


def test_translate_success_returns_aligned_list():
    """网关可用且模型返回编号多行 → 去掉编号、按输入顺序对齐、fallback=False。"""
    import asyncio
    from unittest.mock import patch, AsyncMock

    with patch("app.services.ai_translate.gateway.resolve", return_value={"url": "u", "key": "k"}), \
         patch("app.services.ai_translate._chat_model", return_value="m"), \
         patch(
             "app.services.ai_translate._complete_translate",
             new=AsyncMock(return_value="1. Hello\n2. World"),
         ):
        r = asyncio.run(ai_translate.translate(["你好", "世界"], "en"))
    assert r["fallback"] is False
    assert r["translated"] == ["Hello", "World"]


def test_translate_empty_input_still_returns_list():
    """空条目也保留占位,返回数量与输入一致(保证 override 映射不串位)。"""
    import asyncio

    r = asyncio.run(ai_translate.translate(["", "  ", "文案"], "en"))
    # 网关未配 → 原样返回,但数量恒等于输入
    assert len(r["translated"]) == 3
