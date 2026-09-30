# -*- coding: utf-8 -*-
"""AI 文案生成:纯文本 / 图文结合两条链路(迁至 worker 后的单测)

重点:配了视觉模型才把画面喂给模型;没配就安静降级为纯文本 ——
不能让"没配视觉模型"变成"文案生成不可用"。
"""
import asyncio

from app.services import ai_copy
from app.services import ai_vision

REPLY = '{"title": "兔子好可爱", "subtitle": "毛茸茸的治愈瞬间", "script": "今天带你们看看这只兔子"}'

DEMAND_REPLY = (
    '{"title": "这把梳子真顺滑", "subtitle": "一梳到底不扯发", '
    '"script": "换把好梳子,头发顺到发光,链接放下面了", '
    '"subject": "一把木质气垫梳", '
    '"demand": "把参考视频里的洗发水换成上传图里的木质气垫梳,其余场景与运镜保持原样"}'
)


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _patch_gateways(monkeypatch, vision_model="doubao-seed-1-6-vision-250815", chat_model="deepseek-chat"):
    """伪造 worker 侧网关取值函数(对应 ai_copy 内部的 _vision_model/_vision_gateway 等)"""

    async def _vision_model():
        return vision_model

    def _vision_gateway():
        return {"url": "http://vision", "key": "vk"}

    async def _chat_model():
        return chat_model

    def _llm_gateway():
        return {"url": "http://chat", "key": "ck"}

    monkeypatch.setattr(ai_copy, "_vision_model", _vision_model)
    monkeypatch.setattr(ai_copy, "_vision_gateway", _vision_gateway)
    monkeypatch.setattr(ai_copy, "_chat_model", _chat_model)
    monkeypatch.setattr(ai_copy, "_llm_gateway", _llm_gateway)


def _mock_post(monkeypatch, captured, content=REPLY, fail=False):
    """打桩 AsyncOpenAI 的 chat.completions.create,记录入参并回吐预设文本。
    兼容对 messages / model / enable_thinking / thinking 的断言。
    """

    class _Message:
        def __init__(self, content):
            self.content = content

    class _Choice:
        def __init__(self, content):
            self.message = _Message(content)

    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]

    class _Completions:
        async def create(self, **kwargs):
            payload = {
                "model": kwargs.get("model"),
                "messages": kwargs.get("messages"),
                "temperature": kwargs.get("temperature"),
            }
            if kwargs.get("response_format"):
                payload["response_format"] = kwargs["response_format"]
            payload.update(kwargs.get("extra_body") or {})
            captured["payload"] = payload
            if fail:
                raise RuntimeError("网关 500")
            return _Resp(content)

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    class _AsyncOpenAI:
        def __init__(self, *a, **k):
            self.chat = _Chat()

    monkeypatch.setattr(ai_copy, "AsyncOpenAI", _AsyncOpenAI)
    # 素材识别(锚点/逐图类型)在 generate 内部走的是 ai_vision 的网关调用,
    # 测试里一律打桩返回空,避免单测发出真实网络请求;具体用例需要锚点时再覆写
    async def _no_subjects(images, roles=None):
        return ai_vision._empty_subjects()

    async def _no_types(images, roles=None):
        return {}

    monkeypatch.setattr(ai_vision, "classify_subjects", _no_subjects)
    monkeypatch.setattr(ai_vision, "classify_material_types", _no_types)


_VISION_CFG = {"model": "doubao-seed-1-6-vision-250815"}
_TEXT_CFG = {"model": ""}


def test_vision_used_when_model_and_images_present(monkeypatch):
    """配了视觉模型 + 传了画面 → 走视觉网关的多模态消息(文案才会与视频内容相符)"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured)

    data = asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None, ["https://oss/x1.jpg", "https://oss/x2.jpg"],
    ))

    assert data["vision"] is True
    assert data["title"] == "兔子好可爱"
    assert captured["payload"]["model"] == "doubao-seed-1-6-vision-250815"
    content = captured["payload"]["messages"][1]["content"]
    assert isinstance(content, list), "视觉链路必须用 content 数组"
    assert content[0]["type"] == "text"
    assert [c["type"] for c in content[1:]] == ["image_url", "image_url"]
    assert content[1]["image_url"]["url"] == "https://oss/x1.jpg"
    # 方舟系模型不认 qwen 的 enable_thinking,视觉链路不得携带
    assert "enable_thinking" not in captured["payload"]


def test_vision_prompt_mentions_combining_draft(monkeypatch):
    """用户填了草稿 → 提示词要求"画面 + 草稿结合",而不是照抄或脱离画面"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured)

    asyncio.run(ai_copy.generate(
        "模板", "零售带货", "小兔子", None, "来看兔子", ["https://oss/x1.jpg"],
    ))

    text = captured["payload"]["messages"][1]["content"][0]["text"]
    assert "结合润色" in text
    assert "参考画面" in text


def test_images_ignored_without_vision_model(monkeypatch):
    """没配视觉模型 → 忽略画面走纯文本,并保留 enable_thinking=False(短文案不提速会拖到 30s)"""
    _patch_gateways(monkeypatch, vision_model=_TEXT_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured)

    data = asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None, ["https://oss/x1.jpg"],
    ))

    assert data["vision"] is False
    assert isinstance(captured["payload"]["messages"][1]["content"], str)
    assert captured["payload"]["enable_thinking"] is False


def test_no_images_keeps_text_path(monkeypatch):
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured)

    data = asyncio.run(ai_copy.generate("模板", "零售带货"))
    assert data["vision"] is False


