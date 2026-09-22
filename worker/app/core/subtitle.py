# -*- coding: utf-8 -*-
'''
@文件    :subtitle.py
@说明    :字幕烧录编排 — 把字幕压进成片(回写 backend 之前执行)
@时间    :2026/09/21 12:00:00
@作者    :一源AI
@版本    :1.1
@说明    :链路:视频 URL → 下载本地 → 分析音轨停顿 → 生成 SRT → ffmpeg 烧录 → 上传 OSS → 返回新 URL。

          设计前提(用户决策):
            ① 回写前烧 —— 所以本模块在 BaseGenService 组装 payload 之前调用;
            ② 字幕必须烧进成片(不是外挂字幕轨);
            ③ BGM 沿用视频自带音轨 —— 所以烧录命令是 `-c:a copy`,绝不重编码/替换音频。

          时间轴:优先用**成片音轨的真实停顿**对齐(silencedetect),拿到的是"哪里真的在说话";
          拿不到(无音轨/检测失败)就回退到按词数摊分的估算。**对齐失败不影响烧录**。

          容错原则:**任何环节失败都返回 None,调用方保留原视频 URL**。
          一次生成已经付费,不能因为"加个字幕"把结果变成失败任务。
          同理,字体缺失时直接跳过(ffmpeg 缺字体不报错,只会烧出豆腐块)。
'''
from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core import align, compose
from app.core.plugin import logger
from app.tools.script_anchor import build_script, estimate_timing, split_words
from app.utils.oss import download_to_local, upload_local_file

# 烧录/分析超时(秒):短视频(5~10s)重编码通常几秒,给足余量
BURN_TIMEOUT = 300


def _script_and_sentences(params: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Tuple[str, int]]]:
    """取出词锚点脚本,并把所有段落的句子摊平成 [(句子, 词数), ...]

    文案来源按优先级:
      ① params["script"]   —— backend 已下发的词锚点脚本(含 segments[].text,即 title/subtitle/script 原文);
      ② params["structured"] —— 原始结构化文案,现场 build_script;
      ③ params["text"]     —— 数字人口播文案(digital 走这条)。

    摊平是因为:口播是**连续一段**,句子应按真实语音顺序排,而不是按段落各分一段时间。
    """
    if not params:
        return {}, []

    script = params.get("script") or {}
    if not (script.get("segments") or []):
        structured = params.get("structured")
        text = params.get("text")
        if structured:
            script = build_script(structured)
        elif text:
            script = build_script({"script": text})
        else:
            return {}, []

    sentences: List[Tuple[str, int]] = []
    for seg in script["segments"]:
        for sentence in compose.split_sentences(seg.get("text") or ""):
            if sentence:
                sentences.append((sentence, len(split_words(sentence))))
    return script, sentences


def build_subtitle_cues(
    params: Dict[str, Any], duration_sec: float, silences: Optional[List[Tuple[float, float]]] = None,
) -> List[compose.Cue]:
    """生成字幕 cue(纯逻辑,便于单测)

    silences 给的是"检测到的静音区间";给了就按真实停顿对齐,没给(或对齐失败)回退估算。
    """
    script, sentences = _script_and_sentences(params)
    if not sentences:
        return []
    return _cues_from(script, sentences, duration_sec, silences)


def _cues_from(
    script: Dict[str, Any], sentences: List[Tuple[str, int]], duration_sec: float,
    silences: Optional[List[Tuple[float, float]]],
) -> List[compose.Cue]:
    """对齐优先,失败回退估算"""
    if silences:
        speech = align.speech_segments(silences, duration_sec)
        cues = align.align_sentences(sentences, speech, duration_sec)
        if cues:
            return cues
    timing = estimate_timing(script, duration_sec)
    return compose.build_cues(script["segments"], timing)


