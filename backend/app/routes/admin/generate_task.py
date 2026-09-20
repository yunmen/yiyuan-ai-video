# -*- coding: utf-8 -*-
'''
@文件    :generate_task.py
@说明    :管理端-生成任务管理
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.generate_task import QuerySchema
from app.services.generate_task import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list", summary="任务列表", dependencies=[Depends(AdminPermissionChecker("video:task:list"))])
async def task_list(payload: QuerySchema):
    total, data = await service.list(payload)
    return Success(data=data, total=total)


@router.post("/detail", summary="任务详情", dependencies=[Depends(AdminPermissionChecker("video:task:list"))])
async def task_detail(
    id: int = Body(..., description="任务Id", embed=True)
):
    data = await service.detail(id)
    return Success(data=data)


@router.post("/delete", summary="删除任务", dependencies=[Depends(AdminPermissionChecker("video:task:delete"))])
async def task_delete(
    id: int = Body(..., description="任务Id", embed=True)
):
    await service.delete(id)
    return Success()


@router.post("/resume", summary="断点续跑(管理端)", dependencies=[Depends(AdminPermissionChecker("video:task:list"))])
async def task_resume(
    id: int = Body(..., description="任务Id", embed=True)
):
    data = await service.resume(id, user=None, ignore_owner=True)
    return Success(data=data)
