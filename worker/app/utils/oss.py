# -*- coding: utf-8 -*-
'''
@文件    :oss.py
@说明    :OSS 转存工具 — 把远程资源(模型返回的临时直链)下载后转存到自有 OSS
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
@说明    :OSS 未启用或转存失败时,保留原始直链,不阻塞主流程。
'''
import asyncio
import os
import re
import tempfile
import uuid
from typing import List, Optional

import httpx

from app.core.plugin import oss, logger

# 常见媒体类型 → 扩展名映射
_EXT_MAP = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/bmp": ".bmp",
    "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm",
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav",
    "audio/x-wav": ".wav", "application/pdf": ".pdf",
}
_URL_RE = re.compile(r"^https?://\S+$")


def _ext_from_content_type(content_type: str) -> str:
    return _EXT_MAP.get((content_type or "").split(";")[0].strip().lower(), ".bin")


def upload_bytes(data: bytes, key: str) -> Optional[str]:
    """把二进制数据上传到 OSS,返回 URL;OSS 未启用或失败返回 None"""
    if not oss:
        return None
    try:
        return oss.put_object(key, data)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"OSS 上传失败 key={key}: {exc}")
        return None


def _upload_remote(url: str, prefix: str) -> Optional[str]:
    """下载远程资源并转存 OSS,返回 OSS URL;失败抛出异常由调用方兜底"""
    resp = httpx.get(url, timeout=120.0, follow_redirects=True)
    resp.raise_for_status()
    data = resp.content
    original = url.split("/")[-1].split("?")[0]
    _, ext = os.path.splitext(original)
    if not ext:
        ext = _ext_from_content_type(resp.headers.get("content-type", ""))
    key = f"generate/result/{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    return upload_bytes(data, key)


def _persist_single(url: str, prefix: str) -> str:
    """单条转存:非 URL / OSS 未启用时原样返回;转存失败保留原直链"""
    if not oss or not _URL_RE.match(url or ""):
        return url
    try:
        return _upload_remote(url, prefix) or url
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"资源转存 OSS 失败,保留原链: {url} ({exc})")
        return url


async def persist_url_list(urls: List[str], prefix: Optional[str] = None) -> List[str]:
    """批量把在线资源转存到 OSS,返回持久化 URL 列表(长度与入参一致)"""
    if not urls:
        return []
    if not oss:
        return list(urls)
    task_prefix = prefix or uuid.uuid4().hex
    results = await asyncio.gather(
        *(asyncio.to_thread(_persist_single, u, task_prefix) for u in urls)
    )
    return list(results)


def download_to_local(url: str, suffix: str = ".mp4", timeout: float = 180.0) -> Optional[str]:
    """下载远程资源到本地临时文件,返回路径;失败返回 None

    链路上的视频一直是 URL(转存 OSS 后回写),但 ffmpeg 只能处理本地文件 ——
    这里补上「URL → 本地」这一环。调用方负责用完删除(避免临时文件堆积)。
    """
    if not _URL_RE.match(url or ""):
        return None
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(resp.content)
        return path
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"下载资源失败: {url} ({exc})")
        return None


def upload_local_file(path: str, key: str) -> Optional[str]:
    """上传本地文件到 OSS,返回 URL;失败返回 None(ffmpeg 产物的回传入口)"""
    try:
        with open(path, "rb") as f:
            return upload_bytes(f.read(), key)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"本地文件上传失败 key={key}: {exc}")
        return None
