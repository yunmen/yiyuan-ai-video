# -*- coding: utf-8 -*-
'''
@文件    :credit.py
@说明    :用户额度Service(每日免费额度重置/消耗扣减/流水)
@时间    :2026/09/20 10:00:00
@作者    :AI
@版本    :1.0
'''

from datetime import date, datetime, time
from typing import Dict, List, Tuple
from tortoise.expressions import F, Q
from tortoise.transactions import atomic, in_transaction
from fastapi.exceptions import HTTPException
from app.models.account import UserModel, CreditLogModel
from app.cruds.system_config import crud as config_crud
from app.enums.business import CreditLogTypeEnum
from app.schemas.credit import LogQuerySchema
from app.services.cost_rules import settle_refund

DEFAULT_DAILY_FREE = 3


class Service:
    async def _daily_free(self) -> int:
        """每日免费额度:读 DB 配置 gen.daily_free_credits,兜底 3"""
        obj = await config_crud.get_by_key("gen.daily_free_credits")
        try:
            return max(0, int(obj.value)) if obj and obj.value else DEFAULT_DAILY_FREE
        except (TypeError, ValueError):
            return DEFAULT_DAILY_FREE

    async def _ensure_daily_reset(self, user: UserModel) -> UserModel:
        """跨天重置免费额度(登录后首次查询/消耗时触发)"""
        today = date.today()
        if user.last_reset_date == today:
            return user
        daily_free = await self._daily_free()
        old_free = user.free_credits or 0
        user.free_credits = daily_free
        user.last_reset_date = today
        await user.save(update_fields=["free_credits", "last_reset_date", "update_time"])
        delta = daily_free - old_free
        if delta != 0:
            await self._write_log(
                user_id=user.id, change=delta,
                balance=user.free_credits + (user.credits or 0),
                log_type=CreditLogTypeEnum.RESET.value,
                remark=f"每日免费额度重置为 {daily_free} 次",
            )
        return user

    async def _write_log(self, *, user_id: int, change: int, balance: int,
                         log_type: str, task_id: int = None, remark: str = "") -> CreditLogModel:
        return await CreditLogModel.create(
            user_id=user_id, change=change, balance=balance,
            type=log_type, task_id=task_id, remark=remark,
        )

    async def balance(self, user_id: int) -> Dict:
        """额度总览:剩余额度 + 今日已用"""
        user = await UserModel.get_or_none(id=user_id)
        if not user:
            raise HTTPException(status_code=200, detail="用户不存在")
        user = await self._ensure_daily_reset(user)
        today_start = datetime.combine(date.today(), time.min)
        used_logs = await CreditLogModel.filter(
            user_id=user_id, type=CreditLogTypeEnum.CONSUME.value,
            create_time__gte=today_start,
        ).all()
        today_used = sum(-log.change for log in used_logs if log.change < 0)
        daily_free = await self._daily_free()
        return {
            "free_credits": user.free_credits,
            "credits": user.credits,
            "total": (user.free_credits or 0) + (user.credits or 0),
            "daily_free": daily_free,
            "today_used": today_used,
        }

    @atomic()
    async def consume(self, user_id: int, cost: int = 1, remark: str = "生成消耗") -> int:
        """扣减额度:优先免费额度,再扣付费额度;不足抛业务异常(扣减+流水同事务)

        行锁串行化同一用户的并发扣减,避免超额扣成负数。
        返回流水 Id,调用方建单后可回填 task_id。
        """
        # 行锁(必须在事务内):同一用户并发建单时依次扣减
        user = await UserModel.select_for_update().get_or_none(id=user_id)
        if not user:
            raise HTTPException(status_code=200, detail="用户不存在")
        user = await self._ensure_daily_reset(user)
        total = (user.free_credits or 0) + (user.credits or 0)
        if total < cost:
            raise HTTPException(status_code=200, detail="额度不足,请充值后继续使用")
        free_use = min(user.free_credits, cost)
        user.free_credits -= free_use
        user.credits -= (cost - free_use)
        await user.save(update_fields=["free_credits", "credits", "update_time"])
        log = await self._write_log(
            user_id=user.id, change=-cost,
            balance=user.free_credits + user.credits,
            log_type=CreditLogTypeEnum.CONSUME.value,
            remark=remark,
        )
        return log.id

    async def attach_task(self, log_id: int, task_id: int) -> None:
        """把消耗流水关联到具体生成任务"""
        if log_id:
            await CreditLogModel.filter(id=log_id).update(task_id=task_id)

    @atomic()
    async def grant(self, user_id: int, amount: int, log_type: str = CreditLogTypeEnum.RECHARGE.value,
                    remark: str = "充值到账", task_id: int = None) -> None:
        """增加付费额度(充值/赠送/失败返还)

        行锁 + 读回最新余额,避免并发充值/签到时的更新丢失。
        """
        user = await UserModel.select_for_update().get_or_none(id=user_id)
        if not user:
            raise HTTPException(status_code=200, detail="用户不存在")
        # 先做跨天重置再发放:否则流水里的「余额」用的是重置前的旧免费额度,与总览对不上
        user = await self._ensure_daily_reset(user)
        await UserModel.filter(id=user_id).update(
            credits=F("credits") + amount, update_time=datetime.now()
        )
        await user.refresh_from_db(fields=["credits", "free_credits"])
        await self._write_log(
            user_id=user.id, change=amount,
            balance=(user.free_credits or 0) + user.credits,
            log_type=log_type, remark=remark, task_id=task_id,
        )

    async def refund_consume_log(self, log_id: int, remark: str = "建单失败,额度已退回") -> int:
        """按**消耗流水**原路退回(返回退回数量)

        场景:额度已扣、但后续步骤失败(建单/入队异常)。此时流水还没关联任务
        (task_id 为空),`refund_by_task` 按 task_id 找流水的方式用不上,所以单独提供入口。
        幂等:只对 change < 0 的消耗流水动作,重复调用不会重复退。
        """
        if not log_id:
            return 0
        log = await CreditLogModel.get_or_none(id=log_id)
        if not log or (log.change or 0) >= 0:
            return 0
        amount = abs(int(log.change))
        await self.grant(
            log.user_id, amount,
            log_type=CreditLogTypeEnum.REFUND.value,
            remark=remark, task_id=log.task_id,
        )
        return amount

    async def refund_by_task(self, task_id: int, user_id: int = None) -> int:
        """生成失败返还额度:按 task_id 找回消耗流水并原路返还

        幂等:只返还「累计消耗 - 累计已返还」的差额,已返还过的部分不会重复发放
        (支持「重新生成 → 再次失败」的多次消耗场景)。
        **结算返还(SETTLE)同样计入已返还**:否则「成功结算 → 重新生成 → 失败」
        会把已退回的额度再退一次。
        返回本次返还的额度数(0 表示无需返还)。
        """
        if not task_id:
            return 0
        # 计算与发放放在同一事务内,降低并发回调重复返还的概率
        async with in_transaction():
            consume_logs = await CreditLogModel.filter(
                task_id=task_id, type=CreditLogTypeEnum.CONSUME.value, change__lt=0,
            ).all()
            if not consume_logs:
                return 0
            refund_logs = await CreditLogModel.filter(
                task_id=task_id,
                type__in=[CreditLogTypeEnum.REFUND.value, CreditLogTypeEnum.SETTLE.value],
            ).all()
            consumed = sum(-log.change for log in consume_logs)
            refunded = sum(log.change for log in refund_logs if log.change > 0)
            amount = consumed - refunded
            if amount <= 0:
                return 0  # 已全部返还
            await self.grant(
                user_id=user_id or consume_logs[0].user_id,
                amount=amount,
                log_type=CreditLogTypeEnum.REFUND.value,
                remark="生成失败,额度已返还",
                task_id=task_id,
            )
        return amount

    async def settle_by_task(self, task_id: int, user_id: int, actual_cost: int) -> int:
        """结算返还:预扣按预估,成功后按实际用量结算,多扣的部分退回

        与 refund_by_task 共用同一套「消耗 - 已返还」差额计算,幂等且不会超退。
        actual_cost 由 worker 回调的 usage.cost 提供;未提供(或 >= 剩余)时不动作。
        返回本次返还额度数(0 表示无需返还)。
        """
        if not task_id or not user_id or actual_cost is None:
            return 0
        try:
            actual = max(0, int(actual_cost))
        except (TypeError, ValueError):
            return 0
        async with in_transaction():
            consume_logs = await CreditLogModel.filter(
                task_id=task_id, type=CreditLogTypeEnum.CONSUME.value, change__lt=0,
            ).all()
            if not consume_logs:
                return 0
            refund_logs = await CreditLogModel.filter(
                task_id=task_id,
                type__in=[CreditLogTypeEnum.REFUND.value, CreditLogTypeEnum.SETTLE.value],
            ).all()
            consumed = sum(-log.change for log in consume_logs)
            refunded = sum(log.change for log in refund_logs if log.change > 0)
            # 剩余(尚未退回的部分) - 实际用量 = 该退的差额;实际用量更大时不动
            amount = settle_refund(consumed, refunded, actual)
            if amount <= 0:
                return 0
            await self.grant(
                user_id=user_id, amount=amount,
                log_type=CreditLogTypeEnum.SETTLE.value,
                remark="按实际用量结算,多扣额度已返还",
                task_id=task_id,
            )
        return amount

    async def admin_user_list(self, payload) -> Tuple[int, List[Dict]]:
        """管理端:用户额度列表(手机号/昵称模糊搜索)"""
        search = Q()
        if getattr(payload, "keyword", None):
            search &= Q(account__icontains=payload.keyword) | Q(nickname__icontains=payload.keyword)
        total = await UserModel.filter(search).count()
        rows = await UserModel.filter(search).order_by("-id").offset(
            (payload.pageNum - 1) * payload.pageSize
        ).limit(payload.pageSize).all()
        result = []
        for user in rows:
            result.append({
                "id": user.id,
                "account": user.account,
                "nickname": user.nickname,
                "free_credits": user.free_credits,
                "credits": user.credits,
                "total": (user.free_credits or 0) + (user.credits or 0),
                "status": user.status,
                "create_time": user.create_time.strftime("%Y-%m-%d %H:%M:%S") if user.create_time else None,
            })
        return total, result

    async def admin_logs(self, user_id: int, payload: LogQuerySchema) -> Tuple[int, List[Dict]]:
        """管理端:查看指定用户流水"""
        return await self.logs(user_id, payload)

    async def logs(self, user_id: int, payload: LogQuerySchema) -> Tuple[int, List[Dict]]:
        """流水分页"""
        search = Q(user_id=user_id)
        if payload.type:
            search &= Q(type=payload.type)
        query = CreditLogModel.filter(search)
        total = await query.count()
        rows = await query.offset((payload.pageNum - 1) * payload.pageSize).limit(
            payload.pageSize
        ).order_by("-create_time")
        result = []
        label_map = {e.value: e.label for e in CreditLogTypeEnum}
        for row in rows:
            item = row.to_dict()
            item["type_label"] = label_map.get(row.type, row.type)
            result.append(item)
        return total, result


service = Service()
