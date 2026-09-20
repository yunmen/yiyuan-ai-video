# -*- coding: utf-8 -*-
'''
@文件    :settings.py
@说明    :worker 环境配置(pydantic-settings)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
import os
from typing import Any, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """worker 配置(读取 env/.env.{ENVIRONMENT})"""
    model_config = SettingsConfigDict(
        env_file=f"env/.env.{os.getenv('ENVIRONMENT', 'dev')}",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: str = "dev"

    # ================================================= #
    # ***************** Redis / ARQ 配置 ************** #
    # ================================================= #
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB_NAME: int = 0
    REDIS_USER: str = "default"
    REDIS_PASSWORD: str = "123456"
    ARQ_QUEUE_NAME: str = "generate"
    ARQ_CONCURRENCY: int = 5
    ARQ_JOB_TIMEOUT: int = 3600
    ARQ_MAX_RETRIES: int = 3
    ARQ_RETRY_DELAY: int = 10        # 失败重试前的延迟(秒)

    # ================================================= #
    # ***************** 生成进度参数 ****************** #
    # ================================================= #
    GEN_PROGRESS_INTERVAL: int = 5   # 生成过程中回写进度的间隔(秒)

    # ================================================= #
    # ***************** 回调 backend ****************** #
    # ================================================= #
    NOTIFY_URL: str = "http://localhost:8801/api/user/v1/task/callback"
    NOTIFY_TOKEN: str = "worker-callback-secret"
    NOTIFY_RETRY_ATTEMPTS: int = 3   # 回调失败重试次数
    NOTIFY_RETRY_DELAY: int = 2      # 回调重试基础延迟(秒,按次数线性退避)
    BACKEND_PUBLIC_URL: str = "http://127.0.0.1:8801"  # 后端地址(拉取业务配置用)
    CONFIG_REFRESH_INTERVAL: int = 60                  # 业务配置热更新间隔(秒)

    # ================================================= #
    # ***************** 大模型(真实接入) ************* #
    # ================================================= #
    LLM_BASE_API_URL: str = "https://ydtoken.capitalai.cn/v1"  # 【人工配置】视频网关地址(OpenAI 兼容,生视频用)
    LLM_BASE_API_KEY: str = ""                                 # 【人工配置】视频网关密钥(真实生成必填)
    # 主网关(润色/prompt 改写专用):默认与视频网关一致,可被 backend gen.llm_* 热更新覆盖。
    # 双网关模式下 backend 文案润色 + worker prompt 改写走此网关(A),视频走 LLM_BASE_API_URL(B)。
    CHAT_LLM_BASE_URL: str = "https://ydtoken.capitalai.cn/v1"
    CHAT_LLM_API_KEY: str = ""
    CHAT_MODEL: str = "qwen3.7-max"                            # 对话模型(prompt 改写用)
    TEXT_MODEL: str = "qwen3.7-max"                            # 文本生成模型
    IMAGE_MODEL: str = "qwen-image-2.0"                        # 图片生成(文生图)模型
    IMAGE_MODEL_EDIT: str = ""                                 # 图片编辑(图生图)模型,留空则复用 IMAGE_MODEL
    VIDEO_MODEL: str = "happyhorse-1.1-t2v"                    # 视频模型(用量展示用)
    AUDIO_MODEL: str = "qwen-audio-3.0-tts-plus"               # 音频生成(语音)模型
    MUSIC_MODEL: str = "fun-music-v1"                          # 背景音乐生成模型

    # 图片生成
    IMAGE_RATIO: str = "1:1"                 # 默认画幅:1:1/16:9/9:16/4:3/3:4

    # 视频生成:按模式区分模型(文生/图生/参考生)+ 轮询参数
    VIDEO_MODEL_T2V: str = "happyhorse-1.1-t2v"
    VIDEO_MODEL_I2V: str = "happyhorse-1.1-i2v"
    VIDEO_MODEL_R2V: str = "happyhorse-1.1-r2v"
    VIDEO_RATIO: str = "16:9"
    VIDEO_RESOLUTION: str = "720P"
    VIDEO_POLL_INTERVAL: int = 10    # 轮询间隔(秒)
    VIDEO_POLL_TIMEOUT: int = 3300   # 轮询总超时(秒),需 < ARQ_JOB_TIMEOUT(留余量完成回调)

    # 音频生成
    AUDIO_VOICE: str = "alloy"       # 默认音色
    AUDIO_FORMAT: str = "mp3"        # 输出格式

    # ================================================= #
    # ***************** 对象存储 OSS ****************** #
    # ================================================= #
    OSS_ENABLE: bool = False          # 是否启用 OSS 转存(生产建议 true)
    OSS_PROVIDER: str = "aliyun"      # 目前支持 aliyun
    OSS_SECRET_ID: str = ""           # 【人工配置】访问密钥 ID
    OSS_SECRET_KEY: str = ""          # 【人工配置】访问密钥 Secret
    OSS_BUCKET: str = ""              # 【人工配置】Bucket 名称
    OSS_REGION: str = "ap-chengdu"    # 【人工配置】地域,如 ap-chengdu/ap-guangzhou
    OSS_ENDPOINT: str = ""            # 可选:自定义 Endpoint(留空用 oss-{region}.aliyuncs.com)
    OSS_PUBLIC_BASE_URL: str = ""     # 可选:CDN/自定义域名前缀(留空用默认域名)
    OSS_TOKEN: str = ""               # 可选:临时密钥 token(永久密钥留空)
    OSS_SCHEME: str = "https"         # 访问协议 http/https

    @property
    def REDIS_DSN(self) -> str:
        auth = ""
        if self.REDIS_USER and self.REDIS_PASSWORD:
            auth = f"{self.REDIS_USER}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth = f":{self.REDIS_PASSWORD}@"
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_NAME}"

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


config = Settings()
