# -*- coding: utf-8 -*-
'''
@文件    :task.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.system.task import QuerySchema, CreateSchema, UpdateSchema
from app.services.system.task import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/all",summary="获取列表", dependencies=[Depends(AdminPermissionChecker("system:task:all"))])
async def task_all(
    payload: QuerySchema
):
    data =  await service.all(payload)
    return Success(data=data)


@router.post("/create",summary="创建", dependencies=[Depends(AdminPermissionChecker("system:task:create"))])
async def task_create(
    payload: CreateSchema
):
    result = await service.create(payload)
    return Success(data=result)


@router.post("/update",summary="修改", dependencies=[Depends(AdminPermissionChecker("system:task:update"))])
async def task_update(
    payload: UpdateSchema
):
    result = await service.update(payload)
    return Success(data=result)


@router.post("/active",summary="禁用/激活", dependencies=[Depends(AdminPermissionChecker("system:task:active"))])
async def task_active(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.active(id)
    return Success()


@router.post("/delete",summary="删除", dependencies=[Depends(AdminPermissionChecker("system:task:delete"))])
async def task_delete(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.delete(id)
    return Success()


@router.post("/run",summary="立即运行", dependencies=[Depends(AdminPermissionChecker("system:task:run"))])
async def task_run(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.run(id)
    return Success()