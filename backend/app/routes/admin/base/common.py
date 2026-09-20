# -*- coding: utf-8 -*-
'''
@文件    :common.py
@说明    :管理端-公共接口(文件上传,供 sc-upload 组件使用)
@时间    :2026/09/20 14:00:00
@作者    :一源AI
@版本    :1.0
'''
import asyncio
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile
from loguru import logger
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken
from app.settings import config
from app.core.response import Success, Fail
from app.core.oss import get_oss


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "mp4", "mov", "m4v", "webm"}
MAX_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload/file", summary="上传文件(图片/视频)")
async def upload_file(file: UploadFile):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in ALLOWED_EXTENSIONS:
        return Fail(msg=f"不支持的文件类型:.{ext}")
    content = await file.read()
    if len(content) > MAX_SIZE:
        return Fail(msg="文件大小不能超过50MB")

    day = datetime.now().strftime("%Y%m%d")
    filename = f"{uuid.uuid4().hex}.{ext}"

    # 优先上传对象存储;未启用或失败则回退本地磁盘
    oss = get_oss()
    if oss is not None:
        try:
            key = f"uploads/{day}/{filename}"
            url = await asyncio.to_thread(oss.put_object, key, content)
            return Success(data={"url": url, "src": url, "fileName": file.filename, "size": len(content)})
        except Exception as exc:  # noqa: BLE001
            logger.error(f"OSS 上传失败,回退本地存储: {exc}")

    folder = os.path.join(config.STATIC_PATH, "uploads", day)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    url = f"{config.STATIC_URL}/uploads/{day}/{filename}"
    return Success(data={"url": url, "src": url, "fileName": file.filename, "size": len(content)})
