# -*- coding: utf-8 -*-
'''
@文件    :__init__.py
@说明    :
@时间    :2025/07/17 23:03:08
@作者    :睿
@版本    :1.0
'''
from fastapi import FastAPI
from app.enums.base import EnvironmentEnum


def create_app() ->FastAPI:
    """FastAPI工厂函数"""
    from app.settings import config
    from app.core import register, event
    app = FastAPI(
        lifespan=event.lifespan,
        **config.FASTAPI_CONFIG
    )
    register.app_exceptions(app)
    register.app_middlewares(app)
    register.add_routers(app)
    register.add_files(app)
    register.add_docs(app)
    return app
