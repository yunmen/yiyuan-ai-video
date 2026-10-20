# -*- coding: utf-8 -*-
'''
@文件    :account.py
@说明    :C端用户Service
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from datetime import datetime, timedelta
import re
from typing import Optional, Dict
from fastapi.exceptions import HTTPException
from app.cruds.account import crud
from app.core.plugin import password, redis, jwt
from app.core import sms
from app.enums.base import ClientRoleEnum
from app.settings import config
from tortoise.exceptions import IntegrityError
from tortoise.transactions import atomic
from app.models.account import UserModel
from app.services.invitation import service as invitation_service


class Service:
    @atomic()
    async def register(self, payload) -> Dict:
        """创建账号并原子发放邀请奖励，重复账号或无效邀请码整体回滚。"""
        exist = await crud.get_by_account(payload.account)
        if exist:
            raise HTTPException(status_code=200, detail="该账号已注册")
        data = {
            "account": payload.account,
            "password": password.get_password_hash(payload.password),
            "nickname": payload.nickname or f"用户{payload.account[-4:]}",
            "phone": payload.account if re.fullmatch(r"1[3-9]\d{9}", payload.account) else None,
        }
        try:
            obj = await crud.create(data)
        except IntegrityError as exc:
            raise HTTPException(status_code=200, detail="该账号已注册") from exc
        await invitation_service.apply_registration(obj.id, payload.invite_code)
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
        # 验证码核验在数据库事务外完成，持久注册和奖励在同一事务内执行。
        obj, is_new = await self._find_or_register_phone(phone, payload)
        result = await self._build_login_result(obj)
        result["is_new"] = is_new
        return result

    @atomic()
    async def _find_or_register_phone(self, phone: str, payload):
        """已注册手机号只登录；首次注册才消费邀请码，不允许事后补领。"""
        obj = await crud.get_by_phone(phone)
        is_new = False
        if not obj:
            is_new = True
            try:
                obj = await crud.create({
                    "account": phone,
                    "phone": phone,
                    "password": "",  # 空串表示未设置密码,只能用验证码登录
                    "nickname": payload.nickname or f"用户{phone[-4:]}",
                })
            except IntegrityError as exc:
                raise HTTPException(status_code=200, detail="该手机号已注册，请重新获取验证码登录") from exc
            await invitation_service.apply_registration(obj.id, payload.invite_code)
        elif not obj.status:
            raise HTTPException(status_code=200, detail="账号已被禁用")
        return obj, is_new

    @atomic()
    async def set_password(self, user_id: int, payload) -> None:
        """仅为未设置密码的账号首次设置，已有密码必须校验原密码。"""
        obj = await UserModel.select_for_update().get_or_none(id=user_id, deleted=False)
        if not obj:
            raise HTTPException(status_code=200, detail="用户不存在")
        if obj.password:
            raise HTTPException(status_code=200, detail="已设置密码，请使用修改密码功能")
        await crud.update(obj, {"password": password.get_password_hash(payload.password)})

    async def _build_login_result(self, obj) -> Dict:
        """统一密码和验证码登录的公开资料及会话返回值。"""
        token = await self._generate_token(obj)
        return {
            "info": {
                "id": obj.id,
                "account": obj.account,
                "phone": obj.phone,
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

    @atomic()
    async def update_info(self, user_id: int, payload) -> Dict:
        """局部更新资料，校验头像归属；修改用户名后使原会话失效。"""
        from app.services.user_material import verify_materials
        obj = await UserModel.select_for_update().get_or_none(id=user_id, deleted=False)
        if not obj:
            raise HTTPException(status_code=200, detail="用户不存在")
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        old_account = obj.account
        if "nickname" in data:
            data["nickname"] = data["nickname"].strip()
            if not data["nickname"]:
                raise HTTPException(status_code=200, detail="昵称不能为空")
        if data.get("avatar") and data["avatar"] != obj.avatar:
            await verify_materials(user_id, [data["avatar"]])
            if data["avatar"].split("?")[0].rsplit(".", 1)[-1].lower() not in {"jpg", "jpeg", "png", "webp", "gif", "bmp"}:
                raise HTTPException(status_code=200, detail="头像请选择图片文件")
        changed = "account" in data and data["account"] != old_account
        if changed:
            if re.fullmatch(r"1[3-9]\d{9}", data["account"]) and data["account"] != obj.phone:
                raise HTTPException(status_code=200, detail="用户名不能使用未绑定的手机号")
            other = await crud.get_by_account(data["account"])
            if other and other.id != user_id:
                raise HTTPException(status_code=200, detail="该用户名已被使用")
        try:
            await crud.update(obj, data)
        except IntegrityError as exc:
            raise HTTPException(status_code=200, detail="该用户名已被使用") from exc
        if changed:
            await redis.delete(f"{config.REDIS_PREFIX_NAME}:{ClientRoleEnum.USER.value}:{old_account}")
        return {**self._to_dict(obj), "reauth_required": changed}

    @atomic()
    async def change_password(self, user_id: int, payload) -> None:
        """验证原密码再更新哈希，并撤销现有登录会话。"""
        obj = await UserModel.select_for_update().get_or_none(id=user_id, deleted=False)
        if not obj:
            raise HTTPException(status_code=200, detail="用户不存在")
        if not obj.password or not password.verify_password(payload.old_password, obj.password):
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
        """序列化可公开资料，禁止返回密码哈希。"""
        return {
            "id": obj.id,
            "account": obj.account,
            "phone": obj.phone,
            "nickname": obj.nickname,
            "avatar": obj.avatar,
            "has_password": bool(obj.password),
            "create_time": obj.create_time.strftime("%Y-%m-%d %H:%M:%S") if obj.create_time else None,
        }


service = Service()
