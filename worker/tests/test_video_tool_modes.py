# -*- coding: utf-8 -*-
"""视频工具:按素材数量自动选择生成模式(文生/图生/参考生)"""
import asyncio
from unittest.mock import AsyncMock

from app.settings import config
from app.core import media_prep, subtitle
from app.tools.video_tool import LEAD_ACT_ASSETS, VideoGenTool, parse_duration_gears
from app.schemas.base import ToolResult


def _make_tool():
    # 仅构造客户端,不发起网络请求
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _stub_modes(tool, calls):
    async def fake_t2v(prompt, **kwargs):
        calls.append("t2v")
        return ToolResult(content="https://x/t2v.mp4", metadata={"success": True})

    async def fake_i2v(prompt, **kwargs):
        calls.append("i2v")
        return ToolResult(content="https://x/i2v.mp4", metadata={"success": True})

    async def fake_r2v(prompt, **kwargs):
        calls.append("r2v")
        return ToolResult(content="https://x/r2v.mp4", metadata={"success": True})

    tool.text_to_video = fake_t2v
    tool.image_to_video = fake_i2v
    tool.reference_to_video = fake_r2v


def test_no_material_uses_text_to_video():
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    result = asyncio.run(tool.generate({"prompt": "海边日落", "materials": []}))
    assert calls == ["t2v"]
    assert result.metadata["success"] is True


def test_single_material_uses_image_to_video():
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    asyncio.run(tool.generate({"prompt": "动起来", "materials": ["https://x/a.jpg"]}))
    assert calls == ["i2v"]


def test_multiple_materials_uses_reference_to_video():
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    asyncio.run(tool.generate({"prompt": "合集", "materials": ["https://x/a.jpg", "https://x/b.jpg"]}))
    assert calls == ["r2v"]


def test_duration_clamp():
    """时长吸附到模型支持的档位(方舟 seedance 仅支持 5/10)"""
    tool = _make_tool()
    assert tool._clamp_duration(0) == 5      # 低于下限 → 5
    assert tool._clamp_duration(15) == 10    # 方舟不支持的 15 → 吸附 10
    assert tool._clamp_duration(99) == 10    # 上限
    assert tool._clamp_duration(8) == 10     # 就近取档
    assert tool._clamp_duration(6) == 5      # 就近取档
    assert tool._clamp_duration("bad") == 5  # 非法值兜底


# --- 时长档位可配置(换支持连续时长的模型后可放开) ---

def test_parse_duration_gears_discrete_and_range():
    assert parse_duration_gears("5,10") == (5, 10)
    assert parse_duration_gears("4-15") == tuple(range(4, 16))


def test_parse_duration_gears_invalid_means_no_override():
    """配置写错必须"不覆盖",否则会提交模型不支持的时长"""
    for bad in ("", "   ", "abc", "5,x", "15-4", "4-150", None):
        assert parse_duration_gears(bad) == (), f"{bad!r} 应视为非法"


def test_clamp_duration_uses_configured_gears(monkeypatch):
    monkeypatch.setattr(config, "VIDEO_DURATIONS", "4-15")
    assert VideoGenTool._clamp_duration(12) == 12   # 放开后 12 秒原样保留
    monkeypatch.setattr(config, "VIDEO_DURATIONS", "")
    assert VideoGenTool._clamp_duration(12) == 10   # 未配置 → 保持默认档位


# --- 视频编辑(Seedance 2.x) ---

def test_edit_video_payload_carries_video_and_audio(monkeypatch):
    """视频编辑必须传**视频本身**并开启音频:成片语音要与新台词同步,字幕才对得上"""
    from app.core import media_prep

    # 提交前会做「参考视频超长自动裁剪」,其中 probe_duration 会真去 ffprobe 拉取远程地址;
    # 单测只关心 payload 组装,这里让预处理直通(否则每个用例白等数秒网络超时)
    async def _passthrough(url, *a, **k):
        return url

    monkeypatch.setattr(media_prep, "fit_reference_video", _passthrough)
    tool = _make_tool()
    captured = {}

    async def fake_submit(payload, *a, **k):
        captured.update(payload)
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    tool._submit_and_poll = fake_submit
    asyncio.run(tool.edit_video(
        "复刻", reference_video="https://x/ref.mp4", images=["https://x/p.jpg"], duration=8,
    ))
    assert captured["videos"] == ["https://x/ref.mp4"]
    assert captured["generate_audio"] is True
    assert captured["images"] == ["https://x/p.jpg"]


