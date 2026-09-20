# -*- coding: utf-8 -*-
'''
@文件    :role.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.system.role import QuerySchema, CreateSchema, UpdateSchema, PermissionSchema
from app.services.system.role import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list",summary="获取列表", dependencies=[Depends(AdminPermissionChecker("system:role:list"))])
async def role_list(
    payload: QuerySchema
):
    total, data =  await service.list(payload)
    return Success(data=data, total=total)


@router.post("/create",summary="创建", dependencies=[Depends(AdminPermissionChecker("system:role:create"))])
async def role_create(
    payload: CreateSchema
):
    result = await service.create(payload)
    return Success(data=result)


@router.post("/update",summary="修改", dependencies=[Depends(AdminPermissionChecker("system:role:update"))])
async def role_update(
    payload: UpdateSchema
):
    result = await service.update(payload)
    return Success(data=result)


@router.post("/active",summary="禁用/激活", dependencies=[Depends(AdminPermissionChecker("system:role:active"))])
async def role_active(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.active(id)
    return Success()


@router.post("/delete",summary="删除", dependencies=[Depends(AdminPermissionChecker("system:role:delete"))])
async def role_delete(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.delete(id)
    return Success()


@router.post("/all",summary="所有有效角色", dependencies=[Depends(AdminPermissionChecker("system:role:all"))])
async def role_all():
    result = await service.all()
    return Success(data=result)


@router.post("/menu",summary="获取角色菜单", dependencies=[Depends(AdminPermissionChecker("system:role:menu"))])
async def role_menu(
    id: int = Body(...,description="角色Id",embed=True)
):
    result =  await service.get_role_menus(id)
    return Success(data=result)


@router.post("/permission",summary="设置角色权限", dependencies=[Depends(AdminPermissionChecker("system:role:permission"))])
async def role_permissions(
    payload: PermissionSchema
):
    await service.set_role_menus(payload)
    return Success()