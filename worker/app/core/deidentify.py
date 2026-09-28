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
import re
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

# 两轮检测参数:严格轮 → 宽松轮。
# 为什么还要第二轮:调用方只在"平台已判定输入含真人"时才走到这里,**漏检就是整单失败**
# (去身份化产不出新视频 → 编辑不重试 → 换产品直接失败),而误检的代价只是多糊一块
# 已经注定要被打码的画面 —— 两者代价不对等,所以第二轮宁可多检也不能漏。
#   严格轮:少误报,首选(框准、画面损失小);
#   宽松轮:降低 minNeighbors / 放慢金字塔,提高对侧脸、遮挡、远景小脸的召回。
DETECT_PASSES = (
    {"scale_factor": 1.1, "min_neighbors": 5, "min_size": MIN_FACE_PX},
    {"scale_factor": 1.05, "min_neighbors": 3, "min_size": 16},
)

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

    图片是"要被替换成的目标",不能像视频那样直接打码(糊掉等于没有替换目标),
    但可以走调用方决定的处理:丢弃该图改按文字描述生成,或拟态化后再提交。
    定位到具体是哪张图由 parse_blocked_index 完成。
    """
    text = str(error_text or "")
    if any(m in text for m in _IMAGE_BLOCK_MARKERS):
        return True
    low = text.lower()
    return "real person" in low and "image" in low


# 方舟报错里指明被拦素材下标的写法(实测形如 content[1] / contents[1] / content[4])
_CONTENT_INDEX_RE = re.compile(r"content(?:s)?\[(\d+)\]", re.I)


def parse_blocked_index(error_text: str) -> Optional[int]:
    """从方舟报错里解析被拦素材的 content[N] 下标;解析不到返回 None。

    定位到具体是哪张图,才能只处理那一张 —— 否则多图任务(人物图 + 商品图)里
    正常的商品图会被一起丢掉,替换效果直接失效。
    """
    match = _CONTENT_INDEX_RE.search(str(error_text or ""))
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _ffmpeg_bin() -> Optional[str]:
    return ffmpeg_path() or shutil.which("ffmpeg")


def _run(cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="ignore", timeout=timeout)


def _load_cascades() -> Tuple[List, List, List]:
    """Haar 级联(OpenCV 自带,无需下载模型),按"画面损失从小到大"分三组返回:
       · faces:正脸(两套) + 侧脸 —— 只糊脸即可过平台真人审核,且保留身体/场景给编辑模型复用;
       · upper:上半身 —— 检不到脸时兜底(侧脸/遮挡严重),代价是框更大;
       · full :全身 —— 最后兜底(远景人物、背影),框最大,只在前面都没检出时才用。

    多带一个 frontalface_alt2:默认那套对光照/姿态变化较敏感,实测远景小脸会漏,
    两套一起用能覆盖更多真实素材(漏检 = 平台仍拒绝 = 整单失败)。
    """
    import cv2
    faces, upper, full = [], [], []
    base = cv2.data.haarcascades
    for name in (
        "haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_alt2.xml",
        "haarcascade_profileface.xml",
    ):
        path = os.path.join(base, name)
        if os.path.exists(path):
            clf = cv2.CascadeClassifier(path)
            if not clf.empty():
                faces.append(clf)
    for name, bucket in (("haarcascade_upperbody.xml", upper), ("haarcascade_fullbody.xml", full)):
        path = os.path.join(base, name)
        if os.path.exists(path):
            clf = cv2.CascadeClassifier(path)
            if not clf.empty():
                bucket.append(clf)
    return faces, upper, full


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


def _union_for(cascades, workdir: str, src_w: int, src_h: int, pad: float, params=None):
    """用给定级联在抽样帧上检测真人,返回 (并集框(x,y,w,h,原图坐标,偶数化), 命中数);
    未命中返回 (None, 0)。

    params 为 DETECT_PASSES 中的一组检测参数(严格/宽松);不传按严格轮处理。
    """
    if not cascades:
        return None, 0
    # cv2 只在真正检测时才导入(与 _load_cascades / frame_size 同风格:未装 cv2 时
    # 其它环节仍可用)。缺这一行会直接 NameError —— 异常被上层"保留原片"的兜底吞掉,
    # 表现为"去身份化永远不生效、编辑永远不重试",排查时极难定位。
    import cv2
    params = params or DETECT_PASSES[0]
    min_px = int(params.get("min_size") or MIN_FACE_PX)
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
                gray, scaleFactor=params.get("scale_factor", 1.1),
                minNeighbors=params.get("min_neighbors", 5), minSize=(min_px, min_px),
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


# 并集框相对原帧的硬上限:无论检测得多离谱,打码区都不得覆盖超过此比例的画面,
# 否则会连场景/构图锚点一起毁掉(编辑模型无处可"复刻"原片)。
BOX_MAX_W_RATIO = 0.85
BOX_MAX_H_RATIO = 0.85


def _detect_union(workdir: str, src_w: int, src_h: int, pad: float = BOX_PAD, force: bool = False):
    """优先只糊脸(保留身体与场景给编辑模型复用),逐级退到上半身 / 全身兜底。

    为什么只糊脸就够:方舟真人审核拦的是"可识别身份",糊掉脸即破坏识别特征;
    而"换人物"链路本就要把原人物区域重绘成上传形象,身体/背景只需留给编辑模型当构图锚点。
    旧实现把上半身也并入并集框,会把整片中上部全糊掉,编辑模型失去场景参照 → 成片崩。

    按「严格轮 → 宽松轮」各走一遍同一套优先级(脸 → 上半身 → 全身):
    只在**平台已经判定该视频含真人**时才会调用,此时漏检 = 去身份化产不出新视频 = 整单失败,
    而多检一点的代价只是框略大(后续 BOX_MAX_* 会夹紧),故第二轮用更宽松的检测参数兜召回。

    force=True 时(方舟已确认含真人但普通两轮未检出)追加一轮极宽松检测(minNeighbors=2、
    minSize=10、金字塔更慢)进一步提高对侧脸/远景小脸的召回;仍检不到由调用方决定强制打码兜底。
    """
    faces, upper, full = _load_cascades()
    passes = list(DETECT_PASSES)
    if force:
        # 方舟已确认含真人却漏检:再降门槛兜底召回,漏检的代价是整单失败,多检只是框略大
        # 注意:passes 是 list,必须用 list 拼接(不能用元组),否则 list + tuple 抛 TypeError,
        # 导致 force 分支每次都崩、去身份化永远失败、含真人参考视频的编辑整单失败。
        passes = passes + [{"scale_factor": 1.02, "min_neighbors": 2, "min_size": 10}]
    for params in passes:
        for group in (faces, upper, full):
            if not group:
                continue
            box, hits = _union_for(group, workdir, src_w, src_h, pad, params)
            if box is not None:
                return _clamp_box(box, src_w, src_h), hits
    return None, 0


def _forced_box(src_w: int, src_h: int):
    """兜底打码框:本地未定位到真人但方舟确认含真人时,对画面中部一大块强制打码。

    代价是画面中部失去可复刻信息(编辑模型无锚点),故仅作最后兜底;真人若恰在中部
    即可过检测,边缘真人仍可能再次被拦 —— 此时由调用方如实失败,不再伪装成功。
    """
    w = int(src_w * 0.6) // 2 * 2
    h = int(src_h * 0.8) // 2 * 2
    x = max(0, (src_w - w) // 2)
    y = max(0, (src_h - h) // 2)
    return (x, y, w, h)


def _clamp_box(box, src_w: int, src_h: int):
    """安全夹紧:框再大也不得超过画面的约定比例,避免极端检测毁掉整片场景

    宽松轮会提高召回,也可能检出更大的框(甚至占满画面),这里兜住上限 ——
    打码区超过 BOX_MAX_* 就等于把原片场景全糊掉,编辑模型没有可复刻的锚点。
    """
    x0, y0, w, h = box
    max_w = int(src_w * BOX_MAX_W_RATIO) // 2 * 2
    max_h = int(src_h * BOX_MAX_H_RATIO) // 2 * 2
    if w > max_w or h > max_h:
        w = min(w, max_w)
        h = min(h, max_h)
        x0 = max(0, min(x0, src_w - w))
        y0 = max(0, min(y0, src_h - h))
        box = (x0, y0, w, h)
    return box


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
                     pad: float = BOX_PAD, sample_every: Optional[float] = None,
                     force: bool = False) -> Dict[str, object]:
    """把 src 里检测到的真人区域打码后写到 out。

    返回 {"detected": bool, "forced": bool, ...};detected=False 时**不产出文件**(调用方据此保留原片)。
    任何环节失败都抛异常,由调用方决定回退策略(保留原片)。

    sample_every:抽样间隔(秒);不传用默认 SAMPLE_EVERY_SECONDS。force=True 时(调用方已知
        方舟判定含真人)会加密抽样并提高检测召回;若仍定位不到,对画面中部一大块**强制打码**
        作最后兜底 —— 不再像旧实现那样"漏检即静默放弃",因为方舟已明确确认有真人。
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
        every = sample_every or SAMPLE_EVERY_SECONDS
        # 抽样抽帧(缩到 DETECT_WIDTH,检测够用且快);force 时加密抽样,避免真人只出现在
        # 少数几秒而被 2s 抽样整段漏掉(实测远距离/短暂出镜的人物最容易因此漏检)。
        sample = os.path.join(workdir, "s_%03d.jpg")
        r = _run([ffmpeg, "-hide_banner", "-v", "error", "-y", "-i", src,
                  "-vf", f"fps=1/{every},scale={DETECT_WIDTH}:-2", sample])
        if not os.path.exists(os.path.join(workdir, "s_001.jpg")):
            raise RuntimeError(f"抽样失败: {(r.stderr or '').strip()[:200]}")

        box, hits = _detect_union(workdir, src_w, src_h, pad, force=force)
        forced = False
        if box is None and force:
            # 方舟已确认含真人但本地仍定位不到:对画面中部一大块强制打码,给重新提交一个
            # "至少遮住一部分"的机会;真人若恰在中部即可过检测,边缘真人仍可能再次被拦。
            box = _forced_box(src_w, src_h)
            forced = True
        if box is None:
            return {"detected": False, "hits": 0, "size": f"{src_w}x{src_h}"}

        x, y, w, h = box
        r2 = _run([ffmpeg, "-hide_banner", "-v", "error", "-y", "-i", src,
                   "-filter_complex", _mosaic_filter(x, y, w, h, blocks),
                   "-map", "[out]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
                   "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", out])
        if r2.returncode != 0 or not os.path.exists(out):
            raise RuntimeError(f"ffmpeg 处理失败(rc={r2.returncode}): {(r2.stderr or '').strip()[-300:]}")
        return {"detected": True, "hits": hits, "box": box, "size": f"{src_w}x{src_h}", "forced": forced}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
