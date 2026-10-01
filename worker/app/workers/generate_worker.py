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
from app.core.skill_runtime import register_builtin_skills, run_skill, publish_catalog
from app.core.skill_orchestrator import compile_plan, orchestrator


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


async def skills_run(ctx, name: str, instruction: str, params: dict):
    """技能运行时入口:执行 `/技能 <name> <instruction>` 并把标准产物写 Redis 供轮询。

    结果统一为 ToolResult 序列化体 {"content":..., "metadata":...},键 skill:{job_id};
    前端经 backend 的 /skill/<name>/result 轮询拿到与 /copy/result 一致形态的 status/result。
    """
    logger.info(f"[skills_run] start name={name}")
    # 懒注册内置技能(幂等),保证首个请求前 handler 已就位
    register_builtin_skills()
    # 注册后把目录写 Redis,作为 /skills 单一来源(backend 优先读,未就绪回退静态)
    await publish_catalog(ctx.get("redis"))
    result = await run_skill(name, instruction or "", params or {})
    try:
        redis = ctx.get("redis")
        if redis is not None:
            payload = json.dumps(
                {"content": result.content, "metadata": result.metadata},
                ensure_ascii=False,
            )
            await redis.set(f"skill:{ctx.get('job_id')}", payload, ex=900)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[skills_run] 结果写 Redis 失败(不影响主流程): {exc}")
    logger.info(f"[skills_run] done name={name}")
    return {"content": result.content, "metadata": result.metadata}


async def skills_pipeline(ctx, goal: str, meta: dict, plan: dict = None):
    """技能流水线入口:把高层目标编译成计划并顺序执行,标准产物写 Redis 供轮询。

    - plan 为空 → 由 compile_plan(goal, meta) 取预声明模板(如 video-replicate-prep);
    - plan 非空 → 直接按调用方下发的声明式计划执行(灵活组合,但需调用方自证合法);
    结果键复用 skill:{job_id},前端用既有 /skill/<name>/result 轮询即可。
    """
    logger.info(f"[skills_pipeline] start goal={goal}")
    register_builtin_skills()
    await publish_catalog(ctx.get("redis"))
    skill_plan = None
    if plan:
        from app.core.skill_orchestrator import SkillPlan, SkillStep

        try:
            skill_plan = SkillPlan(
                name=plan.get("name", "adhoc"),
                description=plan.get("description", ""),
                steps=[SkillStep(**s) for s in plan.get("steps", [])],
                handoff=plan.get("handoff", ""),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[skills_pipeline] 下发计划非法,回退 compile_plan: {exc}")
    if skill_plan is None:
        skill_plan = await compile_plan(goal or "", meta or {})
    if skill_plan is None:
        # 无匹配计划 → 退化为单技能 run_skill(把 goal 当技能名)
        return await skills_run(ctx, goal or "", meta.get("instruction", ""), meta.get("params", {}))
    result = await orchestrator.run(skill_plan, meta or {})
    try:
        redis = ctx.get("redis")
        if redis is not None:
            payload = json.dumps(
                {"content": result.content, "metadata": result.metadata},
                ensure_ascii=False,
            )
            await redis.set(f"skill:{ctx.get('job_id')}", payload, ex=900)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[skills_pipeline] 结果写 Redis 失败(不影响主流程): {exc}")
    logger.info(f"[skills_pipeline] done plan={skill_plan.name}")
    return {"content": result.content, "metadata": result.metadata}
