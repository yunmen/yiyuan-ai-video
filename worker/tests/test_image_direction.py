# -*- coding: utf-8 -*-
"""图像方向(replicate_image_direction):复刻换商品/人物/场景时的提示词改写。

钉三件事:
  ① 只在**有替换意图**时触发,且图像方向方法论必须真的进 chat 的 system;
  ② 未配 chat 模型 / 网关全挂 → 回退原提示词,绝不因增强丢单;
  ③ 方法论交给"写提示词的模型",而不是拼进图片模型 prompt(后者会干扰出图)。
"""
import asyncio
from types import SimpleNamespace

from app.settings import config
from app.tools import image_tool
from app.tools.image_tool import ImageGenTool

GW = [{"name": "t", "url": "http://x/v1", "key": "k", "proto": "openai"}]


def _tool():
    return ImageGenTool(api_key="k", base_url="http://localhost/v1")


def _stub_chat(monkeypatch, reply: str):
    """打桩 chat 网关:记录请求内容,返回预设文本"""
    captured = {}

    class _Completions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])

    class _Client:
        def __init__(self, *a, **k):
            pass

        chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setattr(image_tool, "AsyncOpenAI", _Client)
    monkeypatch.setattr(image_tool.gateway, "resolve_all", lambda cap: GW)
    return captured


def test_apply_image_direction_rewrites_and_injects_methodology(monkeypatch):
    """有替换意图时改写,且图像方向方法论必须作为 system 注入(证明资产被消费)"""
    monkeypatch.setattr(config, "CHAT_MODEL", "chat-test")
    captured = _stub_chat(monkeypatch, "改写后的提示词")

    out = asyncio.run(_tool()._apply_image_direction("原提示词", ["product"]))

    assert out == "改写后的提示词"
    assert "图像方向" in captured["messages"][0]["content"], "未注入图像方向方法论"
    assert "原提示词" in captured["messages"][1]["content"]
    assert "product" in captured["messages"][1]["content"], "替换意图未传给改写模型"


def test_apply_image_direction_skips_without_chat_model(monkeypatch):
    """未配 chat 模型 → 原样返回(普通文生图行为不变)"""
    monkeypatch.setattr(config, "CHAT_MODEL", "")
    assert asyncio.run(_tool()._apply_image_direction("原提示词", ["product"])) == "原提示词"


def test_apply_image_direction_falls_back_on_gateway_failure(monkeypatch):
    """网关全挂 → 回退原提示词,不能因为一次增强把图片单弄失败"""
    monkeypatch.setattr(config, "CHAT_MODEL", "chat-test")
    monkeypatch.setattr(image_tool.gateway, "resolve_all", lambda cap: GW)
    # 必须先构造:构造函数本身也会 new 一个 client,晚于打桩就会被 _Boom 打穿
    tool = _tool()

    class _Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("网关不可用")

    monkeypatch.setattr(image_tool, "AsyncOpenAI", _Boom)
    assert asyncio.run(tool._apply_image_direction("原提示词", ["product"])) == "原提示词"


def test_build_image_direction_prompt_returns_methodology():
    """资产可用时能取到方法论正文;它是给模型的元指引,含"保留什么/交给参考图"的规则"""
    from skills.prompt_library import build_image_direction_prompt

    text = build_image_direction_prompt()
    assert "图像方向" in text
    assert "保留" in text and "参考" in text
