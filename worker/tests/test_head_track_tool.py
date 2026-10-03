# -*- coding: utf-8 -*-
"""头部检测工具:可选网关 + 优雅降级(对齐 Hypit caption-tracking)

重点是「未配置网关 / 检测失败都返回 None」,由 subtitle 烧录降级为底部字幕,
绝不让一次已付费的生成因「加字幕跟随头部」变失败。
"""
import asyncio
import os

from app.tools.head_track_tool import HeadTrackTool


def _fake_frames(video, out_dir, fps):
    """桩入抽帧:真实写出两个临时文件(否则 _detect_image 打开文件会失败)"""
    paths = []
    for i in range(2):
        p = os.path.join(out_dir, f"frame_{i:04d}.png")
        with open(p, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        paths.append((i / fps, p))
    return paths


def test_detect_no_gateway(monkeypatch):
    """未配置 gen.route.head:直接降级,None(不报错)"""
    monkeypatch.setattr("app.core.gateway.resolve_all", lambda cap: [])
    assert asyncio.run(HeadTrackTool().detect("x.mp4")) is None


def test_detect_with_gateway(monkeypatch):
    """配置了网关:抽帧 + 送检,返回 [(t,x,y,w,h)...]"""
    monkeypatch.setattr(
        "app.core.gateway.resolve_all",
        lambda cap: [{"name": "gw", "url": "http://gw", "key": "k"}],
    )
    tool = HeadTrackTool()
    # 绕过真实抽帧/ffmpeg:直接给两帧(真实写出临时文件)
    monkeypatch.setattr(tool, "_sample_frames", _fake_frames)

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"box": [0.1, 0.2, 0.2, 0.3]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr("app.tools.head_track_tool.httpx.AsyncClient", _Client)
    boxes = asyncio.run(tool.detect("x.mp4"))
    assert boxes and len(boxes) == 2
    assert boxes[0][0] == 0.0
    assert boxes[0][1:5] == (0.1, 0.2, 0.2, 0.3)


def test_detect_gateway_failure_falls_back(monkeypatch):
    """网关全失败:返回 None(降级),不抛异常"""
    monkeypatch.setattr(
        "app.core.gateway.resolve_all",
        lambda cap: [{"name": "gw", "url": "http://gw", "key": "k"}],
    )
    tool = HeadTrackTool()
    monkeypatch.setattr(tool, "_sample_frames", _fake_frames)

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            raise RuntimeError("网关 500")

    monkeypatch.setattr("app.tools.head_track_tool.httpx.AsyncClient", _Client)
    assert asyncio.run(tool.detect("x.mp4")) is None
