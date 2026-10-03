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
import time
import uuid
from typing import Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from app.core import deidentify
from app.core import gateway
from app.core import shots
from app.core.compose import ffmpeg_path, run
from app.core.plugin import logger
from app.settings import config
from app.utils.oss import download_to_local, upload_local_file

# 参考视频时长上限(秒):方舟 Seedance 2.x 实测上限 15.2s,留出余量裁到 15s
# (留 0.2s 余量,避免容器时长取整后刚好越界)
MAX_REFERENCE_SECONDS = 15.0

# 视频编辑(v2v)的参考视频时长上限(秒):方舟按编辑任务判定时明确要求 4~30s,
# 沿用 15s 会把长片后半段白裁掉 —— 编辑链路单独放宽到 30s。
# 该值后台可配(见 runtime_config KEY_MAP: gen.video_edit_max_seconds →
# settings.VIDEO_EDIT_MAX_REFERENCE_SECONDS),运维按模型真实上限调整;
# settings 为该值的单一事实源,此处不再重复定义常量(消除副本漂移)。


def video_edit_max_seconds() -> float:
    """视频编辑(复刻)参考视频时长上限:优先取后台可配 gen.video_edit_max_seconds,
    未配或值非法回退内置默认 30s(与 settings.VIDEO_EDIT_MAX_REFERENCE_SECONDS 默认一致)。
    避免 media_prep 与 settings 各写一份 30.0 互相矛盾。
    """
    try:
        return float(getattr(config, "VIDEO_EDIT_MAX_REFERENCE_SECONDS", 30.0))
    except (TypeError, ValueError):
        return 30.0

# 目标画幅 → 宽高比(输出尺寸的短边由 gen.reference_short_side 配置决定,默认 720)。
# 方舟视频编辑只接受 ratio=adaptive(成片画幅跟随参考视频),故必须把参考视频
# 变成目标画幅,请求里的 9:16 才不会被静默忽略(实测:请求 9:16、成片 16:9)。
_RATIO_ASPECTS = {
    "9:16": (9, 16),
    "16:9": (16, 9),
    "1:1": (1, 1),
    "4:3": (4, 3),
    "3:4": (3, 4),
}

# 方舟对编辑输入的最小像素数要求:低于它在提交阶段就会被拒(等于白跑一轮)
MIN_REFERENCE_PIXELS = 407696
# 短边合法下限:再小基本是配置写错,回落到默认值而不是产出必然失败的尺寸
MIN_SHORT_SIDE = 480
DEFAULT_SHORT_SIDE = 720


def reference_short_side() -> int:
    """参考视频输出短边:取后台可配 gen.reference_short_side(默认 720)

    配置非法或过小时回落 720,避免把"必然被模型拒绝的尺寸"提交上去。
    """
    try:
        value = int(getattr(config, "REFERENCE_SHORT_SIDE", DEFAULT_SHORT_SIDE) or DEFAULT_SHORT_SIDE)
    except (TypeError, ValueError):
        return DEFAULT_SHORT_SIDE
    return value if value >= MIN_SHORT_SIDE else DEFAULT_SHORT_SIDE


