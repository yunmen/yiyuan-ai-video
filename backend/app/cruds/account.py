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
from tortoise.expressions import Q


class CRUDAccount(CRUDBase):
    async def get_by_account(self, account: str) -> Optional[UserModel]:
        """密码登录兼容用户名与已绑定手机号，软删除账号不可登录。"""
        return await self.model.filter(Q(account=account) | Q(phone=account), deleted=False).first()

    async def get_by_phone(self, phone: str) -> Optional[UserModel]:
        """验证码仅匹配绑定手机号，兼容迁移前以手机号为用户名的账号。"""
        return await self.model.filter(Q(phone=phone) | Q(account=phone), deleted=False).first()


crud = CRUDAccount(UserModel)
