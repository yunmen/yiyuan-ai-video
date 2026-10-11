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
import re
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core import align, asr, compose
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
      ③ params["text"]     —— 数字人口播文案(digital 走这条);
      ④ params["prompt_context"] —— 兜底:老任务重跑时 params 缺上述字段,但 [商家信息] 里有台词原文。

    摊平是因为:口播是**连续一段**,句子应按真实语音顺序排,而不是按段落各分一段时间。

    ⚠️ 逐级回退的依据必须是「**能不能构建出 segments**」,不能是「字段是否非空」(实测 task 59):
    旧写法是 `if structured: script = build_script(structured)`,而 build_script 只认
    STRUCTURED_TO_SEGMENT 里的 title/subtitle/script 三个键。structured 非空但键名不符
    (或那几个值为空)时,它会**返回空 segments 并且不再往下尝试**,导致明明有台词(prompt_context
    里就有)却判定"无可用字幕文案"而静默跳过烧录 —— 成片因此没有字幕。
    """
    if not params:
        return {}, []

    script = params.get("script") or {}
    if script.get("segments"):
        return script, _flatten_sentences(script)

    structured = params.get("structured")
    text = params.get("text")
    # 逐个来源尝试:构建出 segments 才算这个来源可用,否则继续往下退。
    for builder in (
        lambda: build_script(structured) if structured else None,
        lambda: build_script({"script": text}) if text else None,
        # 兜底来源:老任务重跑时存储的 params 可能缺 script/structured,
        # 但 prompt_context 的 [商家信息] 里「口播文案:…」就是用户台词原文,
        # 据此现算词锚点,保证老任务也能烧字幕(不必依赖 script 字段存在)。
        lambda: _script_from_prompt_context(params) if params.get("prompt_context") else None,
    ):
        candidate = builder()
        if candidate and candidate.get("segments"):
            return candidate, _flatten_sentences(candidate)
    return {}, []


def _structured_text_fields(structured: Optional[Dict[str, Any]]) -> List[str]:
    """列出 structured 里真正带台词的字段名(供跳过烧录时的日志定位键名不匹配问题)"""
    if not isinstance(structured, dict):
        return []
    return [key for key, value in structured.items() if str(value or "").strip()]


def _flatten_sentences(script: Dict[str, Any]) -> List[Tuple[str, int]]:
    """把脚本各段落的句子摊平成 [(句子, 词数), ...];空句直接丢弃。"""
    sentences: List[Tuple[str, int]] = []
    for seg in script.get("segments") or []:
        for sentence in compose.split_sentences(seg.get("text") or ""):
            if sentence:
                sentences.append((sentence, len(split_words(sentence))))
    return sentences


def _script_from_prompt_context(params: Dict[str, Any]) -> Dict[str, Any]:
    """从 prompt_context 的 [商家信息] 抠出口播/标题/副标题,现算词锚点脚本。

    当前任务一定携带 prompt_context;老任务重跑时存储的 params 可能缺 script/structured,
    但里面的「口播文案:…」就是用户台词原文,据此仍能烧字幕。
    """
    ctx = params.get("prompt_context") or ""
    if not ctx:
        return {}
    found: Dict[str, str] = {}
    for label, key in (
        ("口播文案", "script"), ("口播", "script"),
        ("大标题", "title"), ("标题", "title"), ("副标题", "subtitle"),
    ):
        # 只取标签所在行冒号后的内容,避免把整段提示词当文案
        m = re.search(rf"{label}[::：]\s*(.+)", ctx)
        if m:
            found.setdefault(key, m.group(1).strip())
    if not found:
        return {}
    return build_script(found)


def build_subtitle_cues(
    params: Dict[str, Any], duration_sec: float, silences: Optional[List[Tuple[float, float]]] = None,
    words: Optional[List[Dict[str, Any]]] = None,
    head_boxes: Optional[List[Tuple[float, float, float, float, float]]] = None,
) -> List[compose.Cue]:
    """生成字幕 cue(纯逻辑,便于单测)

    时间轴优先级:词级(words)→ 句子级(silences)→ 估算。
    words 为 ASR 词级时间戳(见 app.core.asr);调用方不传时行为与改造前完全一致。
    head_boxes 为头部跟随字幕的 RegionTimeline [(t,x,y,w,h)...](归一化);提供则把每条 cue
    的字幕锚点贴到其时间窗中点对应的头部上沿中心,实现「字幕跟随头部」。
    """
    script, sentences = _script_and_sentences(params)
    if not sentences:
        return []
    cues: List[compose.Cue] = []
    if words:
        cues = asr.cues_from_words(words, sentences) or []
    if not cues:
        cues = _cues_from(script, sentences, duration_sec, silences)
    if cues and head_boxes:
        _attach_head_positions(cues, head_boxes)
    return cues


def _attach_head_positions(
    cues: List[compose.Cue], head_boxes: List[Tuple[float, float, float, float, float]],
) -> None:
    """把每条 cue 的字幕锚点贴到其时间窗中点对应的头部上沿中心(归一化)。

    head_boxes:[(t,x,y,w,h)...],x/y/w/h 均归一化 0~1(头部框含头发/帽子余量)。
    取时间窗中点最近(且 2s 内)的头部框;无可用头部则该 cue 走默认底部居中。
    """
    if not head_boxes:
        return
    hb = sorted(head_boxes, key=lambda b: b[0])
    for cue in cues:
        t_mid = (cue.start_ms + cue.end_ms) / 2.0 / 1000.0
        box = _nearest_head_box(hb, t_mid)
        if box:
            x, y, w, h = box[1], box[2], box[3], box[4]
            cue.pos = (x + w / 2.0, y)


def _nearest_head_box(
    hb: List[Tuple[float, float, float, float, float]], t: float, max_gap: float = 2.0,
):
    """在已按时间排序的 head_boxes 里找 t 最近(且间隔 <= max_gap 秒)的框;无则 None"""
    best = None
    best_gap = None
    for b in hb:
        gap = abs(b[0] - t)
        if gap <= max_gap and (best_gap is None or gap < best_gap):
            best, best_gap = b, gap
    return best


def _resolve_head_boxes(params: Dict[str, Any], local_video: str):
    """解析头部轨迹:优先用预标注 head_track,否则跑自动头部检测(需配置 gen.route.head)。

    返回 [(t,x,y,w,h)...] 或 None(调用方据此回退底部字幕)。任何异常都降级为 None,不阻断烧录。
    """
    # ① 预标注优先:head_track 是 RegionTimeline [{t(秒), box:[x,y,w,h](归一化)}]
    ht = params.get("head_track")
    if isinstance(ht, list) and ht:
        boxes: List[Tuple[float, float, float, float, float]] = []
        for item in ht:
            if not isinstance(item, dict):
                continue
            box = item.get("box")
            t = item.get("t") if item.get("t") is not None else item.get("time")
            if isinstance(box, list) and len(box) == 4 and t is not None:
                boxes.append((float(t), float(box[0]), float(box[1]), float(box[2]), float(box[3])))
        if boxes:
            return boxes
    # ② 自动检测(可选网关;未配置/失败 → None)
    try:
        from app.tools.head_track_tool import HeadTrackTool
        return HeadTrackTool().detect(local_video)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[subtitle] 头部检测调用失败,回退底部字幕: {exc}")
        return None


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


def _flatten_sentences_with_segment(script: Dict[str, Any]) -> List[Tuple[str, str]]:
    """按段落顺序摊平句子,保留所属段 id —— 用于把真实 cue 归属回各段。"""
    rows: List[Tuple[str, str]] = []
    for seg in (script or {}).get("segments") or []:
        seg_id = str(seg.get("id") or "")
        for sentence in compose.split_sentences(seg.get("text") or ""):
            if sentence:
                rows.append((seg_id, sentence))
    return rows


def segment_spans_from_cues(
    script: Dict[str, Any], cues: List[compose.Cue],
) -> Dict[str, Dict[str, int]]:
    """用真实对齐时间轴(cues)为各段求真实时间窗 {segment_id:{start_ms,end_ms}}。

    cues 与 _flatten_sentences 的句子同序(词级 ASR / 停顿对齐都按文案顺序产出),
    因此按句文本顺序匹配即可把每条 cue 归属回段,再按段并集得到段级真实窗口。
    匹配不到任何 cue 的段不返回(调用方对该段回退估算)。
    """
    rows = _flatten_sentences_with_segment(script or {})
    spans: Dict[str, Dict[str, int]] = {}
    idx = 0
    for cue in cues or []:
        # cues 是句子的子序列(个别句可能未产出 cue),按顺序跳过未命中的句子
        while idx < len(rows) and rows[idx][1] != getattr(cue, "text", None):
            idx += 1
        if idx >= len(rows):
            break
        seg_id = rows[idx][0]
        start, end = int(cue.start_ms), int(cue.end_ms)
        cur = spans.get(seg_id)
        if cur:
            cur["start_ms"] = min(cur["start_ms"], start)
            cur["end_ms"] = max(cur["end_ms"], end)
        else:
            spans[seg_id] = {"start_ms": start, "end_ms": end}
        idx += 1
    return spans


def _is_estimate_cues(
    script: Dict[str, Any], cues: List[compose.Cue], duration_sec: float,
) -> bool:
    """判断给定 cues 是否来自「无真实对齐」的估算路径。

    _cues_from 在无词级、无停顿对齐时产出的正是 estimate_timing + compose.build_cues 的结果;
    逐条比对 (start_ms,end_ms,text) 即可确认 —— 用于给 anchor_timing 诚实标注来源。
    """
    try:
        est_cues = compose.build_cues(
            script.get("segments") or [], estimate_timing(script, duration_sec),
        )
    except Exception:  # noqa: BLE001
        return False
    if len(est_cues) != len(cues or []):
        return False
    for a, b in zip(est_cues, cues):
        if (a.start_ms, a.end_ms, a.text) != (b.start_ms, b.end_ms, b.text):
            return False
    return True


def anchor_timing(
    params: Dict[str, Any], cues: List[compose.Cue], duration_sec: float,
) -> Tuple[Dict[str, Dict[str, int]], str]:
    """把真实对齐时间轴(cues)回灌成锚点窗口(P3-1 的产物)。

    返回 (锚点窗口, 来源):
      · 窗口形如 {"selection:xxx":{"start_ms","end_ms"},
                  "moment:yyy":{"start_ms","end_ms","at_ms"}}(卡点取窗口起点);
      · 来源 "real" = 由真实对齐(cues 归属回段)推得; "estimate" = cues 本身即估算产物
        (词级/停顿对齐都不可用时的降级兜底),此时回退到无回灌的纯估算值,状态与改造前一致。
    无 script / 无 cues / 无可用段窗口时返回 ({}, ""),调用方据此不写 metadata。
    """
    script, _ = _script_and_sentences(params)
    if not script.get("segments") or not cues:
        return {}, ""
    estimate_only = _is_estimate_cues(script, cues, duration_sec)
    spans: Dict[str, Dict[str, int]] = {}
    if not estimate_only:
        spans = segment_spans_from_cues(script, cues)
        if not spans:
            return {}, ""
    timing = estimate_timing(script, duration_sec, segment_spans=spans)
    out: Dict[str, Dict[str, int]] = {}
    for ref, span in (timing.get("anchors") or {}).items():
        item = dict(span)
        if ref.startswith("moment:"):
            # 卡点取窗口起点:下游按「什么时刻触发」消费,而非窗口终点
            item["at_ms"] = int(span.get("start_ms") or 0)
        out[ref] = item
    return out, ("estimate" if estimate_only else "real")


def anchor_windows(
    params: Dict[str, Any], cues: List[compose.Cue], duration_sec: float,
    refs: List[str],
) -> List[Tuple[float, float]]:
    """把一批锚点引用(selection:x / moment:y)解析成真实时间窗(秒),供合成层卡点(P3-3)。

    优先用 P1 真实对齐回灌的锚点窗口;无 cues / 无法回灌时退回 estimate_timing 的估算窗口
    —— 保证「无字幕也能卡点」的降级链与字幕一致。未命中/非法引用直接跳过(不臆造位置);
    窗口按 [start,end] 秒返回(有 duration 时夹在其内)。
    """
    refs = [str(r).strip() for r in (refs or []) if str(r).strip()]
    if not refs:
        return []
    script, _ = _script_and_sentences(params)
    mapping, _source = anchor_timing(params, cues, duration_sec)
    if not mapping:
        # 无真实对齐时退回估算锚点(与 estimate_timing 同源)
        try:
            mapping = (estimate_timing(script, duration_sec) or {}).get("anchors") or {}
        except Exception:  # noqa: BLE001
            mapping = {}
    try:
        duration = max(0.0, float(duration_sec or 0))
    except (TypeError, ValueError):
        duration = 0.0
    wins: List[Tuple[float, float]] = []
    for ref in refs:
        span = mapping.get(ref)
        if not span:
            continue
        start = max(0.0, float(span.get("start_ms") or 0) / 1000.0)
        end = float(span.get("end_ms") or 0) / 1000.0
        if duration > 0:
            end = min(duration, end)
        if end <= start:
            continue
        wins.append((start, end))
    return wins


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


async def burn_subtitle_with_cues(
    video_url: str, params: Dict[str, Any], duration_sec: float, prefix: str = "",
) -> Tuple[Optional[str], List[compose.Cue]]:
    """把字幕烧进视频,返回 (新的视频 URL, 实际烧进成片的时间轴)

    **任何环节失败返回 (None, [])**,调用方保留原 URL。

    为什么把时间轴一并返回:实际烧进的 cue 是**对齐后**的真实时间轴(词级/句子级),
    与建单时按词数摊分的估算值不同。上层把它随用量回写 backend 后,
    「改一句台词重跑」才能定位到真实时间窗,而不是按估算值切错位置。
    """
    if not video_url:
        return None, []

    # ① 环境:没有 ffmpeg 直接跳过(容器未安装时不能硬烧)
    if not compose.available():
        logger.info("[subtitle] 跳过字幕烧录:ffmpeg 不可用")
        return None, []

    # ② 字体:缺字体 ffmpeg 不报错但会烧出豆腐块,宁可不烧
    resolved = compose.resolve_subtitle_font()
    if not resolved:
        logger.warning("[subtitle] 跳过字幕烧录:未找到可用中文字体(容器需装 fonts-noto-cjk)")
        return None, []
    font, fonts_dir = resolved

    # ③ 字幕内容:没有文案就没得烧(放在下载之前,省一次下载)
    script, sentences = _script_and_sentences(params)
    if not sentences:
        # 日志要打出「各来源是否真的带出了台词」,而不是「字段是否非空」——
        # 后者会误导排查(structured 非空但键名不符时,字段=y 而实际一句台词也没有)。
        logger.info(
            "[subtitle] 跳过字幕烧录:无可用字幕文案"
            f"(script.segments={len((params.get('script') or {}).get('segments') or [])},"
            f"structured.文案字段={sorted(_structured_text_fields(params.get('structured')))},"
            f"text={'y' if params.get('text') else 'n'},"
            f"prompt_context={'y' if params.get('prompt_context') else 'n'})"
        )
        return None, []

    workdir = tempfile.mkdtemp(prefix="subtitle_")
    srt_path = os.path.join(workdir, "sub.srt")
    ass_path: Optional[str] = None
    local_video: Optional[str] = None
    burned_path = os.path.join(workdir, "burned.mp4")
    try:
        # ④ 下载:ffmpeg 只认本地文件
        local_video = await asyncio.to_thread(download_to_local, video_url, ".mp4")
        if not local_video:
            logger.warning(f"[subtitle] 跳过字幕烧录:视频下载失败 {video_url}")
            return None, []

        # ⑤ 时间轴:词级(ASR)→ 句子级(音轨停顿)→ 估算,逐级降级,任何一步失败都不影响烧录
        cues: List[compose.Cue] = []
        aligned = False
        word_level = False
        words = await asr.transcribe_words(local_video)
        if words:
            cues = asr.cues_from_words(words, sentences)
            word_level = bool(cues)
        if not cues:
            silences = await detect_speech_segments(local_video, duration_sec)
            cues = _cues_from(script, sentences, duration_sec, silences)
            aligned = bool(silences)
        if not cues:
            logger.info("[subtitle] 跳过字幕烧录:未生成任何字幕条目")
            return None, []
        # ⑤-½ 字幕跟随头部(caption-tracking):开启时按头部位置烧录 ASS,否则底部居中
        caption_tracking = bool(params.get("caption_tracking"))
        head_boxes = None
        canvas = None
        if caption_tracking:
            head_boxes = await _resolve_head_boxes(params, local_video)
            if head_boxes:
                canvas = compose.video_canvas(params.get("ratio"), params.get("resolution"))
        if head_boxes and canvas:
            if cues and head_boxes:
                _attach_head_positions(cues, head_boxes)
            ass_path = os.path.join(workdir, "sub.ass")
            with open(ass_path, "w", encoding="utf-8") as f:
                f.write(compose.build_ass(cues, canvas))
            logger.info("[subtitle] 字幕跟随头部:按头部位置烧录 ASS")
            sub_name = os.path.basename(ass_path)
            burn_builder = compose.build_burn_subtitle_ass_cmd
        else:
            if caption_tracking:
                logger.info("[subtitle] 字幕跟随头部:未获得头部轨迹(未配置网关/无预标注/无头),回退底部字幕")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(compose.build_srt(cues))
            sub_name = os.path.basename(srt_path)
            burn_builder = compose.build_burn_subtitle_cmd

        # ⑥ 烧录:cwd 切到字幕文件所在目录,避免 Windows 盘符冒号被 filter 当分隔符
        # 字幕风格(caption_style)对齐 Hypit captions「Fine styles」,留空回退默认白字黑边
        style = compose.caption_style(font, params.get("caption_style"))
        cmd = burn_builder(local_video, sub_name, burned_path, style, fonts_dir)
        result = await compose.run(cmd, timeout=BURN_TIMEOUT, cwd=workdir)
        if not result.get("ok"):
            logger.warning(f"[subtitle] 字幕烧录失败,保留原片: {result.get('stderr')}")
            return None, []

        # ⑦ 上传回 OSS:失败也必须保留原 URL
        # 关键兜底:oss.put_object 是同步 SDK 调用,其默认连接超时可能极长甚至无超时,
        # 而这里用 asyncio.to_thread 调它又没外层超时 —— 一旦 OSS 上传 hang 住,整个任务会
        # 永久卡在 processing、心跳却一直回传 processing(dev/prod 均复现过)。
        # 用 asyncio.wait_for 兜底:超时即视为上传失败、保留原片,绝不让任务卡死。
        key = f"generate/result/{prefix or 'subtitle'}_{uuid.uuid4().hex[:8]}.mp4"
        try:
            new_url = await asyncio.wait_for(
                asyncio.to_thread(upload_local_file, burned_path, key),
                timeout=300,
            )
        except asyncio.TimeoutError:
            logger.warning("[subtitle] 烧录产物上传 OSS 超时,保留原片")
            return None, []
        if not new_url:
            logger.warning("[subtitle] 烧录产物上传失败,保留原片")
            return None, []

        logger.info(
            f"[subtitle] 字幕已烧进成片 font={font} "
            f"level={'word' if word_level else ('sentence' if aligned else 'estimate')} "
            f"cues={len(cues)} → {new_url}"
        )
        return new_url, cues
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[subtitle] 字幕烧录异常,保留原片: {exc}")
        return None, []
    finally:
        # 临时文件一律清理(下载的原片 + 烧录产物 + SRT)
        for path in (local_video, burned_path, srt_path, ass_path):
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


async def compute_cues(
    video_url: str, params: Dict[str, Any], duration_sec: float,
) -> Optional[List[compose.Cue]]:
    """仅计算字幕时间轴(下载 + ASR + 停顿对齐),不烧录。

    供代码渲染层(overlay.py)复用:它需要先拿到与成片对齐的 cue,才能把字幕画成
    动态排版叠加层。任何一步失败返回 None(调用方据此跳过代码渲染、回退 ASS 烧录)。
    与 burn_subtitle_with_cues 的 ④⑤ 逻辑同源,但不生成 SRT/ASS、不写盘、不上传。
    """
    if not video_url:
        return None
    if not compose.available():
        return None
    if not compose.resolve_subtitle_font():
        return None
    script, sentences = _script_and_sentences(params)
    if not sentences:
        return None
    workdir = tempfile.mkdtemp(prefix="cues_")
    local_video: Optional[str] = None
    try:
        local_video = await asyncio.to_thread(download_to_local, video_url, ".mp4")
        if not local_video:
            return None
        cues: List[compose.Cue] = []
        words = await asr.transcribe_words(local_video)
        if words:
            cues = asr.cues_from_words(words, sentences) or []
        if not cues:
            silences = await detect_speech_segments(local_video, duration_sec)
            cues = _cues_from(script, sentences, duration_sec, silences)
        if not cues:
            return None
        return cues
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[subtitle] 时间轴计算异常,跳过代码渲染: {exc}")
        return None
    finally:
        if local_video and os.path.exists(local_video):
            try:
                os.remove(local_video)
            except OSError:
                pass
        if os.path.isdir(workdir):
            try:
                os.rmdir(workdir)
            except OSError:
                pass


async def burn_subtitle(
    video_url: str, params: Dict[str, Any], duration_sec: float, prefix: str = "",
) -> Optional[str]:
    """兼容入口:只返回烧录后的 URL(失败返回 None)

    多数调用方只关心"烧没烧成功";需要**真实时间轴**的调用方(如 BaseGenService
    把它随用量回写 backend,供"改一句台词重跑"定位真实时间窗)请用 burn_subtitle_with_cues。
    """
    url, _cues = await burn_subtitle_with_cues(video_url, params, duration_sec, prefix)
    return url
