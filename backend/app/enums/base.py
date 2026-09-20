from app.enums import unique, Enum, StrEnum, IntEnum, StrCustomEnum, IntCustomEnum
from typing import Dict


@unique
class EnvironmentEnum(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


@unique
class ClientRoleEnum(StrCustomEnum):
    """客户端角色枚举类"""
    ADMIN = ("admin", "管理员")
    USER = ("user", "普通用户")
    OTHER = ("other", "其他来源")


@unique
class ResultCodeEnum(IntCustomEnum):
    """响应状态码"""
    SUCCESS = (1, "操作成功")
    FAIL = (0, "操作失败")
    AUTH = (9, "未授权")
    ERROR = (-1, "内部服务器错误")


@unique
class LoginTypeEnum(IntCustomEnum):
    """登录类型"""
    PASSWORD = (1, "账号密码登录")                # 账号密码登录
    CODE = (2, "手机号验证码登录")                   # 手机号验证码登录
    WECHAT = (3, "微信登录")                   # 手机号验证码登录


