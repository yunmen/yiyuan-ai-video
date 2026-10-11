# -*- coding: utf-8 -*-
"""图片工具:火山方舟原生网关适配(文生图/图生图走 /images/generations,image 字段传参考图)。"""
import asyncio

import pytest

import app.tools.image_tool as image_mod
from app.tools.image_tool import ImageGenTool

ARK = "https://ark.cn-beijing.volces.com/api/v3"


@pytest.fixture(autouse=True)
def _stub_asset_cache(monkeypatch):
    """P2 资产缓存默认打桩为「未命中」,避免单测触达真实 backend 缓存接口。

    缓存是优化而非链路依赖,默认未命中不影响既有断言;缓存用例内可再次 setattr 覆盖。
    """
    async def _miss(notify_url=None, cache_key=None, asset_type=""):
        return None

    async def _noop(*args, **kwargs):
        return False

    monkeypatch.setattr(image_mod.asset_cache, "fetch", _miss)
    monkeypatch.setattr(image_mod.asset_cache, "store", _noop)


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


def test_text_to_image_cache_hit_skips_gateway(monkeypatch):
    """P2 资产缓存:模型 + 提示词 + 尺寸 + 张数完全相同 → 复用 OSS 直链,零付费调用。

    批量出片/多语言变体常反复请求同一张 B-roll 素材,这是最直接可复用的一笔成本。
    """
    async def run():
        tool = _ark()
        calls = []

        async def fake_ark(**kw):
            calls.append(kw)
            return {"data": [{"url": "https://x/new.jpeg"}]}

        async def hit(notify_url=None, cache_key=None, asset_type=""):
            assert asset_type == "image"
            return {"content": "https://cdn/cached.jpeg,https://cdn/cached2.jpeg", "meta": {}}

        tool._ark_image = fake_ark
        monkeypatch.setattr(image_mod.asset_cache, "fetch", hit)
        r = await tool.text_to_image(
            "一只猫", model="m", ratio="1:1", num_images=2, notify_url="http://b/cb",
        )
        assert r.metadata["success"] is True
        assert r.metadata["cache"] == "hit"
        assert r.metadata["num_images"] == 2
        assert r.content == "https://cdn/cached.jpeg,https://cdn/cached2.jpeg"
        assert calls == []  # 命中即跳过真实生成

    asyncio.run(run())


def test_image_to_image_cache_miss_stores(monkeypatch):
    """未命中 → 正常生成,并按 asset_type=image 把 OSS 直链写回缓存,供后续复用。"""
    async def run():
        tool = _ark()
        stored = []

        async def fake_ark(**kw):
            return {"data": [{"url": "https://x/edit.jpeg"}]}

        async def store(notify_url, cache_key, asset_type, content, **kwargs):
            stored.append((asset_type, content))
            return True

        async def fake_persist(urls, prefix):
            return list(urls)

        tool._ark_image = fake_ark
        monkeypatch.setattr(image_mod.asset_cache, "store", store)
        monkeypatch.setattr(image_mod, "persist_url_list", fake_persist)
        r = await tool.image_to_image(
            "换星空", input_image="https://x/in.jpg", model="m", notify_url="http://b/cb",
        )
        assert r.metadata["success"] is True
        assert r.metadata["cache"] == "miss"
        assert stored == [("image", "https://x/edit.jpeg")]

    asyncio.run(run())