def test_vision_failure_falls_back_to_template(monkeypatch):
    """视觉调用失败必须降级为兜底文案,不能把异常抛给用户"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured, fail=True)

    data = asyncio.run(ai_copy.generate(
        "招牌菜", "零售带货", None, None, None, ["https://oss/x1.jpg"],
    ))
    assert data["fallback"] is True
    assert data["title"]


def test_vision_grounding_injects_recognized_subject(monkeypatch):
    """先识别后生成:识别出的素材描述要作为事实锚点注入提示词,并带上命名一致性硬规则"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured, content=DEMAND_REPLY)

    async def _fake_subjects(images, roles=None):
        return {"person": "", "product": "炸鸡汉堡,金黄面包胚夹炸鸡排",
                "scene": "", "type": "product", "desc": "炸鸡汉堡"}

    monkeypatch.setattr(ai_vision, "classify_subjects", _fake_subjects)

    data = asyncio.run(ai_copy.generate(
        "汉堡宣传", "美食探店", None, None, None, ["https://oss/burger.jpg"],
        with_demand=True, roles=["product"],
    ))

    text = captured["payload"]["messages"][1]["content"][0]["text"]
    assert "素材识别结果" in text and "炸鸡汉堡" in text, "识别锚点必须注入提示词"
    assert "同一个名称" in text, "命名一致性硬规则必须注入提示词"
    assert data["vision"] is True


def test_vision_grounding_failure_keeps_generation(monkeypatch):
    """素材识别失败只损失锚点,文案照常生成,不能因此降级兜底"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured)

    async def _boom(images, roles=None):
        raise RuntimeError("识别服务挂了")

    monkeypatch.setattr(ai_vision, "classify_subjects", _boom)

    data = asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None, ["https://oss/x1.jpg"],
    ))
    assert data["vision"] is True
    assert data["title"] == "兔子好可爱"


def test_vision_images_capped(monkeypatch):
    """画面数量要封顶:每张都是 token,无限传会烧钱"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured)

    asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None,
        [f"https://oss/x{i}.jpg" for i in range(10)],
    ))
    content = captured["payload"]["messages"][1]["content"]
    assert len(content) == 1 + ai_copy.MAX_VISION_IMAGES


def test_with_demand_requests_and_returns_draft(monkeypatch):
    """with_demand=True:系统提示要追加 subject/demand 字段,结果需带出供前端预填"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured, content=DEMAND_REPLY)

    data = asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None, ["https://oss/x1.jpg"], with_demand=True,
    ))

    system_text = captured["payload"]["messages"][0]["content"]
    assert "subject" in system_text and "demand" in system_text
    assert data["subject"] == "一把木质气垫梳"
    assert "木质气垫梳" in data["demand"]


def test_without_demand_keeps_old_contract(monkeypatch):
    """默认不请求 demand:老调用方拿到的字段契约不变(不出现 subject/demand)"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured)

    data = asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None, ["https://oss/x1.jpg"],
    ))

    assert "demand" not in captured["payload"]["messages"][0]["content"]
    assert "subject" not in data and "demand" not in data


def test_fallback_copy_carries_demand_keys():
    """兜底文案在 with_demand 下也要给全字段,前端读取不会拿到 undefined"""
    data = ai_copy.fallback_copy("模板", "零售带货", with_demand=True)
    assert data["fallback"] is True
    assert data["subject"] == ""
    assert data["demand"]
    assert "demand" not in ai_copy.fallback_copy("模板", "零售带货")


def test_fallback_copy_multi_covers_person_and_product():
    """多图(人物图+产品图)兜底时,画面要求要同时覆盖人物与产品"""
    data = ai_copy.fallback_copy("模板", "零售带货", with_demand=True, multi=True)
    assert "人物" in data["demand"] and "产品" in data["demand"]


def test_success_without_demand_field_falls_back(monkeypatch):
    """模型成功但漏掉 demand 字段(视觉模型常见)→ 仍按角色给兜底画面要求,前端才有预填"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured, content=REPLY)
    data = asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None,
        ["https://oss/x1.jpg", "https://oss/x2.jpg"],
        with_demand=True, roles=["product", "person"],
    ))
    assert data["demand"], "成功响应漏 demand 时必须兜底,否则前端画面要求预填为空"
    assert "产品" in data["demand"] and "人物" in data["demand"]


def test_success_without_demand_and_roles_uses_generic_fallback(monkeypatch):
    """成功漏 demand 且无角色标注 → 回退通用兜底画面要求"""
    _patch_gateways(monkeypatch, vision_model=_VISION_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured, content=REPLY)
    data = asyncio.run(ai_copy.generate(
        "模板", "零售带货", None, None, None,
        ["https://oss/x1.jpg"], with_demand=True,
    ))
    assert data["demand"]
    assert "参考视频" in data["demand"]


def test_with_demand_without_vision_does_not_hallucinate_subject(monkeypatch):
    """未配视觉模型时,模型没见过上传图,绝不能采信它按模板标题脑补的 subject/demand。"""
    _patch_gateways(monkeypatch, vision_model=_TEXT_CFG["model"])
    captured = {}
    _mock_post(monkeypatch, captured, content=DEMAND_REPLY)

    data = asyncio.run(ai_copy.generate(
        "汉堡包", "美食探店", None, None, None, ["https://oss/dog.jpg"],
        with_demand=True, roles=["product"],
    ))

    assert data["vision"] is False
    assert data["subject"] == "", "未使用视觉时不得采信脑补主体"
    assert "木质气垫梳" not in data["demand"], "未使用视觉时不得采信脑补的替换对象"
    assert "产品图" in data["demand"], "应改用按角色生成的通用画面要求"
