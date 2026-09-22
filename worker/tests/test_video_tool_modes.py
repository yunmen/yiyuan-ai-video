# -*- coding: utf-8 -*-
"""视频工具:按素材数量自动选择生成模式(文生/图生/参考生)"""
import asyncio

from app.settings import config
from app.tools.video_tool import VideoGenTool, parse_duration_gears
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


def test_without_edit_model_keeps_legacy_path(monkeypatch):
    """未配视频编辑模型时行为不变(旧网关不受影响)"""
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "")
    tool = _make_tool()
    calls = []
    _stub_modes(tool, calls)
    asyncio.run(tool.generate({
        "prompt": "x",
        "materials": ["https://x/a.jpg", "https://x/b.jpg"],
        "reference_video": "https://x/ref.mp4",
    }))
    assert calls == ["r2v"]
