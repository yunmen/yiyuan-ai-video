# -*- coding: utf-8 -*-
'''
@文件    :user.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from pydantic import Field, BaseModel
from typing import Optional, Union, Any, List, Dict
from decimal import Decimal
from datetime import date, datetime
from app.schemas.base import BaseQuerySchema, BaseLoginSchema


class BaseSchema(BaseModel):
    account: Union[str, None] = Field(..., description="账号")
    realname: Union[str, None] = Field(..., description="姓名")
    nickname: Union[str, None] = Field(..., description="昵称")
    avatar: Union[str, None] = Field(None, description="头像")
    email: str = Field(None, description="邮箱")
    phone: Union[str, None] = Field(..., description="电话")
    permission: int = Field(None, description="数据权限")
    active: Union[bool, None] = Field(False, description="是否激活")
    dept: int = Field(..., description="部门")
    roles: List[int] = Field(..., description="角色ID")


class QuerySchema(BaseQuerySchema):
    account: Optional[Union[str, None]] = Field(None, description="账号")
    realname: Optional[Union[str, None]] = Field(None, description="姓名")
    nickname: Optional[Union[str, None]] = Field(None, description="昵称")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[Union[str, None]] = Field(None, description="电话")
    active: Optional[Union[bool, None]] = Field(None, description="是否激活")
    dept_id: Optional[int] = Field(None, description="部门")


class AccountLoginSchema(BaseLoginSchema):
    """账号密码登录"""
    account: str = Field(..., description="账号")
    password: str = Field(..., description="密码")


class CreateSchema(BaseSchema):
    password: Union[str, None] = Field(..., description="密码")


class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id", example="1")


class EditSchema(BaseModel):
    """修改用户自己资料"""
    nickname: str = Field(..., description="用户别名")
    avatar: str = Field(..., description="用户头像")
    email: str = Field(..., description="用户邮箱")
    phone: str = Field(..., description="用户手机号")


class RepwdSchema(BaseModel):
    """修改用户自己密码"""
    oldPassword: str = Field(..., description="旧密码")
    newPassword: str = Field(..., description="新密码")


class ResetPwdSchema(BaseModel):
    """管理员重置用户密码"""
    id: int = Field(..., description="用户Id")
    newPassword: str = Field(..., description="新密码")