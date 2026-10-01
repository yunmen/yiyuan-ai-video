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


def test_video_edit_follows_video_route_by_default():
    """未配 gen.route.video_edit 时,视频编辑跟随 video 网关(不改变现有行为)"""
    _load({
        "gen.gw.ark.url": "https://ark.cn-beijing.volces.com/api/v3",
        "gen.gw.ark.key": "ark-key",
        "gen.gw.ark.proto": "ark",
        "gen.route.video": "ark",
    })
    assert gateway.resolve("video_edit") == gateway.resolve("video")


def test_video_edit_can_use_own_gateway():
    """配了 gen.route.video_edit 时编辑走自己的网关(如中转站),普通视频不受影响"""
    _load({
        "gen.gw.ark.url": "https://ark.cn-beijing.volces.com/api/v3",
        "gen.gw.ark.key": "ark-key",
        "gen.gw.ark.proto": "ark",
        "gen.gw.relay.url": "https://aitoken.example/v1",
        "gen.gw.relay.key": "relay-key",
        "gen.route.video": "ark",
        "gen.route.video_edit": "relay",
    })
    edit = gateway.resolve("video_edit")
    assert edit["name"] == "relay"
    assert edit["url"].startswith("https://aitoken.example")
    assert edit["proto"] == "openai"                      # 非 volces 地址嗅探为 openai 协议
    assert gateway.resolve("video")["name"] == "ark"      # 普通视频仍走方舟


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


# ===================== 网关候选列表 + 故障转移 =====================

def test_resolve_all_orders_route_before_fallbacks():
    """候选列表:路由网关在最前,其后是固定槽位回退链,且不重复"""
    _load({
        "gen.gw.ali.url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "gen.gw.ali.key": "ali-key",
        "gen.route.image": "ali",
    })
    cands = gateway.resolve_all("image")
    assert cands[0]["name"] == "ali"
    assert cands[0]["url"].startswith("https://dashscope")
    urls = [c["url"] for c in cands]
    assert len(urls) == len(set(urls))          # 已去重
    # resolve() 仍取首个,向后兼容
    assert gateway.resolve("image")["name"] == "ali"


def test_resolve_all_dedupes_identical_gateway(monkeypatch):
    """多个槽位指向同一地址时只保留 1 个候选,避免把同一地址重试两遍"""
    from app.settings import config

    monkeypatch.setattr(config, "CHAT_LLM_BASE_URL", "https://same.example/v1")
    monkeypatch.setattr(config, "CHAT_LLM_API_KEY", "k")
    monkeypatch.setattr(config, "LLM_BASE_API_URL", "https://same.example/v1")
    monkeypatch.setattr(config, "LLM_BASE_API_KEY", "k")
    gateway.load({})

    cands = gateway.resolve_all("text")
    assert len(cands) == 1


def test_with_failover_switches_to_next_gateway(monkeypatch):
    """故障转移:当前网关失败 → 按候选顺序切到备选网关重试,首个成功即返回"""
    import asyncio

    from app.settings import config
    from app.tools.base import BaseGenTool

    monkeypatch.setattr(config, "CHAT_LLM_BASE_URL", "https://a.example/v1")
    monkeypatch.setattr(config, "CHAT_LLM_API_KEY", "ka")
    monkeypatch.setattr(config, "LLM_BASE_API_URL", "https://b.example/v1")
    monkeypatch.setattr(config, "LLM_BASE_API_KEY", "kb")
    gateway.load({})

    switched = []

    class _Tool(BaseGenTool):
        name = "test"

        def __init__(self):
            self.api_key = "ka"
            self.base_url = "https://a.example/v1"
            self.proto = "openai"
            self.client = None
            self._pinned = False

        def _switch_gateway(self, gw):
            switched.append(gw["url"])
            self.base_url = gw["url"].rstrip("/")
            self.api_key = gw["key"]
            self.proto = gw["proto"]

    tool = _Tool()
    seen = []

    async def call(gw):
        seen.append(gw["url"])
        if gw["url"].startswith("https://a."):
            raise RuntimeError("a down")
        return "ok"

    assert asyncio.run(tool._with_failover("text", call, label="t")) == "ok"
    assert seen == ["https://a.example/v1", "https://b.example/v1"]
    assert switched == ["https://b.example/v1"]


def test_video_submit_failover_then_poll_uses_winning_gateway(monkeypatch):
    """视频:主网关提交失败 → 切备选提交成功;轮询复用"提交成功的网关",不回到失败网关"""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import app.tools.base as base_mod
    import app.tools.video_tool as vt_mod
    from app.settings import config

    PRIMARY, BACKUP = "https://primary.example/v1", "https://backup.example/v1"
    monkeypatch.setattr(config, "LLM_BASE_API_URL", PRIMARY)
    monkeypatch.setattr(config, "LLM_BASE_API_KEY", "k1")
    monkeypatch.setattr(config, "CHAT_LLM_BASE_URL", BACKUP)
    monkeypatch.setattr(config, "CHAT_LLM_API_KEY", "k2")
    gateway.load({})

    posts, polls, persisted = [], [], []
    # 转存后的自有 OSS 地址(与本用例契约无关,仅作占位返回值)
    PERSISTED = "https://oss.example/v.mp4"

    def make_client(api_key=None, base_url=None):
        async def post(path, cast_to=None, body=None):
            posts.append(base_url)
            if base_url == PRIMARY:
                raise RuntimeError("primary down")
            return {"id": "task-1"}

        async def retrieve(task_id):
            polls.append(base_url)
            return SimpleNamespace(status="completed", metadata={"url": "https://cdn/v.mp4"})

        return SimpleNamespace(post=post, videos=SimpleNamespace(retrieve=retrieve))

    async def fake_persist(urls, prefix=None):
        persisted.append(list(urls))
        return [PERSISTED] * len(urls)

    monkeypatch.setattr(vt_mod, "AsyncOpenAI", make_client)
    monkeypatch.setattr(base_mod, "AsyncOpenAI", make_client)
    # 成片 OSS 转存要真实下载/上传模型临时直链;本用例契约是「故障转移 + 轮询复用获胜网关」,
    # 故把转存换成本地桩,让用例不依赖外网 —— 否则无网环境会因转存失败而误判整个故障转移链路。
    monkeypatch.setattr(vt_mod, "persist_url_list", fake_persist)

    tool = vt_mod.VideoGenTool(api_key="k1", base_url=None)
    tool._optimize_prompt = AsyncMock(return_value="p")
    tool.poll_interval = 0

    result = asyncio.run(tool.generate({"prompt": "x"}))

    assert result.metadata["success"] is True
    assert result.content == PERSISTED           # 交付的是转存后的自有地址(临时直链会过期)
    assert persisted == [["https://cdn/v.mp4"]]  # 转存对象正是轮询拿到的原始直链
    assert posts == [PRIMARY, BACKUP]      # 提交:主网关失败 → 备选成功
    assert polls == [BACKUP]               # 轮询:只打提交成功的网关
