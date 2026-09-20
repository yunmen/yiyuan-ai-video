# -*- coding: utf-8 -*-
'''
@文件    :payment_package.py
@说明    :充值套餐CRUD
@时间    :2026/09/20 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, List
from app.cruds.base import CRUDBase, Total
from app.models.payment import PaymentPackageModel


class CRUDPaymentPackage(CRUDBase):
    async def get_by_id(self, id: int) -> Optional[PaymentPackageModel]:
        return await self.model.get_or_none(id=id, deleted=False)

    async def list_active(self) -> List[PaymentPackageModel]:
        """上架套餐(按 sort 倒序、价格升序)"""
        return await self.model.filter(active=True).order_by("-sort", "price").all()


crud = CRUDPaymentPackage(PaymentPackageModel)
