# -*- coding: utf-8 -*-
'''
@文件    :config.py
@说明    :管理端-系统业务配置(模型/画幅/定价,worker 热更新拉取)
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.system_config import QuerySchema, UpsertSchema
from app.services.system_config import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/list", summary="配置列表", dependencies=[Depends(AdminPermissionChecker("system:config:list"))])
async def config_list(payload: QuerySchema):
    total, data = await service.list(payload)
    return Success(data=data, total=total)


@router.post("/upsert", summary="新增/修改配置", dependencies=[Depends(AdminPermissionChecker("system:config:update"))])
async def config_upsert(payload: UpsertSchema):
    data = await service.upsert(payload)
    return Success(data=data)
