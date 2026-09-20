# -*- coding: utf-8 -*-
'''
@文件    :handlers.py
@说明    :异常处理器
@时间    :2025/08/09 15:55:11
@作者    :睿
@版本    :1.0
'''
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
from app.enums.base import ResultCodeEnum
from app.core.exceptions import BizException
from app.core.plugin import ctx


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    @功能    :http异常处理器
    @参数    :
    @返回值  :
    @时间    :2024/10/18 17:04:35
    @作者    :睿
    @版本    :1.0
    """
    if exc.status_code == 401:
        content=dict(code=ResultCodeEnum.AUTH.value, message=exc.detail)
    elif exc.status_code == 500:
        content=dict(code=ResultCodeEnum.ERROR.value, message=exc.detail)
    else:
        content=dict(code=ResultCodeEnum.FAIL.value, message=exc.detail)
    response = JSONResponse(content=content, status_code=exc.status_code)
    recorder = ctx.get("recorder")
    recorder["status_code"] = response.status_code
    recorder["result"] = content
    return response


async def validate_request_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    @功能    :请求参数异常处理器
    @参数    :
    @返回值  :
    @时间    :2024/10/18 17:05:10
    @作者    :睿
    @版本    :1.0
    """
    errors = []
    for error in exc.errors():
        loc = ".".join(map(str, error["loc"]))  # 转换为可读的路径（如 "body.quantity"）
        message = error["msg"]
        # 去掉 Pydantic 自动添加的 "Value error, " 前缀，保留原始自定义信息
        message = message.removeprefix("Value error, ")
        errors.append({"loc": loc, "msg": message})
    content=dict(code=ResultCodeEnum.FAIL.value, message=message, data=errors)
    response = JSONResponse(content, status_code=status.HTTP_400_BAD_REQUEST)
    recorder = ctx.get("recorder")
    recorder["status_code"] = response.status_code
    recorder["result"] = content
    return response


async def validate_response_handler(request: Request, exc: ResponseValidationError) -> JSONResponse:
    """
    @功能    :响应参数异常处理器
    @参数    :
    @返回值  :
    @时间    :2025/08/10 04:26:52
    @作者    :睿
    @版本    :1.0
    """
    content=dict(code=ResultCodeEnum.ERROR.value, message="响应校验不通过,请检查参数后再试.", data=exc.body)
    response = JSONResponse(content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    recorder = ctx.get("recorder")
    recorder["status_code"] = response.status_code
    recorder["result"] = content
    return response


async def server_exception_handler(request: Request, exc: BizException) -> JSONResponse:
    """
    @功能    :内部服务器错误
    @参数    :
    @返回值  :
    @时间    :2024/10/18 17:04:35
    @作者    :睿
    @版本    :1.0
    """
    content=dict(code=ResultCodeEnum.ERROR.value, message=exc.message, data=exc.data)
    response = JSONResponse(content, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    recorder = ctx.get("recorder")
    recorder["status_code"] = response.status_code
    recorder["result"] = content
    return response