# -*- coding: utf-8 -*-
'''
@文件    :response.py
@说明    :各种响应
@时间    :2025/02/14 17:13:32
@作者    :睿
@版本    :1.0
'''

from typing import Optional
from fastapi.responses import JSONResponse
from app.enums.base import ResultCodeEnum
from fastapi import status


class Success(JSONResponse):
    def __init__(
        self,
        msg: Optional[str] = "操作成功",
        code: int = ResultCodeEnum.SUCCESS.value,
        **kwargs,
    ):
        content = {"code": code, "message": msg}
        content.update(kwargs)
        super().__init__(content=content, status_code=status.HTTP_200_OK)


class Fail(JSONResponse):
    def __init__(
        self,
        msg: Optional[str] = "操作失败",
        code: int = ResultCodeEnum.FAIL.value,
        **kwargs
    ):
        content = {"code": code, "message": msg}
        content.update(kwargs)
        super().__init__(content=content, status_code=status.HTTP_200_OK)


class AUTH(JSONResponse):
    def __init__(
        self,
        msg: Optional[str] = "操作未授权",
        code: int = ResultCodeEnum.AUTH,
        **kwargs
    ):
        content = {"code": code, "message": msg}
        content.update(kwargs)
        super().__init__(content=content, status_code=status.HTTP_401_UNAUTHORIZED)


class ERROR(JSONResponse):
    def __init__(
        self,
        msg: Optional[str] = "操作失败",
        code: int = ResultCodeEnum.FAIL,
        **kwargs
    ):
        content = {"code": code, "message": msg}
        content.update(kwargs)
        super().__init__(content=content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)