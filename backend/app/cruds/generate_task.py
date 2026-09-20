# -*- coding: utf-8 -*-
'''
@文件    :generate_task.py
@说明    :生成任务CRUD
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional
from app.cruds.base import CRUDBase, Total
from app.models.video import GenerateTaskModel


class CRUDGenerateTask(CRUDBase):
    async def get_by_id(self, id: int) -> Optional[GenerateTaskModel]:
        return await self.model.get_or_none(id=id, deleted=False)

    async def get_by_task_no(self, task_no: str) -> Optional[GenerateTaskModel]:
        return await self.model.get_or_none(task_no=task_no, deleted=False)


crud = CRUDGenerateTask(GenerateTaskModel)
