# -*- coding: utf-8 -*-
'''
@文件    :user.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.system.user import QuerySchema, CreateSchema, UpdateSchema, ResetPwdSchema
from app.services.system.user import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list",summary="获取列表", dependencies=[Depends(AdminPermissionChecker("system:user:list"))])
async def user_list(
    payload: QuerySchema
):
    total, objs =  await service.list(payload)
    result = []
    for obj in objs:
        item = obj.to_dict(exclude=['password','superuser'])
        item['dept'] = obj.dept.to_dict(exclude=['path', 'active', 'parent_id', 'create_time', 'update_time', 'desc', 'order'])
        item['roles'] = [{'id':role.id,'name':role.name} for role in obj.roles]
        result.append(item)
    return Success(data=result, total=total)


@router.post("/create",summary="创建", dependencies=[Depends(AdminPermissionChecker("system:user:create"))])
async def user_create(
    payload: CreateSchema
):
    result = await service.create(payload)
    return Success(data=result)


@router.post("/update",summary="修改", dependencies=[Depends(AdminPermissionChecker("system:user:update"))])
async def user_update(
    payload: UpdateSchema
):
    result = await service.update(payload)
    return Success(data=result)


@router.post("/active",summary="禁用/激活", dependencies=[Depends(AdminPermissionChecker("system:user:active"))])
async def user_active(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.active(id)
    return Success()


@router.post("/reset_pwd",summary="重置密码", dependencies=[Depends(AdminPermissionChecker("system:user:update"))])
async def user_reset_pwd(
    id: int = Body(...,description="用户Id",embed=True),
    newPassword: str = Body(...,description="新密码",embed=True)
):
    await service.reset_pwd(id, newPassword)
    return Success()


@router.post("/delete",summary="删除", dependencies=[Depends(AdminPermissionChecker("system:user:delete"))])
async def user_delete(
    id: int = Body(...,description="唯一Id",embed=True)
):
    await service.delete(id)
    return Success()