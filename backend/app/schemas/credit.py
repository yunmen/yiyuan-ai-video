# -*- coding: utf-8 -*-
'''
@文件    :credit.py
@说明    :额度流水Schema定义
@时间    :2026/09/20 10:00:00
@作者    :AI
@版本    :1.0
'''

from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.base import BaseQuerySchema


class LogQuerySchema(BaseQuerySchema):
    type: Optional[str] = Field(None, description="流水类型:reset/consume/recharge/grant/refund")


class AdminUserQuerySchema(BaseQuerySchema):
    keyword: Optional[str] = Field(None, description="手机号/昵称模糊搜索")


class GrantSchema(BaseModel):
    user_id: int = Field(..., description="用户Id")
    amount: int = Field(..., ge=1, le=100000, description="赠送额度(次,正数)")
    remark: str = Field("", description="备注", max_length=255)
