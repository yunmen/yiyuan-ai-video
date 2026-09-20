# -*- coding: utf-8 -*-
'''
@文件    :log.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.system.log import crud, Total
from app.schemas.system.log import QuerySchema, UpdateSchema
from app.enums.base import ClientRoleEnum
from app.settings import config


class Service:

    async def list(self, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q()
        if payload.request_id:
            search &= Q(request_id__icontains=payload.request_id)
        if payload.summary:
            search &= Q(summary__icontains=payload.summary)
        if payload.url:
            search &= Q(url__icontains=payload.url)
        if payload.method:
            search &= Q(method=payload.method)
        if payload.client_ip:
            search &= Q(client_ip__icontains=payload.client_ip)
        if payload.status_code:
            search &= Q(status_code=payload.status_code)
        if payload.client_type:
            search &= Q(client_type=payload.client_type)
        if payload.operator_account:
            search &= Q(operator_account__icontains=payload.operator_account)
        if payload.operator_nickName:
            search &= Q(operator_nickName__icontains=payload.operator_nickName)
        order = ["-create_time"]
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=order)
        result = []
        for obj in objs:
            item = obj.to_dict(exclude=['payload','result','error_log','headers'])
            result.append(item)
        return total, result

    async def create(self, data: Dict) -> Dict:
        payload = dict(data)
        path = payload.get("path", "")
        admin_prefix = f"{config.API_PREFIX}/{ClientRoleEnum.ADMIN.value}"
        user_prefix = f"{config.API_PREFIX}/{ClientRoleEnum.USER.value}"
        if path.startswith(admin_prefix):
            payload["client_type"] = ClientRoleEnum.ADMIN.label
        elif path.startswith(user_prefix):
            payload["client_type"] = ClientRoleEnum.USER.label
        else:
            payload["client_type"] = ClientRoleEnum.OTHER.label
        obj = await crud.create(payload)
        return obj.to_dict()

    async def get(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        return obj.to_dict()

service = Service()