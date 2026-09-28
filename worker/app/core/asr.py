# -*- coding: utf-8 -*-
'''
@文件    :asr.py
@说明    :词级时间戳(ASR 回灌) — 拿到「词 → 秒」,把字幕对齐到真实发音
@时间    :2026/09/24 10:00:00
@作者    :一源AI
@版本    :1.0
@说明    :P1 能力落地。此前 align.py 只做到**句子级**(用 ffmpeg silencedetect 找停顿,
          句内仍按词数摊分),做不到"逐字卡在发音上";本模块补齐词级时间戳:

            用 OpenAI 兼容网关的 transcriptions 接口(verbose_json +
            timestamp_granularities=["word"])对**成片音轨**跑一次识别,
            得到每个词的起止秒数,再按句子边界切成语幕 cue。

          为什么直接送成片(mp4)而不是先抽音轨:
            网关内部本就会用 ffmpeg 解码,抽音轨只会多一次本地 CPU 开销
            与一次临时文件的清理负担,且成片本来已经下载到本地了。

          与 silent 方案的分工(见 subtitle.burn_subtitle):
            ① 词级(本模块)—— 有 ASR_MODEL 时优先,时间精确到词;
            ② 句子级(align.py)—— 未配 ASR 时用,只保证"落在真的在说话的区间";
            ③ 估算(estimate_timing)—— 无音轨/全失败时兜底。

          容错原则与字幕烧录一致:**任何环节失败都返回 None**,
          由调用方回退到句子级/估算 —— 一次生成已经付费,不能因为"对齐"把成片弄丢。

          开关(后台可配,见 runtime_config):
            gen.asr_model            —— ASR 模型名,留空 = 不启用词级(默认关,避免额外成本)
            gen.subtitle_word_level  —— 1=优先词级,0=只用句子级
            gen.route.asr           —— 可选:单独指向支持 transcriptions 的网关
                                      (不配则回退 audio 网关链,见 gateway._FALLBACK["asr"])
'''
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from app.core.compose import Cue
from app.core import gateway
from app.core.plugin import logger
from app.settings import config

# 单次 ASR 超时(秒):成片音轨通常十几秒,
# 但要给网关侧"下载 + 解码 + 识别"留足余量(比视频轮询短得多,超时不至于拖垮任务)
ASR_TIMEOUT = 300

# 低于该时长的词视为识别噪声丢弃(whisper 偶尔会给出 0 时长的标点片段)
MIN_WORD_SEC = 0.02


def enabled() -> bool:
    """是否启用词级对齐:需配了 ASR 模型,且开关未显式关闭。

    默认(ASR_MODEL 为空)= 关闭 —— 词级对齐要多一次 STT 调用(有成本),
    且依赖网关支持 transcriptions,由运营按实际情况开启。
    """
    model = str(getattr(config, "ASR_MODEL", "") or "").strip()
    flag = str(getattr(config, "SUBTITLE_WORD_LEVEL", "1") or "1").strip().lower()
    return bool(model) and flag not in ("0", "false", "off", "no")


def _client():
    """ASR 解析独立的 **asr 能力网关**(gen.route.asr),默认回退音频网关链。

    词级对齐本质是 Whisper 的 /v1/audio/transcriptions,与 TTS 同属音频体系,
    但很多 TTS 专属网关(如火山方舟)并不提供 transcriptions 端点,直接复用
    AudioGenTool 的 client 会稳定 404。因此这里走 gateway.resolve("asr"):
      · 配了 gen.route.asr → 用指向转写网关的独立路由(推荐);
      · 未配 → 回退 AUDIO_LLM_* / LLM_BASE_* / CHAT_LLM_*,与音频回退链一致。
    """
    from openai import AsyncOpenAI

    gw = gateway.resolve("asr")
    return AsyncOpenAI(api_key=gw["key"], base_url=gw["url"])


