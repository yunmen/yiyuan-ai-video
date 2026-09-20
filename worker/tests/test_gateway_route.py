# -*- coding: utf-8 -*-
"""灵活网关:命名网关注册表 + 能力路由 + 显式协议;未配置路由时回退旧槽位。"""
from app.core import gateway
from app.tools.video_tool import VideoGenTool
from app.tools.image_tool import ImageGenTool


def _load(data):
    gateway.load(data)


def teardown_function(_):
    gateway.load({})  # 清理全局状态,避免用例间串扰


def test_resolve_routes_by_capability():
    _load({
        "gen.gw.ali.url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "gen.gw.ali.key": "ali-key",
        "gen.gw.ali.proto": "openai",
        "gen.gw.ark.url": "https://ark.cn-beijing.volces.com/api/v3",
        "gen.gw.ark.key": "ark-key",
        "gen.gw.ark.proto": "ark",
        "gen.route.image": "ali",
        "gen.route.video": "ark",
    })
    img = gateway.resolve("image")
    assert img["name"] == "ali"
    assert img["proto"] == "openai"
    assert img["url"].startswith("https://dashscope")
    vid = gateway.resolve("video")
    assert vid["name"] == "ark"
    assert vid["proto"] == "ark"


def test_resolve_falls_back_when_no_route():
    _load({})
    gw = gateway.resolve("video")
    assert gw["name"].startswith("fallback:")   # 回退旧槽位
    assert gw["url"]                                   # 有可用地址


def test_proto_drives_tool_behavior():
    _load({
        "gen.gw.ali.url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "gen.gw.ali.key": "k",
        "gen.gw.ali.proto": "openai",
        "gen.route.video": "ali",
    })
    tool = VideoGenTool()
    assert tool.base_url.startswith("https://dashscope")
    assert tool._is_ark() is False                       # 显式 proto=openai,不因 URL 猜错


def test_ark_proto_routes_to_native_image():
    _load({
        "gen.gw.ark.url": "https://ark.cn-beijing.volces.com/api/v3",
        "gen.gw.ark.key": "k",
        "gen.gw.ark.proto": "ark",
        "gen.route.image": "ark",
    })
    tool = ImageGenTool()
    assert tool._is_ark() is True


def test_auto_proto_by_url():
    assert gateway.auto_proto("https://ark.cn-beijing.volces.com/api/v3") == "ark"
    assert gateway.auto_proto("https://api.deepseek.com") == "openai"
