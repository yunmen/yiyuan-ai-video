# -*- coding: utf-8 -*-
'''
@文件    :menu.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from typing import List
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.system.menu import QuerySchema, CreateSchema, UpdateSchema
from app.services.system.menu import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list",summary="获取菜单列表", dependencies=[Depends(AdminPermissionChecker("system:menu:list"))])
async def menu_list(
    payload: QuerySchema
):
    total, data =  await service.list(payload)
    return Success(data=data, total=total)


@router.post("/tree",summary="获取所有菜单", dependencies=[Depends(AdminPermissionChecker("system:menu:tree"))])
async def menu_tree():
    data =  await service.tree()
    return Success(data=data)


@router.post("/create",summary="创建", dependencies=[Depends(AdminPermissionChecker("system:menu:create"))])
async def menu_create(
    payload: CreateSchema
):
    result = await service.create(payload)
    return Success(data=result)


@router.post("/update",summary="修改", dependencies=[Depends(AdminPermissionChecker("system:menu:update"))])
async def menu_update(
    payload: UpdateSchema
):
    result = await service.update(payload)
    return Success(data=result)


@router.post("/active",summary="禁用/激活", dependencies=[Depends(AdminPermissionChecker("system:menu:active"))])
async def menu_active(
    id: int = Body(...,description="唯一Id",embed=True)
):
    result = await service.active(id)
    return Success(data=result)


@router.post("/delete",summary="删除", dependencies=[Depends(AdminPermissionChecker("system:menu:delete"))])
async def menu_delete(
    ids: List[int] = Body(...,description="唯一Id",embed=True)
):
    await service.batch_delete(ids)
    return Success()

