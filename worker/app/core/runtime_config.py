# -*- coding: utf-8 -*-
'''
@文件    :runtime_config.py
@说明    :业务配置热更新 — 周期从 backend 拉取 tb_system_config 全量配置(经 X-Worker-Token 鉴权,含网关密钥),
          覆盖本地 config 对应项(网关 base_url/key、模型名、画幅、清晰度),admin 改配置免重启生效。
          拉取失败保持现状,不影响生成主流程。
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
import asyncio
from typing import Any, Optional

import httpx

from app.settings import config
from app.core import gateway
from app.core.plugin import logger

# 后端配置键 → worker 本地配置属性
# 网关(敏感)经 worker 鉴权接口获取;模型/画幅等覆盖本地默认值。
# 值为空时不覆盖(空表示"回退 env 默认值",避免把网关/模型误清空)。
KEY_MAP = {
    # 主网关(敏感,需 X-Worker-Token):backend 文案润色 + worker prompt 改写(chat)走此网关 → CHAT_LLM_*
    "gen.llm_base_url": "CHAT_LLM_BASE_URL",
    "gen.llm_api_key": "CHAT_LLM_API_KEY",
    # Worker 视频专用网关(生视频用):留空则下方 fallback 回退到主网关 CHAT_LLM_*
    # 实现"润色/prompt 改写走 A 中转站、生视频走 B 中转站"的双网关分离
    "gen.worker_llm_base_url": "LLM_BASE_API_URL",
    "gen.worker_llm_api_key": "LLM_BASE_API_KEY",
    # 音频专用网关(方舟无 /audio 接口):留空则由 audio_tool 回退媒体网关/文本网关
    "gen.audio_llm_base_url": "AUDIO_LLM_BASE_URL",
    "gen.audio_llm_api_key": "AUDIO_LLM_API_KEY",
    # chat / 视频 prompt 改写
    "gen.chat_model": "CHAT_MODEL",
    # 视频
    "gen.video_model_t2v": "VIDEO_MODEL_T2V",
    "gen.video_model_i2v": "VIDEO_MODEL_I2V",
    "gen.video_model_r2v": "VIDEO_MODEL_R2V",
    # 视频编辑(Seedance 2.x):配了才启用"参考视频→新片";留空则走 r2v。
    # 注意:值为空时下方 if value 会跳过赋值 → 保持本地默认(空)即"不启用",符合预期。
    "gen.video_model_edit": "VIDEO_MODEL_EDIT",
    # 时长档位:配 "4-15" 放开连续时长(需模型支持),留空沿用 worker 默认 5/10
    "gen.video_durations": "VIDEO_DURATIONS",
    "gen.video_ratio": "VIDEO_RATIO",
    "gen.video_resolution": "VIDEO_RESOLUTION",
    # 数字人口播
    "gen.digital_model": "DIGITAL_MODEL",
    # 文本 / 图片 / 音频 / 音乐
    "gen.text_model": "TEXT_MODEL",
    "gen.image_model": "IMAGE_MODEL",
    "gen.image_model_edit": "IMAGE_MODEL_EDIT",
    "gen.image_ratio": "IMAGE_RATIO",
    "gen.audio_model": "AUDIO_MODEL",
    # P2 资产缓存(关闭则每次都真实调用付费接口)
    "gen.cache.enabled": "CACHE_ENABLED",
    "gen.music_model": "MUSIC_MODEL",
}

_task: Optional[asyncio.Task] = None

# 属性名含这些词的视为密钥:日志会归档/外传,明文打印等于泄漏
_SENSITIVE_HINTS = ("KEY", "SECRET", "TOKEN", "PASSWORD")


def mask_secret(attr: str, value: Any) -> str:
    """密钥类配置在日志里脱敏(保留前 6 后 4,既能核对"换没换 key"又不泄漏完整值)"""
    text = str(value)
    if not any(hint in attr.upper() for hint in _SENSITIVE_HINTS):
        return text
    if len(text) <= 10:
        return "*" * len(text)
    return f"{text[:6]}****{text[-4:]}"


async def refresh_once() -> None:
    """拉取一次配置并覆盖本地值"""
    url = f"{config.BACKEND_PUBLIC_URL.rstrip('/')}/api/user/v1/base/common/worker-config"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={}, headers={"X-Worker-Token": config.NOTIFY_TOKEN})
            data = resp.json()
        if data.get("code") != 1 or not isinstance(data.get("data"), dict):
            return
        changed = []
        for key, attr in KEY_MAP.items():
            value = data["data"].get(key)
            if value and getattr(config, attr, None) != value:
                setattr(config, attr, value)
                # 密钥类属性脱敏后再打印:这条日志此前会把网关 sk-/ark- 密钥明文写进日志文件
                changed.append(f"{attr}={mask_secret(attr, value)}")

        # 双网关回退:worker 视频网关(gen.worker_llm_*)留空 → 视频网关(LLM_BASE_*)回退主网关(CHAT_LLM_*)
        if not (data["data"].get("gen.worker_llm_base_url") or "").strip():
            if config.CHAT_LLM_BASE_URL and config.LLM_BASE_API_URL != config.CHAT_LLM_BASE_URL:
                config.LLM_BASE_API_URL = config.CHAT_LLM_BASE_URL
                config.LLM_BASE_API_KEY = config.CHAT_LLM_API_KEY
                changed.append("LLM_BASE_API_URL<=CHAT_LLM_BASE_URL(回退)")
        # 反向回退:主网关(gen.llm_*)留空 → 主网关(CHAT_LLM_*)回退视频网关(LLM_BASE_*)
        # 保证「仅配置 worker 视频网关 B」时,文本/图片/音频等也能用 B,实现"一处配置全局生效"
        if not (data["data"].get("gen.llm_base_url") or "").strip():
            if config.LLM_BASE_API_URL and config.CHAT_LLM_BASE_URL != config.LLM_BASE_API_URL:
                config.CHAT_LLM_BASE_URL = config.LLM_BASE_API_URL
                config.CHAT_LLM_API_KEY = config.LLM_BASE_API_KEY
                changed.append("CHAT_LLM_BASE_URL<=LLM_BASE_API_URL(回退)")

        # 命名网关 + 能力路由(灵活网关):解析 gen.gw.* / gen.route.*
        changed += gateway.load(data["data"])

        if changed:
            logger.info(f"[配置热更新] {', '.join(changed)}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[配置热更新] 拉取失败(保持现状): {exc}")


async def _loop() -> None:
    await refresh_once()  # 启动先拉一次
    while True:
        await asyncio.sleep(max(15, int(config.CONFIG_REFRESH_INTERVAL)))
        await refresh_once()


def start() -> None:
    """启动配置热更新后台协程(worker on_startup 调用)"""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())


async def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
