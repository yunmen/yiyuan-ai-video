# -*- coding: utf-8 -*-
'''
@文件    :account.py
@说明    :C端用户模型
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class UserModel(BaseModel, TimestampMixin):
    """C端用户表"""
    account = fields.CharField(max_length=20, unique=True, description="账号(手机号)")
    # 手机号与可修改的登录名分开保存，改名后仍可使用原手机号接收验证码。
    phone = fields.CharField(max_length=11, null=True, unique=True, description="绑定手机号")
    nickname = fields.CharField(max_length=30, default="", description="昵称")
    avatar = fields.CharField(max_length=255, null=True, description="头像")
    password = fields.CharField(max_length=128, description="密码")
    status = fields.BooleanField(default=True, description="是否启用")
    free_credits = fields.IntField(default=3, description="每日免费额度(跨天重置)")
    credits = fields.IntField(default=0, description="付费额度(充值/赠送,永久有效)")
    last_reset_date = fields.DateField(null=True, description="免费额度最近重置日期")

    class Meta:
        table = "tb_user"
        table_description = "C端用户表"


class UserSignModel(BaseModel, TimestampMixin):
    """C端用户每日签到表(user_id + sign_date 唯一,防重复签到)"""
    user_id = fields.BigIntField(index=True, description="用户Id")
    sign_date = fields.DateField(description="签到日期")
    credits = fields.IntField(default=1, description="本次获得额度")
    streak = fields.IntField(default=1, description="连续签到天数(含本次)")

    class Meta:
        table = "tb_user_sign"
        table_description = "C端用户签到表"
        unique_together = (("user_id", "sign_date"),)


class CreditLogModel(BaseModel, TimestampMixin):
    """C端用户额度流水表"""
    user_id = fields.BigIntField(index=True, description="用户Id")
    change = fields.IntField(description="变动值(正增负减)")
    balance = fields.IntField(description="变动后余额(免费+付费)")
    type = fields.CharField(max_length=20, description="类型:reset每日重置/consume消耗/recharge充值/grant赠送/refund失败返还")
    task_id = fields.BigIntField(null=True, description="关联生成任务Id")
    remark = fields.CharField(max_length=255, default="", description="备注")

    class Meta:
        table = "tb_credit_log"
        table_description = "C端用户额度流水表"


class UserInvitationModel(BaseModel, TimestampMixin):
    """每个账号只有一个邀请码，注册时记录邀请关系及实际发放额度。"""

    user_id = fields.BigIntField(unique=True, description="邀请码所属用户Id")
    code = fields.CharField(max_length=8, unique=True, description="随机邀请码")
    inviter_id = fields.BigIntField(null=True, index=True, description="注册时的邀请人Id")
    reward_amount = fields.IntField(default=0, description="注册时双方各获得的永久额度")

    class Meta:
        table = "tb_user_invitation"
        table_description = "用户邀请码与注册奖励记录"
