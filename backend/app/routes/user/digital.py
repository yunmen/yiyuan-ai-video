# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :用户端-数字人接口(免登录)
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationUserToken, OptionalUserToken
from app.schemas.digital import QuerySchema, UserCreateSchema
from app.services.digital import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute)


@router.post("/list", summary="数字人列表")
async def digital_list(payload: QuerySchema):
    total, data = await service.list(payload, only_active=True)
    return Success(data=data, total=total)


@router.post("/detail", summary="数字人详情")
async def digital_detail(
    id: int = Body(..., description="数字人Id", embed=True),
    g=Depends(OptionalUserToken),
):
    # 平台数字人匿名可看;专属数字人仅本人可看,避免私密形象被匿名 id 枚举泄漏
    data = await service.detail(id, only_active=True, user=g)
    return Success(data=data)


@router.post("/personal/create", summary="创建专属数字人")
async def digital_personal_create(
    payload: UserCreateSchema,
    g=Depends(DeepValidationUserToken)
):
    # 归属用户由登录态注入,不允许前端指定(防越权把专属数字人挂到他人名下)
    data = await service.create_personal(payload, user_id=g.id)
    return Success(data=data)


@router.post("/personal/list", summary="我的专属数字人列表")
async def digital_personal_list(g=Depends(DeepValidationUserToken)):
    data = await service.list_personal(user_id=g.id)
    return Success(data=data)


@router.post("/personal/delete", summary="删除专属数字人")
async def digital_personal_delete(
    id: int = Body(..., description="数字人Id", embed=True),
    g=Depends(DeepValidationUserToken)
):
    # 只允许删除本人专属形象;已生成的口播视频不受影响(视频资产独立于数字人记录)
    await service.delete_personal(id, user_id=g.id)
    return Success()
