# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :数字人模型
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class DigitalHumanModel(BaseModel, TimestampMixin):
    """数字人表"""
    name = fields.CharField(max_length=50, description="数字人名称")
    avatar = fields.CharField(max_length=255, null=True, description="头像")
    gender = fields.CharField(max_length=10, default="女", description="性别")
    style = fields.CharField(max_length=50, null=True, description="风格")
    desc = fields.TextField(null=True, description="简介")
    tags = fields.JSONField(default=list, description="标签")
    preview_video = fields.CharField(max_length=255, null=True, description="预览视频")
    sort = fields.IntField(default=0, description="排序")
    active = fields.BooleanField(default=True, description="是否上架")

    class Meta:
        table = "tb_digital_human"
        table_description = "数字人表"