def _ratio_size(ratio: str) -> Optional[Tuple[int, int]]:
    """画幅字符串 → 输出尺寸(短边按配置,宽高对齐到偶数);认不出返回 None

    为什么短边要可配:此前写死 720(与当时的模型上限一致),换成支持 1080P 的编辑模型后
    成片仍被压到 720p —— 画质上限被一行常量锁死(与 VIDEO_RESOLUTION_CAP 同类问题)。
    """
    key = str(ratio or "").strip().replace("：", ":").replace("x", ":").lower()
    aspect = _RATIO_ASPECTS.get(key)
    if not aspect:
        return None
    a, b = aspect
    short = reference_short_side()
    if a >= b:
        width, height = int(round(short * a / b)), short
    else:
        width, height = short, int(round(short * b / a))
    # 编码器要求宽高为偶数:奇数尺寸会被 libx264 直接拒绝
    width -= width % 2
    height -= height % 2
    # 像素数不足时按比例放大到满足最小要求,避免提交一个必然失败的编辑请求
    if width * height < MIN_REFERENCE_PIXELS:
        scale = (MIN_REFERENCE_PIXELS / float(width * height)) ** 0.5
        width = int((width * scale + 1) // 2 * 2)
        height = int((height * scale + 1) // 2 * 2)
    return (width, height)


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


async def has_audio_stream(path: str, timeout: int = 30) -> bool:
    """探测媒体是否含音频流;失败按 False(交由调用方降级)。

    用于转场拼接前的兜底:xfade 的 acrossfade 要求每段都有音轨,
    逐镜 i2v 段偶发无音轨时会导致整条过滤链失败、静默降级成硬切 ——
    这里先探出无音轨的段,给它们补一条静音音轨再转场。
    """
    result = await run([
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index", "-of", "csv=p=0", path,
    ], timeout=timeout)
    if not result.get("ok"):
        return False
    return bool((result.get("stdout") or "").strip())


# ---- 主体感知裁切 ----
# 跨画幅裁切(如 16:9 → 9:16)按居中裁可能把偏侧的主体切掉。裁切前抽几帧交给多模态模型
# 判断主体的水平位置,据此偏移裁切窗口;任何一步失败都回退居中裁切,绝不阻断任务。
SUBJECT_FRAME_COUNT = 3                        # 抽帧数量(沿时长均匀取样,覆盖全片)
SUBJECT_VISION_TIMEOUT = 60.0                  # 主体位置识别请求超时(秒);多模态视觉模型处理多张帧 + 网关转发,8s 极易超时触发冷却循环,对齐逐镜头逆推的 90s 档给 60s 余量
SUBJECT_MIN_PCT, SUBJECT_MAX_PCT = 5.0, 95.0   # 结果夹紧,避免极端偏移把画面裁歪
SUBJECT_PROMPT = (
    "下面是同一段视频的几帧画面。请判断画面**主体**(主要人物 / 商品 / 视觉焦点)"
    "的水平中心位于画面宽度的百分之多少(最左=0,正中=50,最右=100)。"
    "只输出一个 0-100 的整数,不要任何其他文字。"
)

# 主体识别是"锦上添花":网关不给权限(403/401)或没这个模型(404)时,它**永远不会成功**,
# 却每次都要等满单个候选的超时才回退居中 —— 一单会触发多次(参考视频一次、成片修正再一次),
# (参考视频一次、成片修正再一次),实测白耗 60s 以上。这里把这类**确定性失败**短路:
# 命中即进入冷却期,期内直接居中裁切,不再发请求。超时/5xx 属于偶发,不短路。
_SUBJECT_VISION_COOLDOWN = 1800.0        # 冷却秒数(30 分钟后重试一次,够运营换配置)
_SUBJECT_VISION_FATAL_STATUS = (401, 403, 404)
# 偶发失败(超时/5xx)连续达此数同样进冷却:网关整体不可用时,不能让每单都白等一个超时
_SUBJECT_VISION_FAIL_LIMIT = 3
_subject_vision_state = {"disabled_until": 0.0, "fails": 0}


def _is_fatal_vision_error(exc: Exception) -> bool:
    """是否属于"重试也没用"的确定性失败:权限/模型不存在"""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return status in _SUBJECT_VISION_FATAL_STATUS


def _parse_pct(text: str) -> Optional[float]:
    """从模型回复里取第一个 0-100 的整数;取不到返回 None"""
    match = re.search(r"\d{1,3}", str(text or ""))
    if not match:
        return None
    pct = float(match.group())
    if pct < 0 or pct > 100:
        return None
    return min(max(pct, SUBJECT_MIN_PCT), SUBJECT_MAX_PCT)


async def _extract_frames(
    video: str, ffmpeg: str, workdir: str, duration: Optional[float],
    times: Optional[List[float]] = None,
) -> List[str]:
    """按给定时间点抽帧;未给时间点时沿时长均匀抽几帧(某个点抽不到就跳过,不影响其余)

    times 由镜头结构解析(shots.shot_frame_times)给出时,抽的是**每个镜头的首帧**;
    均匀抽帧只按时间取样,会漏掉原片真正的场景变化 —— 两者的差别就是这里。
    """
    if not times:
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


async def _shot_frame_times(video: str, duration: Optional[float]) -> Optional[List[float]]:
    """按镜头首帧给出抽帧时间点;镜头检测不可用时返回 None(调用方回退均匀抽帧)"""
    if not duration or duration <= 0:
        return None
    table = await shots.detect_shots(video, duration)
    points = shots.shot_frame_times(table)
    if points:
        logger.info(f"[media_prep] 按镜头首帧抽帧: {len(points)} 帧(检测到 {len(table)} 个镜头)")
    return points or None


async def extract_reference_frames(video: str) -> List[str]:
    """抽样参考视频帧(本地路径或可拉取地址),供「视频编辑失败 → 抽帧走 r2v」降级复用(O3)。

    抽帧点**优先取每个镜头的首帧**(P0 镜头结构解析):均匀抽 3 帧会漏掉镜头结构 ——
    8 个镜头的原片,3 帧很可能全落在同一个镜头里,r2v 拿到的参考画面覆盖不到原片
    真正的场景与构图变化。镜头检测不可用(无 ffmpeg / 时长未知 / 检测失败)时
    自动回退原有的均匀抽帧,行为与改造前一致。

    任何一步失败返回空列表(调用方据此退回原降级链路,不阻断)。
    返回的是本地临时文件,调用方需自行上传 OSS 并在使用后清理临时目录。
    """
    if not video:
        return []
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return []
    duration = await probe_duration(video)
    workdir = tempfile.mkdtemp(prefix="ref_frames_")
    try:
        times = await _shot_frame_times(video, duration)
        return await _extract_frames(video, ffmpeg, workdir, duration, times=times)
    finally:
        # 仅清理空目录:帧文件交给调用方上传/清理,避免误删正在用的文件
        try:
            os.rmdir(workdir)
        except OSError:
            pass


async def _subject_position_pct(frames: List[str]) -> Optional[float]:
    """让多模态模型判断主体的水平位置(占画面宽度百分比);失败返回 None(回退居中)

    必须使用支持图片输入的多模态模型(VISION_MODEL):此前复用 CHAT_MODEL(qwen3.7-max 等纯文本模型),
    带图请求被上游以 400/500 拒绝,只能静默回退居中裁切,v2v 人物可能被裁偏(实测踩过)。
    优先走与逐镜头理解一致的 vision 网关与 VISION_MODEL;
    VISION_MODEL 未配置时直接跳过(回退居中),不再回退纯文本 chat 网关(会必然失败)。
    """
    if not frames:
        return None
    # 冷却期内不发请求:上一次已证明这个视觉网关整体用不了,再试只是白等一个超时
    if time.time() < _subject_vision_state["disabled_until"]:
        return None
    # 主体识别必须是多模态模型;未配置 VISION_MODEL 直接跳过(回退居中),
    # 切勿回退纯文本 CHAT_MODEL —— 纯文本模型不支持 image_url,带图请求必被网关 400/500 拒绝。
    vision_model = str(getattr(config, "VISION_MODEL", "") or "").strip()
    if not vision_model:
        logger.info("[media_prep] 未配置 VISION_MODEL(视觉模型),跳过主体位置识别,回退居中裁切")
        return None
    # 走 resolve_all 故障转移:首个候选网关不含该视觉模型(404)时自动试下一个,
    # 与逐镜头逆推(VideoUnderstandTool)保持一致,避免只试第一个网关就立即进冷却。
    candidates = gateway.resolve_all("vision")
    if not candidates:
        logger.warning(
            "[media_prep] 未解析到任何 vision 网关候选;请在管理端配置 gen.gw.<网关>.url/.key"
            "并用 gen.route.vision 指向它(方舟视觉模型需 gen.route.vision=ark + gen.gw.ark.url/.key)"
        )
        return None
    # 过滤出 url/key 完整的可用候选;只配了模型名却漏配网关密钥会导致 401/404,
    # 此处提前给出明确配置提示,避免静默回退居中而难以定位根因。
    usable = [g for g in candidates if (g.get("url") or "").strip() and (g.get("key") or "").strip()]
    if not usable:
        names = ", ".join(g.get("name", "?") for g in candidates)
        logger.warning(
            f"[media_prep] 视觉模型已配置(VISION_MODEL={vision_model}),但候选网关均缺少 url/key: {names};"
            "请在管理端配置 gen.gw.<网关>.url / gen.gw.<网关>.key"
            "(方舟视觉模型需 gen.gw.ark.url / gen.gw.ark.key,并用 gen.route.vision 指向 ark)"
        )
        return None
    # 组装请求体:图片带 detail=low(低分辨率足够判断主体位置,省 token 且兼容性更好,
    # 与逐镜头逆推一致;无 detail 时部分视觉模型默认高分辨率,易慢/失败)。
    # 重要:统一用 AsyncOpenAI SDK 发请求,与逐镜头逆推(VideoUnderstandTool)保持一致。
    # 此前用裸 httpx 手搓 POST,在 relay/中转站下字段/请求头与 SDK 不完全等价,
    # 中转站对手搓请求直接 400/404 → 命中冷却 → 永久失败;逐镜头逆推用 SDK 却正常,
    # 这正是"同模型同中转站、主体识别一直失败"的根因。
    content: List[dict] = [{"type": "text", "text": SUBJECT_PROMPT}]
    for path in frames:
        with open(path, "rb") as fp:
            b64 = base64.b64encode(fp.read()).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"},
        })
    messages = [{"role": "user", "content": content}]
    last_exc: Optional[Exception] = None
    for gw in usable:
        base_url = str(gw.get("url") or "").rstrip("/")
        key = gw.get("key") or ""
        if not (base_url and key):
            continue
        try:
            client = AsyncOpenAI(api_key=key, base_url=base_url, timeout=SUBJECT_VISION_TIMEOUT)
            resp = await client.chat.completions.create(
                model=vision_model,
                messages=messages,
                temperature=0,
                max_tokens=16,
            )
            text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        except Exception as exc:  # noqa: BLE001
            # 401/403/404 是该候选网关的配置问题(没权限/没模型),不会自愈;记下来试下一个候选。
            # 超时/5xx 属偶发,也试下一个候选。
            last_exc = exc
            logger.warning(f"[media_prep] 主体识别网关 {gw.get('name')} 失败({exc}),尝试下一个候选")
            continue
        # 任一候选成功:连续失败计数归零并直接返回(成功无需再试)
        _subject_vision_state["fails"] = 0
        pct = _parse_pct(text)
        if pct is not None:
            logger.info(f"[media_prep] 主体水平位置识别为 {pct:.0f}%,据此偏移裁切窗口")
        return pct
    # 所有候选都失败:决定冷却。fatal(401/403/404)一次性冷却;偶发(超时/5xx)连续 3 次才冷却。
    if last_exc is not None:
        if _is_fatal_vision_error(last_exc):
            _subject_vision_state["fails"] = _SUBJECT_VISION_FAIL_LIMIT
        else:
            _subject_vision_state["fails"] += 1
        if _subject_vision_state["fails"] >= _SUBJECT_VISION_FAIL_LIMIT:
            _subject_vision_state["disabled_until"] = time.time() + _SUBJECT_VISION_COOLDOWN
            logger.warning(
                f"[media_prep] 主体识别连续不可用({last_exc or '超时'}),"
                f"{int(_SUBJECT_VISION_COOLDOWN)}s 内直接居中裁切,不再逐单等待"
            )
        else:
            logger.warning(f"[media_prep] 主体位置识别失败,回退居中裁切: {last_exc}")
    return None


