# -*- coding: utf-8 -*-
'''
@文件    :log.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.system.log import QuerySchema, CreateSchema, UpdateSchema
from app.services.system.log import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list",summary="获取列表", dependencies=[Depends(AdminPermissionChecker("system:log:list"))])
async def log_list(
    payload: QuerySchema
):
    total, data = await service.list(payload)
    return Success(data=data, total=total)

@router.post("/detail",summary="获取日志详情", dependencies=[Depends(AdminPermissionChecker("system:log:detail"))])
async def log_detail(
    id: int = Body(...,description="唯一Id",embed=True)
):
    result = await service.get(id)
    return Success(data=result)