def test_action_reference_skips_marketing_script(monkeypatch):
    """动作仍提交原视频编辑，但不得调用自动口播生成。"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "test-edit")
    tool = _make_tool()
    tool._optimize_prompt = AsyncMock(return_value="参考动作")
    tool._build_replicate_script = AsyncMock(side_effect=AssertionError("动作不应生成口播"))
    captured = {}

    async def fake_edit(prompt, **kwargs):
        """隔离模型收费，只记录编辑请求和动作约束。"""
        captured.update(kwargs, prompt=prompt)
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    tool.edit_video = fake_edit
    result = asyncio.run(tool.generate({"prompt": "参考动作", "replicate_mode": "action", "materials": [], "reference_video": "https://x/ref.mp4"}))
    tool._build_replicate_script.assert_not_awaited()
    assert captured["reference_video"] == "https://x/ref.mp4"
    assert "不要新增商品推广" in captured["prompt"]
    assert result.metadata["success"] is True


def test_reference_video_prefers_edit_mode(monkeypatch):
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    tool = _make_tool()
    calls = []

    async def fake_edit(prompt, **kwargs):
        calls.append(("edit", kwargs.get("reference_video")))
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    _stub_modes(tool, calls)
    tool.edit_video = fake_edit
    asyncio.run(tool.generate({
        "prompt": "复刻", "materials": ["https://x/a.jpg"], "reference_video": "https://x/ref.mp4",
    }))
    assert calls[0] == ("edit", "https://x/ref.mp4")


def test_edit_failure_falls_back_to_image_pipeline(monkeypatch):
    """网关不认 videos 字段时不能把整单任务打成失败 —— 降级回图片参考链路"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)

    async def fake_edit_fail(prompt, **kwargs):
        return ToolResult(content="字段不支持", metadata={"success": False, "error": "unknown field videos"})

    tool.edit_video = fake_edit_fail
    result = asyncio.run(tool.generate({
        "prompt": "复刻",
        "materials": ["https://x/a.jpg", "https://x/b.jpg"],
        "reference_video": "https://x/ref.mp4",
    }))
    assert calls == ["r2v"]
    assert result.metadata["success"] is True


def test_edit_switches_gateway_to_video_edit_route(monkeypatch):
    """编辑走独立网关(如中转站的 doubao)时工具要跟着切,否则会拿编辑模型去方舟提交"""
    from app.core import gateway

    monkeypatch.setattr(gateway, "GATEWAYS", {
        "ark": {"url": "https://ark.cn-beijing.volces.com/api/v3", "key": "ark-key", "proto": "ark"},
        "relay": {"url": "https://aitoken.example/v1", "key": "relay-key", "proto": ""},
    })
    monkeypatch.setattr(gateway, "ROUTES", {"video": "ark", "video_edit": "relay"})

    tool = VideoGenTool()          # 不 pin base_url,才会按能力解析网关
    assert tool.capability == "video"
    assert tool.proto == "ark"

    tool._use_capability("video_edit")
    assert tool.capability == "video_edit"
    assert tool.base_url == "https://aitoken.example/v1"
    assert tool.proto == "openai"  # 中转站是 OpenAI 兼容协议


def test_pinned_tool_never_switches_gateway(monkeypatch):
    """显式传 base_url(测试/直连)时不得被切换,否则会打到真实网关上"""
    from app.core import gateway

    monkeypatch.setattr(gateway, "GATEWAYS", {
        "relay": {"url": "https://aitoken.example/v1", "key": "relay-key", "proto": ""},
    })
    monkeypatch.setattr(gateway, "ROUTES", {"video_edit": "relay"})

    tool = _make_tool()            # base_url="http://localhost/v1" → pinned
    tool._use_capability("video_edit")
    assert tool.base_url == "http://localhost/v1"
    assert tool.capability == "video"


