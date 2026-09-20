# -*- coding: utf-8 -*-
'''
@文件    :base.py
@说明    :
@时间    :2025/02/14 17:02:16
@作者    :睿
@版本    :1.0
'''
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class BaseLoginSchema(BaseModel):
    """账号密码登录"""
    client_ip: Optional[str] = Field(None, description="客户端IP")


class BaseQuerySchema(BaseModel):
    """查询参数"""
    pageNum: int = Field(default=1, description="页码")
    pageSize: int = Field(default=10, description="每页数量")

    @model_validator(mode="before")
    def remove_empty_strings(cls, values):
        # 遍历所有字段，如果值为空字符串则删除该字段
        return {k: v for k, v in values.items() if v != ""}