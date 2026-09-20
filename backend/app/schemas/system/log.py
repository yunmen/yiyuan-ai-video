# -*- coding: utf-8 -*-
'''
@文件    :log.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from pydantic import Field, BaseModel
from typing import Optional, Union, Any, List, Dict
from decimal import Decimal
from datetime import date, datetime
from app.schemas.base import BaseQuerySchema


class BaseSchema(BaseModel):
    request_id: str = Field(..., description="请求Id")
    summary: str = Field(..., description="接口说明")
    url: str = Field(..., description="请求地址")
    method: str = Field(None, description="请求类型")
    client_ip: str = Field(None, description="客户端IP")
    headers: str = Field(None, description="请求头")
    payload: Dict = Field(None, description="请求参数")
    result: Dict = Field(None, description="响应结果")
    status_code: str = Field(None, description="响应码")
    process_time: str = Field(None, description="响应时间")
    error_log: str = Field(None, description="错误日志")
    client_type: str = Field(None, description="客户端")
    operator_account: str = Field(None, description="操作人账号")
    operator_nickName: str = Field(None, description="操作人昵称")


class QuerySchema(BaseQuerySchema):
    request_id: Optional[str] = Field(None, description="请求Id")
    summary: Optional[str] = Field(None, description="接口说明")
    url: Optional[str] = Field(None, description="请求地址")
    method: Optional[str] = Field(None, description="请求类型")
    client_ip: Optional[str] = Field(None, description="客户端IP")
    status_code: Optional[str] = Field(None, description="响应码")
    process_time: Optional[str] = Field(None, description="响应时间")
    client_type: Optional[str] = Field(None, description="客户端")
    operator_account: Optional[str] = Field(None, description="操作人账号")
    operator_nickName: Optional[str] = Field(None, description="操作人昵称")


class CreateSchema(BaseSchema):
    ...

class UpdateSchema(BaseSchema):
    id: int = Field(..., description="主键Id", example="1")