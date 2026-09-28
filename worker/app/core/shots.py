# -*- coding: utf-8 -*-
'''
@文件    :shots.py
@说明    :参考视频镜头结构解析 — 把「参考视频」从「几张均匀抽帧」升级为
          「带镜头边界与原片台词的**分镜表**」。
@时间    :2026/09/27 10:00:00
@作者    :一源AI
@版本    :1.0
@说明    :为什么需要它(此前链路的两处真实损失):
            ① 复刻只把**均匀抽的 3 张画面**当参考,原片的镜头结构完全没被继承 ——
               8 个镜头的原片,3 帧很可能全落在同一个镜头里;
            ② 多段生成按「秒」均衡切分(multiseg.plan_segments),切点会落在镜头中间,
               同一个镜头被拆到两段里分别生成,衔接处最容易出现人物/场景突变。

          本模块只负责「看懂原片结构」,不做生成决策,也不引入任何第三方依赖:
            · 镜头边界检测 —— 复用 ffmpeg 的 scene 滤镜 + 解析 showinfo 的 pts_time;
            · 分镜表构建(纯函数)—— 切点 → 镜头区间,合并过短镜头、限制镜头总数;
            · 台词归集(纯函数)—— 复用 asr.transcribe_words 的词级时间戳,
              按镜头区间拼成 narration(默认关闭,见 narrate_shots);
            · 抽帧时间点(纯函数)—— 每个镜头取首帧(可含尾帧),供降级链路使用。

          容错原则与 media_prep / subtitle 一致:**任何一步失败都返回空结果**,
          由调用方回退到原有行为(按秒切分 / 均匀抽帧)。解析是增强能力,
          不能让"看懂原片"这件事反过来把一次已付费的生成任务弄失败。
'''
from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core import compose
from app.core.plugin import logger
from app.settings import config

# 场景变化判定阈值(0~1):画面差异超过它才算一次镜头切换。
# 0.3 是 PySceneDetect 类工具与常见实践里的经验值 —— 低了会把镜头内的运动
# (挥手/推镜)误判成切镜,高了会漏掉色调接近的硬切。
DEFAULT_SCENE_THRESHOLD = 0.3


