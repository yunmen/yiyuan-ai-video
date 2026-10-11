# -*- coding: utf-8 -*-
"""代码渲染层(零模型成本)数据契约与命令构建(纯函数)

这些命令/ spec 会直接喂给 ffmpeg 合成与 PIL 绘制,拼错参数或 spec 结构是
「叠加层静默失效」,所以在不依赖 ffmpeg/OSS 的前提下先把契约钉死。
"""
from app.core.compose import Cue
from app.core import overlay


def _cue(start_ms, end_ms, text, pos=None):
    """构造与 compose.Cue 同字段的 dict(Cue 是 dataclass,这里用 dict 模拟黑名单结构)"""
    return {"start_ms": start_ms, "end_ms": end_ms, "text": text, "pos": pos}


def test_build_design_spec_from_cues():
    """cue → 动态字幕元素;携带 pos 实现头部跟随锚点"""
    cues = [
        _cue(0, 3000, "这款产品真的很好用"),
        _cue(3000, 6000, "现在下单还有优惠", pos=[0.5, 0.3]),
    ]
    spec = overlay.build_design_spec(cues, {"caption_style": "highlight", "duration": 6}, (1080, 1920))
    assert spec is not None
    assert spec["canvas"] == [1080, 1920]
    assert len(spec["elements"]) == 2
    caps = [e for e in spec["elements"] if e["type"] == "caption"]
    assert caps[0]["style"]["preset"] == "highlight"
    assert caps[1]["pos"] == [0.5, 0.3]
    # 元素内必须带 _canvas(绘制函数据此缩放/定位)
    assert caps[0]["_canvas"] == [1080, 1920]


def test_build_design_spec_card_badge_only_when_provided():
    """信息卡/角标仅当显式提供才生成,绝不臆造商品信息"""
    cues = [_cue(0, 2000, "测试")]
    params = {"duration": 2}
    spec = overlay.build_design_spec(cues, params, (1080, 1920))
    types = {e["type"] for e in spec["elements"]}
    assert types == {"caption"}

    params2 = {
        "duration": 2,
        "overlay_card": {"title": "商品名", "body": "限时特惠", "corner": "bl"},
        "overlay_badge": {"text": "AI 生成", "corner": "tr"},
    }
    spec2 = overlay.build_design_spec(cues, params2, (1080, 1920))
    types2 = {e["type"] for e in spec2["elements"]}
    assert types2 == {"caption", "card", "badge"}


def test_build_design_spec_no_cues_returns_none():
    """没有任何字幕且未提供卡/标 → 返回 None(调用方跳过渲染)"""
    assert overlay.build_design_spec([], {"duration": 1}, (1080, 1920)) is None


def test_build_overlay_track_cmd():
    """逐帧透明 PNG → 保留 alpha 的叠加轨(纯函数)"""
    cmd = overlay.build_overlay_track_cmd("/tmp/frames", 25.0, "/tmp/track.mov")
    assert cmd[0] == "ffmpeg"
    assert "-framerate" in cmd
    assert cmd[cmd.index("-framerate") + 1] == "25.000"
    assert "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] == "png"


def test_build_overlay_compose_cmd():
    """透明叠加轨叠到成片(scale2ref 适配 + overlay),纯函数"""
    cmd = overlay.build_overlay_compose_cmd("/tmp/base.mp4", "/tmp/track.mov", "/tmp/out.mp4")
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "scale2ref" in fc
    assert "overlay=shortest=1" in fc
    assert "-map" in cmd


def test_wrap_line_respects_max_and_cap():
    """字幕折行优先标点后断,且最多 _CAPTION_MAX_LINES 行"""
    long_text = "这款产品真的很好用而且现在下单还有优惠活动大家不要错过"
    lines = overlay._wrap_line(long_text)
    assert len(lines) <= overlay._CAPTION_MAX_LINES
    for ln in lines:
        assert len(ln) <= overlay._CAPTION_MAX_LINE_CHARS + 1  # 末行省略号可能 +1


def test_build_design_spec_ranking():
    """排行榜仅当显式提供 items 才生成,且条目/错峰时长被透传"""
    cues = [_cue(0, 2000, "测试")]
    params = {
        "duration": 5,
        "overlay_ranking": {
            "title": "热度榜",
            "items": [{"label": "A", "value": "98"}, {"label": "B", "value": "87"}],
            "corner": "bl", "stagger_ms": 400,
        },
    }
    spec = overlay.build_design_spec(cues, params, (1080, 1920))
    rk = [e for e in spec["elements"] if e["type"] == "ranking"][0]
    assert rk["title"] == "热度榜"
    assert len(rk["items"]) == 2
    assert rk["items"][0]["label"] == "A" and rk["items"][0]["value"] == "98"
    assert rk["stagger_ms"] == 400
    assert rk["_canvas"] == [1080, 1920]


def test_build_design_spec_reveal_flash_sticker_only_when_provided():
    """揭示板/闪烁/贴纸均仅当显式提供关键字段才生成,缺省不臆造"""
    cues = [_cue(0, 2000, "测试")]
    params = {"duration": 2}
    spec = overlay.build_design_spec(cues, params, (1080, 1920))
    types = {e["type"] for e in spec["elements"]}
    assert types == {"caption"}  # 未提供任何动效 → 只有字幕

    params2 = {
        "duration": 2,
        "overlay_reveal": {"text": "上新啦", "emoji": "✨", "at_ms": 1000},
        "overlay_flash": {"color": "#FFD400", "at_ms": 800, "duration_ms": 400},
        "overlay_sticker": {"text": "这个我买过", "side": "l", "at_ms": 2000},
    }
    spec2 = overlay.build_design_spec(cues, params2, (1080, 1920))
    types2 = {e["type"] for e in spec2["elements"]}
    assert types2 == {"caption", "reveal", "flash", "sticker"}
    rv = [e for e in spec2["elements"] if e["type"] == "reveal"][0]
    assert rv["at_ms"] == 1000 and rv["emoji"] == "✨"
    fl = [e for e in spec2["elements"] if e["type"] == "flash"][0]
    assert fl["color"] == "#FFD400"
    st = [e for e in spec2["elements"] if e["type"] == "sticker"][0]
    assert st["side"] == "l"
