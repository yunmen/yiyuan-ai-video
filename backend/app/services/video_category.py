# -*- coding: utf-8 -*-
'''
@文件    :video_category.py
@说明    :视频模板分类Service(后台维护分类,用户端读取启用分类 + 模板数量)
@时间    :2026/09/20 19:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Dict, List, Tuple
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.video_category import crud, Total
from app.schemas.video_category import QuerySchema, CreateSchema, UpdateSchema, SaveSchema
from app.schemas.base import BaseQuerySchema

# 默认分类(首次启动播种,之后以数据库为准)
DEFAULT_CATEGORIES: List[str] = [
    "美食探店", "零售带货", "美妆个护", "健身运动", "教育培训", "家居生活", "门店宣传",
]


class Service:
    async def init_category_data(self) -> None:
        """启动播种:分类表为空时写入默认分类"""
        if await crud.model.filter().count():
            return
        for index, name in enumerate(DEFAULT_CATEGORIES):
            await crud.create({
                "name": name,
                "sort": (len(DEFAULT_CATEGORIES) - index) * 10,
            })

    async def list(self, payload: BaseQuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q()
        if payload.keyword:
            search &= Q(name__icontains=payload.keyword)
        if getattr(payload, "active", None) is not None:
            search &= Q(active=payload.active)
        total, objs = await crud.list(
            page_num=payload.pageNum, page_size=payload.pageSize,
            search=search, order=["-sort", "id"],
        )
        counts = await crud.template_counts()
        result = []
        for obj in objs:
            item = obj.to_dict()
            item["template_count"] = counts.get(obj.name, 0)
            result.append(item)
        return total, result

    async def list_active(self) -> List[Dict]:
        """用户端分类列表:仅启用分类,带上架模板数量"""
        objs = await crud.list_active()
        counts = await crud.template_counts()
        result = []
        for obj in objs:
            item = obj.to_dict()
            item["count"] = counts.get(obj.name, 0)
            result.append(item)
        # 分类表为空时兼容旧数据:按模板表聚合
        if not result:
            from app.cruds.video_template import crud as template_crud
            for row in await template_crud.get_category_counts():
                result.append({"id": 0, "name": row["category"], "count": row["count"], "cover": None, "sort": 0})
        return result

    async def create(self, data: CreateSchema) -> Dict:
        if await crud.get_by_name(data.name):
            raise HTTPException(status_code=200, detail="该分类已存在")
        obj = await crud.create(data.model_dump())
        return obj.to_dict()

    async def update(self, data: UpdateSchema) -> Dict:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="分类不存在")
        exist = await crud.get_by_name(data.name)
        if exist and exist.id != data.id:
            raise HTTPException(status_code=200, detail="该分类已存在")
        obj = await crud.update(obj, data.model_dump(exclude={"id"}))
        return obj.to_dict()

    async def save(self, data: SaveSchema) -> Dict:
        payload = data.model_dump()
        if payload.get("id"):
            return await self.update(UpdateSchema(**payload))
        payload.pop("id", None)
        return await self.create(CreateSchema(**payload))

    async def delete(self, id: int) -> None:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="分类不存在")
        await crud.delete(obj)


service = Service()
