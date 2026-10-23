# -*- coding: utf-8 -*-
"""视觉识别降级：视觉失败返回空，不把图片请求发给普通文本模型。"""
import asyncio

from app.services import ai_vision


def _patch(monkeypatch, post_impl, vision_model="doubao-vision-x"):
    """把视觉调用相关的取值函数与底层 POST 都替成可控桩"""
    async def _vision_model():
        return vision_model

    def _vision_gateway():
        return {"url": "http://vision", "key": "vk"}

    monkeypatch.setattr(ai_vision, "_vision_model", _vision_model)
    monkeypatch.setattr(ai_vision, "_vision_gateway", _vision_gateway)
    monkeypatch.setattr(ai_vision, "_post_vision", post_impl)


def test_vision_404_does_not_send_images_to_chat(monkeypatch):
    """视觉模型不可达时返回空，不把图片发给未声明视觉能力的 chat 模型。"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        if model == "doubao-vision-x":
            raise RuntimeError("方舟返回 404: InvalidEndpointOrModel.NotFound")
        return '{"person":"红衣女士","product":"","scene":"","type":"person"}'

    _patch(monkeypatch, fake_post)
    result = asyncio.run(ai_vision.classify_subjects(["http://img/person.jpg"]))

    assert calls == ["doubao-vision-x"]
    assert result == ai_vision._empty_subjects()


def test_vision_ok_does_not_call_chat(monkeypatch):
    """视觉模型本身可用 → 不触发 chat 回退(避免无谓跨模型调用)"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        return '{"person":"","product":"红色水壶","scene":"","type":"product"}'

    _patch(monkeypatch, fake_post)
    result = asyncio.run(ai_vision.classify_subjects(["http://img/p.jpg"]))

    assert calls == ["doubao-vision-x"]
    assert result["type"] == "product"
    assert result["product"] == "红色水壶"


def test_vision_timeout_returns_empty_without_chat(monkeypatch):
    """视觉超时只按增强项降级，不向文本模型发送无效图片请求。"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        raise TimeoutError("视觉请求超时")

    _patch(monkeypatch, fake_post)
    result = asyncio.run(ai_vision.classify_subjects(["http://img/x.jpg"]))

    assert calls == ["doubao-vision-x"]
    assert result == ai_vision._empty_subjects()


def test_no_vision_model_configured_skips(monkeypatch):
    """未配置 gen.vision_model → 直接跳过识别(沿用既有「未配置则不识别」语义)"""
    calls = []

    async def fake_post(base_url, api_key, model, payload):
        calls.append(model)
        return "x"

    _patch(monkeypatch, fake_post, vision_model="")
    result = asyncio.run(ai_vision.classify_subjects(["http://img/x.jpg"]))

    assert calls == []
    assert result == ai_vision._empty_subjects()


# ---- 解析层单测(多图分组识别:人物/产品/场景各出一段描述) ----
def test_parse_subjects_splits_person_and_product():
    raw = (
        '{"person":"短发女模特,米色针织衫",'
        '"product":"木质气垫梳,原木色,圆头梳齿",'
        '"scene":"","primary":"product"}'
    )
    result = ai_vision._parse_subjects(raw)
    assert result["person"] == "短发女模特,米色针织衫"
    assert result["product"] == "木质气垫梳,原木色,圆头梳齿"
    assert result["type"] == "product"
    assert result["desc"] == "木质气垫梳,原木色,圆头梳齿"


def test_parse_subjects_infers_primary_when_model_omits_it():
    result = ai_vision._parse_subjects('{"person":"女模特","product":"","scene":""}')
    assert result["type"] == "person"
    assert result["desc"] == "女模特"


def test_parse_subjects_falls_back_to_single_subject():
    result = ai_vision._parse_subjects("一只黑白毛色的狗趴在老宅木门前")
    assert result["desc"]
    assert result["type"] in ai_vision.ALLOWED_TYPES
    assert any(result[role] for role in ai_vision.VALID_ROLES)


def test_parse_subjects_cleans_newlines_and_padding():
    result = ai_vision._parse_subjects(
        '{"person":"  女模特\\n穿红裙  ","product":"","scene":""}'
    )
    assert result["person"] == "女模特 穿红裙"


def test_parse_subjects_truncates_long_desc():
    long_desc = "很长的描述" * 40
    result = ai_vision._parse_subjects('{"person":"","product":"%s","scene":""}' % long_desc)
    assert len(result["product"]) <= 80


def test_role_hint_marks_each_image_in_order():
    hint = ai_vision._role_hint(["person", "product"])
    assert "第1张=人物形象图" in hint
    assert "第2张=产品图" in hint


def test_role_hint_empty_without_roles():
    assert ai_vision._role_hint([]) == ""
    assert ai_vision._role_hint(["", "unknown"]) == ""


def test_empty_subjects_keeps_key_contract():
    result = ai_vision._empty_subjects()
    assert set(result) == {"person", "product", "scene", "type", "desc"}
    assert all(result[k] == "" for k in result)
