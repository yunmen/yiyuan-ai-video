# -*- coding: utf-8 -*-
'''
@文件    :task.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from urllib.parse import unquote

from pydantic import Field, BaseModel, field_validator
from typing import Optional, Union, Any, List, Dict
from decimal import Decimal
from datetime import date, datetime
from app.schemas.base import BaseQuerySchema


class BaseSchema(BaseModel):
    name: str = Field(..., description="任务名称")
    func: str = Field(..., description="执行方法")
    args: Union[List, None] = Field([], description="位置参数")
    kwargs: Union[Dict, None] = Field({}, description="关键字参数")
    trigger: str = Field(..., description="触发器")
    executor: str = Field(..., description="执行器")
    jobstore: str = Field(..., description="储存器")
    start_date: Union[datetime, None] = Field(None, description="开始时间")
    end_date: Union[datetime, None] = Field(None, description="结束时间")
    trigger_args: str = Field(..., description="触发器参数")
    desc: Optional[str] = Field(None, description="任务说明")
    @field_validator("args", mode="before")
    @classmethod
    def parse_args(cls, value: Optional[str]) -> List[str]:
        if not value:
            return []
        # 解码 URL 编码（如 %20 转空格）并分割逗号
        decoded_value = unquote(value)
        args = [item.strip() for item in decoded_value.split(",") if item.strip()]
        return args

    @field_validator("kwargs", mode="before")
    @classmethod
    def parse_kwargs(cls, value: Optional[str]) -> Dict[str, str]:
        if not value:
            return {}
        decoded_value = unquote(value)
        kwargs = {}
        # 分割键值对（处理 & 符号）
        for pair in decoded_value.split("&"):
            pair = pair.strip()
            if not pair:
                continue
            # 分割键和值（仅分割第一个等号，支持值中包含等号）
            if "=" in pair:
                key, val = pair.split("=", 1)
                # 解码键和值并去空格
                cleaned_key = unquote(key).strip()
                cleaned_val = unquote(val).strip()
                kwargs[cleaned_key] = cleaned_val
        return kwargs

class QuerySchema(BaseQuerySchema):
    name: Optional[str] = Field(None, description="任务名称")
    func: Optional[str] = Field(None, description="执行方法")
    args: Optional[Union[str, None]] = Field(None, description="位置参数")
    kwargs: Optional[Union[str, None]] = Field(None, description="关键字参数")
    trigger: Optional[str] = Field(None, description="触发器")
    start_date: Optional[Union[datetime, None]] = Field(None, description="开始时间")
    end_date: Optional[Union[datetime, None]] = Field(None, description="结束时间")
    trigger_args: Optional[str] = Field(None, description="触发器参数")
    active: Optional[int] = Field(None, description="状态,1启动2禁用")
    

class CreateSchema(BaseSchema):
    ...

    
class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id", example="1")