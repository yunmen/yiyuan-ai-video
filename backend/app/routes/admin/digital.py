# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :管理端-数字人管理
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.digital import QuerySchema, CreateSchema, UpdateSchema
from app.services.digital import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list", summary="数字人列表", dependencies=[Depends(AdminPermissionChecker("video:digital:list"))])
async def digital_list(payload: QuerySchema):
    total, data = await service.list(payload)
    return Success(data=data, total=total)


@router.post("/detail", summary="数字人详情", dependencies=[Depends(AdminPermissionChecker("video:digital:list"))])
async def digital_detail(
    id: int = Body(..., description="数字人Id", embed=True)
):
    data = await service.detail(id)
    return Success(data=data)


@router.post("/create", summary="创建数字人", dependencies=[Depends(AdminPermissionChecker("video:digital:create"))])
async def digital_create(payload: CreateSchema):
    data = await service.create(payload)
    return Success(data=data)


@router.post("/update", summary="修改数字人", dependencies=[Depends(AdminPermissionChecker("video:digital:update"))])
async def digital_update(payload: UpdateSchema):
    data = await service.update(payload)
    return Success(data=data)


@router.post("/active", summary="上架/下架", dependencies=[Depends(AdminPermissionChecker("video:digital:active"))])
async def digital_active(
    id: int = Body(..., description="数字人Id", embed=True)
):
    data = await service.active(id)
    return Success(data=data)


@router.post("/delete", summary="删除数字人", dependencies=[Depends(AdminPermissionChecker("video:digital:delete"))])
async def digital_delete(
    id: int = Body(..., description="数字人Id", embed=True)
):
    await service.delete(id)
    return Success()
