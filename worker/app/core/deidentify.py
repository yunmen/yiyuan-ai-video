# -*- coding: utf-8 -*-
'''
@文件    :deidentify.py
@说明    :本地真人去身份化 —— 让"含真人的参考视频"能通过方舟的隐私审核

为什么要这一步
    方舟 Seedance 对**输入视频含真人**会直接拒绝:
        InputVideoSensitiveContentDetected.PrivacyInformation:
        The request failed because the input video 'content[N]' may contain real person.
    这是平台隐私策略,**与提示词无关**(实测连"仅提升画质"也拦),配置改不掉。
    素材本身已获授权、只是需要过检测时,可在本机先把真人区域打码再提交。

实现方式(为什么是"抽样检测 + 固定框")
    ① ffmpeg 抽样(默认每 2 秒一帧、缩到 480 宽);
    ② OpenCV Haar 级联检测人脸/侧脸/上半身,取**并集框**(外扩留余量,宁大勿小);
    ③ 一次 ffmpeg 把该矩形打成马赛克(crop → 缩小 → 最近邻放大 → overlay)。
    不做逐帧检测的原因:逐帧要把原始帧在 Python ↔ ffmpeg 之间来回搬(1440p 每帧 11MB),
    实测又慢又易踩本机管道文本模式的坑;而"人在镜头里位置连续",抽样并集框足够覆盖。
    只动真人区域、不做全片风格化:参考视频的场景/构图/运镜要留给模型,整片风格化会
    让成片跟着变风格,反而伤效果。

代价(必须在调用方体现,不能静默)
    打码区域就是"要被替换掉的主体",所以成片里该处的过渡会比原片粗糙;
    且这只解决**输入视频**,若参考图本身是真人,方舟同样会拦(那是被替换的主体,本地处理帮不上)。
'''
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple

from app.core.compose import ffmpeg_path
from app.core.plugin import logger

# 抽样:每 N 秒取一帧做检测
SAMPLE_EVERY_SECONDS = 2.0
# 检测时的缩放宽度(越小越快);检测框会按比例还原到原始分辨率
DETECT_WIDTH = 480
# 并集框外扩比例:人脸框通常只框到五官,外扩后能把下巴/头发一起盖住
BOX_PAD = 0.15
# 马赛克块数(按区域宽度切):越小越糊。14 在脸部区域上已足以破坏识别特征
DEFAULT_BLOCKS = 14
# 检测缩放后的最小人脸尺寸(像素):太小容易把花纹误判成脸
MIN_FACE_PX = 24

# "素材含真人被平台拦截"的判定关键词:方舟同步 400 与异步失败两种形态都出现过
_VIDEO_BLOCK_MARKERS = ("InputVideoSensitiveContentDetected",)
_IMAGE_BLOCK_MARKERS = ("InputImageSensitiveContentDetected",)


def is_input_video_blocked(error_text: str) -> bool:
    """错误是否属于「输入**视频**含真人被拦」—— 这种情况可以本地去身份化后重试"""
    text = str(error_text or "")
    if any(m in text for m in _VIDEO_BLOCK_MARKERS):
        return True
    low = text.lower()
    return "real person" in low and "video" in low


def is_input_image_blocked(error_text: str) -> bool:
    """错误是否属于「输入**图片**含真人被拦」

    这种本地处理帮不上忙:图片正是要被替换的主体,去打码等于把"要换成的东西"模糊掉。
    只能换非真人形象图,或走方舟官方「可信素材库 + 真人认证」(asset://)。
    """
    text = str(error_text or "")
    if any(m in text for m in _IMAGE_BLOCK_MARKERS):
        return True
    low = text.lower()
    return "real person" in low and "image" in low


def _ffmpeg_bin() -> Optional[str]:
    return ffmpeg_path() or shutil.which("ffmpeg")


def _run(cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="ignore", timeout=timeout)


def _load_cascades() -> List:
    """Haar 级联(OpenCV 自带,无需下载模型):正脸 + 侧脸 + 上半身,任一命中即算命中"""
    import cv2
    out = []
    base = cv2.data.haarcascades
    for name in ("haarcascade_frontalface_default.xml",
                 "haarcascade_profileface.xml",
                 "haarcascade_upperbody.xml"):
        path = os.path.join(base, name)
        if os.path.exists(path):
            clf = cv2.CascadeClassifier(path)
            if not clf.empty():
                out.append(clf)
    return out


