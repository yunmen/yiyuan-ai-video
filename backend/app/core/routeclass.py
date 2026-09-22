# -*- coding: utf-8 -*-
'''
@文件    :routeclass.py
@说明    :
@时间    :2025/08/09 23:56:30
@作者    :睿
@版本    :1.0
'''
import json
from typing import Callable, Coroutine, Any
from fastapi import Request
from types import SimpleNamespace
from fastapi.routing import APIRoute
from fastapi.responses import Response, JSONResponse, FileResponse, PlainTextResponse
from starlette.datastructures import UploadFile
from app.core.logger import ctx
from loguru import logger


class OperationLogRoute(APIRoute):
    async def before_request(self, request: Request):
        """请求前操作"""
        route: APIRoute = request.scope.get("route") or SimpleNamespace(name="404_not_found", endpoint="404_not_found", summary="404_not_found")
        recorder = ctx.get("recorder")
        recorder['summary'] = route.summary
        payload = {}
        try:
            json_data = await request.json()
            payload.update(json_data)
        except Exception as exc:
            logger.debug(f"请求体非 JSON,回退表单解析: {exc}")
            form_data = await request.form()
            for key in form_data:
                values = form_data.getlist(key)
                if len(values) == 1:
                    value = values[0]
                    if isinstance(value, UploadFile):
                        payload[key] = value.filename
                    else:
                        payload[key] = value
                else:
                    payload[key] = values
        finally:
            payload.update(dict(request.query_params))
        recorder["payload"] = payload


    async def after_request(self, response: Response):
        """请求后操作"""
        recorder = ctx.get("recorder")
        if isinstance(response, PlainTextResponse):
            result = {"text": response.body.decode()}
        elif isinstance(response, JSONResponse):
            result = json.loads(response.body.decode())
        elif isinstance(response, FileResponse):
            result = {
                "filename": response.filename,
                "media_type": response.media_type
            }
        else:
            result = {"message": f"{type(response).__name__}类型不支持记录"}
        recorder["status_code"] = response.status_code
        recorder["result"] = result


    def get_route_handler(self) ->  Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def operation_route_handler(request: Request) -> Response:
            await self.before_request(request)
            response = await original_route_handler(request)
            await self.after_request(response)
            return response
        return operation_route_handler