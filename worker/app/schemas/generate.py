# -*- coding: utf-8 -*-
'''任务入参 / 生成参数(文档与可选校验用)'''
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TaskEnqueueParams(BaseModel):
    """worker 任务方法的统一入参(由 backend 通过 ARQ 下发为位置参数)"""
    task_id: int = Field(..., description="任务Id")
    notify_url: str = Field(..., description="回写状态的回调地址")
    params: Dict[str, Any] = Field(default_factory=dict, description="生成所需业务参数")


class VideoGenParams(BaseModel):
    """视频生成业务参数"""
    template_id: Optional[int] = None
    materials: list = Field(default_factory=list, description="用户上传素材")
    result_video: Optional[str] = None
    duration: int = 10
