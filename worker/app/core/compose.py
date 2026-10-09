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
# 画中画时默认压低背景原声的音量(0~1):数字人口播是主信息,背景只做铺底,
# 不压低会两路人声打架、听不清台词(此前更糟:直接丢掉口播声)。
DEFAULT_PIP_BG_VOLUME = 0.2
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


def subtitle_font_path() -> Optional[str]:
    """返回可用中文字体的**文件绝对路径**(供 PIL 直接加载,而非 ffmpeg 的字体族名)。

    代码渲染层(overlay.py)用 PIL 画字幕/卡片/角标,需要的是真实字体文件;
    与 resolve_subtitle_font 同源探测,优先仓库自带目录、再查系统字体目录的嵌套子目录。
    没有可用字体返回 None(调用方应跳过代码渲染,保留原片)。
    """
    bundled = bundled_font_dir()
    for name, _family in _FONT_FILES:
        if (bundled / name).exists():
            return str(bundled / name)
    for directory in system_font_dirs():
        if not directory.is_dir():
            continue
        for name, _family in _FONT_FILES:
            hit = next(directory.rglob(name), None)
            if hit is not None:
                return str(hit)
    return None


def default_subtitle_style(font: str, font_size: int = DEFAULT_SUBTITLE_FONT_SIZE) -> str:
    """生成 ASS force_style:白字黑边 + 底部居中"""
    return (
        f"FontName={font},FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,"
        "Alignment=2,MarginV=40"
    )


# 字幕风格预设(对齐 Hypit captions「Fine styles」):每个预设给出 force_style 的字体/颜色/描边差异,
# 统一从默认推导;未知/留空回退 default,保证旧行为不变。
_CAPTION_PRESETS: Dict[str, Dict[str, Any]] = {
    # 默认:白字黑边(与旧版 default_subtitle_style 完全一致)
    "default":  {"fontsize": DEFAULT_SUBTITLE_FONT_SIZE, "primary": "&H00FFFFFF",
                 "outline": "&H00000000", "outline_w": 2, "shadow": 1, "back": None,
                 "align": 2, "marginv": 40},
    # 醒目:综艺/促销感,黄字粗描边 + 半透明底纹,字号更大,突出口播重点
    "highlight": {"fontsize": DEFAULT_SUBTITLE_FONT_SIZE + 6, "primary": "&H0000FFFF",
                  "outline": "&H00000000", "outline_w": 3, "shadow": 2, "back": "&H80000000",
                  "align": 2, "marginv": 40},
    # 简约:小一号白字 + 浅灰细描边,无阴影,适合画面信息密集的片段
    "minimal":   {"fontsize": DEFAULT_SUBTITLE_FONT_SIZE - 4, "primary": "&H00FFFFFF",
                  "outline": "&H00333333", "outline_w": 1, "shadow": 0, "back": None,
                  "align": 2, "marginv": 48},
    # 活泼:绿字白描边,适合轻松带货/种草口播
    "variety":   {"fontsize": DEFAULT_SUBTITLE_FONT_SIZE + 2, "primary": "&H0000FF00",
                  "outline": "&H00FFFFFF", "outline_w": 2, "shadow": 1, "back": None,
                  "align": 2, "marginv": 40},
}


