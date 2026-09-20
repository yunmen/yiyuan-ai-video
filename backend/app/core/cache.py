# -*- coding: utf-8 -*-
'''
@文件    :cache.py
@说明    :缓存相关操作
@时间    :2025/08/25 18:53:44
@作者    :睿
@版本    :1.0
'''

from app.core.plugin import redis
from app.core.logger import logger

async def init_redis_cache():
    """初始化redis缓存数据"""
    await redis.startup()
    await redis.set("test", "test")
    logger.info("初始化redis缓存数据")


async def close_redis_cache():
    """关闭redis缓存数据"""
    await redis.shutdown()
    logger.info("关闭redis缓存数据")