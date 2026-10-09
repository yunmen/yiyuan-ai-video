# -*- coding: utf-8 -*-
'''
@文件    :gen_template.py
@说明    :用户工程模板(参数模板化 / 一套结构百变体)请求结构。
          模板只保存「创意配置快照」,生成变体时由调用方补入新素材(materials)与覆盖项(overrides)。
'''
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseQuerySchema


class GenTemplateSaveSchema(BaseModel):
    """保存工程模板:只存创意配置快照,不存素材。"""
    title: str = Field(..., max_length=100, description="模板标题")
    format: str = Field("", max_length=30, description="复刻形态(replicate_format)")
    cover: Optional[str] = Field(None, description="封面图")
    params: Dict[str, Any] = Field(default_factory=dict, description="生成参数快照(创意配置)")


class GenTemplateQuerySchema(BaseQuerySchema):
    """模板列表查询。"""
    keyword: Optional[str] = Field(None, description="标题模糊搜索")


class GenTemplateIdSchema(BaseModel):
    """按 id 操作模板。"""
    id: int = Field(..., description="模板 id")


class GenTemplateVariantSchema(BaseModel):
    """单个变体:本次使用的素材 + 覆盖项(换主播/排名/语言/画幅等)。"""
    materials: List[str] = Field(..., description="本次变体的素材(对标视频/参考图)")
    overrides: Dict[str, Any] = Field(default_factory=dict, description="覆盖项(局部覆盖模板配置)")
    remark: Optional[str] = Field(None, description="备注")


class GenTemplateGenerateSchema(BaseModel):
    """按工程模板生成单个变体。"""
    template_id: int = Field(..., description="模板 id")
    materials: List[str] = Field(..., description="本次变体的素材(对标视频/参考图)")
    overrides: Dict[str, Any] = Field(default_factory=dict, description="覆盖项(换主播/排名/语言/画幅等)")
    remark: Optional[str] = Field(None, description="备注")


class GenTemplateBatchSchema(BaseModel):
    """按工程模板批量出变体(百变体):一次下发多组变体,逐个入队(受额度校验约束)。"""
    template_id: int = Field(..., description="模板 id")
    variants: List[GenTemplateVariantSchema] = Field(..., description="变体列表")
