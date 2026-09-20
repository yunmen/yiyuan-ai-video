# -*- coding: utf-8 -*-
'''
@文件    :dept.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.system.dept import crud, Total
from app.schemas.system.dept import QuerySchema, CreateSchema, UpdateSchema
from app.utils.buildDataFunc import build_tree_data


class Service:
    async def list(self, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q()
        order = ["-create_time"]
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=order)
        result = []
        for obj in objs:
            item = obj.to_dict()
            result.append(item)
        return total, result

    async def tree(self, payload: QuerySchema) -> List[Dict]:
        search = Q()
        order = ["order"]
        objs = await crud.query(search=search, order=order)
        result = []
        for obj in objs:
            item = obj.to_dict()
            result.append(item)
        return build_tree_data(result)

    async def create(self, data: CreateSchema) -> Dict:
        if data.parent_id:
            parent = await crud.get_by_id(data.parent_id)
            if parent:
                data.path = f"{parent.path}/{parent.id}"
            else:
                raise HTTPException(status_code=200, detail="上级部门不存在")
        obj = await crud.create(data)
        return obj.to_dict()
    
    async def update(self, data: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        if data.parent_id:
            parent = await crud.get_by_id(data.parent_id)
            if parent:
                data.path = f"{parent.path}/{parent.id}"
            else:
                raise HTTPException(status_code=200, detail="上级部门不存在")
        data_dict = data.model_dump(exclude={'id'})
        obj =  await crud.update(obj, data_dict)
        return obj.to_dict()

    async def active(self, id: int) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        obj = await crud.update(obj, {
            "active": not obj.active
        })
        return obj.to_dict()
    
    async def delete(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        await crud.delete(obj)

    async def init_dept_data(self):
        """初始化菜单数据"""
        count = await crud.count()
        if count == 0:
            from app.mock.data import depts
            for item in depts:
                await crud.create(item)

service = Service()