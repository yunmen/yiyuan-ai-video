# -*- coding: utf-8 -*-
'''
@文件    :system_config.py
@说明    :系统业务配置Schema
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import Field, BaseModel
from typing import Optional
from app.schemas.base import BaseQuerySchema


class QuerySchema(BaseQuerySchema):
    keyword: Optional[str] = Field(None, description="配置键/说明模糊搜索")
    group: Optional[str] = Field(None, description="配置分组")


class UpsertSchema(BaseModel):
    key: str = Field(..., max_length=64, description="配置键")
    value: Optional[str] = Field(None, description="配置值")
    group: str = Field("gen", max_length=32, description="配置分组")
    remark: str = Field("", max_length=255, description="配置说明")
    is_public: bool = Field(True, description="是否允许未登录读取")
