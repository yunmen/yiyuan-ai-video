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
from app.core.logger import logger

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
        """初始化菜单数据

        - 菜单表为空:按 mock 种子全量播种(全新环境自举);
        - 菜单表已有数据:按 name 做「接口权限点」增量同步(已部署环境自愈)。
        """
        from app.mock.data import menus
        count = await crud.count()
        if count == 0:
            for item in menus:
                await crud.create(item)
            return
        await self._sync_menu_api_list(menus)

    async def _sync_menu_api_list(self, seeds: List[Dict]) -> None:
        """把种子里声明、库中缺失的接口权限点补齐(只增不减,不覆盖管理员自定义项)。

        目的:种子里的 apiList 会随后端权限点演进而调整(如 create/update/active 拆分),
        但 init_menu_data 原本仅在菜单表为空时播种,已部署环境不会更新,导致非超管角色
        访问新增接口时 403。这里按菜单 name 匹配后只追加缺失权限点,既修复问题又不动
        管理员已有的自定义权限。
        """
        for item in seeds:
            api_list = item.get("apiList") or []
            if not api_list:
                continue
            obj = await crud.model.get_or_none(name=item["name"])
            if not obj:
                continue
            current = list(obj.apiList or [])
            missing = [p for p in api_list if p not in current]
            if not missing:
                continue
            await crud.update(obj, {"apiList": current + missing})
            logger.info(f"菜单权限点同步 [{item['name']}] 补齐: {missing}")

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