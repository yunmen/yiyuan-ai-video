# -*- coding: utf-8 -*-
'''
@文件    :user.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from typing import Optional, Tuple, List
from tortoise.expressions import Q
from app.cruds.base import CRUDBase, Total
from app.models.system import SystemUserModel, SystemRoleModel
from app.schemas.system.user import CreateSchema, UpdateSchema


class Crud(CRUDBase[SystemUserModel, CreateSchema, UpdateSchema]):
    def __init__(self):
        super().__init__(model=SystemUserModel)

    async def list(self, page_num: int, page_size: int, search: Q = Q(), order: list = []) -> Tuple[Total, List[SystemUserModel]]:
        query = self.model.filter(search).select_related("dept").prefetch_related("roles")
        return await query.count(), await query.offset((page_num - 1) * page_size).limit(page_size).order_by(*order)

    async def get_by_account(self, account: str) -> Optional[SystemUserModel]:
        return await self.model.get_or_none(account=account)

    async def get_by_phone(self, phone: str) -> Optional[SystemUserModel]:
        return await self.model.get_or_none(phone=phone)

    async def get_by_id(self, id: int) -> Optional[SystemUserModel]:
        return await self.model.get_or_none(id=id)

    async def superuser_is_exist(self) -> bool:
        return  await self.model.exists(superuser=True)
    
    async def save_user_roles(self, obj: SystemUserModel, roles: List[SystemRoleModel]) -> SystemUserModel:
        await obj.roles.clear()
        for role in roles:
            await obj.roles.add(role)
        return obj

crud = Crud()