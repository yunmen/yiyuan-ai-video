# -*- coding: utf-8 -*-
'''
@文件    :business.py
@说明    :业务枚举
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from app.enums import unique, StrCustomEnum, IntCustomEnum


@unique
class TaskStatusEnum(StrCustomEnum):
    """生成任务状态"""
    PROCESSING = ("processing", "生成中")
    SUCCESS = ("success", "生成成功")
    FAILED = ("failed", "生成失败")


@unique
class TemplateSortEnum(IntCustomEnum):
    """模板排序方式"""
    HOT = (1, "最热")
    NEW = (2, "最新")
    USED = (3, "最多使用")


@unique
class DeviceTypeEnum(StrCustomEnum):
    """设备类型"""
    DESKTOP = ("desktop", "桌面端")
    MOBILE = ("mobile", "移动端")


@unique
class CreditLogTypeEnum(StrCustomEnum):
    """额度流水类型"""
    RESET = ("reset", "每日重置")
    CONSUME = ("consume", "生成消耗")
    RECHARGE = ("recharge", "充值到账")
    GRANT = ("grant", "系统赠送")
    REFUND = ("refund", "失败返还")
    # 预算前置:预扣按预估,任务成功后按实际用量结算,多扣部分退回
    SETTLE = ("settle", "结算返还")
