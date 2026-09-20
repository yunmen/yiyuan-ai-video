# -*- coding: utf-8 -*-
'''
@文件    :payment.py
@说明    :管理端-支付订单管理(订单查询/退款/退款查询)
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from fastapi import Body
from app.schemas.base import BaseQuerySchema
from app.schemas.payment import OrderQuerySchema, RefundSchema, PackageSaveSchema
from app.services.payment import service
from app.services.payment_package import service as package_service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/package/list", summary="充值套餐列表", dependencies=[Depends(AdminPermissionChecker("payment:package:list"))])
async def package_list(payload: BaseQuerySchema):
    total, data = await package_service.list(payload)
    return Success(data=data, total=total)


@router.post("/package/save", summary="新增/编辑充值套餐", dependencies=[Depends(AdminPermissionChecker("payment:package:save"))])
async def package_save(payload: PackageSaveSchema):
    data = await package_service.save(payload)
    return Success(data=data, msg="保存成功")


@router.post("/package/delete", summary="删除充值套餐", dependencies=[Depends(AdminPermissionChecker("payment:package:delete"))])
async def package_delete(id: int = Body(..., description="主键Id", embed=True)):
    await package_service.delete(id)
    return Success(msg="删除成功")


@router.post("/order/list", summary="订单列表", dependencies=[Depends(AdminPermissionChecker("payment:order:list"))])
async def order_list(payload: OrderQuerySchema):
    result = await service.list_all(payload)
    return Success(data=result["data"], total=result["total"])


@router.post("/order/refund", summary="发起退款", dependencies=[Depends(AdminPermissionChecker("payment:order:refund"))])
async def order_refund(payload: RefundSchema):
    data = await service.apply_refund(payload.order_no, payload.reason)
    return Success(data=data)


@router.post("/order/refund-query", summary="退款查询(回调丢失兜底)", dependencies=[Depends(AdminPermissionChecker("payment:order:refund"))])
async def order_refund_query(
    order_no: str = Body(..., description="商户订单号", embed=True),
):
    data = await service.refund_query(order_no)
    return Success(data=data)