def test_edit_failure_does_not_degrade_when_replace_intent(monkeypatch):
    """换产品/换人物/换场景:编辑失败后降级 = 把上传图当首帧重画整片,原片全丢。

    那样的成片"看似成功、其实没做替换",用户既拿不到效果也拿不回额度(实测踩过),
    所以带替换意图时必须直接失败并回写原因,走失败链路的退款/返还额度。
    """
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)

    async def fake_edit_fail(prompt, **kwargs):
        return ToolResult(content="字段不支持", metadata={
            "success": False, "error": "unknown field videos", "error_type": "request_error",
        })

    tool.edit_video = fake_edit_fail
    result = asyncio.run(tool.generate({
        "prompt": "换产品",
        "materials": ["https://x/a.jpg"],
        "reference_video": "https://x/ref.mp4",
        "intent": ["product"],
    }))
    assert calls == []                              # 没有降级到图生视频
    assert result.metadata["success"] is False
    assert "商品" in result.metadata["error"]        # 原因要说清是哪个维度的替换失败


def test_edit_failure_without_intent_still_degrades(monkeypatch):
    """未选替换意图(纯复刻)时保留降级:拿一段成片总比整单失败好,但必须打上 degraded 标记"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)

    async def fake_edit_fail(prompt, **kwargs):
        return ToolResult(content="字段不支持", metadata={"success": False, "error": "unknown field videos"})

    tool.edit_video = fake_edit_fail
    result = asyncio.run(tool.generate({
        "prompt": "复刻",
        "materials": ["https://x/a.jpg"],
        "reference_video": "https://x/ref.mp4",
    }))
    assert calls == ["i2v"]
    assert result.metadata["success"] is True
    assert result.metadata.get("degraded") is True   # 降级不能静默
    assert result.metadata.get("degrade_reason")


def test_replace_intent_without_edit_model_fails_loudly(monkeypatch):
    """有原片也选了替换意图却没配编辑模型:不能静默走图片链路(那等于放弃原片)"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "")
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    result = asyncio.run(tool.generate({
        "prompt": "x",
        "materials": ["https://x/a.jpg"],
        "reference_video": "https://x/ref.mp4",
        "intent": ["product", "scene"],
    }))
    assert calls == []
    assert result.metadata["success"] is False
    assert result.metadata["error_type"] == "config_error"
    assert "商品" in result.metadata["error"] and "场景" in result.metadata["error"]


def test_edit_output_mismatching_reference_is_flagged(monkeypatch):
    """成片与原片明显不符(换产品那次的 960×960/10s vs 1440×2560/23.5s)必须被打标

    那次差得极其明显却没有任何环节发现,最后靠人工 ffprobe 才定性。自检把这类
    "静默产出错片"在发生那一刻就暴露出来。
    """
    from app.core import media_prep

    async def fake_size(url):
        return (960, 960) if "edit" in url else (1440, 2560)      # 成片是正方形

    async def fake_duration(url):
        return 10.0 if "edit" in url else 23.5

    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    monkeypatch.setattr(media_prep, "probe_size", fake_size)
    monkeypatch.setattr(media_prep, "probe_duration", fake_duration)
    tool = _make_tool()

    async def fake_edit(prompt, **kwargs):
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    tool.edit_video = fake_edit
    result = asyncio.run(tool.generate({
        "prompt": "复刻", "materials": ["https://x/a.jpg"], "reference_video": "https://x/ref.mp4",
    }))
    mismatch = result.metadata.get("output_mismatch") or {}
    assert "画幅 960x960" in (mismatch.get("reason") or "")
    assert "时长" in (mismatch.get("reason") or "")
    assert result.metadata["success"] is True      # 只标记,不阻断(成片已付费)


def test_edit_output_matching_reference_is_not_flagged(monkeypatch):
    """成片与参考视频一致时不得打标(否则会成为噪音)"""
    from app.core import media_prep

    async def fake_size(_url):
        return (720, 1280)

    async def fake_duration(url):
        return 23.5

    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    monkeypatch.setattr(media_prep, "probe_size", fake_size)
    monkeypatch.setattr(media_prep, "probe_duration", fake_duration)
    tool = _make_tool()

    async def fake_edit(prompt, **kwargs):
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    tool.edit_video = fake_edit
    result = asyncio.run(tool.generate({
        "prompt": "复刻", "materials": ["https://x/a.jpg"], "reference_video": "https://x/ref.mp4",
    }))
    assert "output_mismatch" not in result.metadata


