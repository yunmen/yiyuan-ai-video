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
        # 同一任务固定 job id:重复下发(重试/续跑/孤儿回收)会被 ARQ 自动忽略,不会跑两遍
        _job_id=job_id(task_id),
        _queue_name=config.ARQ_QUEUE_NAME,
    )


def job_id(task_id: int) -> str:
    """任务 → ARQ job id(固定映射:既用于去重,也便于查存活状态)"""
    return f"task-{int(task_id)}"


async def job_alive(task_id: int) -> bool:
    """任务是否仍在队列里 / 正在执行(用于孤儿回收时避免重复入队)

    用 ARQ 的 ``exists(job_id)``:queued / in-progress / deferred / retry 时返回 True,
    任务跑完(job 键被删)后返回 False。
    ⚠️ 原实现误用了 ``job_status`` —— ARQ 0.28 并没有这个方法,异常被吞掉后**恒定返回 True**,
    孤儿任务因此永远回收不了。改用 exists,并且只在**确认不存在**时才判定为死。
    判不出来(池未初始化/查询异常)时仍**保守返回 True**:宁可漏回收,也不能把在跑的任务重复入队。
    """
    if arq_pool is None:
        return True
    try:
        return bool(await arq_pool.exists(job_id(task_id)))
    except Exception:  # noqa: BLE001
        return True
