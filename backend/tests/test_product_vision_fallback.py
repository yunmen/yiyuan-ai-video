# -*- coding: utf-8 -*-
"""视觉识别兜底:管理端把 gen.vision_model 配成不可达模型(如方舟 doubao-vision-* 返 404)
时,自动回退用 chat 模型(同多模态,如 deepseek-v4-1-flash),识别不中断。

否则会出现「管理端配了视觉模型却识别全失败、复刻退化成纯产品替换」的静默问题。
"""
import asyncio

from app.services import product_vision


def _patch(monkeypatch, post_impl, vision_model="doubao-vision-x"):
    """把视觉调用相关的取值函数与底层 POST 都替成可控桩"""
    async def _vision_model():
        return vision_model

    async def _vision_gateway():
        return ("http://vision", "vk")

    async def _llm_gateway():
        return ("http://chat", "ck")

    async def _chat_model():
        return "deepseek-flash"

    monkeypatch.setattr(product_vision, "_vision_model", _vision_model)
    monkeypatch.setattr(product_vision, "_vision_gateway", _vision_gateway)
    monkeypatch.setattr(product_vision, "_llm_gateway", _llm_gateway)
    monkeypatch.setattr(product_vision, "_chat_model", _chat_model)
    monkeypatch.setattr(product_vision, "_post_vision", post_impl)


def test_vision_falls_back_to_chat_on_404(monkeypatch):
    """视觉模型返 404(无权限/不存在)→ 回退 chat 模型并成功识别"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        if model == "doubao-vision-x":
            raise RuntimeError("方舟返回 404: InvalidEndpointOrModel.NotFound")
        # chat 模型返回合法分组 JSON
        return '{"person":"红衣女士","product":"","scene":"","type":"person"}'

    _patch(monkeypatch, fake_post)
    result = asyncio.run(product_vision.classify_subjects(["http://img/person.jpg"]))

    # 确实走了「视觉模型 → chat 模型」回退链
    assert calls == ["doubao-vision-x", "deepseek-flash"]
    assert result["type"] == "person"
    assert result["person"] == "红衣女士"


def test_vision_ok_does_not_call_chat(monkeypatch):
    """视觉模型本身可用 → 不触发 chat 回退(避免无谓跨模型调用)"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        return '{"person":"","product":"红色水壶","scene":"","type":"product"}'

    _patch(monkeypatch, fake_post)
    result = asyncio.run(product_vision.classify_subjects(["http://img/p.jpg"]))

    assert calls == ["doubao-vision-x"]
    assert result["type"] == "product"
    assert result["product"] == "红色水壶"


def test_vision_and_chat_both_fail_returns_empty(monkeypatch):
    """视觉与 chat 均失败 → 按增强项降级返回空,绝不阻断建单"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        raise RuntimeError("方舟返回 500: InternalServiceError")

    _patch(monkeypatch, fake_post)
    result = asyncio.run(product_vision.classify_subjects(["http://img/x.jpg"]))

    assert calls == ["doubao-vision-x", "deepseek-flash"]
    assert result == product_vision._empty_subjects()


def test_no_vision_model_configured_skips(monkeypatch):
    """未配置 gen.vision_model → 直接跳过识别(沿用既有「未配置则不识别」语义)"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        return "x"

    _patch(monkeypatch, fake_post, vision_model="")
    result = asyncio.run(product_vision.classify_subjects(["http://img/x.jpg"]))

    assert calls == []
    assert result == product_vision._empty_subjects()
