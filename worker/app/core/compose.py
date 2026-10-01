# -*- coding: utf-8 -*-
'''
@文件    :compose.py
@说明    :P3 合成层 — ffmpeg 命令构建(纯函数) + 异步执行
@时间    :2026/09/21 11:00:00
@作者    :一源AI
@版本    :1.0
@说明    :本模块是 P3(字幕轨 / B-roll 轨 / BGM 轨)的地基,当前只做**不依赖词级时间戳**的能力:
          ① 视频 + 口播音频合成(音轨补齐)
          ② BGM 铺底混音(整轨,只需视频时长,不需要 P1 的词级时间戳)

          卡拉 OK 字幕与 B-roll 卡点必须等 P1 落地(否则无时间轴可卡点,先做会返工),
          届时只需在本模块追加 build_subtitle_cmd / build_broll_cmd,命令构建风格一致。

          安全:一律用 create_subprocess_exec + 参数列表,**不拼接 shell 字符串**,
          素材 URL 来自外部输入,拼接 shell 会直接变成命令注入。
'''
from __future__ import annotations

import asyncio
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 默认 BGM 音量(0~1):铺底不能压过人声,默认压到 30%
DEFAULT_BGM_VOLUME = 0.3
# 合成超时(秒):长视频重编码可能很慢,超时按失败处理并回退原片
DEFAULT_TIMEOUT = 600

# 字幕样式:ASS 颜色为 AABBGGRR(低位在前);白色字 + 黑色描边是通用高对比方案
DEFAULT_SUBTITLE_FONT_SIZE = 28
# 单行中文字幕约 16 个字,超过则折行(**优先在标点后断开**)
MAX_SUBTITLE_LINE_CHARS = 16
# 单条字幕的字数上限:整句超过它,就按逗号级标点继续细分成多条。
# 否则 20+ 字的台词会整条挂在屏幕上一动不动,观感发闷(实测成片只有 2 条字幕、
# 每条停留 5 秒,就是因为没做这一层细分)。
MAX_SUBTITLE_CUE_CHARS = 12
# 折行时优先断在这些标点之后。硬折会把标点甩到下一行行首(如「，喜欢就」),像排版事故
_BREAK_AFTER = "，,、：:；;。！？!?; "

# 字体文件 → 字体家族名:按此顺序在字体目录里找第一个存在的
# 只列「免费可分发 + 各平台常见」的字体,避免上线才发现字体缺失
_FONT_FILES: Tuple[Tuple[str, str], ...] = (
    ("msyh.ttc", "Microsoft YaHei"),          # Windows
    ("msyhbd.ttc", "Microsoft YaHei"),
    ("simhei.ttf", "SimHei"),
    ("NotoSansCJKsc-Regular.otf", "Noto Sans CJK SC"),   # Debian fonts-noto-cjk
    ("NotoSansCJK-Regular.ttc", "Noto Sans CJK SC"),
    ("NotoSansSC-Regular.ttf", "Noto Sans SC"),
    ("wqy-zenhei.ttc", "WenQuanYi Zen Hei"),
    ("wqy-microhei.ttc", "WenQuanYi Micro Hei"),
)


def bundled_font_dir() -> Path:
    """仓库自带字体目录:worker/app/assets/fonts(可选,放进去即优先生效)"""
    return Path(__file__).resolve().parents[1] / "assets" / "fonts"


def system_font_dirs() -> List[Path]:
    """系统字体目录:Windows 与 Linux 差异极大,按平台返回"""
    if os.name == "nt":
        return [Path(r"C:\Windows\Fonts")]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"]


