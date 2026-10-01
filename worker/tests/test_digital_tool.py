# -*- coding: utf-8 -*-
"""数字人口播工具:入参校验、音频准备(TTS/复用断点)、提交载荷与能力路由。"""
import asyncio

from app.core import gateway
from app.settings import config
from app.schemas.base import ToolResult
import app.tools.digital_tool as dig_mod


def _load(data):
    gateway.load(data)


def teardown_function(_):
    gateway.load({})  # 清理全局状态,避免用例间串扰


def _make_tool(monkeypatch, model="digital-model-v1"):
    """构造数字人工具(显式 base_url 使其 _pinned,避免用例间候选网关串扰)"""
    monkeypatch.setattr(config, "DIGITAL_MODEL", model)
    return dig_mod.DigitalHumanTool(api_key="k", base_url="https://gw.example/v1")


def test_digital_requires_model(monkeypatch):
    """未配置 gen.digital_model 时明确失败,而不是静默产出错误结果"""
    tool = _make_tool(monkeypatch, model="")
    result = asyncio.run(tool.generate({"avatar": "https://cdn/a.jpg", "text": "你好"}))
    assert result.metadata["success"] is False
    assert result.metadata["error_type"] == "invalid_request"
    assert "gen.digital_model" in result.content


def test_digital_supports_ark_proto(monkeypatch):
    """方舟原生协议同样可用:形象图以 reference_image、口播音频以 audio_url 下发

    此前这里直接拒绝 ark 协议(理由:方舟载荷不带 audio) —— 结果是
    gen.route.digital 一旦指向方舟,数字人功能整体不可用。现已支持,故改钉新契约:
      · 形象图不能标 first_frame(那会被当图生视频处理、丢掉音频驱动);
      · 口播音频必须以 audio_url 下发,否则口型驱动无所依据。
    """
    _load({
        "gen.gw.ark.url": "https://ark.cn-beijing.volces.com/api/v3",
        "gen.gw.ark.key": "k",
        "gen.gw.ark.proto": "ark",
        "gen.route.digital": "ark",
    })
    monkeypatch.setattr(config, "DIGITAL_MODEL", "digital-model-v1")
    tool = dig_mod.DigitalHumanTool()
    assert tool._is_ark() is True

    # 直接校验请求体组装(_ark_body 是纯函数,不发网络请求)
    body = tool._ark_body({
        "model": "digital-model-v1",
        "prompt": "欢迎光临",
        "image": "https://cdn/a.jpg",
        "audio": "https://cdn/tts.mp3",
        "seconds": "8",
        "metadata": {"parameters": {"resolution": "720p", "ratio": "9:16", "duration": 8}},
    })
    content = body["content"]
    image_item = next(i for i in content if i["type"] == "image_url")
    assert image_item["role"] == "reference_image"
    audio_item = next(i for i in content if i["type"] == "audio_url")
    assert audio_item["audio_url"]["url"] == "https://cdn/tts.mp3"


def test_digital_requires_avatar(monkeypatch):
    tool = _make_tool(monkeypatch)
    result = asyncio.run(tool.generate({"text": "你好"}))
    assert result.metadata["success"] is False
    assert "avatar" in result.content


def test_digital_requires_text_or_audio(monkeypatch):
    tool = _make_tool(monkeypatch)
    result = asyncio.run(tool.generate({"avatar": "https://cdn/a.jpg"}))
    assert result.metadata["success"] is False
    assert "口播文案" in result.content


def test_digital_synthesizes_audio_then_submits(monkeypatch):
    """无 audio 时先用 TTS 合成,再把形象图 + 音频提交给数字人模型"""
    tool = _make_tool(monkeypatch)
    seen = {}

    class _FakeAudio:
        # notify_url:P2 资产缓存新增的入参(同文案可命中缓存、零合成调用),fake 必须同步;
        # voice_reference:声纹复用(voice-casting)透传给网关克隆音色,测试桩忽略该值但需接受
        async def text_to_speech(self, text, voice=None, task_id=None, notify_url=None, voice_reference=None):
            seen["tts"] = {"text": text, "voice": voice, "voice_reference": voice_reference}
            return ToolResult(content="https://cdn/tts.mp3", metadata={"success": True})

    async def fake_submit(payload, label, duration, resolution, ratio, checkpoint=None, on_stage=None):
        seen["payload"] = payload
        return ToolResult(content="https://cdn/digital.mp4", metadata={"success": True})

    monkeypatch.setattr(dig_mod, "AudioGenTool", _FakeAudio)
    tool._submit_and_poll = fake_submit

    result = asyncio.run(tool.generate({
        "avatar": "https://cdn/a.jpg", "text": "欢迎光临", "voice": "female-1", "duration": 9,
    }))

    # voice_reference 为声纹复用透传参数(本例未传 → None),同步断言确保链路接受该字段
    assert seen["tts"] == {"text": "欢迎光临", "voice": "female-1", "voice_reference": None}
    payload = seen["payload"]
    assert payload["model"] == "digital-model-v1"
    assert payload["image"] == "https://cdn/a.jpg"
    assert payload["audio"] == "https://cdn/tts.mp3"
    assert payload["seconds"] == "10"   # 时长吸附到模型支持档位(5/10)
    assert result.metadata["success"] is True
    assert result.metadata["mode"] == "digital"


def test_digital_reuses_checkpoint_audio(monkeypatch):
    """断点续跑:checkpoint 已有音频 → 不再重复合成(省一次 TTS 费用)"""
    tool = _make_tool(monkeypatch)
    seen = {}
    tts_called = []

    class _FakeAudio:
        async def text_to_speech(self, **kwargs):
            tts_called.append(True)
            return ToolResult(content="https://cdn/tts.mp3", metadata={"success": True})

    async def fake_submit(payload, label, duration, resolution, ratio, checkpoint=None, on_stage=None):
        seen["payload"] = payload
        return ToolResult(content="https://cdn/digital.mp4", metadata={"success": True})

    monkeypatch.setattr(dig_mod, "AudioGenTool", _FakeAudio)
    tool._submit_and_poll = fake_submit

    asyncio.run(tool.generate(
        {"avatar": "https://cdn/a.jpg", "text": "欢迎光临"},
        checkpoint={"stage": 1, "audio": "https://cdn/cached.mp3"},
    ))

    assert tts_called == []
    assert seen["payload"]["audio"] == "https://cdn/cached.mp3"


def test_digital_uses_dedicated_capability_route(monkeypatch):
    """gen.route.digital 可把数字人单独指向其它网关,不受视频路由影响"""
    _load({
        "gen.gw.ali.url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "gen.gw.ali.key": "ali-key",
        "gen.gw.ali.proto": "openai",
        "gen.gw.relay.url": "https://relay.example/v1",
        "gen.gw.relay.key": "relay-key",
        "gen.route.digital": "relay",
        "gen.route.video": "ali",
    })
    monkeypatch.setattr(config, "DIGITAL_MODEL", "digital-model-v1")

    tool = dig_mod.DigitalHumanTool()
    assert tool.capability == "digital"
    assert tool.base_url.startswith("https://relay.example")
