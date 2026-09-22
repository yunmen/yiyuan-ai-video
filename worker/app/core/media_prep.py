# -*- coding: utf-8 -*-
'''
@文件    :media_prep.py
@说明    :参考素材预处理 — 在提交前把素材规整到模型侧能接受的范围内。
          视频编辑(Seedance 2.x)对**参考视频时长**有硬上限(实测 15.2s),
          超限直接 400,且错误信息只指向 `content[4]` 这样的数组下标,极难定位
          (用户看到的就是「生成失败」)。这里自动裁剪,用户不必自己剪视频。
@时间    :2026/09/21 22:00:00
@作者    :一源AI
@版本    :1.0
'''
import asyncio
import base64
import os
import re
import tempfile
import uuid
from typing import Dict, List, Optional, Tuple

import httpx

from app.core import deidentify
from app.core.compose import ffmpeg_path, run
from app.core.plugin import logger
from app.settings import config
from app.utils.oss import download_to_local, upload_local_file

# 参考视频时长上限(秒):方舟 Seedance 2.x 实测上限 15.2s,留出余量裁到 15s
# (留 0.2s 余量,避免容器时长取整后刚好越界)
MAX_REFERENCE_SECONDS = 15.0

# 视频编辑(v2v)的参考视频时长上限(秒):方舟按编辑任务判定时明确要求 4~30s,
# 沿用 15s 会把长片后半段白裁掉 —— 编辑链路单独放宽到 30s。
VIDEO_EDIT_MAX_REFERENCE_SECONDS = 30.0

# 目标画幅 → 输出尺寸(短边 720,与模型 720p 上限一致;像素数须 ≥ 407696)。
# 方舟视频编辑只接受 ratio=adaptive(成片画幅跟随参考视频),故必须把参考视频
# 变成目标画幅,请求里的 9:16 才不会被静默忽略(实测:请求 9:16、成片 16:9)。
_RATIO_SIZES = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
    "1:1": (720, 720),
    "4:3": (960, 720),
    "3:4": (720, 960),
}


def _ratio_size(ratio: str) -> Optional[Tuple[int, int]]:
    """画幅字符串 → 输出尺寸;认不出返回 None(调用方按"不需要处理"放行)"""
    key = str(ratio or "").strip().replace("：", ":").replace("x", ":").lower()
    return _RATIO_SIZES.get(key)


def _ratio_close(size: Tuple[int, int], target: Tuple[int, int], tolerance: float = 0.02) -> bool:
    """两个尺寸的画幅是否足够接近(默认 2% 容差,避免就为了 1px 差异白转一次)"""
    w, h = size
    tw, th = target
    if not w or not h or not tw or not th:
        return True
    return abs((w / h) - (tw / th)) / (tw / th) <= tolerance


async def probe_size(path_or_url: str, timeout: int = 60) -> Optional[Tuple[int, int]]:
    """读取视频分辨率 (宽, 高);读取失败返回 None(调用方按「未知」放行)"""
    result = await run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path_or_url,
    ], timeout=timeout)
    if not result.get("ok"):
        return None
    try:
        raw = (result.get("stdout") or "").strip().splitlines()[0]
        w, h = raw.split("x")[:2]
        return (int(w), int(h))
    except (ValueError, IndexError):
        return None


