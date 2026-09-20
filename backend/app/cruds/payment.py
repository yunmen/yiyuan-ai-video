# -*- coding: utf-8 -*-
'''
@文件    :payment.py
@说明    :支付订单CRUD(回调/交付用行锁保证幂等)
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, List
from app.cruds.base import CRUDBase
from app.models.payment import UserPaymentModel


class CRUDPayment(CRUDBase):
    async def get_by_order_no(self, order_no: str) -> Optional[UserPaymentModel]:
        return await self.model.get_or_none(order_no=order_no)

    async def get_by_order_no_for_update(self, order_no: str) -> Optional[UserPaymentModel]:
        """行锁查询(必须在事务内调用),串行化同一订单的重复/并发回调"""
        return await self.model.select_for_update().get_or_none(order_no=order_no)

    async def list_expired_pending(self, deadline) -> List[UserPaymentModel]:
        """扫描超时未支付订单(对账用)"""
        return await self.model.filter(status=1, create_time__lt=deadline).all()


crud = CRUDPayment(UserPaymentModel)
