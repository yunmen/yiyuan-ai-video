# -*- coding: utf-8 -*-
'''
@文件    :video_template.py
@说明    :视频模板CRUD
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, List, Dict
from tortoise.functions import Count
from app.cruds.base import CRUDBase, Total
from app.models.video import VideoTemplateModel


class CRUDVideoTemplate(CRUDBase):
    async def get_by_id(self, id: int) -> Optional[VideoTemplateModel]:
        # 过滤软删除,避免已删除模板仍被详情/下单命中
        return await self.model.get_or_none(id=id, deleted=False)

    async def get_category_counts(self) -> List[Dict]:
        """按分类分组统计数量"""
        rows = await self.model.filter(active=True, deleted=False).group_by("category").annotate(count=Count("id")).values("category", "count")
        return list(rows)


crud = CRUDVideoTemplate(VideoTemplateModel)
