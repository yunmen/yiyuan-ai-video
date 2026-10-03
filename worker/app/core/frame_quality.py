# -*- coding: utf-8 -*-
'''退化画面检测:识别「测试卡 / 彩条 / 纯色 / 黑屏」这类不可能是真实拍摄内容的画面。

背景(实测 task 58/59):参考视频本身是一段复古 CRT 风格的电视彩条测试图,视频编辑链路
因「参考视频像素数不足 407696」被方舟 400 拒绝后,降级链路抽了参考视频首帧(就是彩条)
喂给图生视频,模型忠实地把彩条"动"了 5 秒 —— 于是交付了一片有声无画的彩条片,
系统却判成功、还计了费、还把额度核销掉。

与「字幕烧录失败就保留原片」不同,这类成片**没有任何可用价值**,必须拦下来报错退额度,
不能当成功交付。故在两处设卡:
  1. 降级抽帧前:参考帧本身就是退化画面 → 降级必然产出垃圾,直接判失败(不花钱重生成);
  2. 成片转存后:兜底校验(detect_degenerate_video),防止其他链路漏网
     (如参考视频是彩条但视频编辑直接成功 —— 此时根本不走降级,第 1 道卡拦不住)。

—— 判据怎么来的(实测,别凭感觉改)——
worker 依赖里没有 Pillow/numpy,故用已有的 ffmpeg 解出原始 RGB 字节流做统计,不新增依赖。
在真实彩条成片与真实图片上实测过四类候选指标,结论如下:
  · 唯一颜色数:彩条 13770 / 正常图 4617 —— 彩条反而更高(有噪点与滚动条动画),**无区分度**;
  · 垂直/水平梯度:彩条 2.98/4.62 vs 正常 5.14/5.53 —— 差距小且随内容波动,**无区分度**;
  · 纯色列占比:彩条 0% vs 正常 5.2% —— **方向相反**,彩条带噪点导致每列都不纯,**不可用**;
  · 色相集中度:彩条占 10/12 个色相桶、正常图只占 1/12 —— **方向相反**,**不可用**;
  · 高饱和像素占比(S>=0.7):彩条 85.2% / 84.9%,正常图 3.6% —— **区分度极佳,采用**。

所以最终只用两个互补判据:
  A. 高饱和像素占比 >= _MAX_HIGH_SAT_RATIO(默认 0.70)→ 判为彩条/测试卡;
     真实画面要凑到 70% 的像素饱和度超过 0.7 极难(实测正常图仅 3.6%),余量充足。
     饱和度按 S=(max-min)/max 直接算,不引入 colorsys —— 纯整数比较快一个量级。
  B. 唯一颜色数 <= _PURE_COLOR_MAX(默认 8)→ 判为纯色/黑屏(彩条判据 A 覆盖不到的情况,
     比如纯白背景、纯黑画面这类低饱和但毫无内容的帧)。
两者都不命中即视为正常画面,放行。**判定刻意保守:宁可漏放也不误杀** ——
误杀会把正常成片判失败、白扣用户额度,比漏放一个坏片的代价大得多。
'''
import asyncio
import os
import shutil
import tempfile
from typing import List, Optional, Tuple

from app.core.compose import run
from app.core.plugin import logger
from app.settings import config

# 判据 A:高饱和(S>=0.70)像素占比阈值。实测彩条 85%、正常图 3.6%,取 0.70 留足余量。
_MAX_HIGH_SAT_RATIO = 0.70
# 单像素判为「高饱和」的饱和度下限。
_HIGH_SAT_THRESHOLD = 0.70
# 判据 B:唯一 RGB 颜色数上限。纯色/黑屏画面颜色数极少(1~5);真实画面即便大面积纯色
# 背景,也会因渐变与噪点产生大量颜色。取 8 留余量。
_PURE_COLOR_MAX = 8
# 统计用的降采样尺寸(宽 x 高):约 2.9 万像素,足够稳定地反映颜色分布,
# 又能让纯 Python 循环在毫秒级跑完(逐像素用 ffmpeg 全分辨率会慢到不可接受)。
_PROBE_W, _PROBE_H = 128, 228


def _sample_size(width: int, height: int) -> Tuple[int, int]:
    """等比缩放到统计尺寸(保持原图比例,避免拉伸影响颜色分布判断)"""
    if width <= 0 or height <= 0:
        return 0, 0
    scale = min(1.0, _PROBE_W / width, _PROBE_H / height)
    return max(2, int(width * scale)), max(2, int(height * scale))


async def _probe_size(frame_path: str, timeout: int) -> Optional[Tuple[int, int]]:
    """读取单张图片的(宽,高)"""
    result = await run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", frame_path,
    ], timeout=timeout)
    if not result.get("ok"):
        return None
    try:
        raw = (result.get("stdout") or "").strip().splitlines()[0]
        w, h = raw.split("x")[:2]
        return int(w), int(h)
    except (ValueError, IndexError):
        return None


