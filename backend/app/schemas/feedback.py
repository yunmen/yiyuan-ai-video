# -*- coding: utf-8 -*-
'''
@文件    :feedback.py
@说明    :意见反馈 Schema
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from pydantic import BaseModel, Field
from typing import Optional


class FeedbackCreateSchema(BaseModel):
    """提交意见反馈"""
    content: str = Field(..., description="反馈内容", min_length=1, max_length=1000)
    contact: Optional[str] = Field(default="", description="联系方式(选填)", max_length=100)
