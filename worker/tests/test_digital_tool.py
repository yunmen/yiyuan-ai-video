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


def _stub_asset_cache(monkeypatch, fetch=None, store=None):
    """P2 资产缓存默认打桩为「未命中」,避免单测触达真实 backend 缓存接口。

    缓存是优化而非链路依赖,默认未命中不影响既有断言;需要验证缓存行为的用例可传入
    自定义 fetch/store 覆盖。返回记录键值的列表便于断言缓存键随入参变化。
    """
    keys = []

    async def _default_fetch(notify_url=None, cache_key=None, asset_type=""):
        keys.append(cache_key)
        return None

    async def _default_store(*args, **kwargs):
        return False

    monkeypatch.setattr(dig_mod.asset_cache, "fetch", fetch or _default_fetch)
    monkeypatch.setattr(dig_mod.asset_cache, "store", store or _default_store)
    return keys


def _make_tool(monkeypatch, model="digital-model-v1"):
    """构造数字人工具(显式 base_url 使其 _pinned,避免用例间候选网关串扰)"""
    monkeypatch.setattr(config, "DIGITAL_MODEL", model)
    _stub_asset_cache(monkeypatch)
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
        # voice_reference:声纹复用(voice-casting)透传给网关克隆音色,测试桩忽略该值但需接受;
        # speed:语速(0.5x~2.0x)经网关 extra_body 透传,同样只接受不参与断言以外的逻辑;
        # dialect:方言语义键,同样只接受不参与断言以外的逻辑(实测在 audio_tool 内进 extra_body)
        async def text_to_speech(
            self, text, voice=None, task_id=None, notify_url=None, voice_reference=None, speed=None, dialect=None,
        ):
            seen["tts"] = {
                "text": text, "voice": voice, "voice_reference": voice_reference, "speed": speed,
            }
            return ToolResult(content="https://cdn/tts.mp3", metadata={"success": True})

    async def fake_submit(payload, label, duration, resolution, ratio, checkpoint=None, on_stage=None):
        seen["payload"] = payload
        return ToolResult(content="https://cdn/digital.mp4", metadata={"success": True})

    monkeypatch.setattr(dig_mod, "AudioGenTool", _FakeAudio)
    tool._submit_and_poll = fake_submit

    result = asyncio.run(tool.generate({
        "avatar": "https://cdn/a.jpg", "text": "欢迎光临", "voice": "female-1",
        "duration": 9, "speed": 1.3,
    }))

    # voice_reference 为声纹复用透传参数(本例未传 → None);speed 为语速,同步断言确保链路接受该字段
    assert seen["tts"] == {
        "text": "欢迎光临", "voice": "female-1", "voice_reference": None, "speed": 1.3,
    }
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


def test_digital_forwards_motion_to_gateway(monkeypatch):
    """换动作(motion)必须进入网关自定义参数区。

    此前 render 路线把 motion 直接 pop 丢弃,用户在「换口播」页选的动作永远到不了网关,
    是个死字段。motion 只能放 metadata.parameters —— 顶层加未知字段会被网关拒。
    """
    tool = _make_tool(monkeypatch)
    seen = {}

    class _FakeAudio:
        async def text_to_speech(self, **kwargs):
            return ToolResult(content="https://cdn/tts.mp3", metadata={"success": True})

    async def fake_submit(payload, label, duration, resolution, ratio, checkpoint=None, on_stage=None):
        seen["payload"] = payload
        return ToolResult(content="https://cdn/digital.mp4", metadata={"success": True})

    monkeypatch.setattr(dig_mod, "AudioGenTool", _FakeAudio)
    tool._submit_and_poll = fake_submit

    asyncio.run(tool.generate({
        "avatar": "https://cdn/a.jpg", "text": "欢迎光临", "motion": "挥手",
    }))

    parameters = seen["payload"]["metadata"]["parameters"]
    assert parameters["motion"] == "挥手"

    # 未指定动作时不得凭空下发该键
    seen.clear()
    asyncio.run(tool.generate({
        "avatar": "https://cdn/a.jpg", "text": "欢迎光临",
    }))
    assert "motion" not in seen["payload"]["metadata"]["parameters"]


