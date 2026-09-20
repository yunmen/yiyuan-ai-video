# -*- coding: utf-8 -*-
'''
@文件    :role.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from typing import Optional, Tuple, List
from tortoise.expressions import Q
from app.cruds.base import CRUDBase, Total
from app.models.system import SystemRoleModel, SystemMenuModel
from app.schemas.system.role import CreateSchema, UpdateSchema


class Crud(CRUDBase[SystemRoleModel, CreateSchema, UpdateSchema]):
    def __init__(self):
        super().__init__(model=SystemRoleModel)

    async def list(self, page_num: int, page_size: int, search: Q = Q(), order: list = []) -> Tuple[Total, List[SystemRoleModel]]:
        query = self.model.filter(search)
        return await query.count(), await query.offset((page_num - 1) * page_size).limit(page_size).order_by(*order)

    async def get_by_id(self, id: int) -> Optional[SystemRoleModel]:
        return await self.model.get_or_none(id=id)

    async def save_role_menus(self, obj: SystemRoleModel, menus: List[SystemMenuModel]) -> SystemRoleModel:
        await obj.menus.clear()
        for role in menus:
            await obj.menus.add(role)
        return obj

crud = Crud()