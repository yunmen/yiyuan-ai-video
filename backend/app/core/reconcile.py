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
    orphan_timeout = int(config.TASK_ORPHAN_TIMEOUT)
    silent_warn = int(config.TASK_SILENT_WARN)
    while True:
        try:
            # ① 静默预警(只打日志、不动状态):在判失败/续跑之前先留下可排查的痕迹 ——
            #    "任务还活着只是没回调"与"任务已死"在用户侧都表现为进度不动,这里先区分出来。
            for item in await service.list_silent_tasks(silent_warn):
                logger.warning(
                    f"[对账] 任务长时间无回调 task={item['id']} type={item['type']} "
                    f"progress={item['progress']} 静默≈{item['silent_seconds']}s "
                    f"(最后回调 {item['update_time']})"
                )
            # ② 先回收孤儿(worker 中断、还没提交外部任务的),再对超时任务标记失败
            recovered = await service.recover_orphan_tasks(orphan_timeout)
            if recovered:
                logger.info(f"[对账] 已重新入队 {recovered} 个孤儿任务")
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
