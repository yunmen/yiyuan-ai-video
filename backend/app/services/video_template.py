# -*- coding: utf-8 -*-
'''
@文件    :video_template.py
@说明    :视频模板Service
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.video_template import crud, Total
from app.enums.business import TemplateSortEnum
from app.schemas.video_template import QuerySchema, CreateSchema, UpdateSchema
from app.services.video_category import service as category_service


SORT_MAPPING = {
    TemplateSortEnum.HOT.value: ["-hot", "-sort", "-create_time"],
    TemplateSortEnum.NEW.value: ["-create_time"],
    TemplateSortEnum.USED.value: ["-use_count", "-create_time"],
}
DEFAULT_ORDER = ["-sort", "-hot", "-create_time"]


class Service:
    async def list(self, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q()
        if payload.keyword:
            search &= Q(title__icontains=payload.keyword) | Q(tags__icontains=payload.keyword) | Q(desc__icontains=payload.keyword)
        if payload.category:
            search &= Q(category=payload.category)
        if payload.active is not None:
            search &= Q(active=payload.active)
        if payload.recommend is not None:
            search &= Q(recommend=payload.recommend)
        order = SORT_MAPPING.get(payload.sort_type, DEFAULT_ORDER)
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=order)
        return total, [obj.to_dict() for obj in objs]

    async def recommend_list(self, limit: int = 8) -> List[Dict]:
        """首页热门推荐:取后台勾选的推荐位;未配置任何推荐时按热度兜底"""
        objs = await crud.model.filter(active=True, recommend=True).order_by(
            "-recommend_sort", "-hot", "-create_time"
        ).limit(limit).all()
        if not objs:
            objs = await crud.model.filter(active=True).order_by(
                "-hot", "-sort", "-create_time"
            ).limit(limit).all()
        return [obj.to_dict() for obj in objs]

    async def category_list(self) -> List[Dict]:
        """分类及模板数量:统一走分类表(可在管理端维护)"""
        return await category_service.list_active()

    async def detail(self, id: int, add_use_count: bool = False) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="模板不存在")
        if add_use_count:
            obj.use_count += 1
            await obj.save(update_fields=["use_count"])
        return obj.to_dict()

    async def create(self, data: CreateSchema) -> Dict:
        obj = await crud.create(data)
        return obj.to_dict()

    async def update(self, data: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="模板不存在")
        obj = await crud.update(obj, data.model_dump(exclude={"id"}))
        return obj.to_dict()

    async def active(self, id: int) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="模板不存在")
        obj = await crud.update(obj, {"active": not obj.active})
        return obj.to_dict()

    async def recommend(self, id: int) -> Optional[Dict]:
        """首页推荐位开关"""
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="模板不存在")
        obj = await crud.update(obj, {"recommend": not obj.recommend})
        return obj.to_dict()

    async def delete(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="模板不存在")
        await crud.delete(obj)


service = Service()
