# -*- coding: utf-8 -*-
'''
@文件    :worker.py
@说明    :ARQ 任务配置(plain settings 类)— 注册任务方法、队列、并发与生命周期
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from app.settings import config
from app.core.event import on_startup, on_shutdown
from app.workers.generate_worker import (
    process_video,
    process_text,
    process_image,
    process_audio,
    process_digital,
    process_render,
    process_deconstruct,
    ai_recognize,
    ai_copy_generate,
    ai_image_prompt_generate,
)


def get_worker_settings():
    """
    返回 ARQ 配置类(arq 0.28 通过 create_worker 读取类属性构建 Worker)。
    create_worker 仅抽取 Worker.__init__ 支持的参数,其余忽略。
    """
    from plugin.arq import get_redis_settings

    class WorkerSettings:
        functions = [process_video, process_text, process_image, process_audio, process_digital, process_render, process_deconstruct, ai_recognize, ai_copy_generate, ai_image_prompt_generate]
        queue_name = config.ARQ_QUEUE_NAME
        redis_settings = get_redis_settings()
        on_startup = on_startup
        on_shutdown = on_shutdown
        max_jobs = config.ARQ_CONCURRENCY        # 并发数
        job_timeout = config.ARQ_JOB_TIMEOUT      # 单任务超时(秒)
        max_tries = config.ARQ_MAX_RETRIES        # 最大尝试次数(含首次)
        # 结果保留时长(秒)。backend 的 ai_recognize 要同步 await ARQ 返回值,
        # 必须在此显式设置:依赖默认值一旦为 0,结果键不落库,调用方只能拿到空结果
        keep_result = config.ARQ_KEEP_RESULT
        retry_jobs = True

    return WorkerSettings
