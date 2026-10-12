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
from fastapi import APIRouter, Body, Request, UploadFile, Header, Depends
from app.core.dependencies import DeepValidationUserToken
from app.services.user_material import register_material
from app.core.routeclass import OperationLogRoute
from app.settings import config
from app.core.response import Success, Fail, AUTH
from app.core.oss import get_oss
from app.core import ratelimit
from app.core.upload import save_upload_file, is_allowed_extension, MAX_SIZE


router = APIRouter(route_class=OperationLogRoute)

# 免登录接口频控(防脚本刷 LLM / 刷存储):同一 IP 每分钟上限
UPLOAD_LIMIT_PER_MINUTE = 30


@router.post("/gen-config", summary="公开业务配置(模型/画幅/定价/复刻形态,供前端与 worker 读取)")
async def gen_config():
    """返回管理端可配的公开配置,并附带代码内置的能力选项。

    `replicate_formats`(复刻目标形态)与 `replicate_intents`(替换意图)是代码内置、
    非管理端可改的能力选项,随本接口一并返回,让前端直接渲染标签,**不另存一份白名单副本** ——
    否则新增选项要同时改后端与前端两处,极易漂移(能选却校验不过或反之)。
    """
    from app.services.gen_rules import REPLICATE_DEFAULTS, REPLICATE_FORMAT_OPTIONS
    from app.services.prompt_builder import (
        CREATIVE_LEVEL_OPTIONS,
        HOOK_BOOST_OPTIONS,
        INTENT_OPTIONS,
        LEAD_ACT_OPTIONS,
    )
    from app.services.system_config import service as config_service

    data = await config_service.get_public_map()
    data["replicate_formats"] = [dict(opt) for opt in REPLICATE_FORMAT_OPTIONS]
    data["replicate_intents"] = [dict(opt) for opt in INTENT_OPTIONS]
    # 主角表现档位(换人物时的创意增强:跟随原片/跳舞/推广)同样代码内置、随本接口下发
    data["lead_acts"] = [dict(opt) for opt in LEAD_ACT_OPTIONS]
    # 创意档位(忠实复刻/轻度改写/爆款改写)与开头钩子强化:决定在原片骨架上"改写多少"。
    # 正文散文(方法论)始终留在 backend/skills/prompts/replicate/,前端只拿 label/desc ——
    # 用户调的是"改多少"这个业务旋钮,不是直接编辑提示词。
    data["replicate_creative_levels"] = [dict(opt) for opt in CREATIVE_LEVEL_OPTIONS]
    data["replicate_hook_boosts"] = [dict(opt) for opt in HOOK_BOOST_OPTIONS]
    # 推荐默认值:小白用户不调参,前端拿它预填建单参数(用户不感知);
    # 值来自 gen_rules.REPLICATE_DEFAULTS 单一来源,与后端兜底逻辑同源,不会前后端漂移。
    data["replicate_defaults"] = dict(REPLICATE_DEFAULTS)
    return Success(data=data)


@router.post("/worker-config", summary="Worker 全量配置(含网关密钥,需 X-Worker-Token 鉴权)")
async def worker_config(x_worker_token: str = Header(None, description="Worker 回调鉴权令牌")):
    """Worker 专用:返回含敏感网关密钥的全量配置,供 worker 热更新 base_url/key 与模型名。
    鉴权令牌需与 backend WORKER_CALLBACK_SECRET 一致(即 worker 的 NOTIFY_TOKEN)。"""
    if not hmac.compare_digest(x_worker_token or "", config.WORKER_CALLBACK_SECRET):
        return AUTH(msg="未授权的 Worker")
    from app.services.system_config import service as config_service
    return Success(data=await config_service.get_full_map())


@router.post("/upload/file", summary="上传素材文件")
async def upload_file(request: Request, file: UploadFile, g=Depends(DeepValidationUserToken)):
    """仅允许已登录账号上传素材，并登记持久素材归属。"""
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
    if g:
        await register_material(g.id, info["url"], file.filename or "", info["size"])
    return Success(data={"url": info["url"], "filename": file.filename, "size": info["size"]})


@router.post("/upload/sign", summary="获取素材直传预签名URL(浏览器直传对象存储)")
async def upload_sign(
    request: Request,
    filename: str = Body(..., embed=True, description="原始文件名(用于取扩展名)"),
    g=Depends(DeepValidationUserToken),
):
    """为已登录用户返回 PUT 预签名 URL,由浏览器直传对象存储。

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
    if g:
        await register_material(g.id, oss.public_url(key), filename, storage_key=key)
    return Success(data={
        "uploadUrl": oss.presign_put(key),
        "url": oss.public_url(key),
        "filename": filename,
    })
