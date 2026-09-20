# -*- coding: utf-8 -*-
'''
@文件    :base.py
@说明    :基础模型
@时间    :2024/10/26 19:04:31
@作者    :睿
@版本    :1.0
'''
from tortoise import fields
from tortoise.manager import Manager
from tortoise.models import Model
from datetime import datetime, date
from decimal import Decimal


class DefaultFilterManager(Manager):
    def get_queryset(self):
        return super(DefaultFilterManager, self).get_queryset().filter(deleted=False)


class BaseModel(Model):
    id = fields.BigIntField(pk=True, index=True, description="主键Id")
    deleted = fields.BooleanField(default=False, description="软删除标记,True无效False有效")

    def to_dict(self, exclude: list[str] | None = None, include: dict | None = None):
        if exclude is None:
            exclude = []
        if include is None:
            include = {}
        exclude.append("deleted")
        result = {}
        for field in self._meta.db_fields:
            if field in exclude:
                continue
            value = getattr(self, field)
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(value, date):
                value = value.strftime("%Y-%m-%d")
            if isinstance(value, Decimal):
                value = str(value)
            result[field] = value
        for k, value in include.items():
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(value, date):
                value = value.strftime("%Y-%m-%d")
            if isinstance(value, Decimal):
                value = str(value)
            include[k] = value
        result.update(include)
        return result
    
    async def delete(self):
        self.deleted = True
        await self.save()

    class Meta:
        abstract = True


class TimestampMixin:
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    @property
    def format_create_time(self) -> str:
        """使用静态格式常量格式化日期"""
        return self.create_time.strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def format_update_time(self) -> str:
        """使用静态格式常量格式化日期"""
        return self.update_time.strftime("%Y-%m-%d %H:%M:%S")