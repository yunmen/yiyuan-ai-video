# -*- coding: utf-8 -*-
'''
@文件    :feedback.py
@说明    :意见反馈业务
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from app.models.feedback import FeedbackModel


class FeedbackService:
    """意见反馈:落库用户提交内容,供运营查看处理(免登录,匿名可提交)"""

    async def create(self, content: str, contact: str = "", user_id: int = None) -> int:
        obj = await FeedbackModel.create(
            content=content,
            contact=contact or None,
            user_id=user_id,
        )
        return obj.id


service = FeedbackService()
