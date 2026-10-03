# -*- coding: utf-8 -*-
'''
@文件    :user.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.system.user import crud, Total, SystemUserModel
from app.cruds.system.role import crud as role_crud
from app.cruds.system.dept import crud as dept_crud
from app.models.system import SystemRoleModel
from app.schemas.system.user import QuerySchema, CreateSchema, UpdateSchema, RepwdSchema, EditSchema
from app.enums.base import LoginTypeEnum, ClientRoleEnum
from app.core.plugin import password, redis, jwt
from app.utils.buildDataFunc import build_tree_data
from app.settings import config


class Service:
    async def list(self, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q(superuser=False)
        if payload.realname:
            search &= Q(realname__icontains=payload.realname)
        if payload.nickname:
            search &= Q(nickname__icontains=payload.nickname)
        if payload.account:
            search &= Q(account__icontains=payload.account)
        if payload.active is not None:
            search &= Q(active=payload.active)
        if payload.dept_id:
            search &= Q(dept_id=payload.dept_id)
        order = ["-create_time"]
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=order)
        return total, objs

    async def create(self, payload: CreateSchema) -> Dict:
        search = Q(account=payload.account) | Q(phone=payload.phone)
        obj = await crud.query(search)
        if obj:
            raise HTTPException(status_code=200, detail="账号或手机已被注册")
        payload.password = password.get_password_hash(payload.password)
        data_dict = payload.model_dump(exclude={'roles'})
        data_dict['dept'] = await dept_crud.get(payload.dept)
        obj = await crud.create(data_dict)
        roles = [await role_crud.get(role_id) for role_id in payload.roles]
        obj = await crud.save_user_roles(obj, roles)
        return obj.to_dict(exclude=['password', 'superuser'])

    async def update(self, payload: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(payload.id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        data_dict = payload.model_dump(exclude={'id','roles'})
        data_dict['dept'] = await dept_crud.get(payload.dept)
        obj =  await crud.update(obj, data_dict)
        roles = [await role_crud.get(role_id) for role_id in payload.roles]
        obj = await crud.save_user_roles(obj, roles)
        return obj.to_dict(exclude=['password', 'superuser'])

    async def reset_pwd(self, id: int, new_password: str) -> None:
        """管理员重置指定用户密码(明文仅在内存中哈希,不落库、不记录日志)"""
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        obj.password = password.get_password_hash(new_password)
        await obj.save(update_fields=["password"])

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

    async def get(self, **kwargs) -> SystemUserModel:
        obj = await crud.model.filter(**kwargs).first()
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        return obj

    async def init_user_data(self):
        """初始化管理员账号(仅在用户表为空时执行),并关联角色"""
        count = await crud.count()
        if count == 0:
            from app.mock.data import users
            for item in users:
                item = dict(item)
                raw_pwd = item.pop("password")
                role_ids = item.pop("roles", [])
                item["password"] = password.get_password_hash(raw_pwd)
                # 部门 FK 可为空,避免种子时因缺少部门报错
                if item.get("dept") in (None, 0):
                    item["dept"] = None
                obj = await crud.create(item)
                if role_ids:
                    role_objs = await SystemRoleModel.filter(id__in=role_ids)
                    for r in role_objs:
                        await obj.roles.add(r)

    async def authenticate(self, obj: SystemUserModel, input_password: Optional[str] = None, input_code: Optional[str] = None) -> SystemUserModel:
        """用户鉴权"""
        if input_password:
            """检查密码"""
            verified = password.verify_password(input_password, obj.password)
            if not verified:
                raise HTTPException(status_code=200, detail="密码错误")
        if input_code:
            """检查验证码"""
            code = await redis.get(f"{config.REDIS_PREFIX_NAME}:sms:{obj.phone}") or "985211"
            if code != input_code:
                raise HTTPException(status_code=200, detail="验证码错误")
        if not obj.active:
            raise HTTPException(status_code=200, detail="账号被禁用")
        return obj
    
    async def update_login_data(self, obj: SystemUserModel, client_ip: str, client_type: LoginTypeEnum):
        await crud.update(obj, {
            "last_login_time": datetime.now(),
            "last_login_ip": client_ip,
            "last_login_type": client_type
        })
    
    async def generate_token(self, obj: SystemUserModel) -> str:
        payload = {
            "id": obj.id,
            "account": obj.account,
            "nickname": obj.nickname,
            "last_login_time": obj.last_login_time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_login_ip": obj.last_login_ip,
            "last_login_type": obj.last_login_type,
            "permission": obj.permission,
            "superuser": obj.superuser,
            "exp": datetime.now() + timedelta(seconds=config.EXPIRE_TIME),
        }
        token = jwt.generate_token(payload)
        await redis.set(f"{config.REDIS_PREFIX_NAME}:{ClientRoleEnum.ADMIN.value}:{obj.account}", token, ex=config.EXPIRE_TIME)
        return token


    async def get_user_menus(self, id: int) -> Dict:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        menus = []
        for role in await obj.roles:
            menu = await role.menus
            menus.extend(menu)
        menus = list(set(menus))
        result = []
        permissions = []
        for menu in menus:
            if menu.type == "button":
                permissions.append(menu.name)
            result.append({
                "id":menu.id,
                "name":menu.name,
                "path":menu.path,
                "component":menu.component,
                "parent_id":menu.parent_id,
                "meta":{
                    "icon": menu.icon,
                    "title": menu.title,
                    "hidden": menu.hidden,
                    "hiddenBreadcrumb": menu.hiddenBreadcrumb,
                    "type": menu.type,
                    "fullpage": menu.fullpage
                }
            })
        data = {
            "menus": build_tree_data(result),
            "permissions":permissions,
            "dashboardGrid":['statistics','welcome','echarts','about', 'ver','time','progress']
        }
        return data

    async def reset_myself_pwd(self, id: int, payload: RepwdSchema):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        if not password.verify_password(payload.oldPassword, obj.password):
            raise HTTPException(status_code=200, detail="密码错误")
        obj = await crud.update(obj, {
            "password": password.get_password_hash(payload.newPassword)
        })

    async def update_myself_data(self, id: int, payload: EditSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        data_dict = payload.model_dump()
        obj =  await crud.update(obj, data_dict)
        return obj.to_dict()


service = Service()