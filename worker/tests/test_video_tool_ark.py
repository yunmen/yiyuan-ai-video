# -*- coding: utf-8 -*-
"""视频工具:火山方舟原生网关适配。
方舟视频生成走 POST /contents/generations/tasks(model + content[text/image_url]),
查询走 GET /contents/generations/tasks/{id}(结果取 content.video_url);
OpenAI 兼容中转站仍走 /videos。"""
import asyncio
from unittest.mock import AsyncMock

from app.tools.video_tool import VideoGenTool


def _ark_tool():
    return VideoGenTool(api_key="k", base_url="https://ark.cn-beijing.volces.com/api/v3")


def test_is_ark_detection():
    assert _ark_tool()._is_ark() is True
    assert VideoGenTool(api_key="k", base_url="http://localhost/v1")._is_ark() is False


def test_ark_body_builds_content():
    tool = _ark_tool()
    payload = {
        "model": "doubao-seedance-1-0-pro-250528",
        "prompt": "一只猫",
        "image": "https://x/a.jpg",
        "seconds": "12",
        "metadata": {"parameters": {"resolution": "1080P", "ratio": "9:16", "duration": 12}},
    }
    body = tool._ark_body(payload)
    assert body["model"] == "doubao-seedance-1-0-pro-250528"
    text = body["content"][0]
    assert text["type"] == "text"
    assert "--resolution 1080p" in text["text"]   # 方舟用小写分辨率
    # ratio/duration 走**顶层字段**:新版方舟(Seedance 2.5 等)会整段忽略 text 内的
    # --ratio/--duration 标记,写进 text 的表现是"时长/比例不对且永远没声音"。
    # 故这里锁定契约:两者都不在 text 里,只在 body 顶层。
    assert "--ratio" not in text["text"]
    assert "--duration" not in text["text"]
    assert body["ratio"] == "9:16"
    assert body["duration"] == 12
    image = body["content"][1]
    assert image["type"] == "image_url" and image["image_url"]["url"] == "https://x/a.jpg"
    assert image["role"] == "first_frame"   # 单图即首帧图


def test_ark_submit_and_poll(monkeypatch):
    async def run():
        tool = _ark_tool()
        tool._optimize_prompt = AsyncMock(return_value="p")
        calls = []
        # 转存与成片兜底校验都会真去下载素材地址,单测必须离线(否则在本机走真实网络必然失败)
        async def fake_persist(urls, prefix=None):
            # 转存后换成自有 COS 地址:与轮询直链相同会被判成「转存失败保留原链」
            return ["https://mycos/persisted.mp4" for _ in urls]

        async def fake_detect(video, **kwargs):
            return None

        monkeypatch.setattr("app.tools.video_tool.persist_url_list", fake_persist)
        monkeypatch.setattr("app.core.frame_quality.detect_degenerate_video", fake_detect)

        async def fake_req(method, path, body=None):
            calls.append((method, path, body))
            if method == "POST":
                return {"id": "cgt-1"}
            if len([c for c in calls if c[0] == "GET"]) == 1:
                return {"id": "cgt-1", "status": "running"}
            return {"id": "cgt-1", "status": "succeeded", "content": {"video_url": "https://x/v.mp4"}}

        tool._ark_request = fake_req
        tool.poll_interval = 0

        result = await tool.generate(
            {"prompt": "x", "materials": ["https://x/a.jpg"]}, checkpoint=None, on_stage=AsyncMock()
        )
        assert result.metadata["success"] is True
        assert result.content == "https://mycos/persisted.mp4"   # 交付的是转存后的自有地址
        # 提交走方舟原生端点,content 数组正确(文本 + 图片)
        assert calls[0][0] == "POST" and calls[0][1] == "/contents/generations/tasks"
        assert calls[0][2]["content"][0]["type"] == "text"
        assert calls[0][2]["content"][1]["type"] == "image_url"
        # 查询走方舟原生端点
        assert calls[1][1] == "/contents/generations/tasks/cgt-1"

    asyncio.run(run())


def test_ark_body_carries_reference_video():
    """参考视频必须转成 video_url:漏掉它会让"视频编辑"静默退化成文生视频"""
    tool = _ark_tool()
    body = tool._ark_body({
        "model": "doubao-seedance-2-0-fast-260128",
        "prompt": "复刻",
        "videos": ["https://x/ref.mp4"],
        "images": ["https://x/p.jpg"],
        "metadata": {"parameters": {"duration": 8, "ratio": "9:16", "resolution": "1080P"}},
    })
    types = [c["type"] for c in body["content"]]
    assert types == ["text", "image_url", "video_url"]
    assert body["content"][-1]["video_url"]["url"] == "https://x/ref.mp4"
    # role 必填:方舟按 role 区分素材用途(reference_video=参考视频, reference_image=参考图),
    # 缺 role 会被拒:"reference media mode requires video role to be reference_video"
    assert body["content"][-1]["role"] == "reference_video"
    assert body["content"][1]["role"] == "reference_image"


def test_private_material_converted_to_data_uri(monkeypatch):
    """内网素材(127.0.0.1)模型侧拉不到,提交前必须转成 data URI / OSS 公网地址"""
    class _Resp:
        content = b"fake-image-bytes"
        headers = {"content-type": "image/jpeg"}

        def raise_for_status(self):
            return None

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            return _Resp()

    monkeypatch.setattr("app.tools.video_tool.httpx.AsyncClient", _Client)
    # 本用例验证 data URI 兜底分支:上传不可用时(未启用/失败)必须回退成 data URI。
    # 注意 OSS_ENABLED 是只读 property(由 OSS 配置推导),只能从这里 mock 上传结果。
    monkeypatch.setattr("app.utils.oss.upload_bytes", lambda *a, **k: None)

    async def run():
        tool = _ark_tool()
        assert tool._is_private_url("http://127.0.0.1:8801/static/uploads/a.jpg") is True
        assert tool._is_private_url("https://oss.example.com/a.jpg") is False
        payload = await tool._prepare_media({
            "image": "http://127.0.0.1:8801/static/uploads/a.jpg",
            "images": ["https://oss.example.com/b.jpg"],
        })
        assert payload["image"].startswith("data:image/jpeg;base64,")
        assert payload["images"] == ["https://oss.example.com/b.jpg"]   # 公网地址原样透传

    asyncio.run(run())
