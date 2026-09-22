# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :用户端-数字人接口(免登录)
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body
from app.core.routeclass import OperationLogRoute
from app.schemas.digital import QuerySchema
from app.services.digital import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute)


@router.post("/list", summary="数字人列表")
async def digital_list(payload: QuerySchema):
    total, data = await service.list(payload, only_active=True)
    return Success(data=data, total=total)


@router.post("/detail", summary="数字人详情")
async def digital_detail(
    id: int = Body(..., description="数字人Id", embed=True)
):
    data = await service.detail(id, only_active=True)
    return Success(data=data)
