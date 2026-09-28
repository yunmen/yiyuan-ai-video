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
    # 单任务超时(秒)。必须**明显大于** VIDEO_POLL_TIMEOUT:
    # 轮询拿到直链后还有"下载成片 → 烧字幕 → 上传 OSS"的收尾,23s/20MB 的成片收尾要几分钟。
    # 此前 3300/3600 的组合只留了 5 分钟余量,长视频会在收尾阶段被 ARQ 直接掐掉
    # (日志表现:process_video max retries 3 exceeded)—— 实测踩过。
    ARQ_JOB_TIMEOUT: int = 5400
    ARQ_MAX_RETRIES: int = 3
    ARQ_RETRY_DELAY: int = 10        # 失败重试前的延迟(秒)

    # 单次网关调用的瞬时错误退避重试(配合 ARQ 整任务重试,二者互补不冲突):
    # 方舟 429 限流 / 5xx 内部错误 / 网络抖动在单次调用内就地重试,避免整条任务失败。
    # 非瞬时错误(400/401/403 参数或鉴权)不重试,立即抛给上层。
    GEN_TRANSIENT_RETRIES: int = 3   # 瞬时错误最大重试次数(含首次共 1+3 次)
    GEN_TRANSIENT_BACKOFF: float = 2.0  # 退避基数(秒),其后指数翻倍

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
    # P2 资产缓存:跨任务复用中间产物(TTS 音频/改写 prompt),关掉则每次都真实调用
    CACHE_ENABLED: str = "1"                           # gen.cache.enabled(1=启用)

    # ================================================= #
    # ***************** 大模型(真实接入) ************* #
    # ================================================= #
    LLM_BASE_API_URL: str = "https://ydtoken.capitalai.cn/v1"  # 【人工配置】视频网关地址(OpenAI 兼容,生视频用)
    LLM_BASE_API_KEY: str = ""                                 # 【人工配置】视频网关密钥(真实生成必填)
    # 主网关(润色/prompt 改写专用):默认与视频网关一致,可被 backend gen.llm_* 热更新覆盖。
    # 双网关模式下 backend 文案润色 + worker prompt 改写走此网关(A),视频走 LLM_BASE_API_URL(B)。
    CHAT_LLM_BASE_URL: str = "https://ydtoken.capitalai.cn/v1"
    CHAT_LLM_API_KEY: str = ""
    # 音频(语音/音乐)专用网关:火山方舟无 /audio 接口,音频需独立网关(如支持 /audio 的 OpenAI 兼容中转站)。
    # 留空依次回退媒体网关 LLM_BASE_*、文本网关 CHAT_LLM_*。
    AUDIO_LLM_BASE_URL: str = ""
    AUDIO_LLM_API_KEY: str = ""
    CHAT_MODEL: str = "qwen3.7-max"                            # 对话模型(prompt 改写用)
    # 视觉理解模型:视频拆解「逐镜头逆推」专用,必须支持 image_url 多模态输入;
    # 留空则跳过逆推(产生无描述的空分镜,并在日志明确提示配置)。请勿填纯文本模型(如 qwen3.7-max),
    # 否则网关会返回 400 "Unexpected item type in content"。
    VISION_MODEL: str = ""
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
    # 视频编辑(Seedance 2.x):以参考视频为输入重生成;留空则不启用,自动回退 r2v
    VIDEO_MODEL_EDIT: str = ""
    # 时长档位配置:"5,10"(只认固定档的模型)/ "4-15"(支持连续时长的模型);
    # 留空则沿用 video_tool.SUPPORTED_DURATIONS 默认值,保证旧模型不被传非法时长。
    VIDEO_DURATIONS: str = ""
    # 短视频默认竖版高清;与 backend 系统配置 gen.video_ratio / gen.video_resolution 默认值一致,
    # 实际以 backend 下发到 params 的 ratio/resolution 为准(未配置时走这里的 env 兜底)。
    VIDEO_RATIO: str = "9:16"
    VIDEO_RESOLUTION: str = "1080P"
    # 视频 prompt 引擎:默认 "native"(沿用既有中文改写链路);
    # 设为 "pixelle" 时,多段生成会用 Pixelle 的 narration→英文分镜能力重建逐段提示词。
    # 开关默认 native 保证既有管线零变化;仅在显式开启且联网正常时切换,失败自动回退 native。
    VIDEO_PROMPT_ENGINE: str = "native"
    # 复刻时成片画幅是否跟随参考视频:开(True)且纯复刻(无替换意图)时,
    # 不强制把参考视频裁到系统画幅,保留原片构图(D5)。
    REPLICATE_FOLLOW_REFERENCE_RATIO: bool = False
    # 逐镜头质检低分后是否**自动重跑**低分片段。默认关闭:自动重跑会额外花一次模型费用,
    # 属于必须由运营/用户显式开启的行为变更,不得默认开启(见复刻能力融入方案文档 §5 P1-7)。
    # 开启后只对从第一个低分镜头起的后缀片段重跑一次(有界),仍低分则放弃,只标记不阻断。
    VIDEO_QC_AUTO_RETRY: bool = False
    VIDEO_POLL_INTERVAL: int = 10    # 轮询间隔(秒)
    # 轮询总超时(秒),需 < ARQ_JOB_TIMEOUT 且留足收尾余量(下载/字幕/上传):
    # 30s 长片原生编辑实测要十几分钟,再算上多段拼接场景,给 60 分钟上限;
    # 与 ARQ_JOB_TIMEOUT(5400)之间保留 30 分钟收尾余量。
    VIDEO_POLL_TIMEOUT: int = 3600
    # 视频编辑(复刻)参考视频时长上限(秒):方舟编辑任务实测 4~30s,超过直接 400。
    # 改为后台可配(gen.video_edit_max_seconds)后,运维可按模型真实上限调整,
    # 收口为单一事实源,避免 media_prep 写死 30 与 video_tool 注释的 15.2s 互相矛盾。
    VIDEO_EDIT_MAX_REFERENCE_SECONDS: float = 30.0
    # 各编辑/参考生视频模型的清晰度上限(模型名子串:档位,分号分隔,如 seedance-2:720p)。
    # 切换到支持 1080P 的编辑模型时在此放开,否则成片被硬压 720p(原 _MODEL_RESOLUTION_CAP 写死)。
    VIDEO_RESOLUTION_CAP: str = "seedance-2:720p"
    # 镜头切分(参考视频解析)的场景变化阈值(0~1):画面差异超过它才算一次镜头切换。
    # 0.3 为经验值(PySceneDetect 类工具常见取值);运营可按素材类型(碎剪/长镜头)微调,
    # 避免把镜头内运动误判成切镜、或漏掉色调接近的硬切。非法值由 shots.scene_threshold() 回退默认。
    SHOT_SCENE_THRESHOLD: float = 0.3
    # 参考图被平台判定含真人时的处理方式:
    #   drop(默认)= 丢弃该图,改按已有的视觉识别文字描述生成(零成本、必然过检测);
    #   stylize     = 先用图生图把真人图拟态化为非写实风格再提交(保留"有个人"但非本人,多一次图片调用)
    # 说明:打码对图片不成立(图片正是要被替换的目标),所以只提供"丢弃/拟态化"两种。
    IMAGE_REAL_PERSON_MODE: str = "drop"

    # 数字人口播(数字人形象 + 口播音频 → 口型驱动视频)
    # 留空表示尚未接入该能力:数字人任务会以明确原因失败,不会静默产出错误结果。
    DIGITAL_MODEL: str = ""

    # 音频生成
    AUDIO_VOICE: str = "alloy"       # 默认音色
    AUDIO_FORMAT: str = "mp3"        # 输出格式

    # 字幕词级对齐(ASR 回灌):留空 = 不启用,字幕只用「成片音轨停顿」做句子级对齐。
    # 配了模型名(如 whisper-1)才走 ASR 拿词级时间戳 —— 多一次 STT 调用且需网关支持
    # transcriptions 接口,由运营按成本决定是否开启。
    ASR_MODEL: str = ""
    # 字幕是否优先词级对齐(需 ASR_MODEL):0=只用句子级停顿对齐
    SUBTITLE_WORD_LEVEL: str = "1"

    # 参考视频(视频编辑输入)的输出短边像素:与模型可用清晰度上限一致,默认 720。
    # 换到支持 1080P 的编辑模型后经 gen.reference_short_side 放开(1080);
    # 小于 480 视为配置错误回落 720(过小不满足模型最小分辨率要求,提交必然失败)。
    REFERENCE_SHORT_SIDE: int = 720

    # ================================================= #
    # ************* 对象存储(腾讯云 COS) ************** #
    # ================================================= #
    OSS_ENABLE: bool = False          # 是否启用 COS 转存(生产建议 true)
    OSS_SERVICE_SecretId: str = ""    # 【人工配置】腾讯云 SecretId
    OSS_SERVICE_SecretKey: str = ""   # 【人工配置】腾讯云 SecretKey
    OSS_SERVICE_Bucket: str = ""      # 【人工配置】Bucket 名称(含 APPID 后缀)
    OSS_SERVICE_Region: str = "ap-chengdu"  # 【人工配置】地域
    # 服务器与桶跨地域时开启全球加速:上传改走 {bucket}.cos.accelerate.myqcloud.com
    OSS_SERVICE_Accelerate: bool = False
    OSS_SERVICE_TIMEOUT_SECONDS: int = 300

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
        """OSS 是否可用(开关打开且三要素齐全)"""
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


config = Settings()
