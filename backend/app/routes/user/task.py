# -*- coding: utf-8 -*-
'''
@文件    :task.py
@说明    :用户端-生成任务接口(免登录可创建;登录后按归属校验)
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.1
'''
import hmac
from typing import Optional

from fastapi import APIRouter, Body, Depends, Header
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationUserToken, OptionalUserToken
from app.schemas.generate_task import (
    CacheQuery,
    CacheSchema,
    CreateSchema,
    EstimateSchema,
    QuerySchema,
    CallbackSchema,
    ImageCreateSchema,
    AudioCreateSchema,
    TextCreateSchema,
    DigitalCreateSchema,
    PrecheckSchema,
    DeconstructSchema,
    CheckpointSchema,
    CheckpointQuery,
)
from app.services.generate_task import service
from app.services.asset_cache import service as cache_service
from app.core.response import Success, AUTH
from app.settings import config


router = APIRouter(route_class=OperationLogRoute)


@router.post("/callback", summary="Worker 回写任务状态(内部接口)")
async def task_callback(
    payload: CallbackSchema,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if not hmac.compare_digest(x_worker_token or "", config.WORKER_CALLBACK_SECRET):
        return AUTH(msg="非法回调请求")
    await service.callback(payload)
    return Success()


@router.get("/checkpoint", summary="Worker 拉取断点检查点(内部接口)")
async def task_checkpoint_get(
    task_id: int,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if not hmac.compare_digest(x_worker_token or "", config.WORKER_CALLBACK_SECRET):
        return AUTH(msg="非法回调请求")
    data = await service.get_checkpoint(task_id)
    return Success(data=data)


@router.post("/checkpoint", summary="Worker 回写断点检查点(内部接口)")
async def task_checkpoint(
    payload: CheckpointSchema,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if not hmac.compare_digest(x_worker_token or "", config.WORKER_CALLBACK_SECRET):
        return AUTH(msg="非法回调请求")
    await service.update_checkpoint(payload)
    return Success()


@router.get("/cache", summary="Worker 读取资产缓存(内部接口)")
async def task_cache_get(
    cache_key: str,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    """命中返回 content;未命中/过期返回 data=None(worker 侧按未命中处理,正常生成)"""
    if not hmac.compare_digest(x_worker_token or "", config.WORKER_CALLBACK_SECRET):
        return AUTH(msg="非法回调请求")
    data = await cache_service.get(cache_key)
    return Success(data=data)


@router.post("/cache", summary="Worker 回写资产缓存(内部接口)")
async def task_cache_set(
    payload: CacheSchema,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if not hmac.compare_digest(x_worker_token or "", config.WORKER_CALLBACK_SECRET):
        return AUTH(msg="非法回调请求")
    await cache_service.set(
        payload.cache_key, payload.asset_type, payload.content,
        task_type=payload.task_type, meta=payload.meta,
    )
    return Success()


@router.post("/estimate", summary="预估本次生成消耗(下单前可见花费)")
async def task_estimate(payload: EstimateSchema, g=Depends(OptionalUserToken)):
    data = await service.estimate(payload, user=g)
    return Success(data=data)


@router.post("/create", summary="创建生成任务")
async def task_create(payload: CreateSchema, g=Depends(OptionalUserToken)):
    # 归属以登录态为准(忽略 body 传入的 user_id,防止越权归属)
    data = await service.create(payload, user=g)
    return Success(data=data)


@router.post("/deconstruct", summary="拆解对标视频分镜(带货视频复刻前置)")
async def task_deconstruct(payload: DeconstructSchema, g=Depends(OptionalUserToken)):
    # 拆解只做分析,不消耗生成额度;结果由 worker 经 result_text 回写,前端轮询 /detail 读取
    data = await service.deconstruct(payload, user=g)
    return Success(data=data)


@router.post("/list", summary="我的作品", dependencies=[Depends(DeepValidationUserToken)])
async def task_list(payload: QuerySchema, g=Depends(DeepValidationUserToken)):
    total, data = await service.my_list(g.id, payload)
    return Success(data=data, total=total)


@router.post("/delete", summary="删除作品", dependencies=[Depends(DeepValidationUserToken)])
async def task_delete(
    id: int = Body(..., description="任务Id", embed=True),
    g=Depends(DeepValidationUserToken)
):
    await service.delete_by_user(id, g.id)
    return Success()


@router.post("/precheck", summary="建单前预检(返回结构化缺失项,供前端引导补素材)")
async def task_precheck(data: PrecheckSchema):
    result = await service.precheck(data)
    return Success(data=result)


@router.post("/detail", summary="任务详情")
async def task_detail(
    id: int = Body(..., description="任务Id", embed=True),
    g=Depends(OptionalUserToken)
):
    data = await service.detail(id, user=g)
    return Success(data=data)


@router.post("/regenerate", summary="重新生成(可带 style 换效果)")
async def task_regenerate(
    id: int = Body(..., description="任务Id", embed=True),
    creative_level: Optional[str] = Body(None, description="换效果:创意档位(不传=沿用原任务)", embed=True),
    hook_boost: Optional[str] = Body(None, description="换效果:开头钩子(不传=沿用原任务)", embed=True),
    g=Depends(OptionalUserToken)
):
    # style 只承载"效果"类旋钮(小白的「换个效果」入口),不开放素材/时长等口径类参数
    style = {
        "creative_level": creative_level,
        "hook_boost": hook_boost,
    }
    data = await service.regenerate(id, user=g, style=style)
    return Success(data=data)


@router.post("/regenerate_segment", summary="局部重跑(改一句台词重生成,预留接口)")
async def task_regenerate_segment(
    id: int = Body(..., description="任务Id", embed=True),
    segment_index: int = Body(..., description="目标分段下标(从 0 开始)", embed=True),
    new_text: str = Body("", description="新口播文案", embed=True),
    g=Depends(OptionalUserToken),
):
    data = await service.regenerate_segment(id, segment_index, new_text, user=g)
    return Success(data=data)


@router.post("/resume", summary="断点续跑(从检查点继续,不重复扣额度)")
async def task_resume(
    id: int = Body(..., description="任务Id", embed=True),
    g=Depends(OptionalUserToken)
):
    data = await service.resume(id, user=g)
    return Success(data=data)


@router.post("/image/create", summary="创建图片生成任务")
async def task_image_create(payload: ImageCreateSchema, g=Depends(OptionalUserToken)):
    data = await service.create_image(payload, user=g)
    return Success(data=data)


@router.post("/audio/create", summary="创建音频生成任务(语音/背景音乐)")
async def task_audio_create(payload: AudioCreateSchema, g=Depends(OptionalUserToken)):
    data = await service.create_audio(payload, user=g)
    return Success(data=data)


@router.post("/text/create", summary="创建文本生成任务")
async def task_text_create(payload: TextCreateSchema, g=Depends(OptionalUserToken)):
    data = await service.create_text(payload, user=g)
    return Success(data=data)


@router.post("/digital/create", summary="创建数字人口播任务")
async def task_digital_create(payload: DigitalCreateSchema, g=Depends(OptionalUserToken)):
    data = await service.create_digital(payload, user=g)
    return Success(data=data)
