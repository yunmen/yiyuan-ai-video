# -*- coding: utf-8 -*-
"""语音合成(audio_tool.text_to_speech)的方言指令注入逻辑。

豆包 2.0 每种方言认的 token 往往不同(如 <方言:川渝> 而非 chuanyu),故 worker 支持两路:
  ① 逐方言映射 gen.tts_dialect_map(JSON:{语义键: 该方言完整指令})—— 优先级最高;
  ② 单模板 gen.tts_dialect_instruct({dialect}=语义键)—— 回退;
  ③ 皆空则不注入,且永远把语义键透传 extra_body["dialect"]。

本测试只验证「input 文本前拼了什么 + extra_body 透传了什么」,不触网关/不碰 Redis/OSS——
网关、asset_cache、OSS 全部打桩,专注方言指令装配这一处易错逻辑。
"""
import asyncio

from app.settings import config
import app.tools.audio_tool as at_mod


def _make_tool(monkeypatch):
    """构造 AudioGenTool 并把网关选择/cache/OSS 全部打桩,隔离到方言指令装配逻辑本身"""
    monkeypatch.setattr(config, "AUDIO_MODEL", "m")
    monkeypatch.setattr(config, "AUDIO_VOICE", "v")
    monkeypatch.setattr(config, "AUDIO_FORMAT", "mp3")
    monkeypatch.setattr(config, "TTS_DIALECT_INSTRUCT", "")
    monkeypatch.setattr(config, "TTS_DIALECT_MAP", "")

    tool = at_mod.AudioGenTool()
    captured = {}

    async def fake_create(**kw):
        captured.update(kw)
        # 仿 openai SDK 响应:二进制音频
        class _R:
            content = b"audio-bytes"

        return _R()

    # 打桩客户端 speech.create:真实捕获 input / extra_body
    monkeypatch.setattr(tool.client.audio.speech, "create", fake_create)
    # 打桩网关选择:直接执行调用(绕过 gateway.select,避免要求真实网关配置)
    async def fake_failover(_kind, call, label=None):
        return await call(None)

    monkeypatch.setattr(tool, "_with_failover", fake_failover)
    # 打桩 OSS 转换与缓存,避免触碰外部存储(_to_url 被 await,故必须是 async)
    async def fake_to_url(resp, prefix, fmt):
        return "https://cdn/tts.mp3"

    monkeypatch.setattr(tool, "_to_url", fake_to_url)
    monkeypatch.setattr(at_mod.asset_cache, "fetch", lambda *a, **k: asyncio.sleep(0, result=None))
    monkeypatch.setattr(at_mod.asset_cache, "store", lambda *a, **k: asyncio.sleep(0, result=None))
    return tool, captured


def test_dialect_map_wins_over_template(monkeypatch):
    """映射命中时直接拼该方言完整指令(豆包实际认的 <方言:川渝> 而非语义键 chuanyu)"""
    tool, captured = _make_tool(monkeypatch)
    monkeypatch.setattr(config, "TTS_DIALECT_MAP", '{"chuanyu":"<方言:川渝>","cantonese":"<方言:广东话>"}')
    monkeypatch.setattr(config, "TTS_DIALECT_INSTRUCT", "<方言:{dialect}>")  # 即便模板也配了,映射优先

    asyncio.run(tool.text_to_speech("欢迎光临", dialect="chuanyu"))

    assert captured["input"] == "<方言:川渝>欢迎光临", f"input 应为川渝指令,实际={captured.get('input')}"
    # 语义键仍透传 extra_body(支持方言参数的网关读取)
    assert captured["extra_body"]["dialect"] == "chuanyu"


def test_dialect_falls_back_to_template(monkeypatch):
    """映射未命中该方言 → 回退单模板,{dialect} 替换为语义键"""
    tool, captured = _make_tool(monkeypatch)
    monkeypatch.setattr(config, "TTS_DIALECT_MAP", '{"chuanyu":"<方言:川渝>"}')
    monkeypatch.setattr(config, "TTS_DIALECT_INSTRUCT", "<方言:{dialect}>")

    asyncio.run(tool.text_to_speech("你好", dialect="shanghai"))  # shanghai 不在映射里

    assert captured["input"] == "<方言:shanghai>你好", f"input 应回退模板,实际={captured.get('input')}"
    assert captured["extra_body"]["dialect"] == "shanghai"


def test_dialect_no_config_no_injection(monkeypatch):
    """两个方言配置都为空 → 不拼任何指令,也不透传 dialect,台词原样合成(安全降级)"""
    tool, captured = _make_tool(monkeypatch)
    # 默认 TTS_DIALECT_INSTRUCT / TTS_DIALECT_MAP 均为空(已在 _make_tool 置空)

    asyncio.run(tool.text_to_speech("你好", dialect="chuanyu"))

    # 未配置指令模板/映射时:台词原样合成(安全降级,绝不乱拼指令)
    assert captured["input"] == "你好", f"未配置时不应拼方言指令,实际={captured.get('input')}"
    # 但语义键仍透传 extra_body(支持 dialect 参数的网关可据此触发方言,不支持则忽略)
    assert captured["extra_body"] == {"dialect": "chuanyu"}


def test_dialect_map_bad_json_ignored(monkeypatch):
    """映射 JSON 填错时优雅忽略(回退模板/不注入),不抛异常、不把脏串拼进台词"""
    tool, captured = _make_tool(monkeypatch)
    monkeypatch.setattr(config, "TTS_DIALECT_MAP", "{这不是合法json")
    monkeypatch.setattr(config, "TTS_DIALECT_INSTRUCT", "<方言:{dialect}>")

    asyncio.run(tool.text_to_speech("你好", dialect="chuanyu"))

    # 映射解析失败 → 回退模板
    assert captured["input"] == "<方言:chuanyu>你好"
