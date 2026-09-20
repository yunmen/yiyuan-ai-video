# -*- coding: utf-8 -*-
'''
@文件    :video_category.py
@说明    :视频模板分类Schema
@时间    :2026/09/20 19:00:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import Field, BaseModel
from typing import Optional
from app.schemas.base import BaseQuerySchema


class BaseSchema(BaseModel):
    name: str = Field(..., description="分类名称", max_length=50)
    cover: Optional[str] = Field(None, description="分类图标/封面")
    sort: int = Field(0, description="排序(倒序,越大越靠前)")
    active: bool = Field(True, description="是否启用")
    remark: str = Field("", description="备注", max_length=255)


class QuerySchema(BaseQuerySchema):
    keyword: Optional[str] = Field(None, description="分类名称关键词")
    active: Optional[bool] = Field(None, description="是否启用")


class CreateSchema(BaseSchema):
    ...


class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id")


class SaveSchema(BaseSchema):
    id: Optional[int] = Field(None, description="主键Id(为空则新增)")
