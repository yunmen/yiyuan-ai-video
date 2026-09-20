# -*- coding: utf-8 -*-
'''
@文件    :dependencies.py
@说明    :依赖项
@时间    :2025/02/13 17:14:24
@作者    :睿
@版本    :1.0
'''
import jwt as JWT
from typing import List, Set
from fastapi import Security, Depends, HTTPException
from app.core.security import api_key_header
from app.core.plugin import ctx, redis, jwt, logger
from app.enums.base import ClientRoleEnum
from app.settings import config


async def validate_admin_api_key(
        api_key: str = Security(api_key_header),
    ):
    """
    @功能    :对要求登录的接口进行token校验
    @参数    :
    @返回值  :
    @时间    :2024/10/19 20:01:04
    @作者    :睿
    @版本    :1.0
    """
    recorder = ctx.get("recorder")
    recorder['apikey'] = api_key
    if not api_key:
        raise HTTPException(status_code=401, detail="操作未授权")
    if api_key.startswith(config.SECURITY_HEADER_PREFIX):
        token = api_key.replace(config.SECURITY_HEADER_PREFIX + " ", "")
    else:
        raise HTTPException(status_code=401, detail="无效的授权")
    try:
        data = jwt.decrypt_token(token, space=True)
    except JWT.DecodeError:
        raise HTTPException(status_code=401, detail="无效的授权")
    except JWT.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="授权已过期")
    except Exception as e:
        # 异常详情只进日志,不回传客户端(避免泄漏内部实现)
        logger.error(f"admin token 解析异常: {repr(e)}")
        raise HTTPException(status_code=500, detail="授权解析失败")
    if token != await redis.get(f"{config.REDIS_PREFIX_NAME}:{ClientRoleEnum.ADMIN.value}:{data.account}"):
        raise HTTPException(status_code=401, detail="授权已过期")
    recorder['operator_account'] = data.account
    recorder['operator_nickname'] = data.nickname
    ctx.set("g", data)
    return data


async def validate_user_api_key(
        api_key: str = Security(api_key_header),
    ):
    """
    @功能    :对要求登录的接口进行token校验
    @参数    :
    @返回值  :
    @时间    :2024/10/19 20:01:04
    @作者    :睿
    @版本    :1.0
    """
    recorder = ctx.get("recorder")
    recorder['apikey'] = api_key
    if not api_key:
        raise HTTPException(status_code=401, detail="操作未授权")
    if api_key.startswith(config.SECURITY_HEADER_PREFIX):
        token = api_key.replace(config.SECURITY_HEADER_PREFIX + " ", "")
    else:
        raise HTTPException(status_code=401, detail="无效的授权")
    try:
        data = jwt.decrypt_token(token, space=True)
    except JWT.DecodeError:
        raise HTTPException(status_code=401, detail="无效的授权")
    except JWT.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="授权已过期")
    except Exception as e:
        logger.error(f"user token 解析异常: {repr(e)}")
        raise HTTPException(status_code=500, detail="授权解析失败")
    if token != await redis.get(f"{config.REDIS_PREFIX_NAME}:{ClientRoleEnum.USER.value}:{data.account}"):
        raise HTTPException(status_code=401, detail="授权已过期")
    recorder['operator_account'] = data.account
    recorder['operator_nickname'] = data.nickname
    ctx.set("g", data)
    return data


async def get_user_permissions(user_id: int) -> Set[str]:
    """
    @功能    :获取用户所有接口权限
    @参数    :user_id: 用户ID
    @返回值  :权限字符串集合
    @时间    :2026/07/10 10:00:00
    @作者    :睿
    @版本    :1.0
    """
    from app.cruds.system.user import crud as user_crud
    permissions = set()
    user = await user_crud.get_by_id(user_id)
    if not user:
        return permissions
    for role in await user.roles:
        for menu in await role.menus:
            if menu.apiList:
                permissions.update(menu.apiList)
    return permissions


class AdminPermissionChecker:
    """
    @说明    :管理员接口权限校验器
    @参数    :permission: 权限标识,如 system:user:list
    @时间    :2026/07/10 10:00:00
    @作者    :睿
    @版本    :1.0
    """
    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(self):
        """
        @功能    :校验当前管理员是否拥有指定接口权限
        @说明    :依赖 router 层 DeepValidationAdminToken 完成身份认证并写入 ctx.g
        """
        g = ctx.get("g")
        if not g:
            raise HTTPException(status_code=401, detail="操作未授权")
        if g.superuser:
            return g
        permissions = await get_user_permissions(g.id)
        if self.permission not in permissions:
            raise HTTPException(status_code=403, detail="无权限访问")
        return g


async def optional_user_api_key(
        api_key: str = Security(api_key_header),
    ):
    """
    @功能    :可选登录校验 —— 携带有效用户 token 时返回用户,否则返回 None(不抛异常)
    @说明    :用于免登录也可用、但登录后需做归属校验的接口(如创建/查看生成任务)
    @时间    :2026/09/18 15:00:00
    """
    try:
        return await validate_user_api_key(api_key)
    except Exception:
        return None


# 注意:两种使用形态分别导出——
# admin 侧用于 dependencies=[DeepValidationAdminToken],必须是 Depends 实例;
# user 侧用于 Depends(DeepValidationUserToken),必须是裸函数(新版 FastAPI 不允许 Depends 再包 params 对象)
DeepValidationAdminToken = Depends(validate_admin_api_key)  # 检查管理员操作权限
DeepValidationUserToken = validate_user_api_key  # 检查用户操作权限
OptionalUserToken = optional_user_api_key  # 可选登录(无/无效 token 返回 None)