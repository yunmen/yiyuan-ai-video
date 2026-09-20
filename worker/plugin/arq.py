# -*- coding: utf-8 -*-
'''
@文件    :arq.py
@说明    :ARQ RedisSettings 工厂(worker 与 backend 共用同一 Redis)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from arq.connections import RedisSettings
from app.settings import config


def get_redis_settings() -> RedisSettings:
    """根据配置构建 ARQ 的 RedisSettings"""
    return RedisSettings(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD or None,
        username=config.REDIS_USER or None,
        database=config.REDIS_DB_NAME,
        ssl=False,
    )
