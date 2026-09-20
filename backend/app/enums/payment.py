# -*- coding: utf-8 -*-
'''
@文件    :payment.py
@说明    :支付相关枚举(参考 ai-creator 项目设计)
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from enum import Enum


class OrderStatusEnum(Enum):
    """订单状态"""
    PENDING = 1      # 待支付
    PAID = 2         # 已支付(待交付)
    DELIVERED = 3    # 已交付(已创建生成任务)
    CANCELLED = 4    # 已取消(超时未支付)
    REFUNDING = 5    # 退款中
    REFUNDED = 6     # 已退款


class PaymentGatewayEnum(Enum):
    """支付网关"""
    WECHAT = "wechat"
    MOCK = "mock"


class PaymentBizTypeEnum(Enum):
    """业务类型"""
    VIDEO_GEN = 1        # 视频生成付费
    CREDIT_RECHARGE = 2  # 额度充值
