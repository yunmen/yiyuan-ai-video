# -*- coding: utf-8 -*-
'''
@文件    :system_config.py
@说明    :系统业务配置CRUD
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional
from app.cruds.base import CRUDBase
from app.models.system import SystemConfigModel


class CRUDSystemConfig(CRUDBase):
    async def get_by_key(self, key: str) -> Optional[SystemConfigModel]:
        return await self.model.get_or_none(key=key)


crud = CRUDSystemConfig(SystemConfigModel)