async def probe_duration(path_or_url: str, timeout: int = 60) -> Optional[float]:
    """读取媒体时长(秒);读取失败返回 None(调用方按「未知」放行)"""
    result = await run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path_or_url,
    ], timeout=timeout)
    if not result.get("ok"):
        return None
    try:
        return float((result.get("stdout") or "").strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


# ---- 主体感知裁切 ----
# 跨画幅裁切(如 16:9 → 9:16)按居中裁可能把偏侧的主体切掉。裁切前抽几帧交给多模态模型
# 判断主体的水平位置,据此偏移裁切窗口;任何一步失败都回退居中裁切,绝不阻断任务。
SUBJECT_FRAME_COUNT = 3                        # 抽帧数量(沿时长均匀取样,覆盖全片)
SUBJECT_VISION_TIMEOUT = 30.0                  # 主体位置识别请求超时(秒)
SUBJECT_MIN_PCT, SUBJECT_MAX_PCT = 5.0, 95.0   # 结果夹紧,避免极端偏移把画面裁歪
SUBJECT_PROMPT = (
    "下面是同一段视频的几帧画面。请判断画面**主体**(主要人物 / 商品 / 视觉焦点)"
    "的水平中心位于画面宽度的百分之多少(最左=0,正中=50,最右=100)。"
    "只输出一个 0-100 的整数,不要任何其他文字。"
)


def _parse_pct(text: str) -> Optional[float]:
    """从模型回复里取第一个 0-100 的整数;取不到返回 None"""
    match = re.search(r"\d{1,3}", str(text or ""))
    if not match:
        return None
    pct = float(match.group())
    if pct < 0 or pct > 100:
        return None
    return min(max(pct, SUBJECT_MIN_PCT), SUBJECT_MAX_PCT)


async def _extract_frames(video: str, ffmpeg: str, workdir: str, duration: Optional[float]) -> List[str]:
    """沿时长均匀抽几帧(某个时间点抽不到就跳过,不影响其余)"""
    total = duration or 0.0
    if total > 0:
        times = [total * (i + 1) / (SUBJECT_FRAME_COUNT + 1) for i in range(SUBJECT_FRAME_COUNT)]
    else:
        times = [0.0]
    frames: List[str] = []
    for idx, at in enumerate(times):
        out = os.path.join(workdir, f"frame_{idx}.jpg")
        result = await run([
            ffmpeg, "-y", "-ss", f"{at:.2f}", "-i", video,
            "-frames:v", "1", "-vf", "scale=480:-1", out,
        ], timeout=120)
        if result.get("ok") and os.path.exists(out):
            frames.append(out)
    return frames


async def _subject_position_pct(frames: List[str]) -> Optional[float]:
    """让多模态模型判断主体的水平位置(占画面宽度百分比);失败返回 None(回退居中)

    复用 chat 网关的对话模型(方舟上的 GLM 支持图片输入),不额外引入视觉模型依赖。
    """
    if not frames:
        return None
    model = str(getattr(config, "CHAT_MODEL", "") or "").strip()
    base = str(config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL or "").rstrip("/")
    key = config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY
    if not (model and base and key):
        return None
    try:
        content: List[dict] = [{"type": "text", "text": SUBJECT_PROMPT}]
        for path in frames:
            with open(path, "rb") as fp:
                b64 = base64.b64encode(fp.read()).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
            "max_tokens": 16,
        }
        async with httpx.AsyncClient(timeout=SUBJECT_VISION_TIMEOUT) as cli:
            resp = await cli.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json=payload,
            )
            resp.raise_for_status()
            text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[media_prep] 主体位置识别失败,回退居中裁切: {exc}")
        return None
    pct = _parse_pct(text)
    if pct is not None:
        logger.info(f"[media_prep] 主体水平位置识别为 {pct:.0f}%,据此偏移裁切窗口")
    return pct


async def _crop_x_aware(
    local: str, ffmpeg: str, duration: Optional[float], width: int, crop_w: int,
) -> int:
    """裁切窗口的横向起点:按主体位置偏移;识别失败或无需裁宽时居中"""
    center = (width - crop_w) // 2
    if crop_w >= width:
        return 0
    workdir = tempfile.mkdtemp(prefix="subj_")
    try:
        frames = await _extract_frames(local, ffmpeg, workdir, duration)
        pct = await _subject_position_pct(frames)
    finally:
        for name in os.listdir(workdir):
            try:
                os.remove(os.path.join(workdir, name))
            except OSError:
                pass
        try:
            os.rmdir(workdir)
        except OSError:
            pass
    if pct is None:
        return center
    offset = int(width * pct / 100.0 - crop_w / 2.0)
    return max(0, min(offset, width - crop_w))


