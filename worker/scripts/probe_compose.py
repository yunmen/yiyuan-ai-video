# -*- coding: utf-8 -*-
"""P3 合成层能力探测:ffmpeg 到底能不能用、能用到什么程度。

为什么先探测(P3 是 5~8d 的大工程,起步前必须确认地基):
  1. **容器里没有 ffmpeg**:`devops/worker/Dockerfile` 是 `python:3.12-slim-bullseye`,
     未安装 ffmpeg → worker 容器内直接调用必然失败(而开发机可能已装,极易误判为"可用");
  2. 合成需要**编码器**(H.264/AAC):即使有 ffmpeg,slim 镜像里的构建也可能缺 libx264;
  3. 真实跑一次最小合成(视频 + 音频 / BGM 混音)才能确认参数在本机可用 —— 只看 `-version` 不够。

本脚本只探测、不改业务代码;结果打印为 JSON(可重定向存档)。

用法:
  python worker/scripts/probe_compose.py --plan    # 只打印探测计划(不执行 ffmpeg)
  python worker/scripts/probe_compose.py           # 真实探测(需本机/容器内 ffmpeg 可用)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 探测用素材参数(只用 lavfi 合成,不依赖任何外部文件)
SIZE = "640x360"
DURATION = 3
# 关键编码器:缺任何一个,对应能力就不可用
REQUIRED_ENCODERS = {"libx264": "H.264 视频编码", "aac": "AAC 音频编码"}
# 字幕探测:中文文本(字体缺失会渲染成豆腐块,必须用中文探测)
SUBTITLE_TEXT = ["欢迎来到一源AI", "这是字幕烧录探测"]
# Windows 常见中文字体;Linux 容器通常没有(届时表现为豆腐块,需装字体并配 fontsdir)
SUBTITLE_FONT = "Microsoft YaHei"
# YAVG(平均亮度)下降超过该阈值才算「真的画上了字」
YAVG_DROP_THRESHOLD = 1.0


def _run(args: List[str], timeout: int = 120, truncate: bool = True) -> Dict[str, Any]:
    """执行一条命令并返回结构化结果(不抛异常,便于探测脚本整体输出)

    truncate=False 时保留完整输出:ffmpeg 的 metadata 行位于输出的**中段**,
    尾部截断会把它切掉(表现为"命令成功但读不到任何指标")。
    """
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": stdout[:2000] if truncate else stdout,
            "stderr": stderr[-2000:] if truncate else stderr,
        }
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": "command not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"timeout after {timeout}s"}


def plan() -> Dict[str, Any]:
    """离线打印探测计划:确认将要探测哪些能力(不执行 ffmpeg)"""
    return {
        "probe_targets": {
            "ffmpeg": "可执行文件路径与版本",
            "ffprobe": "时长/流信息读取(可选,缺失则跳过时长断言)",
            "encoders": REQUIRED_ENCODERS,
            "mix_audio": "视频 + 口播音频合成(音轨替换)",
            "mix_bgm": "视频原声 + BGM 铺底混音(amix)",
            "burn_subtitle": "字幕烧录(subtitles filter + 中文字体 + Windows 路径转义)",
            "burn_keeps_audio": "烧录后音轨是否保留(-c:a copy)",
            "burn_visible": "抽帧比对平均亮度(YAVG)—— 证明字真的画上去了,而不是静默失败",
            "subtitle_font": "中文字体是否可用(缺失时 ffmpeg 不报错,只烧出豆腐块)",
        },
        "why": "worker 容器(python:3.12-slim-bullseye)未安装 ffmpeg —— 容器与开发机结论可能相反,必须分开确认",
        "sample_material": f"lavfi 合成 {SIZE} / {DURATION}s(不依赖外部素材)",
    }


def _write_srt(path: Path, cues: List[List[str]]) -> None:
    """写一份最小 SRT(cues 为 [start, end, text] 列表,时间用 SRT 的 mm:ss,mmm 格式)"""
    lines = []
    for idx, (start, end, text) in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    path.write_text("\r\n".join(lines), encoding="utf-8")


def _yavg(ffmpeg: str, image: Path) -> Tuple[Optional[float], str]:
    """读取单帧平均亮度(YAVG):用于判断画面上到底有没有画东西

    注意:metadata=print 的输出是 **info 级**,加 `-v error` 会把它一起抑制掉(表现为读不到值),
    所以这里用默认日志级别,从 stderr 里正则取 `lavfi.signalstats.YAVG=`。
    返回 (亮度, 诊断信息):解析失败时诊断信息保留 stderr 尾部,便于定位。
    """
    if not image.exists():
        return None, "frame missing"
    proc = _run([
        ffmpeg, "-i", str(image), "-vf", "signalstats,metadata=print", "-f", "null", "-",
    ], truncate=False)
    # metadata=print 的输出落在 **stdout**(实测 ffmpeg 9.x),只搜 stderr 会一无所获 —— 两边都搜
    haystack = f"{proc['stdout']}\n{proc['stderr']}"
    match = re.search(r"lavfi\.signalstats\.YAVG=(\d+(?:\.\d+)?)", haystack)
    if match:
        return float(match.group(1)), ""
    return None, f"rc={proc['returncode']} tail={haystack[-300:]}"


def _probe_subtitle(ffmpeg: str, ffprobe: Optional[str], video: Path, workdir: Path) -> Dict[str, Any]:
    r"""字幕烧录探测:不仅看返回码,还要证明「字真的画到了画面上」

    两个经典静默失败:
      1. 字体缺失 → ffmpeg 返回 0,画面上是豆腐块或干脆没字;
      2. **Windows 盘符路径含冒号** → subtitles filter 把冒号当选项分隔符,直接报错
         (实测报错:Unable to parse "original_size" option value)。
    所以这里:用 cwd + 相对文件名绕开路径问题,再用抽帧平均亮度(YAVG)证明画上了像素。
    """
    out: Dict[str, Any] = {}
    srt = workdir / "sub.srt"
    _write_srt(srt, [
        ["00:00:00,200", "00:00:01,400", SUBTITLE_TEXT[0]],
        ["00:00:01,600", "00:00:02,800", SUBTITLE_TEXT[1]],
    ])
    style = f"FontName={SUBTITLE_FONT},FontSize=32,PrimaryColour=&H000000FF,Alignment=2,MarginV=40"

    # 基线帧(烧录前)
    base_frame = workdir / "frame_before.png"
    made_frame = _run([ffmpeg, "-y", "-ss", "1", "-i", str(video), "-frames:v", "1", str(base_frame)])
    out["frame_before"] = {"ok": made_frame["ok"], "exists": base_frame.exists()}
    if not made_frame["ok"]:
        out["frame_before"]["stderr"] = made_frame["stderr"][-500:]
    out["yavg_before"], before_note = _yavg(ffmpeg, base_frame)
    if before_note:
        out["yavg_before_note"] = before_note

    # 方案①:cwd 切到 srt 所在目录 + 相对文件名(规避 Windows 路径冒号问题)
    burned = workdir / "burned.mp4"
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", str(video), "-vf", f"subtitles={srt.name}:force_style='{style}'",
         "-c:v", "libx264", "-c:a", "copy", str(burned)],
        capture_output=True, text=True, cwd=str(workdir), timeout=180,
    )
    out["relative_path"] = {"ok": proc.returncode == 0, "stderr": (proc.stderr or "").strip()[-800:]}

    # 方案②(对照):绝对路径原样传给 filter —— 记录此路是否可行,决定正式实现要不要转义
    abs_out = workdir / "burned_abs.mp4"
    proc_abs = subprocess.run(
        [ffmpeg, "-y", "-i", str(video), "-vf", f"subtitles={str(srt)}:force_style='{style}'",
         "-c:v", "libx264", "-c:a", "copy", str(abs_out)],
        capture_output=True, text=True, timeout=180,
    )
    out["absolute_path"] = {"ok": proc_abs.returncode == 0, "stderr": (proc_abs.stderr or "").strip()[-400:]}

    if not burned.exists():
        out["conclusion"] = "字幕烧录未产出文件"
        return out

    # 证明画上了:同一秒抽帧,平均亮度应下降(白底黑字)
    after_frame = workdir / "frame_after.png"
    _run([ffmpeg, "-y", "-ss", "1", "-i", str(burned), "-frames:v", "1", str(after_frame)])
    out["yavg_after"], after_note = _yavg(ffmpeg, after_frame)
    if after_note:
        out["yavg_after_note"] = after_note
    if out["yavg_before"] is not None and out["yavg_after"] is not None:
        drop = round(out["yavg_before"] - out["yavg_after"], 3)
        out["yavg_drop"] = drop
        out["visible"] = drop > YAVG_DROP_THRESHOLD
    else:
        out["visible"] = None

    # 音轨必须保留(烧字幕只动画面,不能把原片 BGM/口播弄丢)
    if ffprobe:
        streams = _run([
            ffprobe, "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(burned),
        ])
        types = streams["stdout"].splitlines()
        out["keeps_audio"] = "audio" in types
        out["streams"] = types
        dur = _run([
            ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(burned),
        ])
        out["duration"] = dur["stdout"] if dur["ok"] else None

    out["conclusion"] = (
        f"字幕烧录可用(YAVG 下降 {out.get('yavg_drop')},音轨保留={out.get('keeps_audio')})"
        if out.get("visible") else "字幕未画上画面(疑似字体缺失或 filter 参数问题,见 stderr)"
    )
    return out


def detect() -> Dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    result: Dict[str, Any] = {
        "ffmpeg_path": ffmpeg,
        "ffprobe_path": ffprobe,
        "version": None,
        "encoders": {},
        "mix_audio": None,
        "mix_bgm": None,
        "conclusion": "",
    }
    if not ffmpeg:
        result["conclusion"] = "未找到 ffmpeg → P3 合成层无法运行(容器需先安装 ffmpeg)"
        return result

    ver = _run([ffmpeg, "-version"])
    if ver["ok"]:
        result["version"] = ver["stdout"].splitlines()[0] if ver["stdout"] else None

    # 编码器探测:-h encoder=xxx 成功即视为可用
    for name, desc in REQUIRED_ENCODERS.items():
        probe = _run([ffmpeg, "-hide_banner", "-h", f"encoder={name}"])
        result["encoders"][name] = {"desc": desc, "available": probe["ok"]}

    # 中文字体探测:ffmpeg 缺字体**不报错**,只会烧出豆腐块 —— 必须单独确认
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from app.core.compose import bundled_font_dir, resolve_subtitle_font

        resolved = resolve_subtitle_font()
        result["subtitle_font"] = {
            "font": resolved[0] if resolved else None,
            "fonts_dir": resolved[1] if resolved else None,
            "bundled_dir": str(bundled_font_dir()),
            "conclusion": (
                f"中文字体可用: {resolved[0]}"
                if resolved else
                "未找到中文字体 —— 字幕将跳过不烧;Linux 需 apt install fonts-noto-cjk"
            ),
        }
    except Exception as exc:  # noqa: BLE001
        result["subtitle_font"] = {"error": str(exc)}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        silent = tmp_dir / "silent.mp4"
        voice = tmp_dir / "voice.m4a"
        bgm = tmp_dir / "bgm.m4a"
        out_mixed = tmp_dir / "mixed.mp4"
        out_bgm = tmp_dir / "with_bgm.mp4"

        # 造素材:白底视频 + 两段音频(白底便于用亮度变化判断字幕有没有画上去)
        made_video = _run([
            ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c=white:s={SIZE}:d={DURATION}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent),
        ])
        made_voice = _run([ffmpeg, "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={DURATION}", "-c:a", "aac", str(voice)])
        made_bgm = _run([ffmpeg, "-y", "-f", "lavfi", "-i", f"sine=frequency=880:duration={DURATION}", "-c:a", "aac", str(bgm)])
        result["materials"] = {"video": made_video["ok"], "voice": made_voice["ok"], "bgm": made_bgm["ok"]}
        if not (made_video["ok"] and made_voice["ok"] and made_bgm["ok"]):
            result["conclusion"] = "素材生成失败,无法继续(见 materials.stderr)"
            result["materials_error"] = {
                "video": made_video["stderr"], "voice": made_voice["stderr"], "bgm": made_bgm["stderr"],
            }
            return result

        # 能力①:视频 + 口播音频(音轨替换/补齐)
        mix = _run([
            ffmpeg, "-y", "-i", str(silent), "-i", str(voice),
            "-shortest", "-c:v", "copy", "-c:a", "aac", str(out_mixed),
        ])
        result["mix_audio"] = {"ok": mix["ok"], "stderr": mix["stderr"] if not mix["ok"] else ""}

        # 能力②:BGM 铺底混音(原声 + BGM,amix 后取最短)
        bgm_mix = _run([
            ffmpeg, "-y", "-i", str(out_mixed if mix["ok"] else silent), "-i", str(bgm),
            "-filter_complex", "[1:a]volume=0.3[bgm];[0:a][bgm]amix=inputs=2:duration=shortest[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out_bgm),
        ])
        result["mix_bgm"] = {"ok": bgm_mix["ok"], "stderr": bgm_mix["stderr"] if not bgm_mix["ok"] else ""}

        # 时长校验(有 ffprobe 时):产物时长应≈素材时长
        durations = {}
        if ffprobe:
            for name, path in (("mixed", out_mixed), ("with_bgm", out_bgm)):
                if not path.exists():
                    continue
                probe = _run([
                    ffprobe, "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(path),
                ])
                durations[name] = probe["stdout"] if probe["ok"] else None
        result["durations"] = durations
        result["sizes"] = {
            "mixed": out_mixed.stat().st_size if out_mixed.exists() else 0,
            "with_bgm": out_bgm.stat().st_size if out_bgm.exists() else 0,
        }

        # 字幕烧录(P3-1 主线):用带音轨的成片做输入,顺便验证音轨保留
        if mix["ok"]:
            result["burn_subtitle"] = _probe_subtitle(ffmpeg, ffprobe, out_mixed, tmp_dir)

    encoders_ok = all(v["available"] for v in result["encoders"].values())
    mix_ok = bool(result["mix_audio"] and result["mix_audio"]["ok"])
    bgm_ok = bool(result["mix_bgm"] and result["mix_bgm"]["ok"])
    result["conclusion"] = (
        "本机合成能力可用(视频+音频 / BGM 混音均通过) —— 但需确认 worker 容器同样可用"
        if (encoders_ok and mix_ok and bgm_ok)
        else f"合成能力不完整: encoders_ok={encoders_ok} mix_audio={mix_ok} mix_bgm={bgm_ok}"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="P3 合成层(ffmpeg)能力探测")
    parser.add_argument("--plan", action="store_true", help="只打印探测计划(不执行 ffmpeg)")
    args = parser.parse_args()
    payload = plan() if args.plan else detect()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
