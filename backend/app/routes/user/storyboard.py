# -*- coding: utf-8 -*-
'''
@文件    :storyboard.py
@说明    :用户端-分镜/镜头接口(分镜级状态查询 / 镜头编辑)
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter, Body
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationUserToken, OptionalUserToken
from app.schemas.storyboard import ShotQuery, ShotUpdate
from app.services.storyboard import service
from app.core.response import Success, Fail

router = APIRouter(route_class=OperationLogRoute)


@router.post("/list", summary="查询任务的分镜/镜头列表")
async def storyboard_list(payload: ShotQuery, _=OptionalUserToken):
    """分镜级状态查询:返回分镜集与各镜头(逆推提示词/台词/生成状态/质检分数)"""
    data = await service.get_by_task(payload.task_id, payload.page_num, payload.page_size)
    return Success(data=data)


@router.post("/shot/update", summary="编辑单个镜头(提示词/台词/时长)")
async def shot_update(
    payload: ShotUpdate,
    _=DeepValidationUserToken,
):
    """编辑镜头提示词/台词/时长,供后续局部重跑使用(返回更新后的镜头)"""
    item = await service.update_shot(
        payload.task_id, payload.index, payload.prompt, payload.narration,
        payload.start_ms, payload.end_ms,
    )
    if not item:
        # 镜头不存在时按业务失败返回:避免前端把 code=1 误判为「已更新」(提示词其实没写进去)
        return Fail(msg="镜头不存在或不属于该任务")
    return Success(data=item)
