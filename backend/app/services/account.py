# -*- coding: utf-8 -*-
'''
@文件    :account.py
@说明    :C端用户Service
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi.exceptions import HTTPException
from app.cruds.account import crud
from app.core.plugin import password, redis, jwt
from app.core import sms
from app.enums.base import ClientRoleEnum
from app.settings import config


class Service:
    async def register(self, payload) -> Dict:
        exist = await crud.get_by_account(payload.account)
        if exist:
            raise HTTPException(status_code=200, detail="该账号已注册")
        data = {
            "account": payload.account,
            "password": password.get_password_hash(payload.password),
            "nickname": payload.nickname or f"用户{payload.account[-4:]}",
        }
        obj = await crud.create(data)
        return self._to_dict(obj)

    async def login(self, payload) -> Dict:
        obj = await crud.get_by_account(payload.account)
        if not obj:
            raise HTTPException(status_code=200, detail="账号不存在,请使用验证码登录")
        if not obj.password:
            # 验证码注册的用户未设置密码,不能走密码登录
            raise HTTPException(status_code=200, detail="该账号未设置密码,请使用验证码登录")
        if not password.verify_password(payload.password, obj.password):
            raise HTTPException(status_code=200, detail="密码错误")
        if not obj.status:
            raise HTTPException(status_code=200, detail="账号已被禁用")
        return await self._build_login_result(obj)

    # ------------------------------------------------------------ 验证码登录
    async def send_sms_code(self, payload) -> Dict:
        """发送登录/注册验证码(首次登录自动注册)"""
        return await sms.send_code(payload.phone)

    async def login_by_code(self, payload) -> Dict:
        """手机号验证码登录:未注册则自动注册(即「初次登录用验证码」)"""
        phone = sms.validate_phone(payload.phone)
        await sms.verify_code(phone, payload.code)
        obj = await crud.get_by_account(phone)
        is_new = False
        if not obj:
            is_new = True
            obj = await crud.create({
                "account": phone,
                "password": "",  # 空串表示未设置密码,只能用验证码登录
                "nickname": payload.nickname or f"用户{phone[-4:]}",
            })
        elif not obj.status:
            raise HTTPException(status_code=200, detail="账号已被禁用")
        result = await self._build_login_result(obj)
        result["is_new"] = is_new
        return result

    async def set_password(self, user_id: int, payload) -> None:
        """设置/重设密码(验证码注册用户首次设置密码)"""
        obj = await crud.get(user_id)
        if not obj:
            raise HTTPException(status_code=200, detail="用户不存在")
        await crud.update(obj, {"password": password.get_password_hash(payload.password)})

    async def _build_login_result(self, obj) -> Dict:
        token = await self._generate_token(obj)
        return {
            "info": {
                "id": obj.id,
                "account": obj.account,
                "nickname": obj.nickname,
                "avatar": obj.avatar,
                "has_password": bool(obj.password),
            },
            "token": token,
        }

    async def info(self, user_id: int) -> Dict:
        obj = await crud.get(user_id)
        if not obj:
            raise HTTPException(status_code=200, detail="用户不存在")
        return self._to_dict(obj)

    async def update_info(self, user_id: int, payload) -> Dict:
        obj = await crud.get(user_id)
        if not obj:
            raise HTTPException(status_code=200, detail="用户不存在")
        await crud.update(obj, {"nickname": payload.nickname, "avatar": payload.avatar})
        return self._to_dict(obj)

    async def change_password(self, user_id: int, payload) -> None:
        obj = await crud.get(user_id)
        if not obj:
            raise HTTPException(status_code=200, detail="用户不存在")
        if not password.verify_password(payload.old_password, obj.password):
            raise HTTPException(status_code=200, detail="原密码错误")
        if payload.old_password == payload.new_password:
            raise HTTPException(status_code=200, detail="新密码不能与原密码相同")
        await crud.update(obj, {"password": password.get_password_hash(payload.new_password)})
        # 使旧 token 失效,强制重新登录
        await redis.delete(f"{config.REDIS_PREFIX_NAME}:{ClientRoleEnum.USER.value}:{obj.account}")

    async def logout(self, user_id: int) -> None:
        """退出登录:删除 Redis 中的 token,使其立即失效"""
        obj = await crud.get(user_id)
        if not obj:
            return
        await redis.delete(f"{config.REDIS_PREFIX_NAME}:{ClientRoleEnum.USER.value}:{obj.account}")

    async def _generate_token(self, obj) -> str:
        payload = {
            "id": obj.id,
            "account": obj.account,
            "nickname": obj.nickname,
            "exp": datetime.now() + timedelta(seconds=config.EXPIRE_TIME),
        }
        token = jwt.generate_token(payload)
        await redis.set(
            f"{config.REDIS_PREFIX_NAME}:{ClientRoleEnum.USER.value}:{obj.account}",
            token,
            ex=config.EXPIRE_TIME,
        )
        return token

    def _to_dict(self, obj) -> Dict:
        return {
            "id": obj.id,
            "account": obj.account,
            "nickname": obj.nickname,
            "avatar": obj.avatar,
            "has_password": bool(obj.password),
            "create_time": obj.create_time.strftime("%Y-%m-%d %H:%M:%S") if obj.create_time else None,
        }


service = Service()
