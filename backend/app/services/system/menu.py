# -*- coding: utf-8 -*-
'''
@文件    :menu.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.system.menu import crud, Total
from app.schemas.system.menu import QuerySchema, CreateSchema, UpdateSchema
from app.utils.buildDataFunc import build_tree_data

class Service:

    async def list(self, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q()
        order = []
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=order)
        result = []
        for obj in objs:
            item = obj.to_dict()
            result.append(item)
        return total, result

    async def tree(self) -> List[Dict]:
        search = Q()
        order = ["order"]
        objs = await crud.query(search=search, order=order)
        result = []
        for obj in objs:
            item = obj.to_dict(exclude=["create_time", "update_time"])
            result.append(item)
        return build_tree_data(result)

    async def create(self, data: CreateSchema) -> Dict:
        obj = await crud.create(data)
        return obj.to_dict()
    
    async def update(self, data: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        data_dict = data.model_dump(exclude={'id'})
        obj = await crud.update(obj, data_dict)
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


    async def batch_delete(self, ids: List[int]):
        for id in ids:
            await self.delete(id)

    async def init_menu_data(self):
        """初始化菜单数据"""
        count = await crud.count()
        if count == 0:
            from app.mock.data import menus
            for item in menus:
                await crud.create(item)

    async def get_superuser_menus(self) -> Dict:
        search = Q()
        order = ["order"]
        objs = await crud.query(search=search, order=order)
        result = []
        permissions = []
        for obj in objs:
            if obj.type == "button":
                permissions.append(obj.name)
            result.append({
                "id":obj.id,
                "name":obj.name,
                "path":obj.path,
                "component":obj.component,
                "parent_id":obj.parent_id,
                "meta":{
                    "icon": obj.icon,
                    "title": obj.title,
                    "hidden": obj.hidden,
                    "hiddenBreadcrumb": obj.hiddenBreadcrumb,
                    "type": obj.type,
                    "fullpage": obj.fullpage
                }
            })
        data = {
            "menus": build_tree_data(result),
            "permissions": permissions,
            "dashboardGrid":['statistics','welcome','echarts','about', 'ver','time','progress']
        }
        return data


service = Service()