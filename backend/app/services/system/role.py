# -*- coding: utf-8 -*-
'''
@文件    :role.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.system.role import crud, Total
from app.cruds.system.menu import crud as menu_crud
from app.models.system import SystemMenuModel
from app.schemas.system.role import QuerySchema, CreateSchema, UpdateSchema, PermissionSchema

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

    async def create(self, payload: CreateSchema) -> Dict:
        obj =  await crud.create(payload)
        return obj.to_dict()
    
    async def update(self, payload: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(payload.id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        data_dict = payload.model_dump(exclude={'id'})
        obj = await crud.update(obj, data_dict)
        return obj.to_dict()

    async def active(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        await crud.update(obj, {
            "active": not obj.active
        })
    
    async def delete(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        await crud.delete(obj)

    async def all(self):
        search = Q(active=True)
        objs = await crud.query(search)
        result = []
        for obj in objs:
            result.append({
                "value":obj.id,
                "label":obj.name
            })
        return result

    async def init_role_data(self):
        """初始化角色数据,并将菜单授权给角色(仅在角色表为空时执行)"""
        count = await crud.count()
        if count == 0:
            from app.mock.data import roles
            for item in roles:
                await crud.create(item)
            # 超级管理员授予全部菜单;运营授予业务模块(业务管理分组 parent_id=1)
            sa = await crud.model.get_or_none(name="超级管理员")
            op = await crud.model.get_or_none(name="运营")
            all_menus = await SystemMenuModel.all()
            if sa:
                for m in all_menus:
                    await sa.menus.add(m)
            if op:
                business = await SystemMenuModel.filter(parent_id=1)
                for m in business:
                    await op.menus.add(m)

    async def get_role_menus(self, id: int) -> List[int]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="角色不存在")
        menu_ids = [m.id for m in await obj.menus]
        return menu_ids

    async def set_role_menus(self, data: PermissionSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="角色不存在")
        menus = [await menu_crud.get(menu_id) for menu_id in data.menus]
        obj = await crud.save_role_menus(obj, menus)
        return obj.to_dict()


service = Service()