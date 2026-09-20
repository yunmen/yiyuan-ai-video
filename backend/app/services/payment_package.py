# -*- coding: utf-8 -*-
'''
@文件    :payment_package.py
@说明    :充值套餐Service(后台维护套餐 + 用户端拉取上架套餐,下单交付走 payment service)
@时间    :2026/09/20 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Dict, List, Tuple
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.payment_package import crud, Total
from app.schemas.payment import PackageCreateSchema, PackageUpdateSchema, PackageSaveSchema
from app.schemas.base import BaseQuerySchema

# 默认套餐(首次启动播种,之后以数据库为准)
DEFAULT_PACKAGES: List[Dict] = [
    {"name": "体验包", "sub_title": "适合首次尝试", "credits": 10, "price": "9.90", "tag": None, "sort": 30},
    {"name": "进阶包", "sub_title": "高频制作首选", "credits": 50, "price": "29.90", "tag": "推荐", "sort": 20},
    {"name": "畅享包", "sub_title": "不限量更划算", "credits": 200, "price": "99.00", "tag": None, "sort": 10},
]


class Service:
    async def init_package_data(self) -> None:
        """启动播种:无套餐数据时补齐默认套餐"""
        if await crud.model.filter().count():
            return
        for item in DEFAULT_PACKAGES:
            await crud.create(item)

    async def list(self, payload: BaseQuerySchema) -> Tuple[Total, List[Dict]]:
        """后台套餐列表"""
        total, objs = await crud.list(
            page_num=payload.pageNum, page_size=payload.pageSize,
            search=Q(), order=["-sort", "price"],
        )
        return total, [obj.to_dict() for obj in objs]

    async def list_active(self) -> List[Dict]:
        """用户端:仅上架套餐"""
        objs = await crud.list_active()
        return [obj.to_dict() for obj in objs]

    async def get_by_id(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj or not obj.active:
            raise HTTPException(status_code=200, detail="套餐不存在或已下架")
        return obj

    async def create(self, data: PackageCreateSchema) -> Dict:
        obj = await crud.create(data.model_dump())
        return obj.to_dict()

    async def update(self, data: PackageUpdateSchema) -> Dict:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="套餐不存在")
        obj = await crud.update(obj, data.model_dump(exclude={"id"}))
        return obj.to_dict()

    async def delete(self, id: int) -> None:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="套餐不存在")
        await crud.delete(obj)

    async def save(self, data) -> Dict:
        """新增/编辑(有 id 走编辑)"""
        payload = data.model_dump()
        if payload.get("id"):
            return await self.update(PackageUpdateSchema(**payload))
        payload.pop("id", None)
        return await self.create(PackageCreateSchema(**payload))


service = Service()
