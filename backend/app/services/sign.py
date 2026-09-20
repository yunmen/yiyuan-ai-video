# -*- coding: utf-8 -*-
'''
@文件    :sign.py
@说明    :每日签到Service(签到送额度,额度数由系统配置 sign.daily_credits 控制)
@时间    :2026/09/20 19:20:00
@作者    :一源AI
@版本    :1.0
'''
from datetime import date, timedelta
from typing import Dict, Optional

from fastapi.exceptions import HTTPException
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.models.account import UserSignModel
from app.cruds.system_config import crud as config_crud
from app.services.credit import service as credit_service
from app.enums.business import CreditLogTypeEnum

DEFAULT_DAILY_CREDITS = 1


class Service:
    async def _daily_credits(self) -> int:
        """每日签到赠送额度:读 DB 配置 sign.daily_credits,兜底 1"""
        obj = await config_crud.get_by_key("sign.daily_credits")
        try:
            return max(0, int(obj.value)) if obj and obj.value else DEFAULT_DAILY_CREDITS
        except (TypeError, ValueError):
            return DEFAULT_DAILY_CREDITS

    async def _streak(self, user_id: int, today: date) -> int:
        """本次签到后的连续天数:昨天签过则在昨日基础上 +1,否则重新从 1 开始"""
        yesterday = await UserSignModel.get_or_none(user_id=user_id, sign_date=today - timedelta(days=1))
        if yesterday:
            return (yesterday.streak or 1) + 1
        return 1

    async def status(self, user_id: int) -> Dict:
        """今日签到状态 + 连续天数 + 可领取额度"""
        today = date.today()
        today_sign = await UserSignModel.get_or_none(user_id=user_id, sign_date=today)
        yesterday = await UserSignModel.get_or_none(user_id=user_id, sign_date=today - timedelta(days=1))
        streak = today_sign.streak if today_sign else (yesterday.streak if yesterday else 0)
        return {
            "signed": bool(today_sign),
            "streak": streak or 0,
            "credits": today_sign.credits if today_sign else await self._daily_credits(),
            "daily_credits": await self._daily_credits(),
            "sign_date": today.strftime("%Y-%m-%d"),
        }

    async def sign(self, user_id: int) -> Dict:
        """每日签到:送额度并写签到记录(同一天重复签到直接返回已领取)"""
        today = date.today()
        exist = await UserSignModel.get_or_none(user_id=user_id, sign_date=today)
        if exist:
            raise HTTPException(status_code=200, detail="今日已签到,明天再来")

        credits = await self._daily_credits()
        if credits <= 0:
            raise HTTPException(status_code=200, detail="签到奖励未开启")
        streak = await self._streak(user_id, today)
        try:
            # 签到记录与额度发放同事务,避免「记录了没发额度 / 发了额度没记录」
            async with in_transaction():
                await UserSignModel.create(
                    user_id=user_id, sign_date=today, credits=credits, streak=streak,
                )
                await credit_service.grant(
                    user_id, credits,
                    log_type=CreditLogTypeEnum.GRANT.value,
                    remark=f"每日签到奖励(连续 {streak} 天)",
                )
        except IntegrityError:
            # 并发重复提交:唯一索引兜底
            raise HTTPException(status_code=200, detail="今日已签到,明天再来")
        return {"credits": credits, "streak": streak}

    async def logs(self, user_id: int, limit: int = 30) -> list:
        """最近签到记录"""
        rows = await UserSignModel.filter(user_id=user_id).order_by("-sign_date").limit(limit).all()
        return [row.to_dict() for row in rows]


service = Service()
