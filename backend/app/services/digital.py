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


def resolve_pose_variant(variants, pose: Optional[str]) -> Optional[Dict]:
    """按名称取派生视图;未指定或未命中时返回 None(用主视图)。

    主视图派生:派生视图只换姿势/景别,不换人 —— 生成时仍以主图作 reference,
    避免「换个姿势就变脸」。命中不了就安静回退主视图,不报错阻断生成。
    """
    if not pose or not isinstance(variants, list):
        return None
    target = str(pose).strip()
    for item in variants:
        if isinstance(item, dict) and str(item.get("name") or "").strip() == target:
            return item
    return None


class Service:
    async def list(self, payload: QuerySchema, only_active: bool = False) -> Tuple[Total, List[Dict]]:
        """数字人列表。

        only_active=True 供用户端使用:强制只返回已上架数据,避免下架数字人仍出现在
        用户可选列表中(管理端传 False,可查看全部并按下架状态筛选)。
        """
        search = Q()
        if payload.keyword:
            # tags 是 JSONField,不支持 icontains(会抛 Unknown filter param → 接口 500),
            # 关键词只匹配名称与简介。
            search &= Q(name__icontains=payload.keyword) | Q(desc__icontains=payload.keyword)
        if payload.gender:
            search &= Q(gender=payload.gender)
        if only_active:
            search &= Q(active=True)
        elif payload.active is not None:
            search &= Q(active=payload.active)
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=DEFAULT_ORDER)
        return total, [obj.to_dict() for obj in objs]

    async def detail(self, id: int, only_active: bool = False) -> Optional[Dict]:
        """数字人详情;only_active=True 供用户端使用,已下架数字人视为不存在。"""
        obj = await crud.get_by_id(id)
        if not obj or (only_active and not obj.active):
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
