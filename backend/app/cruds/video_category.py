# -*- coding: utf-8 -*-
'''
@文件    :video_category.py
@说明    :视频模板分类CRUD
@时间    :2026/09/20 19:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, List, Dict
from tortoise.functions import Count
from app.cruds.base import CRUDBase, Total
from app.models.video import VideoCategoryModel


class CRUDVideoCategory(CRUDBase):
    async def get_by_id(self, id: int) -> Optional[VideoCategoryModel]:
        return await self.model.get_or_none(id=id)

    async def get_by_name(self, name: str) -> Optional[VideoCategoryModel]:
        return await self.model.get_or_none(name=name)

    async def list_active(self) -> List[VideoCategoryModel]:
        return await self.model.filter(active=True, deleted=False).order_by("-sort", "id").all()

    async def names(self) -> List[str]:
        """全部启用分类名称(用于分类下拉与播种去重)"""
        rows = await self.model.filter(active=True).values("name")
        return [r["name"] for r in rows]

    async def template_counts(self) -> Dict[str, int]:
        """按分类统计上架模板数量"""
        from app.models.video import VideoTemplateModel
        rows = await VideoTemplateModel.filter(active=True, deleted=False).group_by("category").annotate(
            count=Count("id")
        ).values("category", "count")
        return {r["category"]: r["count"] for r in rows}


crud = CRUDVideoCategory(VideoCategoryModel)
