# -*- coding: utf-8 -*-
'''
@文件    :payment.py
@说明    :支付Schema
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import Field, BaseModel
from typing import Optional, List, Dict
from decimal import Decimal
from app.schemas.base import BaseQuerySchema


class CreateOrderSchema(BaseModel):
    # 模板 Id 可选:普通生成(选平台模板视频)必传;视频复刻链路用户自带对标视频,无需模板。
    # 与生成建单 CreateSchema 保持一致;视频价格为统一价,与模板无关,故无模板不影响计费。
    template_id: Optional[int] = Field(None, description="模板Id(普通生成必传;视频复刻可不传)")
    materials: List[str] = Field(default_factory=list, description="素材URL列表")
    remark: Optional[str] = Field(None, description="文案备注(大标题/副标题/口播)")
    device: str = Field("desktop", description="设备类型")
    # 替换意图与素材角色映射:与生成建单完全一致,支付链路必须原样透传,
    # 否则付费任务会丢失"换产品/人物/场景"意图与一键三换的角色映射(实测付费后不生效)。
    intent: Optional[List[str]] = Field(None, description="替换意图(换产品/人物/场景,多选)")
    image_roles: Optional[Dict[str, str]] = Field(None, description="素材URL→角色映射(一键三换等多角色场景)")
    # 付费下单快照与额度建单保持一致:形态和真人策略必须保留到支付交付阶段。
    format: Optional[str] = Field(None, description="复刻目标形态(可选)")
    real_person_strategy: Optional[str] = Field(None, description="真人素材处理策略(auto/stylize/drop)")
    # 生成规格(时长/画幅/清晰度):与生成建单 CreateSchema 完全一致,支付链路必须原样透传。
    # 此前缺失导致付费用户选的规格在 orderCreate 被 Pydantic 静默丢弃,服务端访问 payload.duration
    # 还会抛 AttributeError → 整个下单接口 500(额度用户走 task.create 不受影响,故不易察觉)。
    duration: Optional[int] = Field(None, ge=1, le=60, description="时长(秒,可选)")
    ratio: Optional[str] = Field(None, description="画幅(可选):9:16/16:9/1:1/4:3/3:4")
    resolution: Optional[str] = Field(None, description="清晰度(可选):720P/1080P")


class RechargeOrderSchema(BaseModel):
    package_id: int = Field(..., description="充值套餐Id")
    device: str = Field("desktop", description="设备类型")


class PackageBaseSchema(BaseModel):
    name: str = Field(..., description="套餐名称")
    sub_title: Optional[str] = Field(None, description="套餐副标题")
    credits: int = Field(..., ge=1, description="到账额度(次)")
    price: Decimal = Field(..., ge=0, description="售价(元)")
    tag: Optional[str] = Field(None, description="角标文案(如推荐/热卖)")
    sort: int = Field(0, description="排序(倒序,越大越靠前)")
    active: bool = Field(True, description="是否上架")


class PackageCreateSchema(PackageBaseSchema):
    ...


class PackageUpdateSchema(PackageBaseSchema):
    id: int = Field(..., description="主键Id")


class PackageSaveSchema(PackageBaseSchema):
    id: Optional[int] = Field(None, description="主键Id(为空则新增)")


class OrderQuerySchema(BaseQuerySchema):
    status: Optional[int] = Field(None, description="订单状态")
    keyword: Optional[str] = Field(None, description="订单号/商品名模糊搜索")


class RefundSchema(BaseModel):
    order_no: str = Field(..., description="商户订单号")
    reason: Optional[str] = Field(None, description="退款原因")
