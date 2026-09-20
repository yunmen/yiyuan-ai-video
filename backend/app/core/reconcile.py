# -*- coding: utf-8 -*-
'''
@文件    :reconcile.py
@说明    :生成任务超时对账 — 定时把长时间停留在 processing 的任务标记为失败
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
@说明    :worker 崩溃 / 任务丢失 / 回调未到达时,避免任务永久卡在"生成中"。
          以启动即执行一次、之后按 TASK_RECONCILE_INTERVAL 周期执行的后台协程实现。
'''
import asyncio
from typing import Optional

from app.core.plugin import logger
from app.settings import config

_task: Optional[asyncio.Task] = None


async def _loop() -> None:
    from app.services.generate_task import service
    from app.services.payment import service as payment_service

    interval = max(30, int(config.TASK_RECONCILE_INTERVAL))
    timeout = int(config.TASK_STUCK_TIMEOUT)
    while True:
        try:
            affected = await service.reconcile_stuck(timeout)
            if affected:
                logger.info(f"[对账] 已将 {affected} 个超时任务标记为失败")
            cancelled = await payment_service.reconcile_expired()
            if cancelled:
                logger.info(f"[对账] 已取消 {cancelled} 个超时未支付订单")
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.error(f"[对账] 执行异常: {e}")
        await asyncio.sleep(interval)


def start() -> None:
    """启动对账后台任务(应用启动时调用)"""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())


async def stop() -> None:
    """停止对账后台任务(应用关闭时调用)"""
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
