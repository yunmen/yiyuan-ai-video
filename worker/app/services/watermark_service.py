# -*- coding: utf-8 -*-
'''
@文件    :watermark_service.py
@说明    :成片品牌水印/台标去除(确定性后处理)—— 检测 → 分级修补 → 转存 OSS
@时间    :2026/10/04
@作者    :一源AI
@版本    :1.0
@说明    :为什么不用提示词约束:实测让编辑模型"把水印区域还原为自然背景"会连带重绘整个场景
          (原片非洲村落被重画成红土路 + 光秃山丘),即「去水印」与「忠实复刻」在提示词层面
          互相冲突 —— 提示词护栏只能作为双保险的第一道,真正保证"水印消失且画面不变"的是本模块。

          核心原则:水印不在生成阶段解决,而在**成片上做几何/像素处理**。
          模型完全不知道有水印存在,因此成片对原片的忠实度不受任何影响。

          分级策略(与产品决策一致):
            · 贴边水印(绝大多数四角台标)→ crop 掉对应边 + scale 回原分辨率(无痕、不糊);
            · 画面内部水印 → delogo 边缘插值(画幅尺寸不变,该区域略有痕迹);
            · 两者都有 → 先 crop 再 delogo。

          设计原则:任何环节失败(未装 ffmpeg / 视觉网关不可用 / 检测不到水印 / ffmpeg 执行失败)
          一律返回 None,由调用方保留原片 —— 去水印是增强项,绝不能把已付费生成变成失败任务。
'''
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core import compose
from app.core.plugin import logger
from app.services.ai_vision import vision_chat
from app.settings import config
from app.utils.oss import download_to_local, upload_local_file


# 检测抽帧数量:抽首尾两帧取并集 —— 台标通常固定,但个别视频中途才出现(只抽首帧会漏)。
DETECT_FRAME_COUNT = 2
# 送视觉模型的帧宽度:不必原分辨率,越小越省 token(与逐镜头逆推同一取舍)。
DETECT_FRAME_WIDTH = 720
# 贴边判定阈值:框落在画面该侧 12% 区域内视为"贴边",可用 crop 无痕去除;
# 超出则视为画面内部水印,只能 delogo。
EDGE_RATIO = 0.12
# 单个框的最小边长占比(归一化),小于此值视为噪声(模型偶尔会框出零散笔画)直接忽略。
MIN_BOX_RATIO = 0.012
# 裁剪后剩余画面的最小占比:低于此值说明检测框可能框住了主体(模型误判),放弃处理而不是把画面裁没。
MIN_KEEP_RATIO = 0.55
# delogo 区域向外扩的像素:检测框通常略小于真实水印,外扩避免残留边缘。
DELOGO_MARGIN = 6

# 检测用的提示词:只要坐标不要描述,输出 JSON 便于解析。
_DETECT_PROMPT = (
    "请识别图中所有**品牌标识类**元素,并给出它们的位置。"
    "品牌标识类包括:频道台标/角标(如频道名、账号名)、品牌 logo、"
    "平台水印、贴片广告、平台或应用界面元素、版权署名。"
    "\n注意:不要把画面内容本身当成水印 —— 人物、物体、场景、"
    "以及作为内容一部分的字幕/标题都不属于品牌标识。"
    "\n严格输出 JSON(不要任何解释文字):"
    '{"watermarks":[{"x":0.05,"y":0.03,"w":0.16,"h":0.09}]}'
    "\n其中 x/y/w/h 均为 0~1 的归一化坐标(相对整张图的宽/高),"
    "x 为左边缘位置、y 为上边缘位置。若图中没有任何品牌标识,输出 {\"watermarks\":[]}。"
)


def _enabled(params: Dict[str, Any]) -> bool:
    """去水印开关:任务级 remove_watermark 优先,否则取系统配置 gen.watermark_removal(默认开)。

    任务级取值:off 关闭 / auto(默认)自动检测 / crop 只裁剪 / delogo 只插值修补。
    """
    mode = str((params or {}).get("remove_watermark") or "auto").strip().lower()
    if mode == "off":
        return False
    if mode in ("auto", "crop", "delogo"):
        return True
    # 非法值回退系统配置,不因此报错(与项目其他归一化策略一致)
    raw = getattr(config, "WATERMARK_REMOVAL", "1")
    return str(raw).strip() not in ("0", "false", "False", "")


