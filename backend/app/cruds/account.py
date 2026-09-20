# -*- coding: utf-8 -*-
'''
@文件    :account.py
@说明    :C端用户CRUD
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional
from app.cruds.base import CRUDBase
from app.models.account import UserModel


class CRUDAccount(CRUDBase):
    async def get_by_account(self, account: str) -> Optional[UserModel]:
        return await self.model.get_or_none(account=account)


crud = CRUDAccount(UserModel)
