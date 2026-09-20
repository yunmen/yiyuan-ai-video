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
            logger.info(f"请求授权: {recorder.get('apikey', '未授权')}")
            logger.info(f"请求参数: {recorder.get('payload')}")
            logger.info(f"响应状态: {recorder.get('status_code')}")
            logger.info(f"响应耗时: {recorder.get('process_time')}")
            logger.info(f"响应结果: {recorder.get('result')}")
            if recorder.get('error_log'):
                logger.error(f"错误日志: {recorder.get('error_log')}")
        logger.info(f"{50*'='+ '>'}请求完成{'<'+'='*50}")
        tasks: BackgroundTasks = ctx.get("task")
        if config.LOGGER_OUTPUT_DATABASE and record:
            recorder.pop("start_time", None)
            recorder.pop("end_time", None)
            # 二次脱敏:入参中的密码/密钥不落库
            if recorder.get('payload') is not None:
                recorder['payload'] = mask_payload(recorder['payload'])
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

