# -*- coding: utf-8 -*-
'''
@文件    :account.py
@说明    :用户端-账号接口
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationUserToken
from app.schemas.account import (
    RegisterSchema,
    LoginSchema,
    EditSchema,
    ChangePasswordSchema,
    SmsSendSchema,
    CodeLoginSchema,
    SetPasswordSchema,
)
from app.schemas.credit import LogQuerySchema
from app.services.account import service
from app.services.credit import service as credit_service
from app.services.sign import service as sign_service
from app.services.invitation import service as invitation_service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute)


@router.post("/invitation", summary="我的邀请码与邀请奖励")
async def invitation(g=Depends(DeepValidationUserToken)):
    """仅返回当前账号的稳定邀请码、奖励规则及实际奖励统计。"""
    return Success(data=await invitation_service.summary(g.id))


@router.post("/register", summary="用户注册")
async def register(payload: RegisterSchema):
    data = await service.register(payload)
    return Success(data=data, msg="注册成功")


@router.post("/login", summary="用户密码登录")
async def login(payload: LoginSchema):
    data = await service.login(payload)
    return Success(data=data, msg="登录成功")


@router.post("/sms/send", summary="发送登录/注册验证码")
async def sms_send(payload: SmsSendSchema):
    data = await service.send_sms_code(payload)
    return Success(data=data, msg="验证码已发送")


@router.post("/login/code", summary="手机号验证码登录(首次自动注册)")
async def login_by_code(payload: CodeLoginSchema):
    data = await service.login_by_code(payload)
    return Success(data=data, msg="注册成功" if data.get("is_new") else "登录成功")


@router.post("/set-password", summary="设置/重设密码(验证码注册后首次设置)", dependencies=[Depends(DeepValidationUserToken)])
async def set_password(payload: SetPasswordSchema, g=Depends(DeepValidationUserToken)):
    await service.set_password(g.id, payload)
    return Success(msg="密码设置成功")


@router.post("/info", summary="我的资料", dependencies=[Depends(DeepValidationUserToken)])
async def info(g=Depends(DeepValidationUserToken)):
    data = await service.info(g.id)
    return Success(data=data)


@router.post("/update", summary="修改资料", dependencies=[Depends(DeepValidationUserToken)])
async def update(payload: EditSchema, g=Depends(DeepValidationUserToken)):
    data = await service.update_info(g.id, payload)
    return Success(data=data)


@router.post("/change-password", summary="修改密码", dependencies=[Depends(DeepValidationUserToken)])
async def change_password(payload: ChangePasswordSchema, g=Depends(DeepValidationUserToken)):
    await service.change_password(g.id, payload)
    return Success(msg="密码修改成功,请重新登录")


@router.post("/logout", summary="退出登录", dependencies=[Depends(DeepValidationUserToken)])
async def logout(g=Depends(DeepValidationUserToken)):
    await service.logout(g.id)
    return Success(msg="已退出登录")


@router.post("/sign", summary="每日签到", dependencies=[Depends(DeepValidationUserToken)])
async def sign(g=Depends(DeepValidationUserToken)):
    data = await sign_service.sign(g.id)
    return Success(data=data, msg=f"签到成功,获得 {data['credits']} 次额度")


@router.post("/sign/status", summary="签到状态(是否已签到/连续天数)", dependencies=[Depends(DeepValidationUserToken)])
async def sign_status(g=Depends(DeepValidationUserToken)):
    data = await sign_service.status(g.id)
    return Success(data=data)


@router.post("/credits", summary="我的额度(余额+今日已用)", dependencies=[Depends(DeepValidationUserToken)])
async def credits(g=Depends(DeepValidationUserToken)):
    data = await credit_service.balance(g.id)
    return Success(data=data)


@router.post("/credits/logs", summary="额度流水(分页)", dependencies=[Depends(DeepValidationUserToken)])
async def credits_logs(payload: LogQuerySchema, g=Depends(DeepValidationUserToken)):
    total, data = await credit_service.logs(g.id, payload)
    return Success(data=data, total=total)
