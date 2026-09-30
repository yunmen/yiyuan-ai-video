# -*- coding: utf-8 -*-
'''
@文件    :feedback.py
@说明    :用户端-意见反馈接口(免登录)
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from fastapi import APIRouter
from app.core.routeclass import OperationLogRoute
from app.schemas.feedback import FeedbackCreateSchema
from app.services.feedback import service
from app.core.response import Success


router = APIRouter(route_class=OperationLogRoute)


@router.post("/create", summary="提交意见反馈")
async def feedback_create(payload: FeedbackCreateSchema):
    # 免登录提交:匿名用户也能反馈,登录态下可由前端在 contact 中附带账号或由后续扩展写入 user_id
    feedback_id = await service.create(payload.content, payload.contact)
    return Success(data={"id": feedback_id}, msg="反馈已提交,感谢你的建议")