async def transcribe_words(
    media_path: str, model: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """对媒体文件跑一次 ASR,返回词级时间戳 [{"word","start","end"}, ...];失败返回 None

    入参 media_path 传**本地成片路径**;不是本地文件或未启用词级时直接返回 None
    (调用方据此走句子级/估算,不需要区分"未启用"与"失败")。
    """
    if not enabled() or not media_path or not os.path.exists(media_path):
        return None
    use_model = str(model or getattr(config, "ASR_MODEL", "") or "").strip()
    if not use_model:
        return None
    try:
        client = _client()
        with open(media_path, "rb") as fh:
            data = fh.read()
        if not data:
            return None
        transcript = await client.audio.transcriptions.create(
            file=(os.path.basename(media_path), data, "application/octet-stream"),
            model=use_model,
            response_format="verbose_json",
            timestamp_granularities=["word"],
            timeout=ASR_TIMEOUT,
        )
        payload: Any = transcript.model_dump() if hasattr(transcript, "model_dump") else transcript
        words = payload.get("words") if isinstance(payload, dict) else None
        if not isinstance(words, list) or not words:
            logger.info(f"[asr] 网关未返回词级时间戳(model={use_model}),回退句子级对齐")
            return None
        out: List[Dict[str, Any]] = []
        for item in words:
            if not isinstance(item, dict):
                continue
            try:
                start = float(item.get("start") or 0)
                end = float(item.get("end") or 0)
            except (TypeError, ValueError):
                continue
            text = str(item.get("word") or item.get("text") or "").strip()
            if not text or end - start < MIN_WORD_SEC:
                continue
            out.append({"word": text, "start": start, "end": end})
        if not out:
            logger.info(f"[asr] 词级时间戳全部无效(model={use_model}),回退句子级对齐")
            return None
        logger.info(f"[asr] 词级时间戳就绪 model={use_model} words={len(out)}")
        return out
    except Exception as exc:  # noqa: BLE001
        # 对齐失败不影响烧录:调用方会回退句子级。
        # 日志带上模型名与网关主机(不打印 key),便于定位 404/401:
        # 404 多为网关不支持 transcriptions(需经 gen.route.asr 指向转写网关);
        # 401 多为 key 不匹配;二者都先确认网关与 TTS 是否同一家中转站。
        host = str(gateway.resolve("asr").get("url") or "").rstrip("/")
        logger.warning(f"[asr] 词级对齐失败(回退句子级): {exc} | model={use_model} gateway={host}")
        return None


def cues_from_words(
    words: List[Dict[str, Any]], sentences: List[Tuple[str, int]],
) -> List[Cue]:
    """把词级时间戳按句子边界切成字幕 cue(纯函数,便于单测)

    入参:
      words     —— ASR 词级时间戳(按时间顺序);
      sentences —— [(句子文本, 词数), ...],顺序即口播顺序。

    为什么要按**累计词数比例**切分而不是逐句取 N 个词:
      ASR 识别出的词序列与用户文案不可能逐字一致(同音字、断词、语气词),
      硬对齐会在几句之后整体错位;按比例切分只在句边界处引入最多一个词的漂移,
      且**末句吃掉全部剩余词**,保证字幕不会丢掉尾巴。

    每句时间 = 该句首词的 start ~ 末词的 end —— 这正是"逐字卡在发音上"的效果。
    """
    if not words or not sentences:
        return []
    # 先剔除时间戳非法的词(end ≤ start,网关偶发):留着会把整句时间算成倒挂而被丢弃
    clean: List[Dict[str, Any]] = []
    for item in words:
        try:
            if float(item.get("end") or 0) > float(item.get("start") or 0):
                clean.append(item)
        except (TypeError, ValueError, AttributeError):
            continue
    words = clean
    if not words:
        return []
    total_words = len(words)
    wanted = sum(max(1, int(count or 1)) for _, count in sentences)
    if wanted <= 0:
        return []

    cues: List[Cue] = []
    cursor = 0.0
    for index, (text, count) in enumerate(sentences):
        if index == len(sentences) - 1:
            lo, hi = int(round(cursor)), total_words
        else:
            span = total_words * max(1, int(count or 1)) / wanted
            lo = int(round(cursor))
            hi = int(round(cursor + span))
            cursor += span
        lo = max(0, min(lo, total_words - 1))
        hi = max(lo + 1, min(hi, total_words))
        chunk = words[lo:hi]
        if not chunk:
            continue
        try:
            start_ms = int(round(float(chunk[0].get("start") or 0) * 1000))
            end_ms = int(round(float(chunk[-1].get("end") or 0) * 1000))
        except (TypeError, ValueError):
            continue
        if end_ms <= start_ms:
            continue
        cues.append(Cue(start_ms=start_ms, end_ms=end_ms, text=text))
    return cues
