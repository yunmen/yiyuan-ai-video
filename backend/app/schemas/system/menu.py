# -*- coding: utf-8 -*-
'''
@文件    :menu.py
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
    title: str = Field(..., description="显示名称")
    parent_id: int = Field(0, description="父菜单ID")
    type: str = Field(..., description="菜单类型")
    name: str = Field(..., description="别名")
    icon: Union[str, None] = Field("", description="菜单图标")
    path: str = Field(..., description="菜单路径")
    redirect: Union[str, None] = Field(None, description="重定向")
    active: Union[str, None] = Field(None, description="菜单高亮")
    component: str = Field(..., description="组件")
    color: Union[str, None] = Field(None, description="颜色")
    hidden: Union[bool, None] = Field(None, description="隐藏菜单")
    hiddenBreadcrumb: Union[bool, None] = Field(None, description="隐藏面包屑")
    fullpage: Union[bool, None] = Field(None, description="整页路由")
    tag: Union[str, None] = Field(None, description="标签")
    order: Union[int, None] = Field(0, description="排序")
    apiList: Union[Union[List, Dict], None] = Field(None, description="接口权限")


class QuerySchema(BaseQuerySchema):
    title: Optional[str] = Field(None, description="显示名称")
    parent_id: Optional[int] = Field(None, description="父菜单ID")
    type: Optional[str] = Field(None, description="菜单类型")
    name: Optional[str] = Field(None, description="别名")
    icon: Optional[str] = Field(None, description="菜单图标")
    path: Optional[str] = Field(None, description="菜单路径")
    redirect: Optional[Union[str, None]] = Field(None, description="重定向")
    active: Optional[Union[str, None]] = Field(None, description="菜单高亮")
    component: Optional[str] = Field(None, description="组件")
    color: Optional[Union[str, None]] = Field(None, description="颜色")
    hidden: Optional[Union[bool, None]] = Field(None, description="隐藏菜单")
    hiddenBreadcrumb: Optional[Union[bool, None]] = Field(None, description="隐藏面包屑")
    fullpage: Optional[Union[bool, None]] = Field(None, description="整页路由")
    tag: Optional[Union[str, None]] = Field(None, description="标签")
    order: Optional[int] = Field(None, description="排序")
    apiList: Optional[Union[Union[List, Dict], None]] = Field(None, description="接口权限")


class CreateSchema(BaseSchema):
    ...

class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id", example="1")