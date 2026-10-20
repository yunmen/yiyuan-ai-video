# -*- coding: utf-8 -*-
'''
@文件    :account.py
@说明    :C端用户Schema
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import BaseModel, Field
from typing import Optional


class RegisterSchema(BaseModel):
    account: str = Field(..., description="手机号/账号", pattern=r"^[A-Za-z0-9._@-]{6,20}$")
    password: str = Field(..., description="密码", min_length=6, max_length=32)
    nickname: Optional[str] = Field(None, description="昵称", max_length=30)
    invite_code: Optional[str] = Field(None, description="注册邀请码", max_length=8)


class LoginSchema(BaseModel):
    account: str = Field(..., description="账号")
    password: str = Field(..., description="密码")


class SmsSendSchema(BaseModel):
    phone: str = Field(..., description="手机号")


class CodeLoginSchema(BaseModel):
    phone: str = Field(..., description="手机号")
    code: str = Field(..., description="短信验证码", min_length=4, max_length=8)
    nickname: Optional[str] = Field(None, description="首次登录时的昵称(可选)", max_length=30)
    invite_code: Optional[str] = Field(None, description="仅首次注册使用的邀请码", max_length=8)


class SetPasswordSchema(BaseModel):
    password: str = Field(..., description="新密码", min_length=6, max_length=32)


class EditSchema(BaseModel):
    nickname: Optional[str] = Field(None, description="昵称", min_length=1, max_length=30)
    avatar: Optional[str] = Field(None, description="已上传的头像地址", max_length=255)
    account: Optional[str] = Field(None, description="用户名", pattern=r"^[A-Za-z0-9._@-]{6,20}$")


class ChangePasswordSchema(BaseModel):
    old_password: str = Field(..., description="原密码")
    new_password: str = Field(..., description="新密码", min_length=6, max_length=32)
