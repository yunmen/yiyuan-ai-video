# -*- coding: utf-8 -*-
'''
@文件    :auth.py
@说明    :授权管理
@时间    :2025/08/08 02:07:08
@作者    :睿
@版本    :1.0
'''
from fastapi import APIRouter, Request
from app.core.routeclass import OperationLogRoute
from app.core.response import Success, Fail
from app.schemas.system.user import AccountLoginSchema
from app.controllers import login as login_controller


router = APIRouter(route_class=OperationLogRoute)


@router.post("/password", summary="账号密码登录授权")
async def auth_password(
    playload: AccountLoginSchema,
    request: Request
):
    playload.client_ip = request.headers.get('X-Real-Ip') or request.client.host
    token = await login_controller.admin_login_by_password(playload)
    return Success(data=token, msg="登录成功")

