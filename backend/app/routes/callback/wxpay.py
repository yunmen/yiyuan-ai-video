# -*- coding: utf-8 -*-
'''
@文件    :wxpay.py
@说明    :微信支付回调(免登录,SDK 验签 + 解密;处理失败返回 400/500 让微信重试)
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.core.wxpay import get_wxpay
from app.core.logger import logger


router = APIRouter()


@router.post("/wxpay/video", summary="视频订单支付结果通知", include_in_schema=False)
async def wxpay_video_notify(request: Request):
    body = await request.body()
    try:
        result = get_wxpay().callback(dict(request.headers), body)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"微信支付回调验签异常: {exc}")
        result = None
    if not result:
        return JSONResponse(status_code=400, content={"code": "FAIL", "message": "验签失败"})
    try:
        from app.services.payment import service
        await service.pay_callback(result["resource"])
    except Exception as exc:  # noqa: BLE001
        logger.error(f"微信支付回调处理失败(将等待微信重试): {exc}")
        return JSONResponse(status_code=500, content={"code": "FAIL", "message": "处理失败"})
    return {"code": "SUCCESS", "message": "成功"}


@router.post("/wxpay/refund", summary="退款结果通知", include_in_schema=False)
async def wxpay_refund_notify(request: Request):
    body = await request.body()
    try:
        result = get_wxpay().callback(dict(request.headers), body)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"微信退款回调验签异常: {exc}")
        result = None
    if not result:
        return JSONResponse(status_code=400, content={"code": "FAIL", "message": "验签失败"})
    try:
        from app.services.payment import service
        await service.refund_callback(result["resource"])
    except Exception as exc:  # noqa: BLE001
        logger.error(f"微信退款回调处理失败(将等待微信重试): {exc}")
        return JSONResponse(status_code=500, content={"code": "FAIL", "message": "处理失败"})
    return {"code": "SUCCESS", "message": "成功"}
