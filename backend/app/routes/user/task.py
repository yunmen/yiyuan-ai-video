# -*- coding: utf-8 -*-
'''
@文件    :task.py
@说明    :用户端-生成任务接口(免登录可创建;登录后按归属校验)
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.1
'''
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
    CheckpointSchema,
    CheckpointQuery,
)
from app.services.generate_task import service
from app.services.asset_cache import service as cache_service
from app.core.response import Success, Fail
from app.settings import config


router = APIRouter(route_class=OperationLogRoute)


@router.post("/callback", summary="Worker 回写任务状态(内部接口)")
async def task_callback(
    payload: CallbackSchema,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if x_worker_token != config.WORKER_CALLBACK_SECRET:
        return Fail(msg="非法回调请求")
    await service.callback(payload)
    return Success()


@router.get("/checkpoint", summary="Worker 拉取断点检查点(内部接口)")
async def task_checkpoint_get(
    task_id: int,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if x_worker_token != config.WORKER_CALLBACK_SECRET:
        return Fail(msg="非法回调请求")
    data = await service.get_checkpoint(task_id)
    return Success(data=data)


@router.post("/checkpoint", summary="Worker 回写断点检查点(内部接口)")
async def task_checkpoint(
    payload: CheckpointSchema,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if x_worker_token != config.WORKER_CALLBACK_SECRET:
        return Fail(msg="非法回调请求")
    await service.update_checkpoint(payload)
    return Success()


@router.get("/cache", summary="Worker 读取资产缓存(内部接口)")
async def task_cache_get(
    cache_key: str,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    """命中返回 content;未命中/过期返回 data=None(worker 侧按未命中处理,正常生成)"""
    if x_worker_token != config.WORKER_CALLBACK_SECRET:
        return Fail(msg="非法回调请求")
    data = await cache_service.get(cache_key)
    return Success(data=data)


@router.post("/cache", summary="Worker 回写资产缓存(内部接口)")
async def task_cache_set(
    payload: CacheSchema,
    x_worker_token: str = Header(None, description="Worker 回调鉴权令牌"),
):
    if x_worker_token != config.WORKER_CALLBACK_SECRET:
        return Fail(msg="非法回调请求")
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


@router.post("/detail", summary="任务详情")
async def task_detail(
    id: int = Body(..., description="任务Id", embed=True),
    g=Depends(OptionalUserToken)
):
    data = await service.detail(id, user=g)
    return Success(data=data)


@router.post("/regenerate", summary="重新生成")
async def task_regenerate(
    id: int = Body(..., description="任务Id", embed=True),
    g=Depends(OptionalUserToken)
):
    data = await service.regenerate(id, user=g)
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
