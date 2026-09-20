# -*- coding: utf-8 -*-
'''
@文件    :video_template.py
@说明    :管理端-视频模板管理
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.video_template import QuerySchema, CreateSchema, UpdateSchema
from app.services.video_template import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list", summary="模板列表", dependencies=[Depends(AdminPermissionChecker("video:template:list"))])
async def template_list(payload: QuerySchema):
    total, data = await service.list(payload)
    return Success(data=data, total=total)


@router.post("/detail", summary="模板详情", dependencies=[Depends(AdminPermissionChecker("video:template:list"))])
async def template_detail(
    id: int = Body(..., description="模板Id", embed=True)
):
    data = await service.detail(id)
    return Success(data=data)


@router.post("/create", summary="创建模板", dependencies=[Depends(AdminPermissionChecker("video:template:create"))])
async def template_create(payload: CreateSchema):
    data = await service.create(payload)
    return Success(data=data)


@router.post("/update", summary="修改模板", dependencies=[Depends(AdminPermissionChecker("video:template:update"))])
async def template_update(payload: UpdateSchema):
    data = await service.update(payload)
    return Success(data=data)


@router.post("/active", summary="上架/下架", dependencies=[Depends(AdminPermissionChecker("video:template:active"))])
async def template_active(
    id: int = Body(..., description="模板Id", embed=True)
):
    data = await service.active(id)
    return Success(data=data)


@router.post("/recommend", summary="首页推荐开关", dependencies=[Depends(AdminPermissionChecker("video:template:active"))])
async def template_recommend(
    id: int = Body(..., description="模板Id", embed=True)
):
    data = await service.recommend(id)
    return Success(data=data)


@router.post("/delete", summary="删除模板", dependencies=[Depends(AdminPermissionChecker("video:template:delete"))])
async def template_delete(
    id: int = Body(..., description="模板Id", embed=True)
):
    await service.delete(id)
    return Success()
