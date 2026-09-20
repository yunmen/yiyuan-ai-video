# -*- coding: utf-8 -*-
'''
@文件    :security.py
@说明    :安全访问
@时间    :2025/08/08 02:42:06
@作者    :睿
@版本    :1.0
'''
from fastapi.security import APIKeyHeader
from app.settings import config

api_key_header = APIKeyHeader(
    name=config.SECURITY_HEADER_NAME, 
    description="API Key请求头授权",
    auto_error=False
)