def resolve_subtitle_font() -> Optional[Tuple[str, Optional[str]]]:
    """解析可用的中文字体,返回 (字体家族名, fontsdir);没有可用字体返回 None

    为什么必须探测:ffmpeg 烧字幕**不会因为缺字体而报错**(返回码仍然是 0),
    只会渲染成豆腐块或干脆不显示 —— 所以宁可不烧,也不能出豆腐块。
    fontsdir 只在字体来自仓库自带目录时返回(系统目录由 fontconfig 自己找,
    且 Windows 盘符路径带冒号,传给 filter 会炸)。
    """
    bundled = bundled_font_dir()
    for name, family in _FONT_FILES:
        if (bundled / name).exists():
            return family, str(bundled)
    for directory in system_font_dirs():
        if not directory.is_dir():
            continue
        for name, family in _FONT_FILES:
            # 系统包字体通常装在嵌套子目录(如 Debian fonts-noto-cjk →
            # opentype/noto/NotoSansCJK-Regular.ttc),只查目录顶层会漏配,
            # 表现为"字体已安装却判定缺失、字幕烧录被跳过"(实测踩过)。
            if next(directory.rglob(name), None) is not None:
                return family, None
    return None


def default_subtitle_style(font: str, font_size: int = DEFAULT_SUBTITLE_FONT_SIZE) -> str:
    """生成 ASS force_style:白字黑边 + 底部居中"""
    return (
        f"FontName={font},FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,"
        "Alignment=2,MarginV=40"
    )


def ffmpeg_path() -> Optional[str]:
    """ffmpeg 可执行文件路径;未安装返回 None(docker-compose 中 worker 镜像已安装)"""
    return shutil.which("ffmpeg")


def available() -> bool:
    """合成层是否可用:容器未装 ffmpeg 时,调用方应跳过合成、保留原片"""
    return ffmpeg_path() is not None


