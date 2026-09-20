# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :数字人CRUD
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional
from app.cruds.base import CRUDBase, Total
from app.models.digital import DigitalHumanModel


class CRUDDigitalHuman(CRUDBase):
    async def get_by_id(self, id: int) -> Optional[DigitalHumanModel]:
        return await self.model.get_or_none(id=id, deleted=False)


crud = CRUDDigitalHuman(DigitalHumanModel)
