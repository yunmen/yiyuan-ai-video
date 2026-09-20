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
    assert "--ratio 9:16" in text["text"]
    assert "--duration 12" in text["text"]
    assert {"type": "image_url", "image_url": {"url": "https://x/a.jpg"}} in body["content"]


def test_ark_submit_and_poll():
    async def run():
        tool = _ark_tool()
        tool._optimize_prompt = AsyncMock(return_value="p")
        calls = []

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
        assert result.content == "https://x/v.mp4"
        # 提交走方舟原生端点,content 数组正确(文本 + 图片)
        assert calls[0][0] == "POST" and calls[0][1] == "/contents/generations/tasks"
        assert calls[0][2]["content"][0]["type"] == "text"
        assert calls[0][2]["content"][1]["type"] == "image_url"
        # 查询走方舟原生端点
        assert calls[1][1] == "/contents/generations/tasks/cgt-1"

    asyncio.run(run())
