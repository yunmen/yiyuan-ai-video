# -*- coding: utf-8 -*-
'''
@文件    :audio_tool.py
@说明    :音频生成工具(真实接入)— 语音合成(TTS) / 背景音乐(bgm),结果转存 OSS
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :2.1
@说明    :按 params.audio_type 路由:bgm/music/song → /audio/music/generations;
          其它(tts/sfx)→ Speech API。语音响应可能是二进制音频或二进制封装的 JSON,
          两种形态都统一转成自有 OSS 的持久化 URL。
'''
import json
import uuid
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from app.schemas.base import ToolResult
from app.tools.base import BaseGenTool
from app.settings import config
from app.core import gateway
from app.core.asset_cache import ASSET_TTS_AUDIO, build_cache_key
from app.core import asset_cache
from app.core.plugin import logger
from app.utils.oss import persist_url_list, upload_bytes

# 输出格式 → 扩展名
_EXT_MAP = {"mp3": ".mp3", "wav": ".wav", "opus": ".opus", "aac": ".aac", "flac": ".flac", "pcm": ".pcm"}


class AudioGenTool(BaseGenTool):
    """音频生成工具 — 语音合成(TTS)与背景音乐(bgm),结果转存自有 OSS"""

    name = "audio"
    description = "音频生成(语音合成/背景音乐)"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # 音频走"能力路由"(gen.route.audio)解析的网关(方舟无 /audio,需独立网关);
        # 未配置则依次回退音频槽位/媒体网关/文本网关
        gw = gateway.resolve("audio")
        self.api_key = api_key or gw["key"] or config.AUDIO_LLM_API_KEY or config.LLM_BASE_API_KEY or config.CHAT_LLM_API_KEY
        self.base_url = (base_url or gw["url"] or config.AUDIO_LLM_BASE_URL or config.LLM_BASE_API_URL or config.CHAT_LLM_BASE_URL).rstrip("/")
        self.proto = gw["proto"] if not base_url else gateway.auto_proto(self.base_url)
        self._pinned = bool(base_url)
        if not self.api_key:
            raise RuntimeError("未配置音频网关 API_KEY,无法调用音频生成接口")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    def _music_client(self, gw: Optional[Dict[str, str]] = None) -> AsyncOpenAI:
        """背景音乐可能路由到不同网关(gen.route.music):当前网关与 music 网关不同址时单独建 client。

        故障转移会传入正在尝试的候选网关;若它与当前网关同址则复用 self.client(已随切换重建)。
        """
        if gw is None:
            gw = gateway.resolve("music")
        url = (gw.get("url") or "").rstrip("/")
        if not url or url == self.base_url.rstrip("/"):
            return self.client
        return AsyncOpenAI(api_key=gw.get("key") or self.api_key, base_url=url)

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        """按 audio_type 路由:bgm/music/song → 背景音乐;其它 → 语音合成"""
        audio_type = (params.get("audio_type") or "tts").lower()
        task_id = str(params.get("_task_id") or uuid.uuid4().hex)
        if audio_type in ("bgm", "music", "song"):
            return await self.generate_music(
                prompt=params.get("prompt") or params.get("text") or "",
                lyrics=params.get("lyrics") or "",
                is_instrumental=bool(params.get("is_instrumental")),
                gender=params.get("gender") or "female",
                model=params.get("model"),
                task_id=task_id,
            )
        return await self.text_to_speech(
            text=params.get("text") or params.get("prompt") or "",
            model=params.get("model"),
            voice=params.get("voice"),
            response_format=params.get("response_format") or config.AUDIO_FORMAT,
            task_id=task_id,
        )

    async def text_to_speech(
        self, text: str, model: Optional[str] = None, voice: Optional[str] = None,
        response_format: str = "mp3", task_id: Optional[str] = None,
        notify_url: Optional[str] = None,
    ) -> ToolResult:
        """语音合成 — Speech API

        P2 资产缓存:文案 + 音色 + 模型 + 格式完全相同 → 复用已合成音频,零付费调用。
        换主播/换背景重跑时口播文案通常没变,这是最直接可复用的一笔成本。
        """
        text = (text or "").strip()
        if not text:
            return self._fail("语音合成文本不能为空", "invalid_request")
        use_model = model or config.AUDIO_MODEL
        use_voice = voice or config.AUDIO_VOICE
        use_format = response_format or config.AUDIO_FORMAT
        prefix = task_id or uuid.uuid4().hex
        cache_key = build_cache_key(ASSET_TTS_AUDIO, {
            "text": text, "model": use_model, "voice": use_voice, "format": use_format,
        })
        cached = await asset_cache.fetch(notify_url, cache_key, ASSET_TTS_AUDIO)
        if cached and cached.get("content"):
            # 命中:复用已转存 OSS 的音频直链,跳过真实合成
            return ToolResult(
                content=str(cached["content"]),
                metadata={
                    "success": True, "mode": "tts", "model": use_model, "voice": use_voice,
                    "chars": len(text), "cache": "hit",
                },
            )
        try:
            resp = await self._with_failover(
                "audio",
                lambda _gw: self.client.audio.speech.create(
                    model=use_model,
                    input=text,
                    voice=use_voice,
                    response_format=response_format,
                ),
                label="语音合成",
            )
            url = await self._to_url(resp, prefix, response_format)
            if not url:
                return self._fail("语音合成失败:未获取到音频内容(二进制结果需开启 OSS)", "invalid_request")
            logger.info(f"[AudioGenTool] 语音合成完成 model={use_model} voice={use_voice} chars={len(text)}")
            await asset_cache.store(
                notify_url, cache_key, ASSET_TTS_AUDIO, url, task_type="audio",
                meta={"model": use_model, "voice": use_voice, "chars": len(text)},
            )
            return ToolResult(
                content=url,
                metadata={
                    "success": True, "mode": "tts", "model": use_model, "voice": use_voice,
                    "chars": len(text), "cache": "miss",
                },
            )
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"语音合成失败: {exc}", "request_error")

    async def generate_music(
        self, prompt: str = "", lyrics: str = "", is_instrumental: bool = False,
        gender: str = "female", model: Optional[str] = None, task_id: Optional[str] = None,
    ) -> ToolResult:
        """背景音乐 — POST /audio/music/generations"""
        prompt = (prompt or "").strip()
        lyrics = (lyrics or "").strip()
        if not prompt and not lyrics:
            return self._fail("背景音乐生成失败:prompt 与 lyrics 至少提供一个", "invalid_request")
        use_model = model or config.MUSIC_MODEL
        payload: Dict[str, Any] = {
            "model": use_model,
            "prompt": prompt or None,
            "lyrics": lyrics or None,
            "is_instrumental": is_instrumental,
            "gender": gender if not is_instrumental else None,
            "format": config.AUDIO_FORMAT,
            "enable_aigc_watermark": False,
            "stream": False,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        prefix = task_id or uuid.uuid4().hex
        try:
            resp = await self._with_failover(
                "music",
                lambda gw: self._music_client(gw).post("/audio/music/generations", cast_to=dict, body=payload),
                label="背景音乐",
                prefer_current=False,
            )
            url = None
            if isinstance(resp, dict):
                data = resp.get("data")
                if isinstance(data, dict):
                    audio = data.get("audio")
                    if isinstance(audio, dict):
                        url = audio.get("url")
            if not url:
                return self._fail(f"背景音乐生成失败:接口未返回音频 URL({resp})", "invalid_request")
            urls = await persist_url_list([url], prefix)
            url = urls[0] if urls else url
            logger.info(f"[AudioGenTool] 背景音乐完成 model={use_model}")
            return ToolResult(
                content=url,
                metadata={"success": True, "mode": "bgm", "model": use_model, "chars": len(prompt)},
            )
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"背景音乐生成失败: {exc}", "request_error")

    async def _to_url(self, resp, task_id: str, fmt: str) -> Optional[str]:
        """把语音响应统一转成可访问 URL(URL 结果转存 / 二进制结果直传 OSS)"""
        content = getattr(resp, "content", None)
        if content is None:
            read = getattr(resp, "read", None)
            content = read() if callable(read) else None
        if not isinstance(content, bytes):
            return None

        # 形态一:以二进制封装的 JSON,实际是音频 URL(部分网关如此返回)
        try:
            payload = json.loads(content.decode("utf-8"))
            if isinstance(payload, dict):
                data = payload.get("data")
                if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("url"):
                    raw = data[0]["url"]
                    urls = await persist_url_list([raw], task_id)
                    return urls[0] if urls else raw
        except Exception:  # noqa: BLE001 - 非 JSON 视为纯音频二进制
            pass

        # 形态二:纯二进制音频,直接上传 OSS
        ext = _EXT_MAP.get((fmt or "mp3").lower(), ".mp3")
        return upload_bytes(content, f"generate/result/{task_id}_{uuid.uuid4().hex[:8]}{ext}")

    def _fail(self, msg: str, error_type: str = "unknown") -> ToolResult:
        logger.error(f"[AudioGenTool] {msg}")
        return ToolResult(content=msg, metadata={"success": False, "error_type": error_type, "error": msg})
