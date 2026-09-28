# -*- coding: utf-8 -*-
'''
@文件    :upload.py
@说明    :上传存储公共能力,管理端/用户端上传接口共用,消除两套路由的平行复制漂移
@时间    :2026/09/27
@作者    :一源AI
@版本    :1.0
'''
import asyncio
import os
import uuid
from datetime import datetime

from fastapi import UploadFile
from loguru import logger

from app.settings import config
from app.core.oss import get_oss


# 允许上传的扩展名与单文件大小上限(管理端与用户端口径一致)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "mp4", "mov", "m4v", "webm"}
MAX_SIZE = 50 * 1024 * 1024  # 50MB


def is_allowed_extension(ext: str) -> bool:
    """扩展名是否在允许上传范围内"""
    return ext in ALLOWED_EXTENSIONS


def is_allowed_size(size: int) -> bool:
    """文件字节数是否超过单文件上限"""
    return size <= MAX_SIZE


async def save_upload_file(file: UploadFile) -> dict:
    """读取并落盘上传文件,返回可访问信息。

    优先上传对象存储(公网可访问,供视频模型侧拉取),未启用或失败时回退本地磁盘。
    管理端与用户端共用此函数,避免两个路由各自维护一份相同的上传逻辑。
    :raises ValueError: 扩展名不支持或文件超过大小上限时抛出,调用方应转为业务失败
    :return: {"url": 可访问地址, "size": 字节数}
    """
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if not is_allowed_extension(ext):
        raise ValueError(f"不支持的文件类型:.{ext}")

    content = await file.read()
    if not is_allowed_size(len(content)):
        raise ValueError("文件大小不能超过50MB")

    day = datetime.now().strftime("%Y%m%d")
    filename = f"{uuid.uuid4().hex}.{ext}"

    # 优先上传对象存储;未启用或失败则回退本地磁盘
    oss = get_oss()
    if oss is not None:
        try:
            key = f"uploads/{day}/{filename}"
            url = await asyncio.to_thread(oss.put_object, key, content)
            return {"url": url, "size": len(content)}
        except Exception as exc:  # noqa: BLE001
            logger.error(f"OSS 上传失败,回退本地存储: {exc}")

    folder = os.path.join(config.STATIC_PATH, "uploads", day)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    url = f"{config.STATIC_URL}/uploads/{day}/{filename}"
    return {"url": url, "size": len(content)}
