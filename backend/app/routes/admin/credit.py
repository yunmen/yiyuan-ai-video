# -*- coding: utf-8 -*-
'''
@文件    :credit.py
@说明    :管理端-用户额度管理(余额查询/手动赠送/流水查询)
@时间    :2026/09/20 19:30:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.schemas.credit import AdminUserQuerySchema, LogQuerySchema, GrantSchema
from app.services.credit import service
from app.enums.business import CreditLogTypeEnum
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/user/list", summary="用户额度列表", dependencies=[Depends(AdminPermissionChecker("credit:user:list"))])
async def user_list(payload: AdminUserQuerySchema):
    total, data = await service.admin_user_list(payload)
    return Success(data=data, total=total)


@router.post("/logs", summary="用户额度流水", dependencies=[Depends(AdminPermissionChecker("credit:user:list"))])
async def credit_logs(
    payload: LogQuerySchema,
    user_id: int = Body(..., description="用户Id", embed=True),
):
    total, data = await service.admin_logs(user_id, payload)
    return Success(data=data, total=total)


@router.post("/grant", summary="赠送额度", dependencies=[Depends(AdminPermissionChecker("credit:user:grant"))])
async def credit_grant(payload: GrantSchema):
    await service.grant(
        payload.user_id, payload.amount,
        log_type=CreditLogTypeEnum.GRANT.value,
        remark=payload.remark or "管理员赠送",
    )
    return Success(msg=f"已赠送 {payload.amount} 次额度")
