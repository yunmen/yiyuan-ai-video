# -*- coding: utf-8 -*-
"""使用真实 Pillow 验证九宫格像素处理，仅替换下载和上传边界。"""
import asyncio
import io
import shutil

import pytest
from PIL import Image

from app.tools import grid_tool


@pytest.fixture
def storage(monkeypatch, tmp_path):
    """提供本地图像与内存上传记录，不访问网络或对象存储。"""
    sources = {}
    uploads = []
    downloads = []

    def download(url, suffix=".jpg"):
        """复制测试素材，保留原图以核对临时文件清理。"""
        if url not in sources:
            return None
        path = tmp_path / f"download_{len(downloads)}{suffix}"
        shutil.copyfile(sources[url], path)
        downloads.append(path)
        return str(path)

    def upload(data, key):
        """记录真实 JPEG 内容并返回稳定的测试地址。"""
        uploads.append((data, key))
        return f"https://test.invalid/{len(uploads)}.jpg"

    monkeypatch.setattr(grid_tool, "download_to_local", download)
    monkeypatch.setattr(grid_tool, "upload_bytes", upload)
    return sources, uploads, downloads


def test_compose_preserves_order_and_blank_cells(storage, tmp_path):
    """两图按行放入前两格，其余格白底，完成后清理下载文件。"""
    sources, uploads, downloads = storage
    for name, color in (("red", "red"), ("blue", "blue")):
        path = tmp_path / f"{name}.png"
        Image.new("RGB", (30, 30), color).save(path)
        sources[name] = path
    assert asyncio.run(grid_tool.compose_grid(["red", "blue"]))
    with Image.open(io.BytesIO(uploads[0][0])) as image:
        assert image.size == (90, 90)
        assert image.getpixel((15, 15))[0] > 240
        assert image.getpixel((45, 15))[2] > 240
        assert min(image.getpixel((75, 75))) > 240
    assert all(not path.exists() for path in downloads)


def test_compose_download_failure_is_not_partial_success(storage, tmp_path):
    """素材下载失败不产生错位的成功拼图，并清理已下载素材。"""
    sources, uploads, downloads = storage
    path = tmp_path / "source.png"
    Image.new("RGB", (9, 9)).save(path)
    sources["ok"] = path
    assert asyncio.run(grid_tool.compose_grid(["ok", "missing"])) is None
    assert uploads == []
    assert all(not path.exists() for path in downloads)


def test_split_covers_non_divisible_dimensions(storage, tmp_path):
    """非三整除的宽高也必须完整覆盖源图，不能遗漏右侧和底部。"""
    sources, uploads, downloads = storage
    path = tmp_path / "source.png"
    Image.new("RGB", (100, 101), "red").save(path)
    sources["source"] = path
    result = asyncio.run(grid_tool.split_grid("source"))
    assert len(result) == 9
    sizes = []
    for data, _ in uploads:
        with Image.open(io.BytesIO(data)) as image:
            sizes.append(image.size)
    assert sum(width * height for width, height in sizes) == 100 * 101
    assert sizes[-1] == (34, 34)
    assert all(not path.exists() for path in downloads)


def test_split_upload_failure_is_not_partial_success(storage, tmp_path, monkeypatch):
    """任一单图上传失败时整体失败，避免九张结果缺失。"""
    sources, _, downloads = storage
    path = tmp_path / "source.png"
    Image.new("RGB", (30, 30)).save(path)
    sources["source"] = path
    monkeypatch.setattr(grid_tool, "upload_bytes", lambda data, key: None)
    assert asyncio.run(grid_tool.split_grid("source")) == []
    assert all(not path.exists() for path in downloads)
