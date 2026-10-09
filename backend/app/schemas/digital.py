# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :数字人Schema
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from app.schemas.base import BaseQuerySchema


class BaseSchema(BaseModel):
    name: str = Field(..., description="数字人名称")
    avatar: Optional[str] = Field(None, description="头像")
    gender: str = Field("女", description="性别")
    style: Optional[str] = Field(None, description="风格")
    desc: Optional[str] = Field(None, description="简介")
    tags: List[str] = Field(default_factory=list, description="标签")
    preview_video: Optional[str] = Field(None, description="预览视频")
    image: Optional[str] = Field(None, description="形象图(口型驱动底图,留空回退头像)")
    voice: Optional[str] = Field(None, description="音色(TTS voice,留空用网关默认音色)")
    voice_reference: Optional[str] = Field(None, description="声纹样本音频地址(可复用声纹,优先级高于 voice;同一数字人跨任务复用同一声音)")
    model: Optional[str] = Field(None, description="生成模型(留空用全局配置 gen.digital_model)")
    default_text: Optional[str] = Field(None, description="默认口播文案")
    pose_variants: List[Dict] = Field(default_factory=list, description="派生视图[{name,image}]")
    sort: int = Field(0, description="排序")
    active: bool = Field(True, description="是否上架")


class QuerySchema(BaseQuerySchema):
    keyword: Optional[str] = Field(None, description="搜索关键词")
    gender: Optional[str] = Field(None, description="性别")
    active: Optional[bool] = Field(None, description="是否上架")


class CreateSchema(BaseSchema):
    ...


class UserCreateSchema(BaseModel):
    """用户端自助创建专属数字人:形象图必填,其余可选。

    归属用户由路由从登录态注入(不允许前端指定,防越权把专属数字人挂到他人名下);
    模型/标签/派生视图/预览视频等由运营侧维护,用户侧不开放。
    """
    name: str = Field(..., description="数字人名称(给自己形象起名)")
    gender: str = Field("女", description="性别")
    style: Optional[str] = Field(None, description="风格")
    desc: Optional[str] = Field(None, description="简介")
    avatar: Optional[str] = Field(None, description="头像(留空用形象图)")
    image: str = Field(..., description="形象图(口型驱动底图,正面半身照;必填)")
    voice: Optional[str] = Field(None, description="音色(TTS voice,留空用网关默认音色)")
    voice_reference: Optional[str] = Field(None, description="声纹样本音频地址(可复用声纹,优先级高于 voice)")
    default_text: Optional[str] = Field(None, description="默认口播文案")


class UserUpdateSchema(UserCreateSchema):
    """用户端编辑专属数字人:字段与创建一致,另带主键。

    仅本人可编辑自己的专属形象(归属校验在 Service 层);模型/标签/派生视图/预览视频等
    运营侧字段与创建一样不接受用户提交。
    """

    id: int = Field(..., description="主键Id(必填,仅限本人专属形象)")


class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id")