def caption_style(font: str, style_name: Optional[str] = None) -> str:
    """按预设名生成 ASS force_style;未知/留空回退 default。

    预设只改字体/颜色/描边等视觉片段,字体名(必须先用 resolve_subtitle_font 确认存在)
    与底部分配对齐仍由调用方注入,避免烧出豆腐块。
    """
    preset = _CAPTION_PRESETS.get((style_name or "default").lower(), _CAPTION_PRESETS["default"])
    back = f"BackColour={preset['back']}," if preset.get("back") else ""
    return (
        f"FontName={font},FontSize={preset['fontsize']},"
        f"PrimaryColour={preset['primary']},OutlineColour={preset['outline']},"
        f"Outline={preset['outline_w']},Shadow={preset['shadow']},"
        f"{back}Alignment={preset['align']},MarginV={preset['marginv']}"
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
    video: str, bgm: str, out: str, bgm_volume: float = DEFAULT_BGM_VOLUME,
    duck_intervals: Optional[List[Tuple[float, float]]] = None,
    duck_level: Optional[float] = None, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """BGM 铺底:视频原声 + BGM 混音(支持可选 ducking)

    amix=inputs=2:duration=shortest —— 以视频为准截断 BGM,避免 BGM 比成片长导致尾部拖音;
    原声轨必须存在,无原声时(生成器只出画面)应先走 build_mix_audio_cmd 补一条静音轨再混。

    ducking:提供 duck_intervals=[(start,end)...](秒)时,人声段把 BGM 压到 duck_level,
    其余保持 bgm_volume,突出口播清晰度。实现上用一串 `volume=enable='between(t,s,e)':volume=X`
    链式滤镜:enable 为假时该滤镜透传(不改变增益),故每段只压自己那一段、互不影响;
    无 duck_intervals 时退化为「整轨恒定音量」的旧行为,命令形状不变。
    """
    if duck_intervals:
        intervals = [iv for iv in duck_intervals if len(iv) == 2 and iv[1] > iv[0]]
        if intervals:
            level = max(0.0, min(1.0, float(duck_level if duck_level is not None else 0.12)))
            chain = f"[1:a]volume={bgm_volume}[b0]"
            label = "[b0]"
            for i, (s, e) in enumerate(intervals, start=1):
                nxt = f"[b{i}]"
                chain += (
                    f";{label}volume=enable='between(t,{s:.3f},{e:.3f})':volume={level}{nxt}"
                )
                label = nxt
            bgm_label = label.lstrip("[").rstrip("]")
            filter_expr = f"{chain};[0:a][{bgm_label}]amix=inputs=2:duration=shortest[a]"
        else:
            filter_expr = f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=shortest[a]"
    else:
        filter_expr = f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=shortest[a]"
    return [
        ffmpeg, "-y", "-i", video, "-i", bgm,
        "-filter_complex", filter_expr,
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
    """一条字幕 cue:屏幕上的文字及其时间窗(毫秒)

    pos:可选,头部跟随字幕时字幕锚点(归一化 0~1 的头部上沿中心 nx,ny),
        由 caption-tracking 在烧录前注入;为 None 时走默认底部居中。
    """
    start_ms: int
    end_ms: int
    text: str
    pos: Optional[Tuple[float, float]] = None


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


def video_canvas(ratio: Optional[str], resolution: Optional[str]) -> Optional[Tuple[int, int]]:
    """由画幅 + 清晰度推算成片像素尺寸(宽,高);无法识别返回 None。

    用于头部跟随字幕(ASS \\pos)把归一化头部坐标换算成画布像素。
    render/digital 的 params 必带 ratio/resolution(已归一化),故通常可解析;
    识别不出时调用方应回退到默认底部字幕,不强行定位。
    """
    base_map = {"1080P": 1080, "1080": 1080, "720P": 720, "720": 720, "480P": 480, "480": 480}
    base = base_map.get((resolution or "").upper() if resolution else "")
    if not base:
        return None
    r = (ratio or "").replace("：", ":").strip()
    if r == "9:16":
        return base, round(base * 16 / 9)
    if r == "16:9":
        return round(base * 16 / 9), base
    if r in ("1:1", "square"):
        return base, base
    return None


def _ms_to_ass(ms: int) -> str:
    """毫秒 → ASS 时间格式 H:MM:SS.cc(厘秒)"""
    total = max(0, int(ms))
    h = total // 3_600_000
    m = (total % 3_600_000) // 60_000
    s = (total % 60_000) // 1000
    cs = (total % 1000) // 10
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass(cues: List[Cue], canvas: Tuple[int, int], max_chars: int = MAX_SUBTITLE_LINE_CHARS) -> str:
    """Cue 列表 → ASS 文本(纯函数,便于单测)

    与 build_srt 的区别:支持逐条字幕定位 —— 带 pos 的 cue 用 {\\an2\\pos(px,py)}
    把字幕底边中点锚到头部上沿中心(即「字幕跟随头部」),未带 pos 的走默认底部居中。
    force_style 仍由调用方经 filter 注入(字体/颜色),此处只负责对齐与位置。
    """
    width, height = canvas
    blocks: List[str] = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,28,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,20,20,20,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cue in cues:
        text = _wrap_text(cue.text, max_chars).replace("\n", "\\N")
        if cue.pos:
            px = round(max(0.0, min(1.0, cue.pos[0])) * width)
            py = round(max(0.0, min(1.0, cue.pos[1])) * height)
            # \\an2 = 底部居中锚点:文字底边中点落在 (px,py),即头部上方居中
            ov = f"{{\\an2\\pos({px},{py})}}{text}"
        else:
            ov = text
        blocks.append(f"Dialogue: 0,{_ms_to_ass(cue.start_ms)},{_ms_to_ass(cue.end_ms)},Default,,0,0,0,,{ov}")
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
    transition: float = 0.5, transition_type: str = "fade",
    transition_types: "list" = None, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """多段成片转场拼接:相邻段 xfade(视频)+ acrossfade(音频)。

    与 build_concat_cmd 的区别:concat demuxer 只能流复制、段间硬切;
    xfade 必须重编码,但能做出平滑过渡。offset 计算:第 i 段(i>=1)的接入点
    = 前 i 段总时长 - i*transition,因为每处交叉重叠都会把总时长缩短 transition。
    段数 < 2 时调用方应退回流复制拼接。

    转场"观感"类型(运镜式):
      - fade / dissolve          交叉溶解(无运镜感)
      - slideleft/right/up/down  上一段滑出、下一段从对侧滑入,像镜头平移扫过(运镜感)
      - coverleft/right/up/down  一块画面像推镜一样覆盖过来
      - zoomin                   推近,像镜头向前推进
    transition_types 为"逐切序列":第 k 个剪切点(连接第 k、k+1 段)使用的转场类型,
    长度不足时循环复用,从而让一条多镜短片的不同接缝呈现不同运镜手法、避免机械重复。
    传 None 则所有剪切点统一使用 transition_type 这一个值。
    注意:transition 这个参数名实际承载的是"转场时长(秒)",历史命名,勿与类型参数混淆。
    """
    n = len(seg_names)
    if n < 2:
        raise ValueError("xfade 至少需要 2 段")
    # 取第 k 个剪切点(0-based)对应的转场类型;未给序列则用统一的 transition_type,
    # 给了序列则循环取用,使每个接缝运镜手法不同。
    def _type_of(k: int) -> str:
        if transition_types:
            return transition_types[k % len(transition_types)]
        return transition_type
    vfilter = f"[{0}:v][{1}:v]xfade=transition={_type_of(0)}:duration={transition}:offset={durations[0] - transition:.3f}[v01]"
    afilter = f"[{0}:a][{1}:a]acrossfade=d={transition}:c1=tri:c2=tri[a01]"
    vlabel, alabel = "[v01]", "[a01]"
    cumulative = durations[0]
    for i in range(2, n):
        cumulative += durations[i - 1]
        offset = cumulative - i * transition
        vi = f"[v{i:02d}]"
        ai = f"[a{i:02d}]"
        vfilter += f";{vlabel}[{i}:v]xfade=transition={_type_of(i - 1)}:duration={transition}:offset={offset:.3f}{vi}"
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


def build_ensure_audio_cmd(src: str, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """为无音轨视频补一条静音音轨(保留原视频流),使 xfade 的 acrossfade 不会因缺音轨失败。

    逐镜 i2v 段可能偶发无音轨;直接 xfade 会因 acrossfade 找不到音轨而整条失败、
    被调用方降级成硬切。补静音轨后转场一定可用,接缝仍是交叉淡化而非生硬跳切。
    """
    return [
        ffmpeg, "-y", "-i", src,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "copy", "-c:a", "aac", "-shortest", out,
    ]


def build_trim_cmd(video: str, out: str, start: int, duration: int, ffmpeg: str = "ffmpeg") -> List[str]:
    """按时间窗裁剪视频(多段生成时把参考视频切成对应段落)

    重编码而非 copy:copy 只能按关键帧切,段落边界会漂移,导致
    "参考段时长"与"生成段时长"对不上(进而影响续接首帧的取法)。
    """
    return [
        ffmpeg, "-y", "-ss", str(max(0, start)), "-i", video, "-t", str(max(1, duration)),
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out,
    ]


async def probe_resolution(video: str, ffprobe: str = "ffprobe", ffmpeg: str = "ffmpeg") -> Tuple[int, int]:
    """探测视频分辨率(宽,高);两条探测路径都失败时返回 (0, 0),调用方回退参数画幅。

    去水印需要「像素坐标 ↔ 归一化坐标」互转,必须知道真实尺寸。

    ① ffprobe:容器镜像自带,输出干净;
    ② `ffmpeg -i`:开发机常只装了 ffmpeg 没装 ffprobe,故再退回解析 Stream 行
       (ffmpeg 把信息打到 stderr,取第一个 WxH 即视频尺寸);
    两条都失败才让调用方走 ratio/resolution 推算 —— 那只是估算,会让像素坐标有偏差。
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x", video,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        lines = (out or b"").decode().strip().splitlines()
        if lines and "x" in lines[0]:
            w, _, h = lines[0].partition("x")
            return int(w), int(h)
    except Exception:
        pass
    try:
        proc = await asyncio.create_subprocess_exec(
            ffmpeg, "-hide_banner", "-i", video,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        hit = re.search(r"(\d{2,5})x(\d{2,5})", (err or b"").decode("utf-8", "ignore"))
        if hit:
            return int(hit.group(1)), int(hit.group(2))
    except Exception:
        pass
    return 0, 0


def build_crop_cmd(
    video: str, out: str, crop_w: int, crop_h: int, x: int = 0, y: int = 0,
    out_w: int = 0, out_h: int = 0, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """裁掉画面边缘一块区域(用于去除贴在画面角落的台标/水印),可选缩放回原尺寸。

    典型用法:台标在左上角 → 裁掉顶部若干像素,再 scale 回原始分辨率,
    输出仍是标准画幅(对应产品决策"裁剪后缩放回原比例");不传 out_w/out_h 则保留裁剪后尺寸。

    必须重编码:裁剪与缩放都要重算像素,stream copy 做不到。
    """
    if crop_w <= 0 or crop_h <= 0:
        raise ValueError("裁剪尺寸必须为正数")
    filters = [f"crop={crop_w}:{crop_h}:{max(0, int(x))}:{max(0, int(y))}"]
    if out_w > 0 and out_h > 0:
        # lanczos:裁剪后画面需要重采样,lanczos 比默认双线性更锐利
        filters.append(f"scale={int(out_w)}:{int(out_h)}:flags=lanczos")
    return [
        ffmpeg, "-y", "-i", video,
        "-vf", ",".join(filters),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", out,
    ]


def build_delogo_cmd(
    video: str, out: str, regions: List[Dict[str, int]], show: int = 0,
    ffmpeg: str = "ffmpeg",
) -> List[str]:
    """用 delogo 滤镜修补画面**内部**的品牌水印/台标(边缘插值填充,画幅尺寸不变)。

    regions: [{"x":..,"y":..,"w":..,"h":..}, ...],像素坐标;show=1 打开红框便于调试。

    与裁剪的分工:贴边水印走 build_crop_cmd(无痕、不糊);位于画面内部时裁不得,
    只能用插值修补,代价是该区域略有痕迹 —— 这是"确定性去除"与"画质无损"的取舍点。
    """
    boxes: List[str] = []
    for r in regions or []:
        try:
            x, y, w, h = int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"])
        except (KeyError, TypeError, ValueError):
            continue
        if w > 0 and h > 0:
            boxes.append(f"delogo=x={x}:y={y}:w={w}:h={h}:show={int(show)}")
    if not boxes:
        raise ValueError("delogo 需要至少一个有效区域")
    return [
        ffmpeg, "-y", "-i", video,
        "-vf", ",".join(boxes),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", out,
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
    margin: int = 20, bg_has_audio: bool = True,
    bg_volume: float = DEFAULT_PIP_BG_VOLUME, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """画中画(presenter-led-explainer):把 overlay 视频缩成小窗叠到背景视频之上。

    数字人讲解场景:数字人成片作为小窗(默认右下角、占背景宽 30%)叠在演示/图表背景上,
    实现"边讲边演示"。

    ⚠️ 音频必须两路混音,不能只取背景:数字人的口播声在小窗里,只取背景音轨等于把人声
    整段丢掉,背景视频本身无音轨时成片更是完全无声(此前实现为 `-map 0:a? -c:a copy`)。
    现在数字人口播为主(音量 1.0)、背景原声压低铺底(默认 DEFAULT_PIP_BG_VOLUME)。

    amix 只能作用于真实存在的流,而背景视频常是录屏/无声素材,因此由调用方先用
    probe_has_audio 探测背景音轨后传入 bg_has_audio:
      - True :两路 volume + amix(duration=shortest,以较短一路收尾,避免尾部留静音);
      - False:直接沿用数字人音轨(-map 1:a),此时不存在「压低背景」的问题。

    与 build_cover_cmd 的区别:pip 两路都有声音、数字人为主;cover 是用前景音替换背景音。
    重编码:overlay 叠加与音频混音都需重编码,视频 libx264、音频统一转 AAC(浏览器/iOS 兼容最好)。
    """
    pos = _PIP_POSITIONS.get((position or "br").lower(), _PIP_POSITIONS["br"]).format(m=int(margin))
    scale_pct = max(0.05, min(1.0, float(scale or 0.3)))
    video_filter = f"[1:v]scale=w=iw*{scale_pct:.3f}:h=-1[ov];[0:v][ov]overlay={pos}[v]"
    if bg_has_audio:
        vol = max(0.0, min(1.0, float(bg_volume)))
        audio_filter = (
            f"[0:a]volume={vol:.3f}[bg];[1:a]volume=1.0[fg];"
            "[bg][fg]amix=inputs=2:duration=shortest:dropout_transition=0[a]"
        )
        audio_map = "[a]"
    else:
        # 背景无音轨:只取数字人音轨,绝不能引用 [0:a](ffmpeg 遇不存在的流会直接报错)
        audio_filter = "anull"
        audio_map = "1:a"
    return [
        ffmpeg, "-y", "-i", bg, "-i", overlay,
        "-filter_complex", f"{video_filter};{audio_filter}",
        "-map", "[v]", "-map", audio_map, "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-shortest", out,
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


def build_broll_cmd(
    main: str, broll: str, out: str, start: float, end: float,
    fade: float = 0.3, scale: float = 1.0, position: str = "center",
    margin: int = 20, broll_type: str = "image", ffmpeg: str = "ffmpeg",
) -> List[str]:
    """B-roll 轨:在 [start,end] 时间窗内把素材(broll 图片/视频)叠到主视频之上,窗外汇透明。

    成片效果:讲解到「商品」时点画面切到产品特写(或演示视频),说完回到主讲 —— Hypit 的 B-roll
    (素材镜头承接/覆盖)思想。窗内 alpha 淡入淡出,边界用 overlay enable between 硬裁,
    避免素材时长不足时拖尾。
    - broll_type="image":-loop 1 让图持续整窗;
    - broll_type="video":-stream_loop -1 循环铺满窗口(素材短于窗口也不露馅)。
    """
    fade_d = max(0.0, min(float(fade), (float(end) - float(start)) / 2.0))
    fa = (f"fade=t=in:st={float(start):.3f}:d={fade_d:.3f}:alpha=1,"
          f"fade=t=out:st={max(float(start), float(end) - fade_d):.3f}:d={fade_d:.3f}:alpha=1")
    scale_pct = max(0.05, min(1.0, float(scale or 1.0)))
    # format=rgba 先保证有 alpha 通道,fade 的 alpha 淡入淡出才不会报错
    br_filter = f"[1:v]format=rgba,scale=w=iw*{scale_pct:.3f}:h=-1,{fa}[br]"
    if (position or "center") == "center":
        pos = "(W-w)/2:(H-h)/2"
    else:
        pos = _PIP_POSITIONS.get((position or "br").lower(), _PIP_POSITIONS["br"]).format(m=int(margin))
    overlay = f"[0:v][br]overlay={pos}:enable='between(t,{float(start):.3f},{float(end):.3f})'[v]"
    cmd = [ffmpeg, "-y", "-i", main]
    if broll_type == "video":
        cmd += ["-stream_loop", "-1"]
    else:
        cmd += ["-loop", "1"]
    cmd += ["-i", broll,
            "-filter_complex", br_filter + ";" + overlay,
            "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "copy", "-shortest", out]
    return cmd


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


async def probe_duration(video: str, ffprobe: str = "ffprobe") -> float:
    """探测视频时长(秒);失败返回 0.0(调用方据此跳过需要时长的步骤,如 ducking 人声段检测)"""
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nokey=1:noprint_wrappers=1",
            video, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        txt = (out or b"").decode().strip()
        return float(txt) if txt else 0.0
    except Exception:
        return 0.0


async def probe_has_audio(video: str, ffprobe: str = "ffprobe") -> bool:
    """探测媒体文件是否含音频流。

    合成命令必须按真实存在的流来拼:背景视频常是录屏/无声素材,此时若仍写 [0:a] 参与
    amix 混音,ffmpeg 会直接因流不存在而报错,整条画中画合成失败。

    ffprobe 缺失或探测异常时返回 True(按有音轨处理):此时让 amix 报错、调用方按既有兜底
    保留原成片,好过因误判「无音轨」而悄悄丢掉背景原声。
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe, "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=index", "-of", "default=nokey=1:noprint_wrappers=1",
            video, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        return bool((out or b"").decode().strip())
    except Exception:
        return True


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


def build_burn_subtitle_ass_cmd(
    video: str, ass_name: str, out: str, style: str,
    fonts_dir: Optional[str] = None, ffmpeg: str = "ffmpeg",
) -> List[str]:
    """字幕烧录(ASS 版):用于头部跟随字幕的逐条定位。

    与 build_burn_subtitle_cmd 完全同构,仅把 SRT 换成 ASS(支持 \\pos 逐条定位)。
    同样的两条硬规则:srt/ass 必须相对文件名(cwd 下)、fonts_dir 不带盘符冒号。
    """
    filter_value = f"subtitles={ass_name}"
    if fonts_dir:
        filter_value += f":fontsdir={fonts_dir}"
    filter_value += f":force_style='{style}'"
    return [
        ffmpeg, "-y", "-i", video, "-vf", filter_value,
        "-c:v", "libx264", "-c:a", "copy", "-shortest", out,
    ]


async def run(
    cmd: List[str], timeout: int = DEFAULT_TIMEOUT, cwd: Optional[str] = None,
    truncate: bool = True, binary: bool = False,
) -> Dict[str, Any]:
    """异步执行 ffmpeg(不阻塞事件循环)

    cwd:字幕烧录等场景需要把 srt 放在 cwd 下,以绕过 Windows 路径冒号问题。
    truncate=False:保留完整输出。**只做分析、不产出文件**的命令(如 silencedetect)
    必须关掉截断 —— 它的结果行位于输出中段,尾部截断会把关键行切掉,
    表现为"命令成功但一个静音都没解析出来"。

    binary=True:stdout 视为二进制(如 rgb24 raw 流)不做 utf-8 解码,原样放在
    stdout_bytes 里返回。给「画面统计」这类需要读原始像素的调用方用;
    默认 False 时行为与原先完全一致(返回解码后的 stdout 字符串)。

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
    if binary:
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stderr": (stderr or b"").decode("utf-8", "ignore")[-1000:] if truncate else (stderr or b"").decode("utf-8", "ignore"),
            "stdout_bytes": stdout or b"",
        }
    out_err = (stderr or b"").decode("utf-8", "ignore")
    out_std = (stdout or b"").decode("utf-8", "ignore")
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stderr": out_err[-1000:] if truncate else out_err,
        "stdout": out_std[-500:] if truncate else out_std,
    }