def test_digital_multiseg_reuses_completed_segments(monkeypatch):
    """多段口播断点续跑:已完成的段直接复用,不重复调 TTS 与数字人模型(两处都计费)。

    此前多段分支既不接收 checkpoint,每段还固定传空 checkpoint,续跑等于整条重跑。
    """
    tool = _make_tool(monkeypatch)
    submitted = []
    tts_called = []

    class _FakeAudio:
        async def text_to_speech(self, **kwargs):
            tts_called.append(kwargs.get("text"))
            return ToolResult(content=f"https://cdn/tts{len(tts_called)}.mp3", metadata={"success": True})

    async def fake_submit(payload, label, duration, resolution, ratio, checkpoint=None, on_stage=None):
        submitted.append(payload["audio"])
        # 模拟真实提交阶段回写断点,验证段内回写不会抹掉顶层 segments
        if on_stage:
            await on_stage(2, {"task_id": f"ext-{len(submitted)}"})
        return ToolResult(content=f"https://cdn/clip{len(submitted)}.mp4", metadata={"success": True})

    monkeypatch.setattr(dig_mod, "AudioGenTool", _FakeAudio)
    monkeypatch.setattr(dig_mod.compose, "available", lambda: True)

    async def fake_concat(urls):
        """拼接是纯本地点缀:这里只关心段数是否被正确复用,不落 ffmpeg"""
        return f"https://cdn/merged{len(urls)}.mp4"

    monkeypatch.setattr(tool, "_concat_clips", fake_concat)
    tool._submit_and_poll = fake_submit

    segments = [{"text": "第一段", "duration": 5}, {"text": "第二段", "duration": 5}]
    # 首次运行:两段都生成,断言断点里按段序号存下了 stage/audio/clip
    stages = []

    async def on_stage(stage, data=None):
        stages.append((stage, data))

    first = asyncio.run(tool.generate(
        {"avatar": "https://cdn/a.jpg", "segments": segments},
        checkpoint={}, on_stage=on_stage,
    ))
    assert first.metadata["success"] is True
    assert first.metadata["segments"] == 2
    assert len(tts_called) == 2
    saved = stages[-1][1]["segments"]
    assert len(saved) == 2
    assert saved[0]["clip"] == "https://cdn/clip1.mp4"
    assert saved[1]["clip"] == "https://cdn/clip2.mp4"
    assert saved[0]["audio"] and saved[1]["audio"]

    # 续跑:带上已保存的 segments → 零 TTS、零模型提交
    tts_called.clear()
    submitted.clear()
    second = asyncio.run(tool.generate(
        {"avatar": "https://cdn/a.jpg", "segments": segments},
        checkpoint={"segments": saved}, on_stage=on_stage,
    ))
    assert second.metadata["success"] is True
    assert tts_called == []
    assert submitted == []


def test_pip_cmd_mixes_digital_voice_with_background():
    """画中画必须把数字人口播与背景两路混音。

    此前实现是 `-map 0:a? -c:a copy`,只取背景音轨:数字人小窗里的口播声被整段丢弃,
    背景视频无音轨时成片完全无声。断言 amix 存在且两路都有 volume。
    """
    from app.core.compose import build_pip_cmd

    cmd = build_pip_cmd("bg.mp4", "digital.mp4", "out.mp4", bg_has_audio=True)
    text = " ".join(cmd)
    assert "amix=inputs=2" in text
    assert "[1:a]volume=1.0" in text   # 数字人口播为主
    assert "[0:a]volume=0.200" in text  # 背景压低铺底
    assert "0:a?" not in text           # 不再只取背景音轨
    assert "-c:a" in cmd and "aac" in cmd

    # 背景无音轨:不能引用 [0:a],否则 ffmpeg 因流不存在直接报错
    cmd_silent = build_pip_cmd("bg.mp4", "digital.mp4", "out.mp4", bg_has_audio=False)
    text_silent = " ".join(cmd_silent)
    assert "[0:a]" not in text_silent
    assert "1:a" in cmd_silent


def test_pip_bg_volume_zero_means_mute(monkeypatch):
    """pip.bg_volume=0(静音背景)必须原样传给 ffmpeg,不能被 `or` 兜底成默认音量。

    此前实现是 `float(pip.get("bg_volume") or DEFAULT_PIP_BG_VOLUME)`,0 是 falsy,
    会被当成「未填」而回退 0.2 —— 用户选「静音背景」后背景原声依旧可闻。
    """
    tool = dig_mod.DigitalHumanTool(api_key="k", base_url="https://gw.example/v1")
    captured = {}

    async def _fake_probe(_path):
        return True  # 背景有音轨,才会走 volume + amix 分支

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        # 产物文件必须真实存在,否则 _apply_pip 会按失败返回 None
        with open(cmd[-1], "wb") as f:
            f.write(b"x")
        return {"ok": True, "stderr": ""}

    async def _fake_run_async(cmd, **kwargs):
        # compose.run 是协程函数,_apply_pip 内为 `await compose.run(...)`
        return _fake_run(cmd, **kwargs)

    monkeypatch.setattr(dig_mod.compose, "available", lambda: True)
    monkeypatch.setattr(dig_mod.compose, "probe_has_audio", _fake_probe)
    monkeypatch.setattr(dig_mod.compose, "run", _fake_run_async)
    monkeypatch.setattr(dig_mod, "download_to_local", lambda url, ext: f"/tmp/{url}{ext}")
    monkeypatch.setattr(dig_mod, "upload_local_file", lambda path, key: "https://cdn/pip.mp4")

    url = asyncio.run(tool._apply_pip("digital.mp4", "bg.mp4", {"position": "br", "scale": 0.3, "bg_volume": 0}))
    assert url == "https://cdn/pip.mp4"
    text = " ".join(captured["cmd"])
    assert "[0:a]volume=0.000" in text  # 静音背景
    assert "[1:a]volume=1.0" in text    # 口播不受影响

    # 缺省 bg_volume 才回退统一默认值 0.2
    asyncio.run(tool._apply_pip("digital.mp4", "bg.mp4", {"position": "br"}))
    assert "[0:a]volume=0.200" in " ".join(captured["cmd"])


