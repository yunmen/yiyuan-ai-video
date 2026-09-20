# -*- coding: utf-8 -*-
'''
@文件    :wxpay.py
@说明    :微信支付 V3 客户端封装(参考 ai-creator 项目设计)
          PAYMENT_MODE=mock 或缺少证书/依赖时使用 Mock 客户端(仅开发环境),
          Mock 下单直接返回模拟二维码,支付回调由 /payment/order/mock/confirm 模拟触发。
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
import asyncio
from typing import Optional, Tuple
from app.settings import config
from app.core.logger import logger


class MockWeChatClient:
    """模拟微信支付客户端(开发用):不下发真实请求,回调验签恒拒绝伪造"""

    def pay(self, description: str, out_trade_no: str, amount: dict, notify_url: str, **kwargs) -> Tuple[int, str]:
        # 返回模拟扫码内容,前端展示后由 mock/confirm 完成支付闭环
        return 200, f"MOCKPAY://{out_trade_no}"

    def refund(self, out_refund_no: str, amount: int, transaction_id: str, out_trade_no: str,
               reason: str, notify_url: str, **kwargs) -> Tuple[int, str]:
        return 200, "MOCK_REFUND_ACCEPTED"

    def callback(self, headers: dict, body: bytes) -> Optional[dict]:
        # Mock 模式不经过微信,任何外部回调都视为伪造,直接拒绝
        return None


class WeChatPayClient:
    """微信支付 V3 真实客户端(同步 SDK 包装为异步)"""

    def __init__(self):
        from wechatpayv3 import WeChatPay, WeChatPayType  # noqa: F401
        self._wx = WeChatPay(
            wechatpay_type=WeChatPayType.NATIVE,
            mchid=config.WECHAT_MCHID,
            private_key=open(config.WECHAT_PRIVATE_KEY, encoding="utf-8").read(),
            cert_serial_no=config.WECHAT_CERT_SERIAL_NO,
            apiv3_key=config.WECHAT_API_V3_KEY,
            appid=config.WECHAT_APP_ID,
            notify_url=None,
            cert_dir=config.WECHAT_CERT_DIR,
        )

    async def pay(self, description: str, out_trade_no: str, amount: dict, notify_url: str, **kwargs) -> Tuple[int, str]:
        code, message = await asyncio.to_thread(
            self._wx.pay,
            description=description,
            out_trade_no=out_trade_no,
            amount=amount,
            notify_url=notify_url,
        )
        return code, message

    async def query(self, out_trade_no: str) -> Tuple[int, str]:
        return await asyncio.to_thread(self._wx.query, out_trade_no=out_trade_no)

    async def refund(self, out_refund_no: str, amount: dict, transaction_id: str, out_trade_no: str,
                     reason: str, notify_url: str, **kwargs) -> Tuple[int, str]:
        return await asyncio.to_thread(
            self._wx.refund,
            out_refund_no=out_refund_no,
            amount=amount,
            transaction_id=transaction_id,
            out_trade_no=out_trade_no,
            reason=reason,
            notify_url=notify_url,
        )

    async def query_refund(self, out_refund_no: str) -> Tuple[int, str]:
        return await asyncio.to_thread(self._wx.query_refund, out_refund_no=out_refund_no)

    def callback(self, headers: dict, body: bytes) -> Optional[dict]:
        """SDK 验签 + AES 解密;失败返回 None"""
        return self._wx.callback(headers, body)


_wxpay_client = None


def get_wxpay():
    """按支付模式获取客户端(单例)"""
    global _wxpay_client
    if _wxpay_client is not None:
        return _wxpay_client
    use_mock = config.PAYMENT_MODE == "mock"
    if not use_mock:
        try:
            _wxpay_client = WeChatPayClient()
            logger.info("微信支付客户端初始化成功(真实模式)")
            return _wxpay_client
        except Exception as exc:  # noqa: BLE001
            if config.ENVIRONMENT.value != "dev":
                raise RuntimeError(f"微信支付初始化失败(非开发环境不允许回退 mock): {exc}")
            logger.warning(f"微信支付初始化失败,回退 Mock 客户端: {exc}")
    _wxpay_client = MockWeChatClient()
    logger.warning("支付使用 Mock 客户端(仅开发环境)")
    return _wxpay_client
