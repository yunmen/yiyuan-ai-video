# -*- coding: utf-8 -*-
'''
@文件    :task_queue.py
@说明    :生成任务队列(基于 ARQ,Redis 作为 broker;后端只负责下发,worker 消费)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from app.settings import config


# 全局 ARQ 连接池(生命周期由 app/core/event.py 管理)
arq_pool: Optional[ArqRedis] = None


async def init_arq() -> ArqRedis:
    """创建 ARQ 连接池(应用启动钩子调用)"""
    global arq_pool
    arq_pool = await create_pool(RedisSettings(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD or None,
        username=config.REDIS_USER or None,
        database=config.REDIS_DB_NAME,
        ssl=False,
    ), default_queue_name=config.ARQ_QUEUE_NAME)
    return arq_pool


async def close_arq() -> None:
    """关闭 ARQ 连接池(应用关闭钩子调用)"""
    global arq_pool
    if arq_pool is not None:
        await arq_pool.close()
        arq_pool = None


async def enqueue_generate_task(
    job_name: str,
    task_id: int,
    notify_url: str,
    params: dict,
) -> None:
    """下发生成任务到 ARQ 队列,由 worker 异步消费并通过 notify_url 回调"""
    if arq_pool is None:
        raise RuntimeError("ARQ 连接池尚未初始化,无法下发任务")
    await arq_pool.enqueue_job(
        job_name,
        task_id,
        notify_url,
        params,
        _queue_name=config.ARQ_QUEUE_NAME,
    )