def test_digital_cache_hit_reuses_clip_without_model_call(monkeypatch):
    """P2 资产缓存:同形象 + 同文案 + 同音色 → 命中成片缓存,零数字人模型调用。

    「换主播只重跑视频生成」的降本前提是「没变的成片能直接复用」;命中时不再提交模型
    (最贵的一次付费),同时仍回报可用的口播音频地址供断点与下载链路使用。
    """
    tool = _make_tool(monkeypatch)
    submitted = []

    async def fake_fetch(notify_url=None, cache_key=None, asset_type=""):
        return {"content": "https://cdn/cached_digital.mp4", "meta": {}, "hit_count": 3}

    async def fake_store(*args, **kwargs):
        submitted.append("store")  # 命中时不应写回
        return True

    class _FakeAudio:
        async def text_to_speech(self, **kwargs):
            return ToolResult(content="https://cdn/tts.mp3", metadata={"success": True})

    async def fake_submit(payload, label, duration, resolution, ratio, checkpoint=None, on_stage=None):
        submitted.append(payload)
        return ToolResult(content="https://cdn/new.mp4", metadata={"success": True})

    monkeypatch.setattr(dig_mod, "AudioGenTool", _FakeAudio)
    _stub_asset_cache(monkeypatch, fetch=fake_fetch, store=fake_store)
    tool._submit_and_poll = fake_submit

    result = asyncio.run(tool.generate({
        "avatar": "https://cdn/a.jpg", "text": "欢迎光临", "voice": "v1",
    }))

    assert result.metadata["success"] is True
    assert result.metadata["cache"] == "hit"
    assert result.content == "https://cdn/cached_digital.mp4"
    assert result.metadata["digital_audio"] == "https://cdn/tts.mp3"
    assert submitted == []  # 既未提交模型,也未写回缓存


def test_digital_cache_key_tracks_inputs(monkeypatch):
    """缓存键随「决定成片的入参」变化:同形象同文案锁定复用,换主播/换音色必须重跑。

    若键漏掉 avatar/motion 等关键入参,「换主播」会误命中旧成片 —— 用户换了形象却看到同一张脸,
    这比多花钱更严重。此处同时断言命中失败时成片会被写回缓存(asset_type=digital_video)。
    """
    tool = _make_tool(monkeypatch)
    keys = []
    stored = []

    async def fake_fetch(notify_url=None, cache_key=None, asset_type=""):
        keys.append(cache_key)
        return None

    async def fake_store(*args, **kwargs):
        stored.append(args)
        return True

    class _FakeAudio:
        async def text_to_speech(self, **kwargs):
            return ToolResult(content="https://cdn/tts.mp3", metadata={"success": True})

    async def fake_submit(payload, label, duration, resolution, ratio, checkpoint=None, on_stage=None):
        return ToolResult(content="https://cdn/out.mp4", metadata={"success": True})

    monkeypatch.setattr(dig_mod, "AudioGenTool", _FakeAudio)
    _stub_asset_cache(monkeypatch, fetch=fake_fetch, store=fake_store)
    tool._submit_and_poll = fake_submit

    base = {"avatar": "https://cdn/a.jpg", "text": "欢迎光临", "voice": "v1"}
    asyncio.run(tool.generate(dict(base)))
    asyncio.run(tool.generate(dict(base)))
    asyncio.run(tool.generate({**base, "avatar": "https://cdn/b.jpg"}))
    asyncio.run(tool.generate({**base, "voice": "v2"}))

    assert keys[0] == keys[1]   # 同形象同文案同音色 → 同键,可跨任务复用
    assert keys[0] != keys[2]   # 换主播 → 不同键,必须重跑(不得误命中)
    assert keys[0] != keys[3]   # 换音色 → 不同键
    # 写回缓存的资产类型与内容必须正确,否则后续任务永远读不到
    assert stored and all(args[2] == "digital_video" for args in stored)
    assert stored[0][3] == "https://cdn/out.mp4"