def test_no_edit_model_with_reference_video_fails_loudly(monkeypatch):
    """未配编辑模型时参考视频会被整个丢弃(成片退化成"用上传图重画"),所以必须明确失败。

    旧行为是"降级成图片链路 + 打 degraded 标记":用户拿到一段以为复刻了原片的成片,
    实际根本没用到参考视频 —— 与换产品那次静默降级属同一类问题。
    现在改为明确失败:失败链路会原路返还额度,并给出"配置编辑模型或改传图片"的可执行原因。
    """
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "")
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    result = asyncio.run(tool.generate({
        "prompt": "x", "materials": ["https://x/a.jpg"], "reference_video": "https://x/ref.mp4",
    }))
    assert calls == []                              # 不再降级到图片链路
    assert result.metadata["success"] is False
    assert result.metadata["error_type"] == "config_error"
    assert "视频编辑模型" in result.metadata["error"]


def test_edit_result_carries_reference_duration_for_subtitles(monkeypatch):
    """编辑成片时长**跟随参考视频**,字幕时间轴与烧录必须按它来

    提交用的是吸附档位(10s),而方舟编辑 duration=-1 → 成片 23.5s。
    用 10s 当基准会把字幕全部挤在成片前 1/3(多段分支踩过并修过,单段编辑漏了同一处)。
    """
    from app.core import media_prep

    async def _probe(_url):
        return 23.5

    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    monkeypatch.setattr(media_prep, "probe_duration", _probe)
    tool = _make_tool()

    async def fake_optimize(prompt, system_prompt=None):
        return prompt

    async def fake_edit(prompt, **kwargs):
        # 提交链路写入的 seconds 是吸附档位,正是要被覆写的那个值
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True, "seconds": 10})

    tool._optimize_prompt = fake_optimize
    tool.edit_video = fake_edit
    result = asyncio.run(tool.generate({
        "prompt": "复刻",
        "materials": ["https://x/a.jpg"],
        "reference_video": "https://x/ref.mp4",
        "script": {"version": 1, "segments": [{"id": "s1", "role": "hook", "words": [{"w": "你"}, {"w": "好"}]}]},
    }))
    assert result.metadata["seconds"] == 23
    assert result.metadata["script"]["timing"]["duration_ms"] == 23000


def test_image_pipeline_keeps_snapped_duration_for_subtitles():
    """图片链路成片就是吸附档位,字幕基准不得被改成模板原始时长"""
    tool = _make_tool()

    async def fake_i2v(prompt, **kwargs):
        return ToolResult(content="https://x/i2v.mp4", metadata={"success": True, "seconds": 10})

    tool.image_to_video = fake_i2v
    result = asyncio.run(tool.generate({
        "prompt": "x", "materials": ["https://x/a.jpg"], "duration": 30,
        "script": {"version": 1, "segments": [{"id": "s1", "role": "hook", "words": [{"w": "你"}]}]},
    }))
    assert result.metadata["seconds"] == 10
    assert result.metadata["script"]["timing"]["duration_ms"] == 10000


def test_without_edit_model_keeps_legacy_path(monkeypatch):
    """未配视频编辑模型时,**无参考视频**的旧链路行为完全不变(多图仍走 r2v)

    带参考视频的情况已改为明确失败(见 test_no_edit_model_with_reference_video_fails_loudly)——
    因为它会被静默丢弃,成片退化成"用上传图重画"。
    """
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "")
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    asyncio.run(tool.generate({
        "prompt": "x",
        "materials": ["https://x/a.jpg", "https://x/b.jpg"],
    }))
    assert calls == ["r2v"]


def test_should_edit_first():
    """O8(D9):时长探测失败不假设短片,改走多段拼接;其余按上限判定"""
    from app.tools.video_tool import _should_edit_first
    max_s = 30.0
    assert _should_edit_first(None, max_s) is False     # 探测失败 → 多段(更稳)
    assert _should_edit_first(10.0, max_s) is True       # 短 → 单段编辑
    assert _should_edit_first(30.0, max_s) is True       # 等于上限 → 单段
    assert _should_edit_first(30.1, max_s) is False      # 超上限 → 多段


def test_edit_output_slight_aspect_mismatch_flagged_after_tightening(monkeypatch):
    """O10(D11):画幅偏差 ~3.9%(旧阈值 5% 不报、新阈值 3% 报),验证自检收紧"""
    from app.core import media_prep

    # 参考 720x1280(9:16);成片 692x1280 → 偏差约 3.9%,介于 3%~5% 之间
    async def fake_size(url):
        return (692, 1280) if "edit" in url else (720, 1280)

    async def fake_duration(url):
        return 23.5

    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    monkeypatch.setattr(media_prep, "probe_size", fake_size)
    monkeypatch.setattr(media_prep, "probe_duration", fake_duration)
    tool = _make_tool()

    async def fake_edit(prompt, **kwargs):
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    tool.edit_video = fake_edit
    result = asyncio.run(tool.generate({
        "prompt": "复刻", "materials": ["https://x/a.jpg"], "reference_video": "https://x/ref.mp4",
    }))
    mismatch = result.metadata.get("output_mismatch") or {}
    assert "画幅 692x1280" in (mismatch.get("reason") or "")


