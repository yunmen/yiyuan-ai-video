# -*- coding: utf-8 -*-
'''
@文件    :payment.py
@说明    :用户端-支付接口
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationUserToken
from app.schemas.payment import CreateOrderSchema, OrderQuerySchema, RechargeOrderSchema
from app.services.payment import service
from app.services.payment_package import service as package_service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute)


@router.post("/order/create", summary="创建视频生成订单")
async def order_create(payload: CreateOrderSchema, g=Depends(DeepValidationUserToken)):
    data = await service.create_video_order(g, payload)
    return Success(data=data)


@router.post("/package/list", summary="充值套餐列表(上架)")
async def package_list():
    data = await package_service.list_active()
    return Success(data=data)


@router.post("/order/recharge", summary="创建额度充值订单")
async def order_recharge(payload: RechargeOrderSchema, g=Depends(DeepValidationUserToken)):
    data = await service.create_credit_order(g, payload)
    return Success(data=data)


@router.post("/order/status", summary="订单状态查询(前端轮询)")
async def order_status(
    g=Depends(DeepValidationUserToken),
    order_no: str = Body(..., description="商户订单号", embed=True),
):
    data = await service.order_status(g, order_no)
    return Success(data=data)


@router.post("/order/list", summary="我的订单列表")
async def order_list(payload: OrderQuerySchema, g=Depends(DeepValidationUserToken)):
    result = await service.list_by_user(g, payload)
    return Success(data=result["data"], total=result["total"])


@router.post("/order/mock/confirm", summary="模拟支付成功(仅开发环境 mock 模式)")
async def order_mock_confirm(
    order_no: str = Body(..., description="商户订单号", embed=True),
    g=Depends(DeepValidationUserToken),
):
    # 即便开发环境也要求登录并校验订单归属,防止越权确认他人订单
    data = await service.mock_confirm(order_no, user=g)
    return Success(data=data)
