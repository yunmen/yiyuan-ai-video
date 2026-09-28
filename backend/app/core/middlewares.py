# -*- coding: utf-8 -*-
'''
@文件    :middlewares.py
@说明    :中间件
@时间    :2025/08/08 03:21:00
@作者    :睿
@版本    :1.0
'''
import uuid
import time
import json
import traceback
import asyncio
from types import SimpleNamespace
from fastapi.requests import Request
from fastapi.routing import APIRoute
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.background import BackgroundTasks
from app.core.response import ERROR
from app.core.plugin import ctx, logger
from app.services.system.log import service as log_service
from app.schemas.system.log import CreateSchema as LogCreateSchema
from app.settings import config


# 这些请求头/字段含凭据,禁止写入操作日志
SENSITIVE_HEADERS = {"authorization", "x-worker-token", "cookie", "set-cookie", "proxy-authorization"}
SENSITIVE_FIELDS = {
    "password", "old_password", "new_password", "confirm_password",
    "api_key", "apikey", "secret", "access_key_secret", "private_key",
    "token", "access_token", "refresh_token", "authorization",
}
MASK = "******"


def mask_headers(headers) -> str:
    """请求头脱敏:鉴权类头一律打码"""
    safe = {}
    for key, value in headers.items():
        safe[key] = MASK if key.lower() in SENSITIVE_HEADERS else value
    return json.dumps(safe)


def mask_payload(payload):
    """请求体脱敏:密码/密钥类字段一律打码"""
    if isinstance(payload, dict):
        return {
            key: (MASK if key.lower() in SENSITIVE_FIELDS else mask_payload(value))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [mask_payload(item) for item in payload]
    return payload


def mask_apikey(apikey):
    """鉴权令牌脱敏:保留前缀与少量字符便于排查,其余打码,避免明文令牌进日志"""
    if not apikey:
        return "未授权"
    prefix = config.SECURITY_HEADER_PREFIX
    if isinstance(apikey, str) and prefix and apikey.startswith(prefix):
        token = apikey.replace(prefix + " ", "", 1)
        if len(token) > 6:
            return f"{prefix} {token[:6]}{'*' * 12}"
        return MASK
    return MASK


def _looks_like_token(value) -> bool:
    """粗略判断是否为下发的令牌(三段式 JWT 等长串),用于响应中 data 字段的脱敏"""
    return isinstance(value, str) and value.count(".") == 2 and len(value) > 20


def mask_result(result):
    """响应结果脱敏:递归打码敏感字段,并对形如 JWT 的下发令牌(data 字段)打码"""
    if isinstance(result, dict):
        masked = {}
        for key, value in result.items():
            if key.lower() in SENSITIVE_FIELDS or (key == "data" and _looks_like_token(value)):
                masked[key] = MASK
            else:
                masked[key] = mask_result(value)
        return masked
    if isinstance(result, list):
        return [mask_result(item) for item in result]
    return result


class HttpLogMiddleware(BaseHTTPMiddleware):
    async def before_request(self, request: Request):
        """请求前操作"""
        logger.info(f"{50*'='+ '>'}请求开始{'<'+'='*50}")
        request_id = str(uuid.uuid4())
        recorder = {}
        recorder['request_id'] = request_id
        recorder['start_time'] = time.perf_counter()
        recorder['url'] = request.url
        recorder['path'] = request.url.path
        recorder['method'] = request.method
        
        recorder['client_ip'] = request.headers.get('X-Real-Ip') or request.client.host
        recorder['headers'] = mask_headers(request.headers)
        ctx.set("stack", request_id)
        ctx.set("task", BackgroundTasks())
        ctx.set("recorder", recorder)


    async def error_request(self, response: Response):
        """错误请求的处理"""
        recorder = ctx.get("recorder")
        recorder["status_code"] = response.status_code
        recorder["result"] = json.loads(response.body.decode())
        recorder["error_log"] = traceback.format_exc()


    async def after_request(self, response: Response):
        """请求后操作"""
        recorder = ctx.get("recorder")
        recorder['end_time'] = time.perf_counter()
        recorder['process_time'] = f'{recorder['end_time']- recorder['start_time']:.4f}s'
        response.headers['x-process-time'] = recorder['process_time']
        record = not config.IGNORE_OPERATION_LOG  # 是否需要打印日志
        if any(recorder.get('path').startswith(path) for path in config.IGNORE_OPERATION_PATH):
            record = False
        if config.LOGGER_OUTPUT_CONSOLE and record:
            logger.info(f"请求地址: {recorder.get('url')}")
            logger.info(f"请求路径: {recorder.get('path')}")
            logger.info(f"请求类型: {recorder.get('method')}")
            logger.info(f"请求描述: {recorder.get('summary')}")
            logger.info(f"请求来源: {recorder.get('client_ip')}")
            # apikey 含 Bearer 令牌,payload/result 可能含密码或下发的令牌,打印前先脱敏,避免凭据明文进日志
            logger.info(f"请求授权: {mask_apikey(recorder.get('apikey'))}")
            logger.info(f"请求参数: {mask_payload(recorder.get('payload'))}")
            logger.info(f"响应状态: {recorder.get('status_code')}")
            logger.info(f"响应耗时: {recorder.get('process_time')}")
            logger.info(f"响应结果: {mask_result(recorder.get('result'))}")
            if recorder.get('error_log'):
                logger.error(f"错误日志: {recorder.get('error_log')}")
        logger.info(f"{50*'='+ '>'}请求完成{'<'+'='*50}")
        tasks: BackgroundTasks = ctx.get("task")
        if config.LOGGER_OUTPUT_DATABASE and record:
            recorder.pop("start_time", None)
            recorder.pop("end_time", None)
            # 二次脱敏:入参与响应中的密码/密钥/令牌不落库
            if recorder.get('payload') is not None:
                recorder['payload'] = mask_payload(recorder['payload'])
            if recorder.get('result') is not None:
                recorder['result'] = mask_result(recorder['result'])
            tasks.add_task(log_service.create, recorder)
        for task in tasks.tasks:
            asyncio.create_task(task())


    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        await self.before_request(request)
        try:
            response = await call_next(request)
        except Exception as exc:
            response = ERROR(str(exc))
            await self.error_request(response)
        finally:
            await self.after_request(response)
            return response

