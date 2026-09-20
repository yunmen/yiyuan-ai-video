# -*- coding: utf-8 -*-
'''
@文件    :video_category.py
@说明    :管理端-视频模板分类管理
@时间    :2026/09/20 19:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.base import BaseQuerySchema
from app.schemas.video_category import SaveSchema
from app.services.video_category import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list", summary="分类列表", dependencies=[Depends(AdminPermissionChecker("video:category:list"))])
async def category_list(payload: BaseQuerySchema):
    total, data = await service.list(payload)
    return Success(data=data, total=total)


@router.post("/save", summary="新增/编辑分类", dependencies=[Depends(AdminPermissionChecker("video:category:save"))])
async def category_save(payload: SaveSchema):
    data = await service.save(payload)
    return Success(data=data, msg="保存成功")


@router.post("/delete", summary="删除分类", dependencies=[Depends(AdminPermissionChecker("video:category:delete"))])
async def category_delete(id: int = Body(..., description="主键Id", embed=True)):
    await service.delete(id)
    return Success(msg="删除成功")
