# -*- coding: utf-8 -*-
'''
@文件    :generate_worker.py
@说明    :ARQ 任务入口(最薄层)— 每个生成类型一个任务方法,只解析入参转调对应 service
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.1
@说明    :透传 ctx(含 job_try),供 service 判定是否重试。
'''
from app.core.plugin import logger
from app.services.video_service import VideoGenService
from app.services.text_service import TextGenService
from app.services.image_service import ImageGenService
from app.services.audio_service import AudioGenService
from app.services.digital_service import DigitalGenService


async def process_video(ctx, task_id: int, notify_url: str, params: dict):
    logger.info(f"[process_video] task_id={task_id} start")
    await VideoGenService().run(task_id, notify_url, params, ctx=ctx)
    logger.info(f"[process_video] task_id={task_id} done")


async def process_text(ctx, task_id: int, notify_url: str, params: dict):
    logger.info(f"[process_text] task_id={task_id} start")
    await TextGenService().run(task_id, notify_url, params, ctx=ctx)
    logger.info(f"[process_text] task_id={task_id} done")


async def process_image(ctx, task_id: int, notify_url: str, params: dict):
    logger.info(f"[process_image] task_id={task_id} start")
    await ImageGenService().run(task_id, notify_url, params, ctx=ctx)
    logger.info(f"[process_image] task_id={task_id} done")


async def process_audio(ctx, task_id: int, notify_url: str, params: dict):
    logger.info(f"[process_audio] task_id={task_id} start")
    await AudioGenService().run(task_id, notify_url, params, ctx=ctx)
    logger.info(f"[process_audio] task_id={task_id} done")


async def process_digital(ctx, task_id: int, notify_url: str, params: dict):
    logger.info(f"[process_digital] task_id={task_id} start")
    await DigitalGenService().run(task_id, notify_url, params, ctx=ctx)
    logger.info(f"[process_digital] task_id={task_id} done")