async def fit_reference_video(
    url: str, max_seconds: float = MAX_REFERENCE_SECONDS, ratio: str = "",
) -> str:
    """把参考视频规整到模型可接受范围:时长不超上限 + (给了 ratio 时)画幅对齐目标比例。

    为什么要对齐画幅:方舟视频编辑只接受 `ratio=adaptive` —— **成片画幅跟随被编辑的
    参考视频**。参考视频若不是目标画幅,请求里的 9:16 会被静默忽略、成片变成 16:9
    (实测踩过)。这里提前把参考视频裁到目标画幅,让 adaptive 输出落在正确画幅上。

    设计原则:**任何一步失败都返回原始 URL**。预处理是尽力而为的优化 ——
    裁不动不该让整单任务失败(模型侧可能仍接受;真不行还有上层降级兜底)。
    """
    if not url:
        return url
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return url

    # 只在明确要改画幅时才探分辨率:不传 ratio 的老调用保持"零额外开销"
    target_size = _ratio_size(ratio)
    size: Optional[Tuple[int, int]] = await probe_size(url) if target_size else None
    duration = await probe_duration(url)

    need_trim = duration is not None and duration > max_seconds
    need_ratio = target_size is not None and size is not None and not _ratio_close(size, target_size)
    if not need_trim and not need_ratio:
        return url

    reasons = []
    if need_trim and duration is not None:
        reasons.append(f"时长 {duration:.1f}s > {max_seconds}s")
    if need_ratio and size is not None:
        reasons.append(f"画幅 {size[0]}x{size[1]} ≠ {ratio}")
    logger.info(f"[media_prep] 参考视频需预处理({'；'.join(reasons)}),自动转换")

    suffix = os.path.splitext(url.split("?")[0])[1] or ".mp4"
    local = download_to_local(url, suffix=suffix)
    if not local:
        logger.warning("[media_prep] 参考视频下载失败,保留原片(交由模型侧判定)")
        return url

    out_path = os.path.join(tempfile.gettempdir(), f"ref_{uuid.uuid4().hex}.mp4")
    try:
        cmd = [ffmpeg, "-y", "-i", local]
        if need_ratio and target_size is not None and size is not None:
            tw, th = target_size
            iw, ih = size
            # 先算"铺满目标画幅"的最大内接裁切框:裁掉的正是成片里本就不存在的部分
            if iw / ih > tw / th:
                crop_w, crop_h = int(ih * tw / th), ih   # 原片更宽 → 裁宽(主体可能偏侧)
            else:
                crop_w, crop_h = iw, int(iw * th / tw)   # 原片更长 → 裁高
            crop_w -= crop_w % 2
            crop_h -= crop_h % 2
            # 横向裁切时按主体位置偏移窗口,而不是死板居中
            crop_x = await _crop_x_aware(local, ffmpeg, duration, iw, crop_w)
            crop_x -= crop_x % 2
            crop_y = (ih - crop_h) // 2
            crop_y -= crop_y % 2
            cmd += ["-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={tw}:{th}"]
        if need_trim:
            cmd += ["-t", str(max_seconds)]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out_path]
        result = await run(cmd, timeout=300)
        if not result.get("ok") or not os.path.exists(out_path):
            logger.warning(f"[media_prep] 参考视频预处理失败,保留原片: {result.get('stderr')}")
            return url
        new_url = upload_local_file(out_path, f"reference/{uuid.uuid4().hex}.mp4")
        if not new_url:
            logger.warning("[media_prep] 预处理后的参考视频上传失败,保留原片")
            return url
        logger.info(f"[media_prep] 参考视频已预处理并替换: {new_url}")
        return new_url
    finally:
        # 清理临时文件(下载的原片 + 产物),避免任务多了把磁盘吃满
        for path in [p for p in (local, out_path) if p]:
            try:
                os.remove(path)
            except OSError:
                pass


# 参考视频"是否含真人"的判定结果与去身份化产物缓存:{原URL: 可用URL}
# 同一参考视频会在重试/多任务中被反复处理,而 COS 对象名是随机的 —— 没有这张表就会
# 每次都重新检测并重新上传一份。上限避免长期运行把内存吃满。
_DEID_CACHE: Dict[str, str] = {}
_DEID_CACHE_MAX = 32


def _remember_deid(src: str, resolved: str) -> None:
    if len(_DEID_CACHE) >= _DEID_CACHE_MAX:
        _DEID_CACHE.pop(next(iter(_DEID_CACHE)))
    _DEID_CACHE[src] = resolved


async def deidentify_reference_video(url: str) -> str:
    """参考视频若含真人(方舟会直接拒绝),本地去身份化后返回新 URL;**不含真人/处理失败一律原样返回**。

    只在提交被"含真人"拦下后调用,所以正常任务只会多一次秒级抽样检测,不会平白多一次转码与上传。
    去身份化本身有画面代价(打码处就是要被替换的主体),因此调用方必须把这件事**显式回写**给用户,
    不能静默替换。
    """
    if not url:
        return url
    cached = _DEID_CACHE.get(url)
    if cached:
        return cached
    if not ffmpeg_path():
        logger.warning("[media_prep] 无可用 ffmpeg,跳过真人去身份化(保留原片)")
        return url

    suffix = os.path.splitext(url.split("?")[0])[1] or ".mp4"
    local = download_to_local(url, suffix=suffix)
    if not local:
        logger.warning("[media_prep] 去身份化:参考视频下载失败,保留原片")
        return url

    out_path = os.path.join(tempfile.gettempdir(), f"deid_{uuid.uuid4().hex}.mp4")
    try:
        # 同步的 ffmpeg/cv2 处理挪到线程,别把事件循环堵住(其他任务还在轮询)
        info = await asyncio.to_thread(deidentify.deidentify_video, local, out_path)
        if not info.get("detected"):
            _remember_deid(url, url)          # 不含真人:记住"无需处理",后续提交不再重复检测
            logger.info("[media_prep] 抽样未检测到真人,保留原片")
            return url
        new_url = upload_local_file(out_path, f"deidentified/{uuid.uuid4().hex}.mp4")
        if not new_url:
            logger.warning("[media_prep] 去身份化产物上传失败,保留原片")
            return url
        _remember_deid(url, new_url)
        logger.info(
            f"[media_prep] 参考视频已本地去身份化(命中 {info.get('hits')} 次,"
            f"打码区 {info.get('box')},源 {info.get('size')}): {new_url}"
        )
        return new_url
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[media_prep] 本地去身份化失败,保留原片: {exc}")
        return url
    finally:
        for path in [p for p in (local, out_path) if p]:
            try:
                os.remove(path)
            except OSError:
                pass
