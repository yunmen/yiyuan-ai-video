# -*- coding: utf-8 -*-
'''
@文件    :feedback.py
@说明    :用户意见反馈模型
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class FeedbackModel(BaseModel, TimestampMixin):
    """用户意见反馈表"""
    content = fields.TextField(description="反馈内容")
    contact = fields.CharField(max_length=100, null=True, description="联系方式(选填)")
    user_id = fields.BigIntField(null=True, description="提交用户Id(登录时记录,匿名留空)")
    status = fields.IntField(default=0, description="处理状态:0待处理 1已处理")

    class Meta:
        table = "tb_feedback"
        table_description = "用户意见反馈表"
