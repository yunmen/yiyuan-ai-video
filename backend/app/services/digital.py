# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :数字人Service
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.digital import crud, Total
from app.schemas.digital import QuerySchema, CreateSchema, UpdateSchema

DEFAULT_ORDER = ["-sort", "-create_time"]


class Service:
    async def list(self, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q()
        if payload.keyword:
            search &= Q(name__icontains=payload.keyword) | Q(desc__icontains=payload.keyword) | Q(tags__icontains=payload.keyword)
        if payload.gender:
            search &= Q(gender=payload.gender)
        if payload.active is not None:
            search &= Q(active=payload.active)
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=DEFAULT_ORDER)
        return total, [obj.to_dict() for obj in objs]

    async def detail(self, id: int) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        return obj.to_dict()

    async def create(self, data: CreateSchema) -> Dict:
        obj = await crud.create(data)
        return obj.to_dict()

    async def update(self, data: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        obj = await crud.update(obj, data.model_dump(exclude={"id"}))
        return obj.to_dict()

    async def active(self, id: int) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        obj = await crud.update(obj, {"active": not obj.active})
        return obj.to_dict()

    async def delete(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        await crud.delete(obj)


service = Service()