async def _read_pixels(frame_path: str, timeout: int) -> Optional[bytes]:
    """用 ffmpeg 解出降采样后的 rgb24 原始像素流(不落盘,直接走 stdout)"""
    size = await _probe_size(frame_path, timeout)
    if not size:
        return None
    width, height = _sample_size(*size)
    result = await run([
        "ffmpeg", "-v", "error", "-i", frame_path,
        "-vf", f"scale={width}:{height}",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
    ], timeout=timeout, binary=True)
    if not result.get("ok"):
        return None
    data = result.get("stdout_bytes") or b""
    return data if data else None


def analyze_pixels(data: bytes) -> Tuple[int, int, int]:
    """统计 (唯一颜色数, 高饱和像素数, 总像素数)

    饱和度手写 S=(max-min)/max:与 colorsys.rgb_to_hsv 的 HSV 饱和度定义一致
    (都等于 (max-min)/max),但省掉函数调用开销,逐像素统计快一个量级。
    """
    colors = set()
    high_sat = 0
    total = len(data) // 3
    for i in range(0, len(data) - 2, 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        colors.add(data[i:i + 3])
        mx = r if r > g else g
        if b > mx:
            mx = b
        mn = r if r < g else g
        if b < mn:
            mn = b
        # 纯黑时 max=0,跳过除法(纯黑由判据 B 的颜色数覆盖)
        if mx and (mx - mn) / mx >= _HIGH_SAT_THRESHOLD:
            high_sat += 1
    return len(colors), high_sat, total


def _high_sat_threshold() -> float:
    """高饱和占比阈值(判据 A):后台 gen.frame_high_sat_ratio 可配,未配用 0.70。

    为什么可调:判据是在**有限样本**上定的 —— 50 张真实照片实测误杀 1 张(2.0%,
    那张 71% 高饱和),而真实事故的彩条成片是 84~85%、ffmpeg 生成的 smptebars 是 70.3%。
    两者咬得很紧,不存在"放之四海皆准"的固定值:
      · 调**低** → 拦得更狠,但会误杀花卉/霓虹这类高饱和正常画面;
      · 调**高** → 误杀变少,但 70% 上下的测试卡会漏放。
    故把选择权交给运营按素材类型调,非法值一律回退默认(绝不因配错而全量误杀)。
    """
    raw = str(getattr(config, "FRAME_HIGH_SAT_RATIO", "") or "").strip()
    if not raw:
        return _MAX_HIGH_SAT_RATIO
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return _MAX_HIGH_SAT_RATIO
    # 只在 0.5~0.95 之间生效:低于 0.5 会误杀大量正常画面,高于 0.95 基本等于不检测
    if not 0.5 <= value <= 0.95:
        return _MAX_HIGH_SAT_RATIO
    return value


async def detect_degenerate_frame(
    frame_path: str, timeout: int = 60,
    max_high_sat_ratio: Optional[float] = None,
    pure_color_max: int = _PURE_COLOR_MAX,
) -> Optional[str]:
    """检测单帧是否为退化画面(彩条测试卡 / 纯色 / 黑屏)。

    返回中文原因字符串表示「确实是退化画面」;画面正常、或任何环节测不出来时返回 None。
    语义刻意保守:宁可漏放,不可误杀(误杀 = 正常成片被判失败,用户白等一场)。
    max_high_sat_ratio 不传时读后台配置(见 _high_sat_threshold)。
    """
    if not frame_path or not os.path.exists(frame_path):
        return None
    if max_high_sat_ratio is None:
        max_high_sat_ratio = _high_sat_threshold()
    try:
        data = await _read_pixels(frame_path, timeout)
    except Exception as exc:  # noqa: BLE001 —— 检测是增强能力,异常绝不能阻断主链路
        logger.warning(f"[frame_quality] 退化画面检测异常(按通过处理): {exc}")
        return None
    if not data:
        return None
    colors, high_sat, total = analyze_pixels(data)
    if total <= 0:
        return None
    # 判据 B:颜色数极少 → 纯色/黑屏(低饱和的退化画面,判据 A 覆盖不到)
    if colors <= pure_color_max:
        return f"画面只有 {colors} 种颜色,是纯色/黑屏一类无实际内容的画面"
    # 判据 A:高饱和占比畸高 → 彩条/测试卡
    ratio = high_sat / total
    if ratio >= max_high_sat_ratio:
        return (
            f"画面 {ratio * 100:.0f}% 的像素为高饱和纯色,"
            f"是彩条/测试图一类无实际内容的画面"
        )
    return None


async def detect_degenerate_frames(frames: List[str], timeout: int = 60) -> Optional[str]:
    """逐帧检测,任一帧退化即返回该帧原因;全部正常返回 None。

    只要有一帧退化就足以判失败:降级链路会把这些帧当参考画面喂给模型,
    一帧彩条就能让整条成片变成彩条片。
    """
    for path in frames or []:
        reason = await detect_degenerate_frame(path, timeout=timeout)
        if reason:
            return reason
    return None


# 成片侧抽帧检测的采样帧数。取 3:既能覆盖"整段都是彩条"的废片,
# 又不会因片头/片尾一帧的黑场或淡入把正常成片误判成黑屏。
_VIDEO_PROBE_FRAMES = 3


def _probe_times(duration: float, samples: int) -> List[float]:
    """在成片时长内均匀取 samples 个采样点,**刻意避开首帧与末帧**。

    短视频普遍有片头黑场/淡入、片尾淡出,只看首帧会把这类正常成片误判成黑屏 ——
    误杀(白扣用户额度)的代价远大于漏放,故采样点按 (i+1)/(samples+1) 内缩分布。
    """
    if not duration or duration <= 0 or samples <= 0:
        return []
    return [duration * (i + 1) / (samples + 1) for i in range(samples)]


async def _extract_probe_frames(
    local_video: str, times: List[float], timeout: int,
) -> Tuple[List[str], str]:
    """在本地视频的指定时间点各抽 1 帧,返回 (帧路径列表, 临时目录)。

    抽帧走本地文件而非远程地址:远程抽帧每取一帧都要重新解码一遍流(等于重复下载),
    而这里要取 3 帧 —— 下载一次再本地 seek 是最省的做法。
    """
    workdir = tempfile.mkdtemp(prefix="probe_frames_")
    frames: List[str] = []
    for idx, moment in enumerate(times):
        out = os.path.join(workdir, f"probe_{idx}.jpg")
        result = await run([
            "ffmpeg", "-v", "error", "-ss", f"{moment:.3f}", "-i", local_video,
            "-frames:v", "1", "-q:v", "2", out,
        ], timeout=timeout)
        if result.get("ok") and os.path.exists(out):
            frames.append(out)
    return frames, workdir


async def detect_degenerate_video(
    video: str, timeout: int = 60, samples: int = _VIDEO_PROBE_FRAMES,
) -> Optional[str]:
    """检测成片是否为退化画面(彩条/测试卡/纯色/黑屏);是则返回中文原因,否则 None。

    与参考侧「任一帧退化即判失败」相反,成片侧要求**所有采样帧都退化**才判失败:
    成片已经付费,误杀等于白扣用户额度并让用户拿不到片子;而漏放的坏片用户一眼可见、
    可以重做。故这里的语义比参考侧更保守。

    任何环节失败(下载/探测/抽帧)一律返回 None 放行 —— 兜底校验绝不能反过来把任务搞失败。
    """
    if not video:
        return None
    try:
        from app.core.media_prep import probe_duration  # 局部导入:避免与 media_prep 形成导入环
        from app.utils.oss import download_to_local     # 同上,且该函数是同步接口
        duration = await probe_duration(video, timeout=timeout)
        times = _probe_times(duration or 0.0, samples)
        if not times:
            return None
        # 已是本地文件就直接用(便于单测与本地链路),否则下载一份再抽帧
        local = video if os.path.exists(video) else await asyncio.to_thread(
            download_to_local, video, ".mp4",
        )
        if not local or not os.path.exists(local):
            return None
        try:
            frames, workdir = await _extract_probe_frames(local, times, timeout)
            try:
                if not frames:
                    return None
                first_reason: Optional[str] = None
                for path in frames:
                    reason = await detect_degenerate_frame(path, timeout=timeout)
                    if not reason:
                        return None      # 有一帧是正常的画面就放行
                    first_reason = first_reason or reason
                return first_reason
            finally:
                shutil.rmtree(workdir, ignore_errors=True)
        finally:
            if local != video:
                try:
                    os.remove(local)
                except OSError:
                    pass
    except Exception as exc:  # noqa: BLE001 —— 兜底校验异常一律按通过处理,不阻断主链路
        logger.warning(f"[frame_quality] 成片退化检测异常(按通过处理): {exc}")
        return None


async def check_reference_video_pixels(
    video: str, min_pixels: int, timeout: int = 60,
) -> Optional[str]:
    """校验参考视频像素数是否达到模型下限,不达标返回中文原因(达标/测不出返回 None)。

    背景(task 58/59):方舟 r2v/v2v 明确要求参考视频像素数 >= 407696,不足直接 400。
    提交前先校验,能把「注定失败的提交 + 一轮无谓故障转移」换成一句可执行的提示。
    """
    if not video or min_pixels <= 0:
        return None
    try:
        from app.core.media_prep import probe_size  # 局部导入:避免与 media_prep 形成导入环
        size = await probe_size(video, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 —— 校验失败按「测不出」放行,不阻断主链路
        logger.warning(f"[frame_quality] 参考视频像素校验异常(按通过处理): {exc}")
        return None
    if not size:
        return None
    width, height = size
    total = width * height
    if total < min_pixels:
        return (
            f"参考视频分辨率 {width}x{height}({total} 像素)低于模型要求的最低 "
            f"{min_pixels} 像素,请换用更高分辨率的参考视频"
        )
    return None
