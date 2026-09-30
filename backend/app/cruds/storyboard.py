# -*- coding: utf-8 -*-
'''
@文件    :storyboard.py
@说明    :分镜/镜头 CRUD
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from app.cruds.base import CRUDBase
from app.models.storyboard import EpisodeModel, ShotModel


class EpisodeCRUD(CRUDBase):
    """分镜集 CRUD(继承基类通用方法)"""

    async def get_by_task(self, task_id: int):
        return await self.model.filter(task_id=task_id).first()


class ShotCRUD(CRUDBase):
    """镜头 CRUD,附带按任务分页查询"""

    async def list_by_task(self, task_id: int, page_num: int, page_size: int):
        query = self.model.filter(task_id=task_id).order_by("index")
        total = await query.count()
        rows = await query.offset((page_num - 1) * page_size).limit(page_size)
        return total, rows

    async def get_by_task_and_index(self, task_id: int, index: int):
        return await self.model.filter(task_id=task_id, index=index).first()


episode_crud = EpisodeCRUD(EpisodeModel)
shot_crud = ShotCRUD(ShotModel)
