# -*- coding: utf-8 -*-
'''
@文件    :config.py
@说明    :环境配置
@时间    :2025/02/13 16:44:01
@作者    :睿
@版本    :1.0
'''

import os
import sys
import secrets
from typing import Dict, Any, Union, List
from pathlib import Path
from functools import lru_cache
from datetime import date
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from app.enums.base import EnvironmentEnum

# SECRET_KEY / WORKER_CALLBACK_SECRET 不再内置任何明文值。
# 缺失时:dev/test 由 _ensure_dev_secrets 自动生成临时密钥(重启失效,仅本地开发);
# prod 必须在 env/.env.prod 中显式配置,否则启动直接拒绝(见 _check_unsafe_defaults)。


class Settings(BaseSettings):
    """系统配置类"""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding="utf-8",
        case_sensitive=True,
        # 忽略 .env 中未在 Settings 声明的变量:避免运维随手加一个变量就导致服务启动失败
        extra="ignore",
    )

    ENVIRONMENT: EnvironmentEnum


    # ================================================= #
    # ******************* 服务器配置 ****************** #
    # ================================================= #
    SERVER_HOST: str         # 允许访问的IP地址
    SERVER_PORT: int         # 服务端口
    RELOAD: bool             # 是否自动重启
    FACTORY: bool            # 是否使用工厂函数
    WORKERS: int             # 启动进程数
    ACCESS_LOG: bool         # 是否开启访问日志


    # ================================================= #
    # ***************** 静态文件配置 ******************* #
    # ================================================= #
    STATIC_URL: str = "/static"  # 访问路由
    STATIC_PATH: str = "static"  # 文件路径
    STATIC_NAME: str = "static"   # 目录名


    # ================================================= #
    # ******************* API文档配置 ****************** #
    # ================================================= #
    DEBUG: bool = False                 # 是否开启调试模式
    TITLE: str                          # 文档标题
    VERSION: str                        # 版本号
    DESCRIPTION: str                    # 文档描述
    SUMMARY: str | None                 # 文档概述
    ROOT_PATH: str = ""                 # 根路径
    ROOT_PATH_IN_SERVERS: bool = False  # 是否在服务器中使用根路径
    SWAGGER_CSS_URL: Path = "static/swagger-ui/swagger-ui.css"
    SWAGGER_JS_URL: Path = "static/swagger-ui/swagger-ui-bundle.js"
    CUSTOM_CSS_URL: Path = "static/custom-ui/styles.css"
    CUSTOM_JS_URL: Path = "static/custom-ui/scripts.js"
    REDOC_JS_URL: Path = "static/redoc/redoc.standalone.js"
    FAVICON_URL: Path = "static/favicon.png"

    # ================================================= #
    # ******************* API安全配置 ****************** #
    # ================================================= #
    API_PREFIX: str = "/api"  # API前缀
    SECRET_KEY: str = ""  # JWT 密钥(dev/test 自动生成临时值,prod 必须在 env/.env.prod 配置)
    SECURITY_HEADER_NAME: str = "Authorization"
    SECURITY_HEADER_PREFIX: str = "Bearer"
    EXPIRE_TIME: int = 60 * 60 * 24 * 30  # 过期时间，单位：秒
    PASSWORD_HASH_ALGORITHM: str = "argon2"  # 密码哈希算法

    # ================================================= #
    # ******************** CORS配置 ******************* #
    # ================================================= #
    CORS_ALLOW_ORIGINS: List[str] = ["*"]  # 允许跨域来源,生产环境建议配置具体域名
    CORS_ALLOW_CREDENTIALS: bool = False  # 允许携带凭证(本系统用 Bearer 头,无需 cookie;通配符来源下必须为 False)
    CORS_ALLOW_METHODS: List[str] = ["*"]  # 允许请求方法
    CORS_ALLOW_HEADERS: List[str] = ["*"]  # 允许请求头

    # ================================================= #
    # ******************* 上下文管理器 ****************** #
    # ================================================= #
    CTX_LIST: List[str] = ["g", "stack", "task", "recorder"]  # 上下文管理器

    # ================================================= #
    # ********************* 日志配置 ******************* #
    # ================================================= #
    LOGGER_SINK: Any = sys.stdout  # date.today().strftime(r'%Y-%m-%d.log') 
    LOGGER_LEVEL: str = "DEBUG"                                              # 日志级别
    LOGGER_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <cyan>{extra[x_requests_id]}</cyan> <level>{message}</level>"
    LOGGER_INTERCEPT: bool = False                                 # 是否接管其他模块的日志
    IGNORE_OPERATION_LOG: bool = False                              # 忽略记录操作日志
    IGNORE_OPERATION_PATH: List[str] = ["/static", "/favicon.ico", "/openapi.json", "/ljdoc", "/docs", "/redoc", "/api/admin/v1/system/log/list"]                       # 忽略要记录操作日志的函数
    LOGGER_OUTPUT_CONSOLE: bool = True                              # 是否输出到控制台
    LOGGER_OUTPUT_DATABASE: bool = False                             # 是否输出到数据库

    # ================================================= #
    # ******************** ORM配置 ******************* #
    # ================================================= #
    ORM_MODELS: List[str] = ['app.models', 'aerich.models']
    ORM_ENGINE: str = "mysql"


    # ================================================= #
    # ******************** Sqlite配置 ******************* #
    # ================================================= #
    SQLITE_DB_PATH: str = "db"
    SQLITE_DB_NAME: str = "db.sqlite3"


    # ================================================= #
    # ******************** MySql配置 ******************* #
    # ================================================= #
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB_NAME: str = "fast_api_boot_framework"
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""  # 生产必须在 env/.env.prod 覆盖,禁止内置默认密码

    # ================================================= #
    # ******************** PostgreSQL配置 ******************* #
    # ================================================= #
    POSTGRESQL_HOST: str = "localhost"
    POSTGRESQL_PORT: int = 5432
    POSTGRESQL_DB_NAME: str = "grapefruit"
    POSTGRESQL_USER: str = "postgres"
    POSTGRESQL_PASSWORD: str = ""  # 生产必须配置数据库密码

    # ================================================= #
    # ******************** Redis配置 ******************* #
    # ================================================= #
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB_NAME: int = 0
    REDIS_USER: str = "default"
    REDIS_PASSWORD: str = ""  # 生产必须配置 Redis 密码
    REDIS_PREFIX_NAME: str = "fast_api_boot"         # redis前缀名

    # ================================================= #
    # **************** ARQ 任务队列配置 ***************** #
    # ================================================= #
    ARQ_QUEUE_NAME: str = "generate"                  # ARQ 队列名(worker 与 backend 需一致)
    BACKEND_PUBLIC_URL: str = "http://localhost:8801"  # 【人工配置】worker 回调本服务所用公网/内网地址
    WORKER_CALLBACK_SECRET: str = ""  # worker 回调令牌(dev/test 自动生成,prod 必须配置且与 worker NOTIFY_TOKEN 一致)
    # 停留 processing 超过该秒数判定为卡死(必须 > worker 单次超时 × 重试次数,
    # 否则会把还在重试的合法长视频任务误判失败:5400s × 3 = 16200)。
    # ⚠️ 这只是**最后兜底**:真正让长任务"及时"的是 recover_orphan_tasks 的僵尸续跑
    # (ARQ job 被杀后约 10 分钟内自动续上,不会干等这个超时)。
    TASK_STUCK_TIMEOUT: int = 18000
    TASK_RECONCILE_INTERVAL: int = 300  # 卡死任务对账扫描间隔(秒)
    # 孤儿任务回收:worker 崩溃/被重启会让 ARQ 里的任务永久丢失(ARQ 不自动重入队),
    # 任务就永久停在"生成中"。**未提交外部任务**却超过该秒数没有进展 → 判定为孤儿并重新入队
    # (断点续跑,不重复生成/扣费)。已提交外部任务的交给 TASK_STUCK_TIMEOUT 兜底。
    TASK_ORPHAN_TIMEOUT: int = 600
    # 静默预警阈值(秒):processing 任务超过该时长**一个回调都没到**(update_time 未刷新)时,
    # 对账只打告警日志、不动状态。刻意比 TASK_STUCK_TIMEOUT 短得多 ——
    # 目的是在任务被判失败/自动续跑之前就留下可排查的痕迹,
    # 而不是让"任务其实还活着、只是没有回调"只在用户侧表现为进度不动(见 task 5 的静默 5 分钟)。
    TASK_SILENT_WARN: int = 600

    @model_validator(mode="after")
    def _ensure_dev_secrets(self) -> "Settings":
        """dev/test 环境缺少密钥时自动生成临时值,避免本地启动失败;prod 不允许自动生成"""
        if self.ENVIRONMENT in (EnvironmentEnum.DEV, EnvironmentEnum.TEST):
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_urlsafe(48)
            if not self.WORKER_CALLBACK_SECRET:
                self.WORKER_CALLBACK_SECRET = secrets.token_urlsafe(24)
        return self

    # ================================================= #
    # ****************** 支付配置(微信V3) ************** #
    # ================================================= #
    PAYMENT_MODE: str = "mock"        # wechat=真实微信支付 mock=模拟(仅开发环境)
    PAYMENT_SOURCE_TAG: str = "yiyuan"  # 集群来源标识(写入 attach,防多系统串单)
    PAYMENT_ORDER_EXPIRE_MINUTES: int = 120  # 待支付订单超时取消(分钟)
    PAYMENT_REFUND_WINDOW_DAYS: int = 7      # 支付后允许退款的窗口(天)
    WECHAT_APP_ID: str = ""           # 【人工配置】微信 AppId
    WECHAT_MCHID: str = ""            # 【人工配置】商户号
    WECHAT_API_V3_KEY: str = ""       # 【人工配置】APIv3 密钥(回调解密)
    WECHAT_CERT_SERIAL_NO: str = ""   # 【人工配置】商户证书序列号
    WECHAT_PRIVATE_KEY: str = ""      # 【人工配置】商户私钥文件路径
    WECHAT_CERT_DIR: str = ""         # 【人工配置】平台证书目录

    # ================================================= #
    # ******** 微信公众号 / 小程序凭据(可选) *********** #
    # ================================================= #
    # 原硬编码在 plugin/wechat/config.py,现统一从环境变量/环境文件读取,禁止在源码写死
    WECHAT_OFFI_APPID: str = ""             # 公众号 AppID
    WECHAT_OFFI_APPSECRET: str = ""         # 公众号 AppSecret
    WECHAT_OFFI_TOKEN: str = ""             # 公众号消息校验 Token
    WECHAT_OFFI_ENCODING_AES_KEY: str = ""  # 公众号消息加解密 EncodingAESKey
    WECHAT_OFFI_CRYPT_MODEL: str = "plaintext"  # 加解密方式:plaintext/compatible/safe
    WECHAT_MINI_APPID: str = ""             # 小程序 AppID
    WECHAT_MINI_APPSECRET: str = ""         # 小程序 AppSecret

    # ================================================= #
    # ****************** 大模型网关(OpenAI兼容) ******* #
    # ================================================= #
    # 【人工配置】与 worker 用同一网关;文案润色等轻量调用走这里
    LLM_BASE_API_URL: str = ""        # 如 https://gateway.example.com/v1
    LLM_BASE_API_KEY: str = ""

    # ================================================= #
    # **************** 短信验证码配置 ***************** #
    # ================================================= #
    SMS_PROVIDER: str = "mock"        # mock=只写日志不发短信(开发自测) tencent=腾讯云短信
    SMS_SIGN_NAME: str = "一源AI"     # 【人工配置】短信签名(腾讯云控制台申请)
    SMS_SDK_APP_ID: str = ""          # 【人工配置】腾讯云短信应用 SDKAppID
    SMS_TEMPLATE_ID: str = ""         # 【人工配置】腾讯云短信模板ID(形参 {1} 为验证码)
    SMS_ACCESS_KEY_ID: str = ""       # 【人工配置】腾讯云 SecretId
    SMS_ACCESS_KEY_SECRET: str = ""   # 【人工配置】腾讯云 SecretKey
    SMS_REGION: str = "ap-guangzhou"  # 【人工配置】腾讯云地域(短信默认 ap-guangzhou)
    SMS_CODE_EXPIRE: int = 300        # 验证码有效期(秒)
    SMS_CODE_INTERVAL: int = 60       # 同一手机号重发间隔(秒)
    SMS_DAY_LIMIT: int = 10           # 同一手机号每日发送上限
    SMS_DEV_RETURN_CODE: bool = True  # dev+mock 时接口直接返回验证码(仅开发环境)

    # ================================================= #
    # *************** 腾讯位置服务(LBS) ***************** #
    # ================================================= #
    TENCENT_LBS_KEY: str = ""         # 【人工配置】腾讯位置服务 Key
    TENCENT_LBS_SK: str = ""          # 【人工配置】腾讯位置服务 SecretKey(服务端校验用)

    # ================================================= #
    # ************* 对象存储(腾讯云 COS) ************** #
    # ================================================= #
    OSS_ENABLE: bool = False          # 是否启用对象存储(生产建议 true,上传素材直接落 COS)
    OSS_SERVICE_SecretId: str = ""    # 【人工配置】腾讯云 SecretId
    OSS_SERVICE_SecretKey: str = ""   # 【人工配置】腾讯云 SecretKey
    OSS_SERVICE_Bucket: str = ""      # 【人工配置】Bucket 名称(含 APPID 后缀)
    OSS_SERVICE_Region: str = "ap-chengdu"  # 【人工配置】地域
    # 服务器与桶跨地域时开启全球加速:上传改走 {bucket}.cos.accelerate.myqcloud.com
    OSS_SERVICE_Accelerate: bool = False
    OSS_SERVICE_TIMEOUT_SECONDS: int = 300

    @property
    def OSS_ENABLED(self) -> bool:
        """对象存储是否可用(开关打开且三要素齐全)"""
        return bool(self.OSS_ENABLE and self.OSS_SERVICE_SecretId and self.OSS_SERVICE_SecretKey and self.OSS_SERVICE_Bucket)

    @property
    def OSS_CONFIG(self) -> Dict[str, Any]:
        """腾讯 COS 客户端构造参数"""
        return {
            "secret_id": self.OSS_SERVICE_SecretId,
            "secret_key": self.OSS_SERVICE_SecretKey,
            "bucket": self.OSS_SERVICE_Bucket,
            "region": self.OSS_SERVICE_Region,
            "timeout": self.OSS_SERVICE_TIMEOUT_SECONDS,
            "accelerate": self.OSS_SERVICE_Accelerate,
        }

    @property
    def LOGGER_CONFIG(self) -> Dict[str, Any]:
        """获取日志配置"""
        return {
            "sink": self.LOGGER_SINK,
            "level": self.LOGGER_LEVEL,
            "format": self.LOGGER_FORMAT,
            "intercept": self.LOGGER_INTERCEPT
        }


    @property
    def FASTAPI_CONFIG(self) -> Dict[str, Union[str, bool, None]]:
        """获取FastAPI应用属性"""
        return {
            "debug": self.DEBUG,
            "title": self.TITLE,
            "version": self.VERSION,
            "description": self.DESCRIPTION,
            "summary": self.SUMMARY,
            "root_path": self.ROOT_PATH,
            "root_path_in_servers": self.ROOT_PATH_IN_SERVERS,
            "docs_url": None,
            "redoc_url": None
        }

    @property
    def UVICORN_CONFIG(self) -> Dict[str, Any]:
        """获取Uvicorn配置"""
        return {
            "host": self.SERVER_HOST,
            "port": self.SERVER_PORT,
            "reload": self.RELOAD,
            "factory": self.FACTORY,
            "workers": self.WORKERS,
            "access_log": self.ACCESS_LOG,
        }

    @property
    def MYSQL_CONFIG(self) -> Dict[str, Union[str, bool, None]]:
        """获取MYSQL的连接配置"""
        return {
            "host": self.MYSQL_HOST,
            "port": self.MYSQL_PORT,
            "db": self.MYSQL_DB_NAME,
            "username": self.MYSQL_USER,
            "password": self.MYSQL_PASSWORD
        }

    @property
    def POSTGRESQL_CONFIG(self) -> Dict[str, Union[str, bool, None]]:
        """获取PostgreSQL的连接配置"""
        return {
            "host": self.POSTGRESQL_HOST,
            "port": self.POSTGRESQL_PORT,
            "db": self.POSTGRESQL_DB_NAME,
            "username": self.POSTGRESQL_USER,
            "password": self.POSTGRESQL_PASSWORD
        }

    @property
    def REDIS_CONFIG(self) -> str:
        """获取REDIS的连接配置"""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "db": self.REDIS_DB_NAME,
            "username": self.REDIS_USER,
            "password": self.REDIS_PASSWORD
        }

    @property
    def REDIS_URL(self) -> str:
        """获取REDIS的连接配置"""
        return f"redis://{self.REDIS_USER}:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_NAME}"
        

    @property
    def ORM_CONFIG(self) -> Dict[str, Union[str, bool, None]]:
        """获取ORM的连接配置"""
        config = {
            "connections": {},
            "apps": {
                "models": {
                    "models": self.ORM_MODELS,
                    "default_connection": "default",
                },
            },
            "use_tz": False,  # Whether to use timezone-aware datetimes
            "timezone": "Asia/Shanghai",  # Timezone setting
        }
        if self.ORM_ENGINE == "mysql":
            connections = {
                "default": {
                    "engine": "tortoise.backends.mysql",
                    "credentials": {
                        "host": self.MYSQL_HOST,  # Database host address
                        "port": self.MYSQL_PORT,  # Database port
                        "user": self.MYSQL_USER,  # Database username
                        "password": self.MYSQL_PASSWORD,  # Database password
                        "database": self.MYSQL_DB_NAME,  # Database name
                    },
                    "maxsize": 20,  # 连接池大小
                }
            }
            config["connections"] = connections
        elif self.ORM_ENGINE == "postgresql":
            connections = {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": self.POSTGRESQL_HOST,  # Database host address
                        "port": self.POSTGRESQL_PORT,  # Database port
                        "user": self.POSTGRESQL_USER,  # Database username
                        "password": self.POSTGRESQL_PASSWORD,  # Database password
                        "database": self.POSTGRESQL_DB_NAME,  # Database name
                    },
                    "maxsize": 20,  # 连接池大小
                }
            }
            config["connections"] = connections
        else:
            connections = {
                "default": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {
                        "file_path": f"{self.SQLITE_DB_PATH}/{self.SQLITE_DB_NAME}" # Path to SQLite database file
                    },
                }
            }
            config["connections"] = connections
        return config


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取配置实例"""
    env = os.getenv('ENVIRONMENT', EnvironmentEnum.DEV.value)
    if env not in [e.value for e in EnvironmentEnum]:
        raise ValueError(f"无效的环境配置: {env}")
    
    env_file = f"env/.env.{env}"
    if not os.path.exists(env_file):
        raise FileNotFoundError(f"环境配置文件不存在: {env_file}")
    settings = Settings(_env_file=env_file)
    _check_unsafe_defaults(settings, env)
    return settings


def _check_unsafe_defaults(settings: "Settings", env: str) -> None:
    """生产环境安全兜底:沿用开发默认密钥直接拒绝启动"""
    if env != EnvironmentEnum.PROD.value:
        return
    problems = []
    if not settings.SECRET_KEY:
        problems.append("SECRET_KEY 未配置,请在 env/.env.prod 中设置(可用 openssl rand -base64 48 生成)")
    if not settings.WORKER_CALLBACK_SECRET:
        problems.append("WORKER_CALLBACK_SECRET 未配置,请在 env/.env.prod 中设置,并与 worker NOTIFY_TOKEN 一致")
    if settings.ORM_ENGINE == "mysql" and not settings.MYSQL_PASSWORD:
        problems.append("MYSQL_PASSWORD 未配置,生产必须设置数据库密码")
    if settings.ORM_ENGINE == "postgresql" and not settings.POSTGRESQL_PASSWORD:
        problems.append("POSTGRESQL_PASSWORD 未配置,生产必须设置数据库密码")
    if not settings.REDIS_PASSWORD:
        problems.append("REDIS_PASSWORD 未配置,生产必须设置 Redis 密码")
    # 仅当短信走真实渠道时禁止回显验证码;mock 渠道本就不真实发码,允许回显用于内部测试
    if settings.SMS_DEV_RETURN_CODE and (settings.SMS_PROVIDER or "mock").lower() != "mock":
        problems.append("短信走真实渠道时 SMS_DEV_RETURN_CODE 必须为 false,否则验证码会直接返回给前端")
    if "*" in settings.CORS_ALLOW_ORIGINS:
        problems.append("CORS_ALLOW_ORIGINS 包含通配符 *,生产请配置为具体域名")
    if problems:
        raise ValueError("生产环境配置不安全:\n  - " + "\n  - ".join(problems))


config = get_settings()