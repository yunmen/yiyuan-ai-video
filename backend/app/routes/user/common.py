# -*- coding: utf-8 -*-
'''
@文件    :common.py
@说明    :用户端-公共接口(免登录,文件上传)
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
import hmac
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Body, Request, UploadFile, Header
from app.core.routeclass import OperationLogRoute
from app.settings import config
from app.core.response import Success, Fail, AUTH
from app.core.oss import get_oss
from app.core import ratelimit
from app.core.upload import save_upload_file, is_allowed_extension, MAX_SIZE


router = APIRouter(route_class=OperationLogRoute)

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
    if not hmac.compare_digest(x_worker_token or "", config.WORKER_CALLBACK_SECRET):
        return AUTH(msg="未授权的 Worker")
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
    images: List[str] = Body(None, description="参考视频的关键画面 URL(可选,传了则图文结合生成)"),
    with_demand: bool = Body(False, description="是否同时返回识别主体(subject)与画面要求草稿(demand),供前端预填"),
    roles: List[str] = Body(None, description="与 images 一一对应的素材角色(person/product/scene),可选;用于多图(人物形象图+产品图)结合生成文案"),
):
    # 该接口直接消耗大模型额度,按 IP 限流,防止被刷
    await ratelimit.check(
        ratelimit.build_key("copy", ratelimit.client_ip(request)),
        COPY_LIMIT_PER_MINUTE, 60, "文案生成过于频繁,请稍后再试",
    )
    from app.services import copy_writer
    data = await copy_writer.generate(
        template_title, category, title, subtitle, script, images, with_demand, roles,
    )
    return Success(data=data)


@router.post("/upload/file", summary="上传素材文件")
async def upload_file(request: Request, file: UploadFile):
    await ratelimit.check(
        ratelimit.build_key("upload", ratelimit.client_ip(request)),
        UPLOAD_LIMIT_PER_MINUTE, 60, "上传过于频繁,请稍后再试",
    )
    # 先按声明大小拦截,避免把超大文件整包读进内存
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_SIZE:
        return Fail(msg="文件大小不能超过50MB")
    # 上传逻辑统一交给 app.core.upload,本端口仅负责频控、校验与响应封装
    try:
        info = await save_upload_file(file)
    except ValueError as exc:
        return Fail(msg=str(exc))
    return Success(data={"url": info["url"], "filename": file.filename, "size": info["size"]})


@router.post("/upload/sign", summary="获取素材直传预签名URL(浏览器直传对象存储)")
async def upload_sign(
    request: Request,
    filename: str = Body(..., embed=True, description="原始文件名(用于取扩展名)")
):
    """返回 PUT 预签名 URL,由浏览器直传对象存储。

    海外服务器中转国内上传速度极慢(实测约 80KB/s),稍大素材必然超时中断;
    改为浏览器直连对象存储,避开跨境上行链路。
    """
    # 与 /upload/file 同一频控口径,避免被脚本刷签名后反复直传占用存储
    await ratelimit.check(
        ratelimit.build_key("upload", ratelimit.client_ip(request)),
        UPLOAD_LIMIT_PER_MINUTE, 60, "上传过于频繁,请稍后再试",
    )
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not is_allowed_extension(ext):
        return Fail(msg=f"不支持的文件类型:.{ext}")

    oss = get_oss()
    if oss is None:
        return Fail(msg="对象存储未启用,请使用常规上传接口")

    day = datetime.now().strftime("%Y%m%d")
    key = f"uploads/{day}/{uuid.uuid4().hex}.{ext}"
    return Success(data={
        "uploadUrl": oss.presign_put(key),
        "url": oss.public_url(key),
        "filename": filename,
    })