def frame_size(video: str) -> Optional[Tuple[int, int]]:
    """读视频分辨率(宽,高);失败返回 None"""
    import cv2
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        return None
    try:
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (w, h) if w and h else None
    finally:
        cap.release()


def _detect_union(workdir: str, src_w: int, src_h: int, pad: float = BOX_PAD):
    """在抽样帧上检测真人,返回 (并集框(x,y,w,h,原图坐标,偶数化), 命中数)"""
    import cv2
    cascades = _load_cascades()
    if not cascades:
        raise RuntimeError("OpenCV 未提供可用的 Haar 级联,无法检测人脸")

    union = None
    hits = 0
    for name in sorted(os.listdir(workdir)):
        img = cv2.imread(os.path.join(workdir, name))
        if img is None:
            continue
        # 每张图各自换算回原图坐标:抽样时高度经 -2 取偶,可能与理论比例差 1px
        fxi = src_w / float(img.shape[1])
        fyi = src_h / float(img.shape[0])
        gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        for clf in cascades:
            for (x, y, w, h) in clf.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(MIN_FACE_PX, MIN_FACE_PX)
            ):
                hits += 1
                box = (x * fxi, y * fyi, (x + w) * fxi, (y + h) * fyi)
                union = box if union is None else (
                    min(union[0], box[0]), min(union[1], box[1]),
                    max(union[2], box[2]), max(union[3], box[3]),
                )
    if union is None:
        return None, 0

    x0, y0, x1, y1 = union
    pw, ph = (x1 - x0) * pad, (y1 - y0) * pad
    x0, y0 = max(0, int(x0 - pw)), max(0, int(y0 - ph))
    x1, y1 = min(src_w, int(x1 + pw)), min(src_h, int(y1 + ph))
    # 编码器要求偶数尺寸
    return (x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2), hits


def _mosaic_filter(x: int, y: int, w: int, h: int, blocks: int) -> str:
    """crop 出目标区域 → 缩到 blocks 宽(最近邻)→ 放回原尺寸 → 覆盖回原位置"""
    bw, bh = max(2, w // blocks), max(2, h // blocks)
    return (
        f"[0:v]split=2[base][tmp];"
        f"[tmp]crop={w}:{h}:{x}:{y},scale={bw}:{bh}:flags=neighbor,"
        f"scale={w}:{h}:flags=neighbor[px];"
        f"[base][px]overlay={x}:{y}[out]"
    )


def deidentify_video(src: str, out: str, blocks: int = DEFAULT_BLOCKS,
                     pad: float = BOX_PAD) -> Dict[str, object]:
    """把 src 里检测到的真人区域打码后写到 out。

    返回 {"detected": bool, ...};detected=False 时**不产出文件**(调用方据此保留原片)。
    任何环节失败都抛异常,由调用方决定回退策略(保留原片)。
    """
    ffmpeg = _ffmpeg_bin()
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg")
    size = frame_size(src)
    if not size:
        raise RuntimeError(f"无法读取视频分辨率: {src}")
    src_w, src_h = size
    if src_w <= 0 or src_h <= 0:
        raise RuntimeError(f"视频分辨率异常: {src_w}x{src_h}")

    workdir = tempfile.mkdtemp(prefix="deid_")
    try:
        # 抽样抽帧(缩到 DETECT_WIDTH,检测够用且快)
        sample = os.path.join(workdir, "s_%03d.jpg")
        r = _run([ffmpeg, "-hide_banner", "-v", "error", "-y", "-i", src,
                  "-vf", f"fps=1/{SAMPLE_EVERY_SECONDS},scale={DETECT_WIDTH}:-2", sample])
        if not os.path.exists(os.path.join(workdir, "s_001.jpg")):
            raise RuntimeError(f"抽样失败: {(r.stderr or '').strip()[:200]}")

        box, hits = _detect_union(workdir, src_w, src_h, pad)
        if box is None:
            return {"detected": False, "hits": 0, "size": f"{src_w}x{src_h}"}

        x, y, w, h = box
        r2 = _run([ffmpeg, "-hide_banner", "-v", "error", "-y", "-i", src,
                   "-filter_complex", _mosaic_filter(x, y, w, h, blocks),
                   "-map", "[out]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", out])
        if r2.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"ffmpeg 处理失败(rc={r2.returncode}): {(r2.stderr or '').strip()[-300:]}")
        return {"detected": True, "hits": hits, "box": box, "size": f"{src_w}x{src_h}"}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