def _parse_boxes(text: str) -> List[Dict[str, float]]:
    """解析视觉模型返回的 JSON,取出归一化框列表;任何异常返回空列表(调用方跳过处理)。"""
    if not text:
        return []
    raw = str(text).strip()
    # 模型常把 JSON 包在 ```json 代码块里,先剥掉围栏再解析
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(raw[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"[Watermark] 视觉返回非 JSON,跳过去水印: {raw[:120]}")
        return []
    items = data.get("watermarks") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    boxes: List[Dict[str, float]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            x, y = float(it["x"]), float(it["y"])
            w, h = float(it["w"]), float(it["h"])
        except (KeyError, TypeError, ValueError):
            continue
        # 归一化坐标可能被模型写成百分数(85 表示 85%),统一夹到 0~1 后再做合理性过滤
        vals = [v / 100.0 if v > 1.5 else v for v in (x, y, w, h)]
        x, y, w, h = vals
        x = min(max(x, 0.0), 1.0)
        y = min(max(y, 0.0), 1.0)
        w = min(max(w, 0.0), 1.0 - x)
        h = min(max(h, 0.0), 1.0 - y)
        if w < MIN_BOX_RATIO or h < MIN_BOX_RATIO:
            continue  # 过小的框视为噪声
        boxes.append({"x": x, "y": y, "w": w, "h": h})
    return boxes


def _classify_boxes(
    boxes: List[Dict[str, float]], width: int, height: int,
) -> Tuple[Dict[str, int], List[Dict[str, int]]]:
    """把归一化框分为「可裁剪的贴边框」与「只能 delogo 的内部框」。

    返回 (裁剪区域, delogo 区域列表),裁剪区域为像素坐标 {x,y,w,h}。
    贴边框只需裁掉它所在的那条边,取各边所需裁切量的最大值 —— 这样画面损失最小。
    """
    tol_x, tol_y = width * EDGE_RATIO, height * EDGE_RATIO
    left = top = right = bottom = 0.0
    inner: List[Dict[str, int]] = []
    for b in boxes:
        px, py = b["x"] * width, b["y"] * height
        pw, ph = b["w"] * width, b["h"] * height
        touches = False
        if px <= tol_x:
            left = max(left, px + pw)
            touches = True
        if py <= tol_y:
            top = max(top, py + ph)
            touches = True
        if px + pw >= width - tol_x:
            right = max(right, width - px)
            touches = True
        if py + ph >= height - tol_y:
            bottom = max(bottom, height - py)
            touches = True
        if not touches:
            inner.append({
                "x": max(0, int(px - DELOGO_MARGIN)),
                "y": max(0, int(py - DELOGO_MARGIN)),
                "w": int(pw + DELOGO_MARGIN * 2),
                "h": int(ph + DELOGO_MARGIN * 2),
            })
    crop_w = width - left - right
    crop_h = height - top - bottom
    # 一条边都不需要裁 → 不做裁剪,否则会白跑一次 crop+scale 重编码
    if left <= 0 and top <= 0 and right <= 0 and bottom <= 0:
        return {}, inner
    # 裁剪后剩余画面过小 → 判定为检测不可靠,宁可不处理也不把画面裁没
    if crop_w <= 0 or crop_h <= 0 \
            or crop_w < width * MIN_KEEP_RATIO or crop_h < height * MIN_KEEP_RATIO:
        crop: Dict[str, int] = {}
    else:
        crop = {"x": int(left), "y": int(top), "w": int(crop_w), "h": int(crop_h)}
    return crop, inner


async def _resolve_size(local_video: str, params: Dict[str, Any]) -> Tuple[int, int]:
    """取成片分辨率:优先 ffprobe 探测真实尺寸,失败回退按生成参数推算画幅。

    回退是必要的:开发机常没有 ffprobe(只有 ffmpeg),此时用 ratio/resolution 推算即可。
    """
    size = await compose.probe_resolution(local_video)
    if size and size[0] > 0 and size[1] > 0:
        return size
    canvas = compose.video_canvas(
        (params or {}).get("ratio"), (params or {}).get("resolution"),
    )
    if canvas:
        return int(canvas[0]), int(canvas[1])
    return 0, 0


async def _detect(local_video: str, workdir: str, task_id: str) -> List[Dict[str, float]]:
    """抽帧 → 上传 OSS → 调视觉模型识别品牌标识,返回归一化框并集。"""
    frame_urls: List[str] = []
    for idx, at in enumerate(_FRAME_POSITIONS):
        out = os.path.join(workdir, f"frame_{idx}.jpg")
        result = await compose.run(
            compose.build_extract_frame_cmd(local_video, out, at, width=DETECT_FRAME_WIDTH),
            timeout=120, cwd=workdir,
        )
        if not result.get("ok") or not os.path.exists(out):
            continue
        url = await asyncio.to_thread(
            upload_local_file, out, f"watermark/{task_id or uuid.uuid4().hex[:8]}/frame_{idx}.jpg",
        )
        if url:
            frame_urls.append(url)
    if not frame_urls:
        logger.info("[Watermark] 抽帧失败,跳过去水印(保留原片)")
        return []

    payload = {
        "model": getattr(config, "VISION_MODEL", "") or "",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": _DETECT_PROMPT},
            ] + [{"type": "image_url", "image_url": {"url": u}} for u in frame_urls],
        }],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    try:
        text = await vision_chat(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Watermark] 视觉检测失败,跳过去水印(保留原片): {exc}")
        return []
    boxes = _parse_boxes(text)
    logger.info(f"[Watermark] 视觉检测到 {len(boxes)} 个品牌标识框 task={task_id}")
    return boxes


