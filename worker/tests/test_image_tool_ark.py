# -*- coding: utf-8 -*-
"""图片工具:火山方舟原生网关适配(文生图/图生图走 /images/generations,image 字段传参考图)。"""
import asyncio
from unittest.mock import AsyncMock

from app.tools.image_tool import ImageGenTool

ARK = "https://ark.cn-beijing.volces.com/api/v3"


def _ark():
    return ImageGenTool(api_key="k", base_url=ARK)


def test_is_ark_detection():
    assert _ark()._is_ark() is True
    assert ImageGenTool(api_key="k", base_url="http://localhost/v1")._is_ark() is False


def test_ark_text_to_image_generates_each():
    async def run():
        tool = _ark()
        calls = []

        async def fake_ark(model=None, prompt=None, size=None, image=None, negative_prompt=None):
            calls.append({"model": model, "prompt": prompt, "size": size, "image": image})
            return {"data": [{"url": f"https://x/{len(calls)}.jpeg"}]}

        tool._ark_image = fake_ark
        r = await tool.text_to_image("一只猫", model="doubao-seedream-4-0-250828", ratio="1:1", num_images=2)
        assert r.metadata["success"] is True
        assert len(calls) == 2                     # num_images=2 逐张生成
        assert calls[0]["image"] is None           # 文生图无参考图
        assert calls[0]["size"] == "1024x1024"
        assert "https://x/1.jpeg" in r.content

    asyncio.run(run())


def test_ark_image_to_image_passes_reference():
    async def run():
        tool = _ark()
        seen = {}

        async def fake_ark(model=None, prompt=None, size=None, image=None, negative_prompt=None):
            seen.update({"model": model, "prompt": prompt, "size": size, "image": image})
            return {"data": [{"url": "https://x/edit.jpeg"}]}

        tool._ark_image = fake_ark
        r = await tool.image_to_image(
            "换成星空背景", input_image="https://x/in.jpg",
            model="doubao-seedream-4-0-250828", ratio="1:1",
        )
        assert r.metadata["success"] is True
        assert seen["image"] == "https://x/in.jpg"  # 参考图作为 image 字段
        assert seen["model"] == "doubao-seedream-4-0-250828"

    asyncio.run(run())