async def detect_speech_segments(
    local_media: str, duration_sec: float,
) -> Optional[List[Tuple[float, float]]]:
    """分析成片音轨,返回语音段(秒);无音轨/分析失败返回 None

    直接分析**成片本身**而不是单独找 TTS 音频:成片本来就要下载,零额外请求,
    且数字人的口播已经在成片音轨里了。
    """
    if not local_media or not os.path.exists(local_media) or duration_sec <= 0:
        return None
    cmd = align.build_silence_cmd(local_media)
    # truncate=False:silencedetect 的结果行在输出中段,截断会把它切掉
    result = await compose.run(cmd, timeout=BURN_TIMEOUT, truncate=False)
    if not result.get("ok"):
        logger.info(f"[subtitle] 音轨停顿分析失败,回退估算时间轴: {result.get('stderr')}")
        return None
    silences = align.parse_silence_ranges(f"{result.get('stderr') or ''}\n{result.get('stdout') or ''}")
    return align.speech_segments(silences, duration_sec) or None


async def burn_subtitle(
    video_url: str, params: Dict[str, Any], duration_sec: float, prefix: str = "",
) -> Optional[str]:
    """把字幕烧进视频,返回新的视频 URL;**任何环节失败返回 None**(调用方保留原 URL)"""
    if not video_url:
        return None

    # ① 环境:没有 ffmpeg 直接跳过(容器未安装时不能硬烧)
    if not compose.available():
        logger.info("[subtitle] 跳过字幕烧录:ffmpeg 不可用")
        return None

    # ② 字体:缺字体 ffmpeg 不报错但会烧出豆腐块,宁可不烧
    resolved = compose.resolve_subtitle_font()
    if not resolved:
        logger.warning("[subtitle] 跳过字幕烧录:未找到可用中文字体(容器需装 fonts-noto-cjk)")
        return None
    font, fonts_dir = resolved

    # ③ 字幕内容:没有文案就没得烧(放在下载之前,省一次下载)
    script, sentences = _script_and_sentences(params)
    if not sentences:
        logger.info("[subtitle] 跳过字幕烧录:无可用字幕文案")
        return None

    workdir = tempfile.mkdtemp(prefix="subtitle_")
    srt_path = os.path.join(workdir, "sub.srt")
    local_video: Optional[str] = None
    burned_path = os.path.join(workdir, "burned.mp4")
    try:
        # ④ 下载:ffmpeg 只认本地文件
        local_video = await asyncio.to_thread(download_to_local, video_url, ".mp4")
        if not local_video:
            logger.warning(f"[subtitle] 跳过字幕烧录:视频下载失败 {video_url}")
            return None

        # ⑤ 时间轴:用成片音轨的真实停顿对齐;失败回退估算(不影响烧录)
        silences = await detect_speech_segments(local_video, duration_sec)
        cues = _cues_from(script, sentences, duration_sec, silences)
        if not cues:
            logger.info("[subtitle] 跳过字幕烧录:未生成任何字幕条目")
            return None
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(compose.build_srt(cues))

        # ⑥ 烧录:cwd 切到 srt 所在目录,避免 Windows 盘符冒号被 filter 当分隔符
        style = compose.default_subtitle_style(font)
        cmd = compose.build_burn_subtitle_cmd(
            local_video, os.path.basename(srt_path), burned_path, style, fonts_dir,
        )
        result = await compose.run(cmd, timeout=BURN_TIMEOUT, cwd=workdir)
        if not result.get("ok"):
            logger.warning(f"[subtitle] 字幕烧录失败,保留原片: {result.get('stderr')}")
            return None

        # ⑦ 上传回 OSS:失败也必须保留原 URL
        key = f"generate/result/{prefix or 'subtitle'}_{uuid.uuid4().hex[:8]}.mp4"
        new_url = await asyncio.to_thread(upload_local_file, burned_path, key)
        if not new_url:
            logger.warning("[subtitle] 烧录产物上传失败,保留原片")
            return None

        logger.info(
            f"[subtitle] 字幕已烧进成片 font={font} "
            f"aligned={bool(silences)} cues={len(cues)} → {new_url}"
        )
        return new_url
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[subtitle] 字幕烧录异常,保留原片: {exc}")
        return None
    finally:
        # 临时文件一律清理(下载的原片 + 烧录产物 + SRT)
        for path in (local_video, burned_path, srt_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        if os.path.isdir(workdir):
            try:
                os.rmdir(workdir)
            except OSError:
                pass
