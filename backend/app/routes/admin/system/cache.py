# -*- coding: utf-8 -*-
'''
@文件    :cache.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from typing import List
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.services.system.cache import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/admin/all",summary="获取在线管理员", dependencies=[Depends(AdminPermissionChecker("system:cache:admin:all"))])
async def cache_admin_get():
    result = await service.get_admin_token()
    return Success(data=result)


@router.post("/admin/delete",summary="清除在线管理员", dependencies=[Depends(AdminPermissionChecker("system:cache:admin:delete"))])
async def cache_admin_delete(
    keys: List[str] = Body(...,description="keys", embed=True)
):
    await service.delete_admin_token(*keys)
    return Success()


