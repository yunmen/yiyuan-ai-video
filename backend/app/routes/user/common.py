# -*- coding: utf-8 -*-
'''
@文件    :common.py
@说明    :用户端-公共接口(免登录,文件上传)
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
import asyncio
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Body, Request, UploadFile, Header
from loguru import logger
from app.core.routeclass import OperationLogRoute
from app.settings import config
from app.core.response import Success, Fail
from app.core.oss import get_oss
from app.core import ratelimit


router = APIRouter(route_class=OperationLogRoute)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "mp4", "mov", "m4v", "webm"}
MAX_SIZE = 50 * 1024 * 1024  # 50MB

# 免登录接口频控(防脚本刷 LLM / 刷存储):同一 IP 每分钟上限
COPY_LIMIT_PER_MINUTE = 10
UPLOAD_LIMIT_PER_MINUTE = 30


@router.post("/gen-config", summary="公开业务配置(模型/画幅/定价,供前端与 worker 读取)")
async def gen_config():
    from app.services.system_config import service as config_service
    return Success(data=await config_service.get_public_map())


@router.post("/worker-config", summary="Worker 全量配置(含网关密钥,需 X-Worker-Token 鉴权)")
async def worker_config(x_worker_token: str = Header(None, description="Worker 回调鉴权令牌")):
    """Worker 专用:返回含敏感网关密钥的全量配置,供 worker 热更新 base_url/key 与模型名。
    鉴权令牌需与 backend WORKER_CALLBACK_SECRET 一致(即 worker 的 NOTIFY_TOKEN)。"""
    if x_worker_token != config.WORKER_CALLBACK_SECRET:
        return Fail(msg="未授权的 Worker", code=401)
    from app.services.system_config import service as config_service
    return Success(data=await config_service.get_full_map())


@router.post("/copy/generate", summary="AI 一键写文案(按模板风格生成/润色大标题/副标题/口播)")
async def copy_generate(
    request: Request,
    template_title: str = Body(..., description="模板标题"),
    category: str = Body("", description="行业分类"),
    title: str = Body(None, description="大标题草稿(可选,润色用)"),
    subtitle: str = Body(None, description="副标题草稿(可选)"),
    script: str = Body(None, description="口播文案草稿(可选)"),
):
    # 该接口直接消耗大模型额度,按 IP 限流,防止被刷
    await ratelimit.check(
        ratelimit.build_key("copy", ratelimit.client_ip(request)),
        COPY_LIMIT_PER_MINUTE, 60, "文案生成过于频繁,请稍后再试",
    )
    from app.services import copy_writer
    data = await copy_writer.generate(template_title, category, title, subtitle, script)
    return Success(data=data)


@router.post("/upload/file", summary="上传素材文件")
async def upload_file(request: Request, file: UploadFile):
    await ratelimit.check(
        ratelimit.build_key("upload", ratelimit.client_ip(request)),
        UPLOAD_LIMIT_PER_MINUTE, 60, "上传过于频繁,请稍后再试",
    )
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in ALLOWED_EXTENSIONS:
        return Fail(msg=f"不支持的文件类型:.{ext}")
    # 先按声明大小拦截,避免把超大文件整包读进内存
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_SIZE:
        return Fail(msg="文件大小不能超过50MB")
    content = await file.read()
    if len(content) > MAX_SIZE:
        return Fail(msg="文件大小不能超过50MB")

    day = datetime.now().strftime("%Y%m%d")
    filename = f"{uuid.uuid4().hex}.{ext}"

    # 优先上传对象存储(公网可访问,供视频模型侧拉取);未启用或失败则回退本地磁盘
    oss = get_oss()
    if oss is not None:
        try:
            key = f"uploads/{day}/{filename}"
            url = await asyncio.to_thread(oss.put_object, key, content)
            return Success(data={"url": url, "filename": file.filename, "size": len(content)})
        except Exception as exc:  # noqa: BLE001
            logger.error(f"OSS 上传失败,回退本地存储: {exc}")

    folder = os.path.join(config.STATIC_PATH, "uploads", day)
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    url = f"{config.STATIC_URL}/uploads/{day}/{filename}"
    return Success(data={"url": url, "filename": file.filename, "size": len(content)})
