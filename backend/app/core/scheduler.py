# -*- coding: utf-8 -*-
'''
@文件    :scheduler.py
@说明    :任务管理
@时间    :2025/08/25 15:56:20
@作者    :睿
@版本    :1.0
'''
import asyncio, os
from app.core.plugin import scheduler, redis, locker
from app.services.system.task import service
from app.core.plugin import logger
from app.settings import config


async def task_listener(event):
    job = scheduler.get_job(event.job_id)
    if event.exception:
        status = False
        desc = event.traceback
    else:
        status = True
        desc = event.retval
    task_id = job.id.replace("task_", "")
    logger.info({"task_id": task_id, "name":job.name, "status": status, "desc": desc})

def sync_listener_wrapper(event):
    # 在当前事件循环中创建任务（自动调度）
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # 如果事件循环已在运行（如在 AsyncIOScheduler 中），直接提交任务
        loop.create_task(task_listener(event))
    else:
        # 如果事件循环未运行（罕见场景），手动运行
        asyncio.run(task_listener(event))

async def init_scheduler_task():
    """初始化定时任务"""
    logger.info("开始初始化定时任务")
    scheduler.configure()
    scheduler.add_listener(sync_listener_wrapper)
    scheduler.add_jobstore("redis", config.REDIS_CONFIG)
    scheduler.start()
    await locker.auto_run_func(service.init_task)
    logger.info("初始化定时任务结束")


async def close_scheduler_task():
    """关闭定时任务"""
    logger.info("开始清理定时任务")
    scheduler.remove_jobs()
    scheduler.shutdown()
    logger.info("清理定时任务结束")
