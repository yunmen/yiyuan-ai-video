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
    # 用户端与管理端共用分页边界，避免负偏移及无上限查询。
    pageNum: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(20, ge=1, le=100, description="每页条数")
    type: Optional[str] = Field(None, description="流水类型:reset/consume/recharge/grant/refund")


class AdminUserQuerySchema(BaseQuerySchema):
    keyword: Optional[str] = Field(None, description="手机号/昵称模糊搜索")


class GrantSchema(BaseModel):
    user_id: int = Field(..., description="用户Id")
    amount: int = Field(..., ge=1, le=100000, description="赠送额度(次,正数)")
    remark: str = Field("", description="备注", max_length=255)