async def _crop_x_aware(
    local: str, ffmpeg: str, duration: Optional[float], width: int, crop_w: int,
    allow_center: bool = True,
) -> Optional[int]:
    """裁切窗口的横向起点:按主体位置偏移;识别失败时居中(allow_center)或放弃(返回 None)

    返回 None 表示"无法定位主体、且调用方不允许赌居中",由调用方决定退路。
    """
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
        # 居中兜底本质是"赌一把":横向裁切会丢掉左右画面(16:9 → 9:16 只保留约 31% 宽度),
        # 主体一旦偏侧就被整段切走 —— 实测成片里"主角和狗推婴儿车"就是这么消失的。
        # 参考视频规整阶段允许赌(不裁的话编辑任务画幅必然跑偏,居中优于不裁);
        # 成片修正阶段绝不允许赌(成片已付费、不可重来),此时返回 None 让调用方保留原片。
        return center if allow_center else None
    offset = int(width * pct / 100.0 - crop_w / 2.0)
    return max(0, min(offset, width - crop_w))


async def fit_reference_video(
    url: str, max_seconds: Optional[float] = MAX_REFERENCE_SECONDS, ratio: str = "",
    key_prefix: str = "reference", label: str = "参考视频",
    allow_center_crop: bool = True,
) -> str:
    """把视频规整到模型可接受范围:时长不超上限 + (给了 ratio 时)画幅对齐目标比例。

    为什么要对齐画幅:方舟视频编辑只接受 `ratio=adaptive` —— **成片画幅跟随被编辑的
    参考视频**。参考视频若不是目标画幅,请求里的 9:16 会被静默忽略、成片变成 16:9
    (实测踩过)。这里提前把参考视频裁到目标画幅,让 adaptive 输出落在正确画幅上。

    复用于成片:模型同样可能无视画幅(实测参考视频已裁成 9:16,成片仍是 1280x720),
    所以自检发现画幅跑偏时也调这里做一次修正 —— 传 key_prefix/label 换掉上传目录与日志主语,
    max_seconds 传 None(成片时长就是用户要的时长,绝不能截)。

    allow_center_crop:横向裁切时主体位置识别失败,是否允许居中兜底。
      · True (默认):参考视频规整阶段 —— 不裁会让编辑任务画幅必然跑偏,居中优于不裁;
      · False:成片修正阶段 —— 成片已付费、不可重来,居中硬裁会切走主体,
        此时宁可**放弃修正、保留原片**,把"画幅没修正"这个事实暴露给上层判失败。

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

    # 只要配置了时长上限就强制裁剪:ffprobe 探不到时长(duration=None)时也不能静默放行超长视频
    # (否则会间歇性地原片直发方舟、被 15.2s 上限 400 拒);-t 只截断不延长,对短视频是 no-op,安全。
    need_trim = bool(max_seconds) and max_seconds > 0 and (duration is None or duration > max_seconds)
    need_ratio = target_size is not None and size is not None and not _ratio_close(size, target_size)
    if not need_trim and not need_ratio:
        return url

    reasons = []
    if need_trim and duration is not None:
        reasons.append(f"时长 {duration:.1f}s > {max_seconds}s")
    elif need_trim and duration is None:
        reasons.append(f"时长探测失败,按上限 {max_seconds}s 强制裁")
    if need_ratio and size is not None:
        reasons.append(f"画幅 {size[0]}x{size[1]} ≠ {ratio}")
    logger.info(f"[media_prep] {label}需预处理({'；'.join(reasons)}),自动转换")

    suffix = os.path.splitext(url.split("?")[0])[1] or ".mp4"
    # to_thread:下载是同步阻塞 I/O,直接调会卡死整个 worker 事件循环 ——
    # 并发任务(ARQ concurrency=5)会一起陪等,实测同一操作从 3s 涨到 33s。
    local = await asyncio.to_thread(download_to_local, url, suffix=suffix)
    if not local:
        logger.warning(f"[media_prep] {label}下载失败,保留原片")
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
            crop_x = await _crop_x_aware(
                local, ffmpeg, duration, iw, crop_w, allow_center=allow_center_crop,
            )
            if crop_x is None:
                # 主体位置识别失败且不允许居中兜底:放弃裁切,保留原片。
                # 这不是"放弃优化",而是**避免把主体切走** —— 成片修正场景下,
                # 居中硬裁出一个主体残缺的竖版片,比保留横版片更糟(前者用户无从察觉)。
                logger.warning(
                    f"[media_prep] {label}主体位置识别失败,放弃画幅裁切以免切走主体,保留原片"
                )
                return url
            crop_x -= crop_x % 2
            crop_y = (ih - crop_h) // 2
            crop_y -= crop_y % 2
            cmd += ["-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={tw}:{th}"]
        if need_trim:
            cmd += ["-t", str(max_seconds)]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out_path]
        result = await run(cmd, timeout=300)
        if not result.get("ok") or not os.path.exists(out_path):
            logger.warning(f"[media_prep] {label}预处理失败,保留原片: {result.get('stderr')}")
            return url
        new_url = await asyncio.to_thread(
            upload_local_file, out_path, f"{key_prefix}/{uuid.uuid4().hex}.mp4",
        )
        if not new_url:
            logger.warning(f"[media_prep] 处理后的{label}上传失败,保留原片")
            return url
        logger.info(f"[media_prep] {label}已处理并替换: {new_url}")
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


async def deidentify_reference_video(url: str, force: bool = False) -> str:
    """参考视频若含真人(方舟会直接拒绝),本地去身份化后返回新 URL;**不含真人/处理失败一律原样返回**。

    只在提交被"含真人"拦下后调用,所以正常任务只会多一次秒级抽样检测,不会平白多一次转码与上传。
    去身份化本身有画面代价(打码处就是要被替换的主体),因此调用方必须把这件事**显式回写**给用户,
    不能静默替换。

    force=True 时(方舟已明确判定该视频含真人):跳过负结果缓存、加密抽样并加一轮极宽松检测,
    仍定位不到则对画面中部强制打码 —— 总之不再"漏检即放弃"让整单失败。仅缓存"已成功去身份化"
    的正结果;**负结果不再入缓存**,避免某次漏检被永久记住、导致复用同一视频的后续任务秒退。
    """
    if not url:
        return url
    if not force:
        # 非强制路径:命中过正结果可直接复用,省一次转码上传
        cached = _DEID_CACHE.get(url)
        if cached:
            return cached
    if not ffmpeg_path():
        logger.warning("[media_prep] 无可用 ffmpeg,跳过真人去身份化(保留原片)")
        return url

    suffix = os.path.splitext(url.split("?")[0])[1] or ".mp4"
    # to_thread:下载是同步阻塞 I/O,直接调会卡死整个 worker 事件循环 ——
    # 并发任务(ARQ concurrency=5)会一起陪等,实测同一操作从 3s 涨到 33s。
    local = await asyncio.to_thread(download_to_local, url, suffix=suffix)
    if not local:
        logger.warning("[media_prep] 去身份化:参考视频下载失败,保留原片")
        return url

    out_path = os.path.join(tempfile.gettempdir(), f"deid_{uuid.uuid4().hex}.mp4")
    try:
        # 同步的 ffmpeg/cv2 处理挪到线程,别把事件循环堵住(其他任务还在轮询)。
        # force 时把抽样间隔压到 1/4(更密),提高对短暂/远距离出镜人物的召回。
        info = await asyncio.to_thread(
            deidentify.deidentify_video, local, out_path,
            sample_every=(deidentify.SAMPLE_EVERY_SECONDS / 4.0) if force else None,
            force=force,
        )
        if not info.get("detected"):
            # 非强制路径未检测到真人:保留原片。负结果不入缓存,避免污染复用同一视频的后续任务。
            logger.info("[media_prep] 抽样未检测到真人,保留原片")
            return url
        new_url = await asyncio.to_thread(
            upload_local_file, out_path, f"deidentified/{uuid.uuid4().hex}.mp4",
        )
        if not new_url:
            logger.warning("[media_prep] 去身份化产物上传失败,保留原片")
            return url
        _remember_deid(url, new_url)          # 仅缓存正结果
        logger.info(
            f"[media_prep] 参考视频已本地去身份化({'强制兜底' if info.get('forced') else '命中'} "
            f"{info.get('hits')} 次,打码区 {info.get('box')},源 {info.get('size')}): {new_url}"
        )
        return new_url
    except Exception as exc:  # noqa: BLE001
        # 用 error 而不是 warning:这里的失败直接导致"编辑不重试 → 整单失败",
        # 混在普通告警里会让排查者以为是无关紧要的增强项没跑到。
        logger.error(f"[media_prep] 本地去身份化失败,保留原片(编辑将无法重试): {exc}")
        return url
    finally:
        for path in [p for p in (local, out_path) if p]:
            try:
                os.remove(path)
            except OSError:
                pass
