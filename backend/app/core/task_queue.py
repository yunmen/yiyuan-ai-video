# -*- coding: utf-8 -*-
'''
@文件    :task_queue.py
@说明    :生成任务队列(基于 ARQ,Redis 作为 broker;后端只负责下发,worker 消费)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional
import json
import uuid
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings, result_key_prefix
from arq.jobs import Job, JobStatus
from app.settings import config
from app.core.logger import logger


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
) -> bool:
    """下发生成任务到 ARQ 队列,由 worker 异步消费并通过 notify_url 回调

    返回**是否真正入队**:ARQ 对固定 job id 做去重,判据是
    ``exists(job_key, result_key)`` 二者取或,命中就**静默返回 None** ——
    调用方若不看返回值,会以为下发成功,任务却永远不被执行(实测踩过:断点续跑被丢弃,
    任务卡在"生成中"既不跑也不失败)。

    其中**结果键**只是上次执行留下的返回值痕迹:backend 从不消费 ARQ 返回值
    (结果一律走 notify_url 回调),它没有理由拦住一次合法的重跑,否则用户要干等
    keep_result(默认 1 小时)过期才能续跑。因此仅当 job 键存在(确实在排队/执行中)
    才判定为真去重;只剩结果键时清掉后重试一次。
    """
    if arq_pool is None:
        raise RuntimeError("ARQ 连接池尚未初始化,无法下发任务")

    async def _enqueue():
        """按固定 job id 下发(固定 id 用于去重与存活查询)"""
        return await arq_pool.enqueue_job(
            job_name,
            task_id,
            notify_url,
            params,
            _job_id=job_id(task_id),
            _queue_name=config.ARQ_QUEUE_NAME,
        )

    job = await _enqueue()
    if job is None:
        if await arq_pool.exists(job_id(task_id)):
            logger.warning(
                f"[任务下发] 任务已在队列中,本次重复下发被忽略 job={job_name} task={task_id}"
            )
            return False
        # 只剩上次执行的残留结果键:清掉后重试(不清理会让续跑/孤儿回收长期失效)
        await arq_pool.delete(result_key_prefix + job_id(task_id))
        logger.info(f"[任务下发] 清理上次执行的残留结果键后重新下发 task={task_id}")
        job = await _enqueue()
        if job is None:
            logger.warning(
                f"[任务下发] 清理结果键后仍未能下发 job={job_name} task={task_id}"
            )
            return False
    return True


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


async def enqueue_ai_task(
    job_name: str,
    *args,
    job_id: Optional[str] = None,
    keep_result: int = 600,
    timeout: Optional[float] = None,
):
    """下发 AI 任务到 ARQ,由 worker 执行(backend 不再直连模型)。

    - timeout 给定 → await 结果后返回(用于 backend 同步需要的识别,如建单前的分类识别);
    - timeout 为 None → 仅下发并返回 Job(用于前端异步轮询的文案生成)。

    job_id 固定映射避免重复下发;未传则生成一次性 uuid(文案生成每次都是新任务)。
    """
    if arq_pool is None:
        raise RuntimeError("ARQ 连接池尚未初始化,无法下发任务")
    jid = job_id or f"ai-{uuid.uuid4().hex}"
    job = await arq_pool.enqueue_job(
        job_name,
        *args,
        _job_id=jid,
        _queue_name=config.ARQ_QUEUE_NAME,
        keep_result=keep_result,
    )
    if job is None:
        raise RuntimeError(f"AI 任务下发失败(可能 job_id 冲突): {job_name} {jid}")
    if timeout is not None:
        # 识别类任务:backend 需要同步拿到结果继续建单。超时按"识别失败"降级(返回空),
        # 与 product_vision 的"增强项不阻断"语义一致。
        return await job.result(timeout=timeout)
    return job


async def read_ai_copy_result(task_id: str):
    """读取 worker 写入的文案结果(键 ai_copy:{task_id})。

    返回 (status, data):
      - ("done", dict)       : 生成完成,data 为文案结果
      - ("pending", None)    : 任务仍在队列/执行中(含 Redis 结果已过期但 job 尚在)
      - ("not_found", None)  : 任务不存在或已过期,前端应提示重新生成
    """
    if arq_pool is None:
        return "not_found", None
    raw = await arq_pool.get(f"ai_copy:{task_id}")
    if raw:
        try:
            return "done", json.loads(raw)
        except Exception:  # noqa: BLE001
            return "done", None
    try:
        # 队列名必须与下发时一致,否则 zscore 查不到排队中的 job,会被误判成"任务不存在"
        job = Job(task_id, redis=arq_pool, _queue_name=config.ARQ_QUEUE_NAME)
        status = await job.status()
    except Exception:  # noqa: BLE001
        return "pending", None
    # arq 0.28 的 status() 不抛 JobNotFound(该异常在新版本已移除),
    # 查不到任何痕迹时返回 JobStatus.not_found;complete 但结果键已过期 → 同样取不到数据
    if status in (JobStatus.not_found, JobStatus.complete):
        return "not_found", None
    # queued / in_progress / deferred:仍在跑
    return "pending", None