def build_mix_audio_cmd(video: str, audio: str, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """视频 + 口播音频 → 成片

    -c:v copy:视频流不重编码(省时且无损,生成的成片本就是 H.264);
    -c:a aac:音频统一转 AAC(浏览器/iOS 兼容性最好);
    -shortest:以较短输入为准,避免音频比视频长时尾部拖一段静音。
    """
    return [ffmpeg, "-y", "-i", video, "-i", audio, "-shortest", "-c:v", "copy", "-c:a", "aac", out]


def build_bgm_cmd(
    video: str, bgm: str, out: str, bgm_volume: float = DEFAULT_BGM_VOLUME, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """BGM 铺底:视频原声 + BGM 混音

    amix=inputs=2:duration=shortest —— 以视频为准截断 BGM,避免 BGM 比成片长导致尾部拖音;
    原声轨必须存在,无原声时(生成器只出画面)应先走 build_mix_audio_cmd 补一条静音轨再混。
    """
    return [
        ffmpeg, "-y", "-i", video, "-i", bgm,
        "-filter_complex",
        f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=shortest[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", out,
    ]


def split_sentences(text: str) -> List[str]:
    """按常见标点把一段文案切成字幕条目(空句/仅空白丢弃)"""
    if not text:
        return []
    parts = re.split(r"([。！？；.!?;])", text.strip())
    sentences: List[str] = []
    buf = ""
    for part in parts:
        if not part:
            continue
        buf += part
        if re.match(r"[。！？；.!?;]", part):
            stripped = buf.strip()
            if stripped:
                sentences.append(stripped)
            buf = ""
    if buf.strip():
        sentences.append(buf.strip())
    return sentences or [text.strip()]


@dataclass
class Cue:
    """一条字幕 cue:屏幕上的文字及其时间窗(毫秒)"""
    start_ms: int
    end_ms: int
    text: str


def _wrap_text(text: str, max_chars: int = MAX_SUBTITLE_LINE_CHARS) -> str:
    """按 max_chars 折行,**优先在标点之后断开**

    硬折(每满 max_chars 切一刀)会把标点甩到下一行行首(「，喜欢就点下方链接」),
    读起来像排版事故;这里在窗口内回退到最近的标点处断开。
    """
    if len(text) <= max_chars:
        return text
    lines: List[str] = []
    rest = text
    while len(rest) > max_chars:
        window = rest[:max_chars]
        cut = 0
        for i in range(len(window) - 1, -1, -1):
            if window[i] in _BREAK_AFTER:
                cut = i + 1
                break
        # 标点太靠前会让这行只剩几个字,还不如硬折(避免出现"孤字行")
        if cut < max_chars // 2:
            cut = max_chars
        lines.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        lines.append(rest)
    return "\n".join(lines)


def _split_by_secondary_breaks(text: str) -> List[str]:
    """按逗号级标点切块,标点归前一块(与 split_sentences 的"句末标点"区分)"""
    tokens: List[str] = []
    buf = ""
    for part in re.split(r"([，,、：:；;])", text):
        if not part:
            continue
        buf += part
        if part in "，,、：:；;":
            tokens.append(buf)
            buf = ""
    if buf:
        tokens.append(buf)
    return tokens


def split_cue_text(text: str, max_chars: int = MAX_SUBTITLE_CUE_CHARS) -> List[str]:
    """把一句文案细分成多条字幕:优先在逗号级标点断开,单块仍超长才按字数硬切

    目的:让字幕跟着语速推进。实测一句 23 字的台词整条显示会挂在屏幕上 5 秒,
    切成语义小组后节奏感接近真实口播。
    """
    chunks: List[str] = []
    buf = ""
    for token in _split_by_secondary_breaks(text or ""):
        if buf and len(buf) + len(token) > max_chars:
            chunks.append(buf)
            buf = ""
        buf += token
        # 单块自身就超长(整句没有任何标点):只能硬切
        while len(buf) > max_chars:
            chunks.append(buf[:max_chars])
            buf = buf[max_chars:]
    if buf:
        chunks.append(buf)
    return chunks


def _ms_to_srt(ms: int) -> str:
    """毫秒 → SRT 时间格式 HH:MM:SS,mmm"""
    total = max(0, ms)
    h = total // 3_600_000
    m = (total % 3_600_000) // 60_000
    s = (total % 60_000) // 1000
    millis = total % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def build_srt(cues: List[Cue], max_chars: int = MAX_SUBTITLE_LINE_CHARS) -> str:
    """Cue 列表 → SRT 文本(纯函数,便于单测)"""
    blocks: List[str] = []
    for idx, cue in enumerate(cues, start=1):
        blocks.append(str(idx))
        blocks.append(f"{_ms_to_srt(cue.start_ms)} --> {_ms_to_srt(cue.end_ms)}")
        blocks.append(_wrap_text(cue.text, max_chars))
        blocks.append("")
    return "\r\n".join(blocks)


def build_cues(segments: List[Dict[str, Any]], timing: Dict[str, Any]) -> List[Cue]:
    """由词锚点脚本 + 时间窗生成字幕 cue

    输入:
      segments: script_anchor.build_segments 产出的段落,含 id/text/words;
      timing  : estimate_timing(script, duration) 产出的时间窗,含 segments.{id}.start_ms/end_ms;
                P1 真实对齐落地后,只要数据结构一致即可无缝替换,上层调用不变。
    处理:
      - 每段按句末标点分句;
      - 每句再按逗号级标点**细分成多条**(长句不再一条挂满整段);
      - 各条按词数占比分摊该段时间;
      - 超长文本折行(优先在标点后断)。
    """
    cues: List[Cue] = []
    seg_timing = (timing or {}).get("segments") or {}
    for seg in segments or []:
        seg_id = seg.get("id")
        seg_window = seg_timing.get(seg_id) or {}
        start_ms = int(seg_window.get("start_ms") or 0)
        end_ms = int(seg_window.get("end_ms") or start_ms)
        seg_words = seg.get("words") or []
        total = len(seg_words)
        if total <= 0 or end_ms <= start_ms:
            # 没有时间窗:整段作为一条 cue,兜底显示
            cues.append(Cue(start_ms=start_ms, end_ms=end_ms, text=seg.get("text") or ""))
            continue
        # 两级切分:先用句末标点断句,再把长句按逗号级标点细分
        units: List[str] = []
        for sent in split_sentences(seg.get("text") or ""):
            units.extend(split_cue_text(sent))
        if not units:
            continue
        # 按各条自身词数占比分配时间(用细分后的词数,比拿整段词数当分母更准)
        unit_words = [max(1, len(re.findall(r"[0-9A-Za-z]+|[\u4e00-\u9fff]", u))) for u in units]
        sum_words = sum(unit_words)
        cursor = start_ms
        for idx, unit in enumerate(units):
            span = round((end_ms - start_ms) * unit_words[idx] / sum_words)
            cues.append(Cue(start_ms=cursor, end_ms=min(cursor + span, end_ms), text=unit))
            cursor += span
    # 兜底:至少保证首尾不越界、文本折行已处理(在 build_srt 里)
    return cues


def build_extract_last_frame_cmd(video: str, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """抽取视频的最后一帧:多段生成的「续接首帧」靠它

    -sseof -0.1 表示"从结尾前 0.1 秒起",比先探时长再算 -ss 少一步(快照式取帧);
    输出用 JPG 而非 PNG:作为首帧要上传给模型,体积小一个量级,下载更快。
    """
    return [ffmpeg, "-y", "-sseof", "-0.1", "-i", video, "-frames:v", "1", "-q:v", "2", out]


def build_extract_frame_cmd(
    video: str, out: str, at: float, width: int = 0, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """在指定时间点抽一帧(逐镜头逆推要按镜头时间点取画面)

    -ss 放在 -i **之前**:输入侧定位只解到目标位置为止,比输出侧定位快一个量级;
    width > 0 时等比缩到该宽度 —— 送多模态模型的画面不必是原分辨率,越小越省 token。
    """
    cmd = [ffmpeg, "-y", "-ss", f"{max(0.0, float(at)):.2f}", "-i", video, "-frames:v", "1"]
    if width and int(width) > 0:
        cmd += ["-vf", f"scale={int(width)}:-1"]
    cmd += ["-q:v", "2", out]
    return cmd


def build_concat_list(segments: List[str]) -> str:
    """生成 concat demuxer 清单文本(条目必须是相对文件名,单引号做转义)"""
    lines = []
    for name in segments:
        lines.append("file '" + str(name).replace("'", "'\\''") + "'")
    return "\n".join(lines)


def build_concat_cmd(list_name: str, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """拼接多段成片:同源同参数,可 stream copy(秒级完成,不重编码)

    ⚠️ list_name 必须是**相对文件名**(放在 cwd 下):与字幕 SRT 同理,
    Windows 盘符的冒号会被 ffmpeg 当选项分隔符解析。
    -fflags +genpts 放在 -i 之前(输入选项),重新生成时间戳,避免拼接后时间轴错乱。
    """
    return [
        ffmpeg, "-y", "-fflags", "+genpts", "-f", "concat", "-safe", "0",
        "-i", list_name, "-c", "copy", out,
    ]


def build_xfade_concat_cmd(
    seg_names: List[str], durations: List[float], out: str,
    transition: float = 0.5, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """多段成片转场拼接:相邻段 xfade(视频)+ acrossfade(音频)交叉淡化。

    与 build_concat_cmd 的区别:concat demuxer 只能流复制、段间硬切;
    xfade 必须重编码,但能做出平滑过渡。offset 计算:第 i 段(i>=1)的接入点
    = 前 i 段总时长 - i*transition,因为每处交叉重叠都会把总时长缩短 transition。
    段数 < 2 时调用方应退回流复制拼接。
    """
    n = len(seg_names)
    if n < 2:
        raise ValueError("xfade 至少需要 2 段")
    vfilter = f"[{0}:v][{1}:v]xfade=transition=fade:duration={transition}:offset={durations[0] - transition:.3f}[v01]"
    afilter = f"[{0}:a][{1}:a]acrossfade=d={transition}:c1=tri:c2=tri[a01]"
    vlabel, alabel = "[v01]", "[a01]"
    cumulative = durations[0]
    for i in range(2, n):
        cumulative += durations[i - 1]
        offset = cumulative - i * transition
        vi = f"[v{i:02d}]"
        ai = f"[a{i:02d}]"
        vfilter += f";{vlabel}[{i}:v]xfade=transition=fade:duration={transition}:offset={offset:.3f}{vi}"
        afilter += f";{alabel}[{i}:a]acrossfade=d={transition}:c1=tri:c2=tri{ai}"
        vlabel, alabel = vi, ai
    inputs = []
    for name in seg_names:
        inputs += ["-i", name]
    return [
        ffmpeg, "-y", *inputs,
        "-filter_complex", f"{vfilter};{afilter}",
        "-map", vlabel, "-map", alabel,
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-shortest", out,
    ]


def build_kenburns_cmd(
    in_path: str, out_path: str, duration: float, width: int, height: int,
    zoom_start: float = 1.0, zoom_end: float = 1.08, fps: int = 30, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """轻度 Ken Burns 运镜:在整段时长内让画面从 zoom_start 线性推近/拉远到 zoom_end,
    保持画面中心,输出时长与输入一致。zoom_end>zoom_start 为缓慢推近,<1 为拉远。

    用 zoompan 实现:zoom>1 时放大并居中对齐,等效于缓慢推进镜头。仅产出命令,
    调用方需自行处理失败回退(滤镜不支持/ffmpeg 异常时回退原片段)。
    """
    try:
        d = max(2, int(round(float(duration) * fps)))
    except (TypeError, ValueError):
        d = 60
    # 逐帧 zoom 表达式:从 zoom_start 线性增长到 zoom_end,min 防止末帧越界抖动
    z_expr = f"min({zoom_start}+(({zoom_end})-({zoom_start}))*on/{d},{zoom_end})"
    vf = f"zoompan=z='{z_expr}':d={d}:s={int(width)}x{int(height)}:fps={fps}:crop=none"
    return [ffmpeg, "-y", "-i", in_path, "-vf", vf, "-c:a", "copy", out_path]


def build_trim_cmd(video: str, out: str, start: int, duration: int, ffmpeg: str = "ffmpeg") -> List[str]:
    """按时间窗裁剪视频(多段生成时把参考视频切成对应段落)

    重编码而非 copy:copy 只能按关键帧切,段落边界会漂移,导致
    "参考段时长"与"生成段时长"对不上(进而影响续接首帧的取法)。
    """
    return [
        ffmpeg, "-y", "-ss", str(max(0, start)), "-i", video, "-t", str(max(1, duration)),
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out,
    ]


# 画中画四个角的位置表达式(overlay 滤镜的 x/y):W/H 为背景尺寸,w/h 为叠加层尺寸
_PIP_POSITIONS = {
    "br": "W-w-{m}:H-h-{m}",  # 右下
    "bl": "{m}:H-h-{m}",      # 左下
    "tr": "W-w-{m}:{m}",      # 右上
    "tl": "{m}:{m}",          # 左上
}


def build_pip_cmd(
    bg: str, overlay: str, out: str, scale: float = 0.3, position: str = "br",
    margin: int = 20, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """画中画(presenter-led-explainer):把 overlay 视频缩成小窗叠到背景视频之上。

    数字人讲解场景:数字人成片作为小窗(默认右下角、占背景宽 30%)叠在演示/图表背景上,
    实现"边讲边演示"。声音以背景音轨为主(数字人成片的音轨被丢弃),符合"主讲声音独立连接"原则。

    - scale:叠加层相对背景宽度的比例(0~1);
    - position:br/bl/tr/tl 四角;
    - 重编码(overlay 必须重编码),音频取背景原声(copy),不重编码音频避免再次解码损耗。
    """
    pos = _PIP_POSITIONS.get((position or "br").lower(), _PIP_POSITIONS["br"]).format(m=int(margin))
    scale_pct = max(0.05, min(1.0, float(scale or 0.3)))
    return [
        ffmpeg, "-y", "-i", bg, "-i", overlay,
        "-filter_complex",
        f"[1:v]scale=w=iw*{scale_pct:.3f}:h=-1[ov];[0:v][ov]overlay={pos}[v]",
        "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "copy", "-shortest", out,
    ]


def build_cover_cmd(
    bg: str, overlay: str, out: str, audio_source: str = "overlay", ffmpeg: str = "ffmpeg",
) -> List[str]:
    """满屏覆盖(presenter-led-explainer / 数字人替换场景):把 overlay(数字人成片)缩放到适配 bg
    并居中叠到背景之上,取 overlay 音轨(口播声)作为成片音轨。

    与 build_pip_cmd 的区别:pip 是「小窗」(保留背景音);cover 是「满屏」(用前景音替换背景音),
    用于「数字人进入视频 A 口播」或「数字人立于场景 B」。缩放用 scale2ref 相对 bg 适配、不裁切,
    故要求 overlay 与 bg 同画幅(数字人路线已按源视频比例生成,通常吻合)。
    """
    audio_map = "1:a" if audio_source == "overlay" else "0:a?"
    return [
        ffmpeg, "-y", "-i", bg, "-i", overlay,
        "-filter_complex",
        "[1:v][0:v]scale2ref=w=iw:h=ih:force_original_aspect_ratio=decrease[ov][bg];"
        "[bg][ov]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[v]",
        "-map", "[v]", "-map", audio_map,
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-shortest", out,
    ]


def build_scene_swap_cmd(
    source: str, scene: str, out: str, color: str = "0x00FF00",
    similarity: float = 0.12, blend: float = 0.05, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """换场景(保留真人):先用色键(chromakey)把 source 的绿幕抠成透明,再把真人叠到 scene 之上。

    适用:源视频为绿幕/蓝幕拍摄;AI 语义抠像(任意背景)需额外模型网关,此处用色键作为内置实现。
    scale2ref 让真人适配场景尺寸(不裁切、居中),scene 可为图片或视频。
    """
    fg = (
        f"[0:v]chromakey=color={color}:similarity={similarity:.3f}:blend={blend:.3f}[fg];"
        f"[fg][1:v]scale2ref=w=iw:h=ih:force_original_aspect_ratio=decrease[fg2][bg];"
        f"[bg][fg2]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[v]"
    )
    return [
        ffmpeg, "-y", "-i", source, "-i", scene,
        "-filter_complex", fg,
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "copy", "-shortest", out,
    ]


# —— AI 抠像(视频换场景保留真人)相关命令 ——
async def probe_fps(video: str, ffprobe: str = "ffprobe") -> float:
    """探测视频帧率(返回小数 fps);探测失败返回 0.0(调用方回退默认 25)。"""
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=nokey=1:noprint_wrappers=1",
            video, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        txt = (out or b"").decode().strip()
        if txt:
            num, _, den = txt.partition("/")
            if den and float(den):
                return float(num) / float(den)
            return float(txt)
    except Exception:
        pass
    return 0.0


def build_matte_frames_extract(video: str, out_dir: str, sample_fps: float = 0.0, ffmpeg: str = "ffmpeg") -> List[str]:
    """抽帧:把源视频逐帧导出为 PNG(供逐帧抠像)。sample_fps>0 时按该帧率降采样,降低长视频负担。"""
    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "frame_%08d.png")
    cmd = [ffmpeg, "-y", "-i", video]
    if sample_fps and sample_fps > 0:
        cmd += ["-vf", f"fps={sample_fps:.3f}"]
    cmd += [pattern]
    return cmd


def build_rgba_frames_assemble(frames_dir: str, out: str, fps: float, ffmpeg: str = "ffmpeg") -> List[str]:
    """把逐帧 RGBA PNG 重组成保留透明通道的前景视频(png 编码保 alpha,封装为 .mov)。"""
    pattern = os.path.join(frames_dir, "frame_%08d.png")
    return [
        ffmpeg, "-y", "-framerate", f"{fps:.3f}", "-i", pattern,
        "-c:v", "png", out,
    ]


def build_matte_overlay_cmd(fg_rgba: str, scene: str, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """AI 抠像合成:把 RGBA 前景(已去背景)叠到场景 B 之上(scale2ref 让场景适配前景尺寸,alpha 自然抠边)。"""
    fc = (
        "[1:v][0:v]scale2ref=w=iw:h=ih[bg][fg];"
        "[bg][fg]overlay=shortest=1[v]"
    )
    return [
        ffmpeg, "-y", "-i", fg_rgba, "-i", scene,
        "-filter_complex", fc,
        "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-shortest", out,
    ]


def build_burn_subtitle_cmd(
    video: str, srt_name: str, out: str, style: str,
    fonts_dir: Optional[str] = None, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """字幕烧录:把 SRT 压到画面上,**音频 copy 保留原音轨**

    ⚠️ 两条硬规则(都是实测踩出来的):
      1. srt_name 必须是**相对文件名**(放在 cwd 下),不要传 Windows 盘符绝对路径 ——
         subtitles filter 把冒号当选项分隔符,会报 `Unable to parse original_size` 这种离奇错误;
         调用时请用 `run(..., cwd=str(srt_path.parent))`。
      2. fonts_dir 同理不能带冒号;它只在字体来自仓库自带目录时才传(系统字体交给 fontconfig)。

    style 由调用方用 `default_subtitle_style(font)` 生成:字体必须先用
    `resolve_subtitle_font()` 确认存在,否则烧出来是豆腐块且 ffmpeg 不报错。
    """
    filter_value = f"subtitles={srt_name}"
    if fonts_dir:
        filter_value += f":fontsdir={fonts_dir}"
    filter_value += f":force_style='{style}'"
    return [
        ffmpeg, "-y", "-i", video, "-vf", filter_value,
        "-c:v", "libx264", "-c:a", "copy", "-shortest", out,
    ]


async def run(
    cmd: List[str], timeout: int = DEFAULT_TIMEOUT, cwd: Optional[str] = None,
    truncate: bool = True,
) -> Dict[str, Any]:
    """异步执行 ffmpeg(不阻塞事件循环)

    cwd:字幕烧录等场景需要把 srt 放在 cwd 下,以绕过 Windows 路径冒号问题。
    truncate=False:保留完整输出。**只做分析、不产出文件**的命令(如 silencedetect)
    必须关掉截断 —— 它的结果行位于输出中段,尾部截断会把关键行切掉,
    表现为"命令成功但一个静音都没解析出来"。

    失败**不抛异常**,返回结构化结果:合成是增强能力,失败应当回退到原片,
    绝不能让「加个 BGM」把一次已付费的生成变成失败任务。
    """
    if not cmd:
        return {"ok": False, "error": "empty command"}
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
    except FileNotFoundError:
        return {"ok": False, "error": "ffmpeg 不可用(容器需安装 ffmpeg)", "returncode": None}
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return {"ok": False, "error": f"合成超时({timeout}s)", "returncode": None}
    out_err = (stderr or b"").decode("utf-8", "ignore")
    out_std = (stdout or b"").decode("utf-8", "ignore")
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stderr": out_err[-1000:] if truncate else out_err,
        "stdout": out_std[-500:] if truncate else out_std,
    }
