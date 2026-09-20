# -*- coding: utf-8 -*-
'''
@文件    :event.py
@说明    :ARQ Worker 生命周期钩子(on_startup / on_shutdown)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from app.core.plugin import logger
from app.core import runtime_config


async def on_startup(ctx):
    runtime_config.start()  # 启动业务配置热更新(admin 改配置免重启生效)
    logger.info("=== worker 启动完成,等待任务 ===")


async def on_shutdown(ctx):
    await runtime_config.stop()
    logger.info("=== worker 正在关闭 ===")