def test_edit_output_lower_resolution_than_reference_flagged(monkeypatch):
    """O10(D11):成片分辨率低于参考视频时应打标(画质不应比原片差)"""
    from app.core import media_prep

    # 参考 1440x2560;成片 720x1280 → 短边 720 < 1440,且画幅一致(9:16)不应被画幅项误报
    async def fake_size(url):
        return (720, 1280) if "edit" in url else (1440, 2560)

    async def fake_duration(url):
        return 23.5

    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    monkeypatch.setattr(media_prep, "probe_size", fake_size)
    monkeypatch.setattr(media_prep, "probe_duration", fake_duration)
    tool = _make_tool()

    async def fake_edit(prompt, **kwargs):
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    tool.edit_video = fake_edit
    result = asyncio.run(tool.generate({
        "prompt": "复刻", "materials": ["https://x/a.jpg"], "reference_video": "https://x/ref.mp4",
    }))
    mismatch = result.metadata.get("output_mismatch") or {}
    reason = mismatch.get("reason") or ""
    assert "分辨率" in reason          # 低分辨率应被标记
    assert "画幅" not in reason        # 画幅一致不应误报


def test_edit_failure_pure_replicate_degrades_to_reference_frames(monkeypatch):
    """O3(D1):纯复刻(无上传图、无替换意图)视频编辑失败 → 抽参考帧走 r2v 保留场景,而非纯文生"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2.0-edit")
    # 避免对假 URL 真实跑 ffprobe / 调真 LLM
    monkeypatch.setattr(media_prep, "probe_duration", AsyncMock(return_value=10.0))
    tool = _make_tool()
    tool._optimize_prompt = AsyncMock(return_value="复刻")
    calls = []
    _stub_modes(tool, calls)

    async def fake_edit_fail(prompt, **kwargs):
        return ToolResult(content="", metadata={"success": False, "error": "InputVideoSensitiveContentDetected"})

    tool.edit_video = fake_edit_fail
    # 抽帧返回本地帧(async,与真实签名一致);上传后变成 OSS URL(>1 张 → reference_to_video)
    async def fake_extract(v):
        return ["/tmp/f1.jpg", "/tmp/f2.jpg", "/tmp/f3.jpg", "/tmp/f4.jpg"]

    monkeypatch.setattr(media_prep, "extract_reference_frames", fake_extract)
    monkeypatch.setattr("app.tools.video_tool.upload_local_file",
                        lambda p, k: "https://oss/frame.jpg")

    result = asyncio.run(tool.generate({
        "prompt": "复刻",
        "reference_video": "https://x/ref.mp4",
    }))
    assert "r2v" in calls                      # 抽帧后走参考生(保留场景)
    assert result.metadata["success"] is True
    assert result.metadata.get("degraded") is True
    assert "抽参考帧" in (result.metadata.get("degrade_note") or "")


def test_edit_follow_reference_ratio_skips_crop(monkeypatch):
    """O5(D5):开关开且纯复刻 → fit_reference_video 传 ratio=\"\"(不裁切,画幅跟随原片)

    开关关、或纯复刻但有替换意图 → 仍裁切到目标画幅。
    """
    tool = _make_tool()
    captured = {}

    async def fake_fit(url, max_seconds=None, ratio=""):
        captured["ratio"] = ratio
        return url

    monkeypatch.setattr(media_prep, "fit_reference_video", fake_fit)
    monkeypatch.setattr(tool, "_submit_and_poll",
                        AsyncMock(return_value=ToolResult(content="https://x/v.mp4", metadata={"success": True})))

    # 开关开 + 无替换意图 → 不裁切
    monkeypatch.setattr(config, "REPLICATE_FOLLOW_REFERENCE_RATIO", True)
    asyncio.run(tool.edit_video("复刻", reference_video="https://x/ref.mp4", replace_intent=None))
    assert captured["ratio"] == ""

    # 开关开 + 有替换意图 → 仍裁切到目标画幅
    captured.clear()
    asyncio.run(tool.edit_video("换产品", reference_video="https://x/ref.mp4", replace_intent=["product"]))
    assert captured["ratio"] == "9:16"

    # 开关关 → 仍裁切
    captured.clear()
    monkeypatch.setattr(config, "REPLICATE_FOLLOW_REFERENCE_RATIO", False)
    asyncio.run(tool.edit_video("复刻", reference_video="https://x/ref.mp4", replace_intent=None))
    assert captured["ratio"] == "9:16"


def test_regenerate_segment_orchestration(monkeypatch):
    """O7(D7):局部重跑按分段重生成 + 烧字幕 + 拼回原片"""
    tool = _make_tool()
    monkeypatch.setattr(tool, "_trim_video_window", AsyncMock(return_value="https://x/window.mp4"))
    monkeypatch.setattr(tool, "edit_video",
                        AsyncMock(return_value=ToolResult(content="https://x/seg.mp4", metadata={"success": True})))
    monkeypatch.setattr(subtitle, "burn_subtitle", AsyncMock(return_value="https://x/burned.mp4"))
    monkeypatch.setattr(tool, "_splice_segment", AsyncMock(return_value="https://x/final.mp4"))

    params = {
        "reference_video": "https://x/ref.mp4",
        "original_video": "https://x/orig.mp4",
        "script": {"segments": [
            {"id": "s0", "text": "老台词0", "timing": {"start_ms": 0, "end_ms": 5000}},
            {"id": "s1", "text": "老台词1", "timing": {"start_ms": 5000, "end_ms": 10000}},
        ]},
    }
    result = asyncio.run(tool.regenerate_segment(params, segment_index=1, new_text="新台词1"))
    assert result.metadata["success"] is True
    assert result.metadata["segment_index"] == 1
    assert result.metadata["window_ms"] == [5000, 10000]
    assert result.content == "https://x/final.mp4"      # 拼回原片
    assert result.metadata["spliced"] is True
    assert result.metadata["subtitle_burned"] is True
    # 重生成时把新台词作为 prompt、分段时长(窗口 5s)传入编辑
    assert tool.edit_video.call_args.args[0] == "新台词1"
    assert tool.edit_video.call_args.kwargs["duration"] == 5


def test_regenerate_segment_invalid_timing_fails(monkeypatch):
    """O7:分段缺有效时间窗或下标越界 → 直接失败(不浪费额度)"""
    tool = _make_tool()
    params = {"original_video": "https://x/orig.mp4", "script": {"segments": [
        {"id": "s0", "text": "x", "timing": {"start_ms": 0, "end_ms": 0}},
    ]}}
    res = asyncio.run(tool.regenerate_segment(params, segment_index=0, new_text="y"))
    assert res.metadata["success"] is False
    assert "时间窗" in res.metadata["error"]

    res2 = asyncio.run(tool.regenerate_segment(params, segment_index=9, new_text="y"))
    assert res2.metadata["success"] is False


def test_replace_directive_person_locks_actions_and_plots():
    """换人物必须同时锁定原片动作与情节,否则会退化成"静景翻拍"(实测:狗拉婴儿车奔跑整段消失)"""
    tool = _make_tool()
    text = tool._build_replace_directive(["person"], ["https://x/p.jpg"])
    assert "完整承接原片人物的动作" in text
    assert "严禁省略或改写原有镜头与事件" in text
    # 未指定主角表现 → 不得凭空追加表演要求
    assert "舞蹈" not in text and "推广" not in text


def test_replace_directive_appends_lead_act_only_for_person():
    """主角表现(跳舞/推广)只在换人物时追加;换产品/换场景不得被追加"""
    tool = _make_tool()
    tool._lead_act = "dance"
    assert "舞蹈" in tool._build_replace_directive(["person"], ["https://x/p.jpg"])
    assert "舞蹈" not in tool._build_replace_directive(["product"], ["https://x/p.jpg"])


def test_lead_act_assets_are_loadable():
    """主角表现正文必须能从资产加载(资产名写错会静默回退内联兜底,导致改 MD 不生效)"""
    from skills.prompts import safe_render
    for key, (name, _default) in LEAD_ACT_ASSETS.items():
        body = safe_render(name, default="")
        assert body, f"主角表现资产 {name}({key})未加载,请确认 backend/skills/prompts 对该环境可见"
