# -*- coding: utf-8 -*-
'''
@文件    :event.py
@说明    :事件管理
@时间    :2025/08/08 03:10:46
@作者    :睿
@版本    :1.0
'''
from fastapi import FastAPI
from typing import Any, AsyncGenerator
from fastapi.concurrency import asynccontextmanager
from app.core import cache, database, logger, reconcile, scheduler, task_queue


async def startup():
    """启动事件"""
    await logger.init_logger_config()
    await cache.init_redis_cache()
    await database.init_database_data()
    await scheduler.init_scheduler_task()
    await task_queue.init_arq()        # 初始化 ARQ 连接池,供下发生成任务
    reconcile.start()                  # 启动卡死任务对账后台协程
    await logger.print_welcome_banner()


async def shutdown():
    """关闭事件"""
    await reconcile.stop()             # 停止对账后台协程
    await scheduler.close_scheduler_task()
    await task_queue.close_arq()       # 关闭 ARQ 连接池
    await cache.close_redis_cache()
    await database.close_database_data()
    await logger.close_logger_config()
    


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    """
    自定义生命周期
    """
    await startup()
    yield
    await shutdown()