# 取样帧的时间点(秒):短视频台标几乎全程存在,取两个点足够覆盖,
# 且不必为"抽尾帧"额外依赖 ffprobe 探测时长。
_FRAME_POSITIONS = [0.5, 3.0]


async def remove_watermark(
    video_url: str, params: Dict[str, Any], task_id: str = "",
) -> Optional[str]:
    """去除成片中的品牌水印/台标,成功返回新视频 URL,失败/无需处理返回 None。

    失败一律返回 None 而不是抛异常:调用方(base 后处理层)拿到 None 就保留原片,
    绝不能因为"去水印"这种增强项把一次已付费的生成变成失败任务。
    """
    if not video_url or not compose.available():
        return None
    task_id = str(task_id or uuid.uuid4().hex[:8])
    workdir = tempfile.mkdtemp(prefix="watermark_")
    try:
        local_video = await asyncio.to_thread(download_to_local, video_url, ".mp4")
        if not local_video:
            return None
        boxes = await _detect(local_video, workdir, task_id)
        if not boxes:
            logger.info(f"[Watermark] 未检测到品牌标识,保留原片 task={task_id}")
            return None

        width, height = await _resolve_size(local_video, params)
        if width <= 0 or height <= 0:
            logger.warning(f"[Watermark] 无法确定成片尺寸,保留原片 task={task_id}")
            return None
        crop, inner = _classify_boxes(boxes, width, height)
        logger.info(
            f"[Watermark] 尺寸={width}x{height} 裁剪={crop} 内部修补={len(inner)} 框 task={task_id}"
        )
        if not crop and not inner:
            logger.info(f"[Watermark] 检测结果不可靠(裁剪过多或无有效区域),保留原片 task={task_id}")
            return None

        mode = str((params or {}).get("remove_watermark") or "auto").strip().lower()
        current = local_video
        step = 0
        # 第一步:贴边水印用裁剪(无痕)。用户选择"裁剪后缩放回原比例",故 out_w/out_h 传原分辨率。
        if crop and mode in ("auto", "crop"):
            out = os.path.join(workdir, f"crop_{step}.mp4")
            result = await compose.run(
                compose.build_crop_cmd(
                    current, out, crop["w"], crop["h"], crop["x"], crop["y"],
                    out_w=width, out_h=height,
                ),
                timeout=900, cwd=workdir,
            )
            if result.get("ok") and os.path.exists(out):
                current, step = out, step + 1
            else:
                logger.warning(f"[Watermark] 裁剪去水印失败,跳过该步: {result.get('stderr')}")
        # 第二步:画面内部水印用 delogo 插值修补(画幅不变)
        if inner and mode in ("auto", "delogo"):
            out = os.path.join(workdir, f"delogo_{step}.mp4")
            result = await compose.run(
                compose.build_delogo_cmd(current, out, inner),
                timeout=900, cwd=workdir,
            )
            if result.get("ok") and os.path.exists(out):
                current = out
            else:
                logger.warning(f"[Watermark] delogo 去水印失败,跳过该步: {result.get('stderr')}")
        if current == local_video:
            return None
        url = await asyncio.to_thread(
            upload_local_file, current, f"generate/result/watermark_{task_id}.mp4",
        )
        if not url:
            return None
        logger.info(f"[Watermark] 去水印完成 task={task_id}")
        return url
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Watermark] 去水印异常,保留原片: {exc}")
        return None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


__all__ = ["remove_watermark"]
