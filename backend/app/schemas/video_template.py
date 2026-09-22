# -*- coding: utf-8 -*-
'''
@文件    :video_template.py
@说明    :视频模板Schema
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import Field, BaseModel
from typing import Optional, List, Dict
from app.schemas.base import BaseQuerySchema


class BaseSchema(BaseModel):
    title: str = Field(..., description="模板标题")
    category: str = Field(..., description="模板分类")
    cover: Optional[str] = Field(None, description="封面图")
    video_url: Optional[str] = Field(None, description="示例视频地址")
    duration: int = Field(10, description="视频时长(秒)")
    hot: int = Field(0, description="热度值")
    use_count: int = Field(0, description="使用次数")
    desc: Optional[str] = Field(None, description="模板描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    example_images: List[str] = Field(default_factory=list, description="示例图")
    default_text: Dict[str, Optional[str]] = Field(default_factory=dict, description="默认文案{title,subtitle,script}")
    # 画面构成三段式:主体/镜头/场景,运营换场景只改 setting
    prompt_parts: Dict[str, Optional[str]] = Field(
        default_factory=dict, description="画面构成{person,shot,setting}"
    )
    recommend: bool = Field(False, description="是否首页推荐")
    recommend_sort: int = Field(0, description="推荐位排序(倒序)")
    sort: int = Field(0, description="排序")
    active: bool = Field(True, description="是否上架")


class QuerySchema(BaseQuerySchema):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    category: Optional[str] = Field(None, description="分类")
    active: Optional[bool] = Field(None, description="是否上架")
    recommend: Optional[bool] = Field(None, description="是否首页推荐")
    sort_type: Optional[int] = Field(None, description="排序:1最热2最新3最多使用")


class CreateSchema(BaseSchema):
    ...


class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id")
