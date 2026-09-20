# -*- coding: utf-8 -*-
'''
@文件    :register.py
@说明    :注册器
@时间    :2025/08/08 00:58:34
@作者    :睿
@版本    :1.0
'''
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import (
    RequestValidationError, 
    ResponseValidationError
)
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from app.core.middlewares import HttpLogMiddleware
from app.core.exceptions import BizException
from app.core.handlers import (
    validate_request_handler,
    http_exception_handler,
    validate_response_handler,
    server_exception_handler
)
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html
)
from app.core.docs import get_custom_ui_html
from app.settings import config


def app_middlewares(app: FastAPI):
    """
    @功能    :中间件注册器
    @参数    :
    @返回值  :
    @时间    :2024/10/26 00:27:43
    @作者    :睿
    @版本    :1.0
    """
    app.add_middleware(HttpLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ALLOW_ORIGINS,
        allow_credentials=config.CORS_ALLOW_CREDENTIALS,
        allow_methods=config.CORS_ALLOW_METHODS,
        allow_headers=config.CORS_ALLOW_HEADERS,
    )


def app_exceptions(app: FastAPI):
    """
    @功能    :异常注册器
    @参数    :
    @返回值  :
    @时间    :2024/10/18 17:05:35
    @作者    :睿
    @版本    :1.0
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validate_request_handler)
    app.add_exception_handler(ResponseValidationError, validate_response_handler)
    app.add_exception_handler(BizException, server_exception_handler)


def add_routers(app: FastAPI, prefix=config.API_PREFIX):
    """
    @功能    :api路由注册器
    @参数    :
    @返回值  :
    @时间    :2024/10/26 00:27:43
    @作者    :睿
    @版本    :1.0
    """
    from app.routes import admin
    from app.routes import user
    from app.routes.callback import wxpay as wxpay_callback


    app.include_router(admin.router, prefix=prefix)
    app.include_router(user.router, prefix=prefix)
    # 微信支付回调(免登录,SDK 验签)
    app.include_router(wxpay_callback.router, prefix=f"{prefix}/callback", tags=["支付回调"])


def add_files(app: FastAPI):
    """
    @功能    :文件挂载注册器
    @参数    :
    @返回值  :
    @时间    :2025/02/13 18:00:51
    @作者    :睿
    @版本    :1.0
    """
    app.mount(
        path=config.STATIC_URL, 
        app=StaticFiles(directory=config.STATIC_PATH), 
        name=config.STATIC_NAME
    )


def add_docs(app: FastAPI) -> None:
    """
    @功能    :接口文档注册器
    @参数    :
    @返回值  :
    @时间    :2025/08/08 01:09:14
    @作者    :睿
    @版本    :1.0
    """

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.root_path + app.openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url=config.SWAGGER_JS_URL,
            swagger_css_url=config.SWAGGER_CSS_URL,
            swagger_favicon_url=config.FAVICON_URL
        )


    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=app.root_path + app.openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url=config.REDOC_JS_URL,
            redoc_favicon_url=config.FAVICON_URL
        )
    
    @app.get("/ljdoc", include_in_schema=False)
    async def custom_langjin_ui_html():
        return get_custom_ui_html(
            openapi_url=app.root_path + app.openapi_url,
            title=app.title + " - LaangJin UI",
            swagger_js_url=config.CUSTOM_JS_URL,
            swagger_css_url=config.CUSTOM_CSS_URL,
            swagger_favicon_url=config.FAVICON_URL
        )

