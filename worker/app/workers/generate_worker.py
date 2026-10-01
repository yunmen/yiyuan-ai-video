# -*- coding: utf-8 -*-
'''
@文件    :generate_worker.py
@说明    :ARQ 任务入口(最薄层)— 每个生成类型一个任务方法,只解析入参转调对应 service
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.1
@说明    :透传 ctx(含 job_try),供 service 判定是否重试。
'''
import json

from app.core.plugin import logger
from app.services.video_service import VideoGenService
from app.services.text_service import TextGenService
from app.services.image_service import ImageGenService
from app.services.audio_service import AudioGenService
from app.services.digital_service import DigitalGenService
from app.services.render_service import RenderGenService
from app.services.deconstruct_service import DeconstructService
from app.services.ai_vision import classify_subjects
from app.services.ai_copy import generate as generate_copy
from app.services.image_prompt import generate as generate_image_prompt
from app.services.prompt_builder import build_gen_params_from_raw


async def process_video(ctx, task_id: int, notify_url: str, params: dict):
    logger.info(f"[process_video] task_id={task_id} start")
    # backend 现在下发「原始参数 + 序列化模板」;若未组装(prompt_context 缺失),
    # worker 在此完成提示词组装(backend 不再持有组装逻辑)。存量已组装任务原样跳过。
    if params.get("prompt_context") is None:
        params = build_gen_params_from_raw(params)
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


async def process_render(ctx, task_id: int, notify_url: str, params: dict):
    """视频换口播:上传视频 + 提示词 → 换声 / 换数字人 / 换场景(路线由 params.route 派生)"""
    logger.info(f"[process_render] task_id={task_id} route={params.get('route')} start")
    await RenderGenService().run(task_id, notify_url, params, ctx=ctx)
    logger.info(f"[process_render] task_id={task_id} done")


async def process_deconstruct(ctx, task_id: int, notify_url: str, params: dict):
    """带货视频复刻前置:拆解对标视频分镜(只分析,不产出媒体)"""
    logger.info(f"[process_deconstruct] task_id={task_id} start")
    await DeconstructService().run(task_id, notify_url, params, ctx=ctx)
    logger.info(f"[process_deconstruct] task_id={task_id} done")


async def ai_recognize(ctx, images, roles):
    """视觉识别(商品/参考图):backend 建单前委托 worker 执行,去掉 backend 的模型直连。

    返回多图分组识别结果 {person, product, scene, type, desc};任何失败返回空字典。
    结果经 ARQ 返回值回传 backend(backend 侧 await)。
    """
    logger.info(f"[ai_recognize] start images={len(images or [])}")
    result = await classify_subjects(images or [], roles or [])
    logger.info(f"[ai_recognize] done")
    return result


async def ai_copy_generate(ctx, template_title, category, title, subtitle, script, images, with_demand, roles):
    """AI 文案生成:backend 文案接口委托 worker 执行,去掉 backend 的模型直连。

    结果除经 ARQ 返回值回传外,**显式写入 Redis(键 ai_copy:{job_id})**,
    便于 backend 的 /copy/result 轮询接口非阻塞读取(前端异步轮询,请求不长时间阻塞)。
    """
    logger.info(f"[ai_copy_generate] start images={len(images or [])}")
    result = await generate_copy(
        template_title, category, title, subtitle, script, images, with_demand, roles
    )
    try:
        redis = ctx.get("redis")
        if redis is not None:
            payload = json.dumps(result, ensure_ascii=False)
            await redis.set(f"ai_copy:{ctx.get('job_id')}", payload, ex=900)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_copy_generate] 结果写 Redis 失败(不影响主流程): {exc}")
    logger.info(f"[ai_copy_generate] done")
    return result


async def ai_image_prompt_generate(ctx, narrations, style=None, min_words=50, max_words=100):
    """AI 图片提示词生成:backend 接口委托 worker 执行,去掉 backend 的模型直连。

    结果除经 ARQ 返回值回传外,**显式写入 Redis(键 ai_image_prompt:{job_id})**,
    便于 backend 的 /image-prompt/result 轮询接口非阻塞读取(前端异步轮询,请求不长时间阻塞)。
    """
    logger.info(f"[ai_image_prompt_generate] start narrations={len(narrations or [])}")
    result = await generate_image_prompt(narrations, style, min_words, max_words)
    try:
        redis = ctx.get("redis")
        if redis is not None:
            payload = json.dumps(result, ensure_ascii=False)
            await redis.set(f"ai_image_prompt:{ctx.get('job_id')}", payload, ex=900)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_image_prompt_generate] 结果写 Redis 失败(不影响主流程): {exc}")
    logger.info(f"[ai_image_prompt_generate] done")
    return result
