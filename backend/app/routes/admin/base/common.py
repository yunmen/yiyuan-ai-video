# -*- coding: utf-8 -*-
'''
@文件    :common.py
@说明    :管理端-公共接口(文件上传,供 sc-upload 组件使用)
@时间    :2026/09/20 14:00:00
@作者    :一源AI
@版本    :1.0
'''
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, UploadFile
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken
from app.core.response import Success, Fail
from app.core.oss import get_oss
from app.core.upload import save_upload_file, is_allowed_extension


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/upload/file", summary="上传文件(图片/视频)")
async def upload_file(file: UploadFile):
    # 上传逻辑统一交给 app.core.upload,本端口仅负责鉴权与响应封装
    try:
        info = await save_upload_file(file)
    except ValueError as exc:
        return Fail(msg=str(exc))
    # src 供管理端 sc-upload 组件经 config.parseData 读取,url 供通用上传辅助函数读取
    return Success(data={"url": info["url"], "src": info["url"], "fileName": file.filename, "size": info["size"]})


@router.post("/upload/sign", summary="获取直传预签名URL(大文件浏览器直传对象存储)")
async def upload_sign(
    filename: str = Body(..., embed=True, description="原始文件名(用于取扩展名)")
):
    """返回 PUT 预签名 URL,由浏览器直传对象存储。

    海外服务器中转国内大文件上传速度极慢(实测约 80KB/s),超过前端超时后中断;
    改为浏览器直连对象存储,避开跨境上行链路。
    """
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
        "src": oss.public_url(key),
        "fileName": filename,
    })
