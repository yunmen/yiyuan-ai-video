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
from typing import Dict, Any, Union, List
from pathlib import Path
from functools import lru_cache
from datetime import date
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.enums.base import EnvironmentEnum

# 这些默认值只用于本地开发,生产沿用等于把系统大门敞开
DEFAULT_SECRET_KEY = "vgb0tnl9d58+6n-6h-ea&u^1#s0ccp!794=krylxcjq75vzps$"
DEFAULT_WORKER_TOKEN = "worker-callback-secret"


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
    SECRET_KEY: str = DEFAULT_SECRET_KEY  # JWT密钥(生产必须在 .env 中覆盖)
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
    MYSQL_PASSWORD: str = "123456"

    # ================================================= #
    # ******************** PostgreSQL配置 ******************* #
    # ================================================= #
    POSTGRESQL_HOST: str = "localhost"
    POSTGRESQL_PORT: int = 5432
    POSTGRESQL_DB_NAME: str = "grapefruit"
    POSTGRESQL_USER: str = "postgres"
    POSTGRESQL_PASSWORD: str = "123456"

    # ================================================= #
    # ******************** Redis配置 ******************* #
    # ================================================= #
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB_NAME: int = 0
    REDIS_USER: str = "default"
    REDIS_PASSWORD: str = "123456"
    REDIS_PREFIX_NAME: str = "fast_api_boot"         # redis前缀名

    # ================================================= #
    # **************** ARQ 任务队列配置 ***************** #
    # ================================================= #
    ARQ_QUEUE_NAME: str = "generate"                  # ARQ 队列名(worker 与 backend 需一致)
    BACKEND_PUBLIC_URL: str = "http://localhost:8801"  # 【人工配置】worker 回调本服务所用公网/内网地址
    WORKER_CALLBACK_SECRET: str = "worker-callback-secret"  # worker 回调鉴权令牌(需与 worker NOTIFY_TOKEN 一致)
    TASK_STUCK_TIMEOUT: int = 14400   # 停留 processing 超过该秒数判定为卡死(应 > worker 单次超时×重试次数)
    TASK_RECONCILE_INTERVAL: int = 300  # 卡死任务对账扫描间隔(秒)

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
    # **************** 对象存储 OSS 配置 *************** #
    # ================================================= #
    OSS_ENABLE: bool = False          # 是否启用 OSS(生产建议 true,上传素材直接落 OSS)
    OSS_SECRET_ID: str = ""           # 【人工配置】访问密钥 ID
    OSS_SECRET_KEY: str = ""          # 【人工配置】访问密钥 Secret
    OSS_BUCKET: str = ""              # 【人工配置】Bucket 名称
    OSS_REGION: str = "ap-chengdu"    # 【人工配置】地域
    OSS_ENDPOINT: str = ""            # 可选:自定义 Endpoint
    OSS_PUBLIC_BASE_URL: str = ""     # 可选:CDN/自定义域名前缀
    OSS_TOKEN: str = ""               # 可选:临时密钥 token
    OSS_SCHEME: str = "https"

    @property
    def OSS_ENABLED(self) -> bool:
        """OSS 是否可用(开关打开且四要素齐全)"""
        return bool(self.OSS_ENABLE and self.OSS_SECRET_ID and self.OSS_SECRET_KEY and self.OSS_BUCKET)

    @property
    def OSS_CONFIG(self) -> Dict[str, Any]:
        """OSS 客户端构造参数"""
        return {
            "secret_id": self.OSS_SECRET_ID,
            "secret_key": self.OSS_SECRET_KEY,
            "token": self.OSS_TOKEN or None,
            "region": self.OSS_REGION,
            "scheme": self.OSS_SCHEME,
            "bucket": self.OSS_BUCKET,
            "endpoint": self.OSS_ENDPOINT or None,
            "public_base_url": self.OSS_PUBLIC_BASE_URL or None,
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
    if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        problems.append("SECRET_KEY 仍为代码内置默认值,请在 env/.env.prod 中覆盖(可用 openssl rand -base64 48 生成)")
    if settings.WORKER_CALLBACK_SECRET == DEFAULT_WORKER_TOKEN:
        problems.append("WORKER_CALLBACK_SECRET 仍为默认值,请在 env/.env.prod 中覆盖并与 worker NOTIFY_TOKEN 一致")
    if settings.SMS_DEV_RETURN_CODE:
        problems.append("SMS_DEV_RETURN_CODE 在生产环境必须为 false,否则验证码会直接返回给前端")
    if "*" in settings.CORS_ALLOW_ORIGINS:
        problems.append("CORS_ALLOW_ORIGINS 包含通配符 *,生产请配置为具体域名")
    if problems:
        raise ValueError("生产环境配置不安全:\n  - " + "\n  - ".join(problems))


config = get_settings()