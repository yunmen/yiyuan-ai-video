"""复刻解析草稿人工补充协议，镜头信息必须来自本人拆解任务。"""
from typing import Optional

from pydantic import BaseModel, Field


class UpdateAnalysisSchema(BaseModel):
    """新增元素或为已有元素追加一个已验证镜头关联。"""

    analysis_id: str = Field(..., pattern="^[a-f0-9]{32}$", description="原解析凭证")
    analysis_version: int = Field(..., ge=1, description="解析协议版本")
    reference_video: str = Field(..., min_length=1, description="当前原视频")
    deconstruct_id: int = Field(..., gt=0, description="本人成功的原片拆解任务")
    shot_index: int = Field(..., ge=0, description="关联镜头序号")
    element_id: Optional[str] = Field(None, max_length=64, description="已有元素标识，空则新增")
    kind: str = Field(..., pattern="^(person|product|scene)$", description="元素分类")
    label: str = Field(..., min_length=1, max_length=200, description="用户确认的元素名称")
