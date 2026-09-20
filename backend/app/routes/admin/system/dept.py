# -*- coding: utf-8 -*-
'''
@文件    :dept.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.system.dept import QuerySchema, CreateSchema, UpdateSchema
from app.services.system.dept import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list",summary="获取列表", dependencies=[Depends(AdminPermissionChecker("system:dept:list"))])
async def dept_list(
    payload: QuerySchema
):
    total, data =  await service.list(payload)
    return Success(data=data, total=total)


@router.post("/tree",summary="获取列表", dependencies=[Depends(AdminPermissionChecker("system:dept:tree"))])
async def dept_tree(
    payload: QuerySchema
):
    data =  await service.tree(payload)
    return Success(data=data)


@router.post("/create",summary="创建", dependencies=[Depends(AdminPermissionChecker("system:dept:create"))])
async def dept_create(
    payload: CreateSchema
):
    result = await service.create(payload)
    return Success(data=result)


@router.post("/update",summary="修改", dependencies=[Depends(AdminPermissionChecker("system:dept:update"))])
async def dept_update(
    payload: UpdateSchema
):
    result = await service.update(payload)
    return Success(data=result)


@router.post("/active",summary="禁用/激活", dependencies=[Depends(AdminPermissionChecker("system:dept:active"))])
async def dept_active(
    id: int = Body(...,description="唯一Id",embed=True)
):
    result = await service.active(id)
    return Success(data=result)


@router.post("/delete",summary="删除", dependencies=[Depends(AdminPermissionChecker("system:dept:delete"))])
async def dept_delete(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.delete(id)
    return Success()