# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :数字人Schema
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import BaseModel, Field
from typing import Optional, List
from app.schemas.base import BaseQuerySchema


class BaseSchema(BaseModel):
    name: str = Field(..., description="数字人名称")
    avatar: Optional[str] = Field(None, description="头像")
    gender: str = Field("女", description="性别")
    style: Optional[str] = Field(None, description="风格")
    desc: Optional[str] = Field(None, description="简介")
    tags: List[str] = Field(default_factory=list, description="标签")
    preview_video: Optional[str] = Field(None, description="预览视频")
    sort: int = Field(0, description="排序")
    active: bool = Field(True, description="是否上架")


class QuerySchema(BaseQuerySchema):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    gender: Optional[str] = Field(None, description="性别")
    active: Optional[bool] = Field(None, description="是否上架")


class CreateSchema(BaseSchema):
    ...


class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id")
