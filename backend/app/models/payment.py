# -*- coding: utf-8 -*-
'''
@文件    :payment.py
@说明    :支付订单模型(参考 ai-creator 项目设计)
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class UserPaymentModel(BaseModel, TimestampMixin):
    """支付订单表"""
    user_id = fields.BigIntField(description="下单用户Id")
    order_no = fields.CharField(max_length=64, unique=True, description="商户订单号")
    transaction_id = fields.CharField(max_length=64, null=True, description="渠道交易号(微信)")
    biz_type = fields.IntField(description="业务类型:1视频生成")
    package_name = fields.CharField(max_length=100, description="商品名称快照")
    amount = fields.DecimalField(max_digits=10, decimal_places=2, description="金额(元)")
    status = fields.IntField(default=1, description="状态:1待支付2已支付3已交付4已取消5退款中6已退款")
    gateway = fields.CharField(max_length=20, default="wechat", description="支付网关:wechat/mock")
    pay_time = fields.DatetimeField(null=True, description="支付完成时间")
    source = fields.JSONField(null=True, description="下单业务快照(模板/素材/文案)")
    request = fields.JSONField(null=True, description="渠道下单响应快照")
    response = fields.JSONField(null=True, description="渠道回调报文快照")
    remark = fields.CharField(max_length=255, default="", description="备注(退款原因等)")

    class Meta:
        table = "tb_user_payment"
        table_description = "支付订单表"


class PaymentPackageModel(BaseModel, TimestampMixin):
    """充值套餐表(额度包,后台可维护)"""
    name = fields.CharField(max_length=50, description="套餐名称")
    sub_title = fields.CharField(max_length=100, null=True, description="套餐副标题")
    credits = fields.IntField(description="到账额度(次)")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="售价(元)")
    tag = fields.CharField(max_length=20, null=True, description="角标文案(如推荐/热卖)")
    sort = fields.IntField(default=0, description="排序(倒序,越大越靠前)")
    active = fields.BooleanField(default=True, description="是否上架")

    class Meta:
        table = "tb_payment_package"
        table_description = "充值套餐表"
