# -*- coding: utf-8 -*-
'''
@文件    :template.py
@说明    :用户端-模板接口(免登录)
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body
from app.core.routeclass import OperationLogRoute
from app.schemas.video_template import QuerySchema
from app.services.video_template import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute)


@router.post("/list", summary="模板列表")
async def template_list(payload: QuerySchema):
    total, data = await service.list(payload)
    return Success(data=data, total=total)


@router.post("/recommend", summary="首页热门推荐模板")
async def template_recommend():
    data = await service.recommend_list()
    return Success(data=data)


@router.post("/category/list", summary="分类列表")
async def category_list():
    data = await service.category_list()
    return Success(data=data)


@router.post("/detail", summary="模板详情")
async def template_detail(
    id: int = Body(..., description="模板Id", embed=True)
):
    data = await service.detail(id, add_use_count=True)
    return Success(data=data)
