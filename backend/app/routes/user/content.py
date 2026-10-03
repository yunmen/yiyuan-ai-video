# -*- coding: utf-8 -*-
'''
@文件    :content.py
@说明    :用户端-内容生成入口(对外的产品功能接口,不暴露内部技能/编排概念)。
         前端只看到产品功能(文案 / 图片提示词 / 语音 / 内容准备),
         具体由哪个 worker 技能(text-generation / image-generation / audio-synthesis /
         video-replicate-prep 流水线)执行,全部在服务端硬编码映射,绝不进入 URL 或响应,
         避免把内部实现细节暴露给终端用户与竞品。
         POST /content/copy         生成带货文案(映射 text-generation)
         POST /content/image-prompt 生成中文图片提示词(映射 image-generation)
         POST /content/voice        语音合成(映射 audio-synthesis)
         POST /content/prepare      内容准备流水线(映射 video-replicate-prep / video-prep 计划)
         POST /content/result       轮询异步产物(仅按 task_id,不含技能名)
         路由统一挂在 router 前缀 /content 下。
@时间    :2026/10/01
@作者    :一源AI
@版本    :1.0
'''
from typing import Dict, Optional

from fastapi import APIRouter, Body, Request

from app.core.routeclass import OperationLogRoute
from app.core.response import Success
from app.core import ratelimit


router = APIRouter(route_class=OperationLogRoute)

# 内容生成按 IP 限流,防止被刷模型额度
CONTENT_LIMIT_PER_MINUTE = 10

# 内部技能名(仅在服务端出现,严禁外泄到 URL / 响应 / 日志)
_SKILL_COPY = "text-generation"
_SKILL_IMAGE = "image-generation"
_SKILL_VOICE = "audio-synthesis"


@router.post("/copy", summary="生成带货文案(大标题/副标题/口播)")
async def content_copy(
    request: Request,
    instruction: str = Body("", description="自然语言指令(可选,缺字段时由模型解析补充)"),
    params: Optional[dict] = Body(None, description="结构化参数:template_title/category/title/subtitle/script/with_demand/images/roles"),
):
    """生成/润色三段带货文案,返回 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 text-generation 技能(ai_copy.generate),技能名不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_copy", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "文案生成请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(_SKILL_COPY, instruction, params or {})
    return Success(data=data)


@router.post("/image-prompt", summary="生成中文图片提示词")
async def content_image_prompt(
    request: Request,
    instruction: str = Body("", description="自然语言指令(可选)"),
    params: Optional[dict] = Body(None, description="结构化参数:narrations/style/min_words"),
):
    """根据口播/旁白生成逐镜中文图片提示词,返回 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 image-generation 技能,技能名不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_img", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "图片提示词生成请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(_SKILL_IMAGE, instruction, params or {})
    return Success(data=data)


@router.post("/voice", summary="语音合成(TTS)")
async def content_voice(
    request: Request,
    instruction: str = Body("", description="自然语言指令(可选)"),
    params: Optional[dict] = Body(None, description="结构化参数:text/voice/voice_reference/audio"),
):
    """文本转语音,返回音频直链 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 audio-synthesis 技能,技能名不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_voice", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "语音合成请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(_SKILL_VOICE, instruction, params or {})
    return Success(data=data)


@router.post("/prepare", summary="内容准备流水线(目标 → 多步骤内容生成)")
async def content_prepare(
    request: Request,
    goal: str = Body("", description="高层目标,如'复刻这段视频'"),
    meta: Optional[dict] = Body(None, description="计划上下文(用户侧元数据,intent/duration/reference_video 等)"),
    plan: Optional[dict] = Body(None, description="可选:调用方下发声明式计划(覆盖默认编译)"),
):
    """下发内容准备流水线到 worker 异步执行,返回 task_id 供前端轮询 /content/result。

    内部映射到 video-replicate-prep / video-prep 等计划模板,按顺序产出文案/图提示词/词锚点,
    技能与编排概念均不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_prep", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "内容准备请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_pipeline

    data = await enqueue_skill_pipeline(goal, meta or {}, plan)
    return Success(data=data)


@router.post("/result", summary="轮询内容生成结果(异步接口,前端轮询)")
async def content_result(
    request: Request,
    task_id: str = Body(..., embed=True, description="/content/* 返回的 task_id"),
):
    """轮询内容生成标准产物。

    返回 data.status:
      - done     : 执行完成,data.result 为产物序列化体 {content, metadata}
      - pending  : 任务仍在执行中(继续轮询)
      - not_found: 任务不存在或已过期
    """
    from app.core.task_queue import read_skill_result

    status, data = await read_skill_result(task_id)
    if status == "done":
        return Success(data={"status": "done", "result": data})
    if status == "not_found":
        return Success(data={"status": "not_found"})
    return Success(data={"status": "pending"})