def scene_threshold(default: float = DEFAULT_SCENE_THRESHOLD) -> float:
    """读取后台可配的镜头切分阈值(gen.shot_scene_threshold);非法值回退默认

    与其它 gen.* 配置共用同一热更新通道:runtime_config 把配置写进 config 属性。
    热更新写入的是 JSON 原值(字符串),这里统一转 float 并夹到 (0,1),避免脏配置
    让检测退化成"全片切碎"或"一个切点都没有"。
    """
    raw = getattr(config, "SHOT_SCENE_THRESHOLD", default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if 0 < value < 1 else default

# 镜头最短时长(秒):比它更短的"镜头"几乎都是误检(快速运动/闪白),
# 一律不断开、并入相邻镜头,避免分镜表被切碎。
MIN_SHOT_SECONDS = 0.8

# 分镜表镜头数上限:碎剪型原片可能检测出几十个切点,
# 超过上限就按时间等分,保证分镜表规模可控(metadata 与后续逐镜头调用都受它保护)。
MAX_SHOTS = 30

# 抽帧点数上限(降级链路把帧当参考图上传):参考图不是越多越好,
# 过多会顶到上游的素材数量限制,也白白拉长提交耗时。
MAX_FRAME_POINTS = 6

# 逐镜头逆推的镜头数上限(P0-3):每个镜头要送 2 张画面(开始帧 + 结束帧)给多模态模型,
# 图片数与 token 成本随镜头数线性增长,这里必须封顶。
MAX_ANALYSIS_SHOTS = 6

# 取帧时相对镜头边界的偏移(秒):贴着切点取帧容易取到转场残影/黑帧,
# 往里让一点拿到的是该镜头稳定后的画面。
FRAME_OFFSET = 0.08

# 镜头检测超时(秒):select+showinfo 要线性解码整条视频,留足余量
DETECT_TIMEOUT = 300

# 单个镜头的台词长度上限(字符):分镜表会随 metadata 回写落库,
# 原片台词只作为"这镜在说什么"的索引,不必逐字保存整段口播。
MAX_NARRATION_CHARS = 60

# 从 ffmpeg showinfo 输出里抓时间戳:形如 `pts_time:1.2`
_PTS_TIME_RE = re.compile(r"pts_time:\s*(-?\d+(?:\.\d+)?)")


def build_scene_detect_cmd(source: str, threshold: float = DEFAULT_SCENE_THRESHOLD, ffmpeg: str = "ffmpeg") -> List[str]:
    """ffmpeg 场景变化检测命令(纯函数)

    `select='gt(scene,阈值)'` 只放行画面变化超过阈值的帧,紧跟的 `showinfo`
    把这些帧的 pts_time 打到 stderr;`-f null` 表示**不产出任何文件**(纯分析)。
    `-an` 跳过音频解码,`-nostats` 关掉进度行,避免把结果行淹掉。

    输出目标用系统空设备(os.devnull)而**不是 `-`**:`-` 在 ffmpeg 里表示 stdout,
    但作为**命令末位参数**极易被调用方或测试桩误当成文件路径落盘
    (实测:单测桩按 cmd[-1] 写文件,在 worker 目录下生成了一个名为 `-` 的杂散文件)。

    命令用参数列表传递、不经过 shell:source 可能是外部 URL,拼接 shell 会变成命令注入。
    """
    return [
        ffmpeg, "-hide_banner", "-nostats", "-an", "-i", source,
        "-filter:v", f"select='gt(scene,{threshold:.3f})',showinfo",
        "-f", "null", os.devnull,
    ]


def parse_scene_times(text: str) -> List[float]:
    """从 ffmpeg 输出里取出场景切换时间点(秒),去重升序;取不到返回空列表

    showinfo 每个被选中的帧输出一行,形如:
      [Parsed_showinfo_1 @ 0x55...] n:   1 pts:     36 pts_time:1.2 ... duration:...
    只认 `pts_time:` 之后的数值,其余字段完全忽略 —— 不同 ffmpeg 版本的
    showinfo 字段会增删(新版会多打一行 color_range),但 pts_time 一直都在。
    """
    times: List[float] = []
    for raw in _PTS_TIME_RE.findall(str(text or "")):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            times.append(value)
    if not times:
        return []
    times.sort()
    # 去重:相邻差小于 1ms 的视为同一个切点(同一帧被打印多次)
    unique: List[float] = []
    for value in times:
        if not unique or value - unique[-1] > 0.001:
            unique.append(round(value, 3))
    return unique


def _even_ranges(total: float, count: int) -> List[Tuple[float, float]]:
    """把 [0, total] 等分成 count 段(切点过多时的降级手段)"""
    if count <= 0 or total <= 0:
        return []
    step = total / float(count)
    ranges: List[Tuple[float, float]] = []
    for idx in range(count):
        start = step * idx
        end = total if idx == count - 1 else step * (idx + 1)
        ranges.append((start, end))
    return ranges


def build_shot_list(
    duration: float, cuts: List[float],
    min_seconds: float = MIN_SHOT_SECONDS, max_shots: int = MAX_SHOTS,
) -> List[Dict[str, Any]]:
    """切点 + 总时长 → 分镜表(纯函数);无法构建时返回空列表

    处理顺序与理由:
      ① 丢弃贴着首尾的切点 —— 会造出 0.1s 这种无意义镜头;
      ② 逐切点断开,但**累计时长不足 min_seconds 就不断开**(合并误检),
         且"断开后剩余不足 min_seconds"时也不再断(把尾巴并进当前镜头);
      ③ 镜头数超过 max_shots 就整体按时间等分 —— 碎剪原片宁可粗一点,
         也不能产出几十个镜头把后续每一步都拖长。

    返回项字段:index / start / end / duration(统一保留两位小数,控制 metadata volume)。
    """
    total = float(duration or 0)
    if total <= 0:
        return []
    valid_cuts: List[float] = []
    for item in cuts or []:
        try:
            value = float(item)
        except (TypeError, ValueError):
            continue
        if min_seconds < value < total - min_seconds:
            valid_cuts.append(value)
    valid_cuts.sort()

    ranges: List[Tuple[float, float]] = []
    start = 0.0
    for cut in valid_cuts:
        if cut - start < min_seconds:
            continue          # 太短:不在此断开,继续累积到下一个切点
        if total - cut < min_seconds:
            break             # 断开后剩余太短:剩下的并入当前镜头
        ranges.append((start, cut))
        start = cut
    ranges.append((start, total))

    if not ranges:
        return []
    if len(ranges) > max(max_shots, 1):
        logger.info(f"[shots] 检测到 {len(ranges)} 个镜头,超过上限 {max_shots},按时间等分")
        ranges = _even_ranges(total, max_shots)
    return _to_table(ranges)


def _to_table(ranges: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
    """区间列表 → 分镜表(统一索引与四舍五入)"""
    table: List[Dict[str, Any]] = []
    for idx, (start, end) in enumerate(ranges):
        table.append({
            "index": idx,
            "start": round(float(start), 2),
            "end": round(float(end), 2),
            "duration": round(float(end) - float(start), 2),
        })
    return table


def _shot_span(item: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """取镜头的 (start, end);字段缺失或区间非法返回 None"""
    try:
        start = float(item.get("start") or 0)
        end = float(item.get("end") or 0)
    except (TypeError, ValueError):
        return None
    return (start, end) if end > start else None


def clip_shots(shots: List[Dict[str, Any]], max_seconds: float) -> List[Dict[str, Any]]:
    """把分镜表裁到 [0, max_seconds](纯函数);空表或全部越界返回空列表

    为什么必须裁:参考视频通常比本次要生成的目标时长更长(如原片 45s、目标 30s)。
    直接拿原片分镜表去切目标时长,镜头时长之和与目标时长对不上,切分只能回退按秒。
    裁剪规则:
      · 起点已超过 max_seconds 的镜头整条丢弃;
      · 跨过 max_seconds 的镜头把 end 截到 max_seconds;
      · 裁完仍未覆盖到 max_seconds 时补一个尾镜头 —— 否则分镜表覆盖不到目标时长尾部,
        按镜头切分就会少生成一段。
    """
    total = float(max_seconds or 0)
    if total <= 0 or not shots:
        return []
    out: List[Dict[str, Any]] = []
    for item in shots:
        span = _shot_span(item)
        if not span:
            continue
        start, end = span
        if start >= total:
            continue
        item_end = min(end, total)
        out.append({
            **item,
            "start": round(start, 2),
            "end": round(item_end, 2),
            "duration": round(item_end - start, 2),
        })
    if not out:
        return []
    if out[-1]["end"] < total:
        start = float(out[-1]["end"])
        out.append({
            "index": len(out), "start": start, "end": round(total, 2),
            "duration": round(total - start, 2), "narration": "",
        })
    for idx, item in enumerate(out):
        item["index"] = idx
    return out


def _is_token_char(char: str) -> bool:
    """是否属于"英文/数字 token"字符(判断拼词时要不要补空格)"""
    return bool(char) and char.isascii() and (char.isalnum() or char in "'-")


def join_words(pieces: List[str]) -> str:
    """词序列 → 一句话(纯函数)

    中文直接相连(ASR 对中文是逐词切分,连起来才是原句),
    英文与数字之间补一个空格(否则 `hello` `world` 会粘成 `helloworld`)。
    """
    text = ""
    for piece in pieces:
        piece = str(piece or "").strip()
        if not piece:
            continue
        if not text:
            text = piece
            continue
        if _is_token_char(text[-1]) and _is_token_char(piece[0]):
            text = f"{text} {piece}"
        else:
            text += piece
    return text


def _shot_index_at(shots: List[Dict[str, Any]], at: float) -> Optional[int]:
    """时间点落在第几个镜头内;都在区间外时归到最近的边界镜头

    归到边界镜头(而不是丢弃)是刻意的:ASR 的词尾时间可能正好等于总时长,
    丢弃会让最后一句话整句从分镜表里消失。
    """
    if not shots:
        return None
    for idx, item in enumerate(shots):
        span = _shot_span(item)
        if not span:
            continue
        start, end = span
        if start <= at < end:
            return idx
    first = _shot_span(shots[0])
    if first and at <= first[0]:
        return 0
    return len(shots) - 1


def attach_narration(shots: List[Dict[str, Any]], words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把词级时间戳按镜头区间归集成台词(纯函数),返回**新**的分镜表

    - 一个词归到"其起始时间落入的镜头";
    - 超长台词截断(分镜表要随 metadata 落库,台词只作"这镜在说什么"的索引);
    - 不修改入参,便于调用方复用手上的原始分镜表。
    """
    table = [{**item, "narration": str(item.get("narration") or "")} for item in shots or []]
    if not table or not words:
        return table
    buckets: Dict[int, List[str]] = {}
    for item in words:
        if not isinstance(item, dict):
            continue
        try:
            at = float(item.get("start") or 0)
        except (TypeError, ValueError):
            continue
        text = str(item.get("word") or item.get("text") or "").strip()
        if not text:
            continue
        idx = _shot_index_at(table, at)
        if idx is None:
            continue
        buckets.setdefault(idx, []).append(text)
    for idx, pieces in buckets.items():
        line = join_words(pieces)
        if len(line) > MAX_NARRATION_CHARS:
            line = f"{line[:MAX_NARRATION_CHARS]}…"
        table[idx]["narration"] = line
    return table


def shot_frame_times(
    shots: List[Dict[str, Any]], per_shot: int = 1, limit: int = MAX_FRAME_POINTS,
) -> List[float]:
    """每个镜头的取帧时间点(纯函数);空表返回空列表

    per_shot=1 取镜头首帧(稳定后的画面),per_shot=2 追加尾帧用于首尾帧双锚。
    超上限时先退回"每镜头一帧",仍超则等距抽稀 —— 与画面覆盖广度相比,
    参考图数量受上游素材限制更硬。
    """
    if not shots:
        return []
    points: List[float] = []
    for item in shots:
        span = _shot_span(item)
        if not span:
            continue
        start, end = span
        offset = min(FRAME_OFFSET, (end - start) / 2.0)
        points.append(round(start + offset, 2))
        if per_shot >= 2:
            points.append(round(end - offset, 2))
    if not points:
        return []
    if len(points) > limit and per_shot >= 2:
        return shot_frame_times(shots, per_shot=1, limit=limit)
    if len(points) > limit and limit > 0:
        step = len(points) / float(limit)
        points = [points[min(int(i * step), len(points) - 1)] for i in range(limit)]
    return sorted(set(points))


def analysis_targets(
    shots: List[Dict[str, Any]], limit: int = MAX_ANALYSIS_SHOTS,
) -> List[Dict[str, Any]]:
    """逐镜头逆推(P0-3)的输入清单;空表或全部镜头无效时返回空列表

    每个镜头取「**开始帧 + 结束帧**」两个时间点 —— 只给一帧推不出运镜,
    而景别与运镜恰恰是本项目最想复刻下来的结构信息(见 shot_reverse 提示词的四要素)。

    镜头数超过 limit 时按位置**等距抽稀**:只保留被选中的镜头,
    保证送出的图片与镜头清单**始终一一对应**,不会出现图片与序号错位。

    返回项:index / start / duration / narration / times([开始帧时刻, 结束帧时刻])。
    """
    rows: List[Dict[str, Any]] = []
    for item in shots or []:
        span = _shot_span(item)
        if not span:
            continue
        start, end = span
        offset = min(FRAME_OFFSET, (end - start) / 2.0)
        rows.append({
            "index": int(item.get("index") or 0),
            "start": round(start, 2),
            "duration": round(end - start, 2),
            "narration": str(item.get("narration") or ""),
            "times": [round(start + offset, 2), round(end - offset, 2)],
        })
    if not rows:
        return []
    if len(rows) > max(int(limit), 1):
        step = len(rows) / float(limit)
        rows = [rows[min(int(i * step), len(rows) - 1)] for i in range(limit)]
    return rows


def review_targets(
    shots: List[Dict[str, Any]], limit: int = MAX_ANALYSIS_SHOTS,
) -> List[Dict[str, Any]]:
    """逐镜头质检(P1-7)的输入清单:每个镜头取**中点**一个时间点;空表返回空列表

    为什么取中点而不是首帧:质检是"原片与成片在**同一时间位置**配对比对",
    首帧紧贴镜头切点、容易取到转场残影,不代表这个镜头的常态画面。

    超过 limit 时与 analysis_targets 同样等距抽稀,保证参与评分的镜头清单稳定。
    """
    rows: List[Dict[str, Any]] = []
    for item in shots or []:
        span = _shot_span(item)
        if not span:
            continue
        start, end = span
        rows.append({
            "index": int(item.get("index") or 0),
            "time": round((start + end) / 2.0, 2),
        })
    if not rows:
        return []
    if len(rows) > max(int(limit), 1):
        step = len(rows) / float(limit)
        rows = [rows[min(int(i * step), len(rows) - 1)] for i in range(limit)]
    return rows


async def detect_shots(
    source: str, duration: Optional[float], threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """检测镜头边界并返回分镜表;**任何失败返回空列表**(调用方回退按秒切分)

    source 可以是本地路径,也可以是模型侧可拉取的 http(s) 地址 —— ffmpeg 两者都能读,
    因此这里**刻意不下载**:降级链路里参考视频不一定已经落在本地。
    duration 必须由调用方提供(上游本就探过时长),探测不到就不做检测 ——
    分镜表没有总时长就构不出来,返回空表让调用方走原逻辑。
    threshold 不传时读后台配置 gen.shot_scene_threshold(见 scene_threshold)。
    """
    total = float(duration or 0)
    if not source or total <= 0:
        logger.info("[shots] 跳过镜头检测:缺少素材地址或时长未知")
        return []
    ffmpeg = compose.ffmpeg_path()
    if not ffmpeg:
        logger.info("[shots] 跳过镜头检测:ffmpeg 不可用(容器需安装 ffmpeg)")
        return []
    # 阈值解析:显式传入优先,否则读后台配置;再统一夹紧到 (0,1) 合法区间,
    # 配置/调用写错(如 3 或 -1)时回退默认值,而不是检测出空结果或全片切碎
    value = scene_threshold() if threshold is None else threshold
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = DEFAULT_SCENE_THRESHOLD
    if not 0 < value < 1:
        value = DEFAULT_SCENE_THRESHOLD
    cmd = build_scene_detect_cmd(source, value, ffmpeg)
    # truncate=False:showinfo 结果行位于输出中段,尾截断会把关键行切掉
    # (与 subtitle.detect_speech_segments 同一坑)
    result = await compose.run(cmd, timeout=DETECT_TIMEOUT, truncate=False)
    if not result.get("ok"):
        logger.info(f"[shots] 镜头检测失败,回退按秒切分: {result.get('stderr')}")
        return []
    cuts = parse_scene_times(f"{result.get('stderr') or ''}\n{result.get('stdout') or ''}")
    table = build_shot_list(total, cuts)
    if not table:
        return []
    logger.info(f"[shots] 镜头检测完成: {len(table)} 个镜头(原始切点 {len(cuts)} 个,阈值 {value})")
    return table


async def _ensure_local(source: str) -> Optional[str]:
    """输入已是本地文件则原样返回,否则下载到临时文件;失败返回 None

    download_to_local 是同步阻塞的,必须挪到线程里执行 —— worker 是单事件循环,
    在协程里直接下载会把其他任务 (含视频轮询) 一起卡住。
    """
    if not source:
        return None
    if os.path.exists(source):
        return source
    from app.utils.oss import download_to_local    # 局部导入:保持模块导入轻量
    suffix = os.path.splitext(str(source).split("?")[0])[1] or ".mp4"
    return await asyncio.to_thread(download_to_local, source, suffix=suffix)


async def narrate_shots(source: str, shots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """给分镜表补上**原片台词**(单镜头识别结果);任何失败都原样返回入参分镜表

    为什么要单独跑一次原片 ASR:复刻需要知道"原片在每个镜头里说了什么",
    这是逐镜头提示词逆推与成片质检的输入。而 asr.transcribe_words 只吃本地文件,
    且词级 ASR 默认关闭(gen.asr_model 为空时不启用,避免额外成本)——
    因此这里**先问 asr.enabled(),关闭时连下载都不做**,不给默认链路加任何开销。
    与成片字幕那次 ASR 是两次独立调用,互不影响。

    无论成功与否,返回值都**带 narration 字段**(拿不到词就是空串):
    分镜表会随 metadata 落库,形状必须稳定,消费方不必再判断字段是否存在。
    """
    if not shots:
        return shots
    from app.core import asr    # 局部导入:asr 会反向拉起音频网关工具,避免模块级循环依赖
    if not asr.enabled():
        logger.info("[shots] 跳过原片台词识别:未启用词级 ASR(gen.asr_model 为空)")
        return attach_narration(shots, [])

    local = await _ensure_local(source)
    if not local:
        logger.warning("[shots] 原片台词识别跳过:素材下载失败")
        return attach_narration(shots, [])
    try:
        words = await asr.transcribe_words(local)
    finally:
        # 只删自己下载的临时文件;调用方传进来的本地文件由调用方负责清理
        if local != source:
            try:
                os.remove(local)
            except OSError:
                pass
    if not words:
        logger.info("[shots] 原片未识别出词级台词(或无音轨),分镜表台词留空")
        return attach_narration(shots, [])
    table = attach_narration(shots, words)
    logger.info(f"[shots] 原片台词已按镜头归集: {len(table)} 个镜头,{len(words)} 个词")
    return table
