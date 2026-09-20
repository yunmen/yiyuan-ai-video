# -*- coding: utf-8 -*-
'''
@文件    :dept.py
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
    name: Union[str, None] = Field(None, description="部门名称")
    path: Union[str, None] = Field("", description="路径")
    desc: Union[str, None] = Field(None, description="备注")
    order: int = Field(..., description="排序")
    parent_id: int = Field(..., description="父部门ID")


class QuerySchema(BaseQuerySchema):
    name: Optional[Union[str, None]] = Field(None, description="部门名称")
    path: Optional[Union[str, None]] = Field(None, description="路径")
    desc: Optional[Union[str, None]] = Field(None, description="备注")
    order: Optional[int] = Field(None, description="排序")
    parent_id: Optional[int] = Field(None, description="父部门ID")
    active: Optional[bool] = Field(None, description="是否激活")


class CreateSchema(BaseSchema):
    ...

class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id", example="1")