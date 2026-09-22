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
            if (directory / name).exists():
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
    """ffmpeg 可执行文件路径;未安装返回 None(worker 容器目前正是这种情况)"""
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


def build_trim_cmd(video: str, out: str, start: int, duration: int, ffmpeg: str = "ffmpeg") -> List[str]:
    """按时间窗裁剪视频(多段生成时把参考视频切成对应段落)

    重编码而非 copy:copy 只能按关键帧切,段落边界会漂移,导致
    "参考段时长"与"生成段时长"对不上(进而影响续接首帧的取法)。
    """
    return [
        ffmpeg, "-y", "-ss", str(max(0, start)), "-i", video, "-t", str(max(1, duration)),
        "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out,
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
