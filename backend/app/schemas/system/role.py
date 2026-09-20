# -*- coding: utf-8 -*-
'''
@文件    :role.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from pydantic import Field, BaseModel
from typing import Optional, Union, Any, List, Dict
from decimal import Decimal
from datetime import date, datetime
from app.schemas.base import BaseQuerySchema


class BaseSchema(BaseModel):
    name: str = Field(..., description="角色名称")
    alias: Union[str, None] = Field(None, description="别名")
    desc: Union[str, None] = Field(None, description="角色描述")


class QuerySchema(BaseQuerySchema):
    name: Optional[str] = Field(None, description="角色名称")
    alias: Optional[Union[str, None]] = Field(None, description="别名")
    desc: Optional[Union[str, None]] = Field(None, description="角色描述")
    active: Optional[bool] = Field(None, description="是否激活")


class CreateSchema(BaseSchema):
    ...

class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id", example="1")


class PermissionSchema(BaseModel):
    """更新角色菜单"""
    id: int = Field(..., description="角色ID")
    menus: List[int] = Field(..., description="菜单ID列表")

