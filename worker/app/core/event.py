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
    # 必须 await:先拿到 backend 全量配置再开始接单。否则 backend 未就绪时
    # worker 会带着 env 文件里不完整的本地默认值消费任务,gen.* 类配置缺失 →
    # 任务被误判失败(如「系统未配置视频编辑模型」)。
    await runtime_config.start()
    # worker 启动即把技能目录与计划注册表发布到 Redis,作为 backend 目录/计划的单一来源,
    # 避免 backend 手抄静态副本(两端漂移);技能任务入口也会再覆盖一次。
    try:
        from app.core.skill_runtime import register_builtin_skills, publish_catalog, publish_plans
        register_builtin_skills()
        redis = ctx.get("redis")
        await publish_catalog(redis)
        await publish_plans(redis)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[worker] 启动发布技能目录/计划失败(不影响接单): {exc}")
    logger.info("=== worker 启动完成,等待任务 ===")


async def on_shutdown(ctx):
    await runtime_config.stop()
    logger.info("=== worker 正在关闭 ===")
