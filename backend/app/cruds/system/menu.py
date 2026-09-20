# -*- coding: utf-8 -*-
'''
@文件    :menu.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from typing import Optional, Tuple, List
from tortoise.expressions import Q
from app.cruds.base import CRUDBase, Total
from app.models.system import SystemMenuModel
from app.schemas.system.menu import CreateSchema, UpdateSchema


class Crud(CRUDBase[SystemMenuModel, CreateSchema, UpdateSchema]):
    def __init__(self):
        super().__init__(model=SystemMenuModel)

    async def list(self, page_num: int, page_size: int, search: Q = Q(), order: list = []) -> Tuple[Total, List[SystemMenuModel]]:
        query = self.model.filter(search)
        return await query.count(), await query.offset((page_num - 1) * page_size).limit(page_size).order_by(*order)

    async def get_by_id(self, id: int) -> Optional[SystemMenuModel]:
        return await self.model.get_or_none(id=id)

crud = Crud()