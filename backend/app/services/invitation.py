"""邀请码与注册奖励：邀请关系和双方入账必须随新账号一起提交或回滚。"""
import secrets

from fastapi.exceptions import HTTPException
from tortoise.functions import Sum
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.cruds.system_config import crud as config_crud
from app.models.account import UserInvitationModel, UserModel
from app.services.credit import service as credit_service


# 运营可通过业务配置修改，0 表示暂停奖励；奖励进入永久额度。
DEFAULT_INVITE_CREDITS = 10
INVITE_REWARD_KEY = "account.invite_reward_credits"


class Service:
    """为老用户按需生成邀请码，为新用户一次性绑定邀请人。"""

    async def reward_amount(self) -> int:
        """读取双方各自奖励，错误配置拒绝发奖，避免静默产生错误账目。"""
        record = await config_crud.get_by_key(INVITE_REWARD_KEY)
        if not record:
            return DEFAULT_INVITE_CREDITS
        try:
            amount = int(record.value)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=200, detail="邀请奖励配置暂不可用") from exc
        if not 0 <= amount <= 100000:
            raise HTTPException(status_code=200, detail="邀请奖励配置暂不可用")
        return amount

    async def identity(self, user_id: int) -> UserInvitationModel:
        """唯一用户约束保证重复请求只产生一个稳定邀请码。"""
        record = await UserInvitationModel.filter(user_id=user_id).first()
        if record:
            return record
        try:
            return await self._create_identity(user_id)
        except IntegrityError:
            # 并发首次打开时复用另一个请求已创建的身份。
            return await UserInvitationModel.get(user_id=user_id)

    async def _create_identity(self, user_id: int, inviter_id: int | None = None, amount: int = 0) -> UserInvitationModel:
        """随机码碰撞时重新生成；保存点避免冲突使整个 PostgreSQL 注册事务失效。"""
        for _ in range(5):
            try:
                async with in_transaction():
                    return await UserInvitationModel.create(
                        user_id=user_id, code=secrets.token_hex(4).upper(),
                        inviter_id=inviter_id, reward_amount=amount,
                    )
            except IntegrityError:
                if await UserInvitationModel.filter(user_id=user_id).exists():
                    raise
        raise HTTPException(status_code=200, detail="邀请码生成繁忙，请稍后重试")

    async def apply_registration(self, user_id: int, raw_code: str | None) -> None:
        """只允许在注册事务内调用；唯一关系防止同一新账号重复领到奖励。"""
        code = (raw_code or "").strip().upper()
        if not code:
            return
        inviter = await UserInvitationModel.filter(code=code, deleted=False).first()
        if not inviter or inviter.user_id == user_id:
            raise HTTPException(status_code=200, detail="邀请码无效，请检查后重试")
        owner = await UserModel.filter(id=inviter.user_id, deleted=False, status=True).first()
        if not owner:
            raise HTTPException(status_code=200, detail="该邀请码暂不可用")
        # 此处使用 create 而非 update，账号唯一约束使重复绑定整体回滚。
        amount = await self.reward_amount()
        await self._create_identity(user_id, owner.id, amount)
        if amount:
            await credit_service.grant(owner.id, amount, log_type="grant", remark="邀请好友注册奖励")
            await credit_service.grant(user_id, amount, log_type="grant", remark="填写邀请码注册奖励")

    async def summary(self, user_id: int) -> dict:
        """返回本人邀请码与已成功邀请的总数、累计实际到账额度。"""
        identity = await self.identity(user_id)
        query = UserInvitationModel.filter(inviter_id=user_id, deleted=False)
        aggregate = await query.annotate(earned=Sum("reward_amount")).values("earned")
        return {
            "code": identity.code, "reward_amount": await self.reward_amount(),
            "invited_count": await query.count(),
            "earned_credits": int(aggregate[0]["earned"] or 0) if aggregate else 0,
        }


service = Service()
