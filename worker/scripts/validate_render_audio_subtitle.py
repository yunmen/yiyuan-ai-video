# -*- coding: utf-8 -*-
'''
@文件    :validate_render_audio_subtitle.py
@说明    :视频换口播「声音混音 ducking」「字幕风格预设」「B-roll 叠加」真实数据验证脚本

@用途    :开发者在真实联调(消除副本飘移)前,用 ffmpeg 真实跑一遍链路,确认:
            ① ducking —— 人声段 BGM 被自动压低(命令真实可合成、产物可播放);
            ② caption_style —— 各预设字幕确实被烧进成片(命令真实可合成、产物可播放);
            ③ broll —— 图片/视频素材在指定时间窗叠加到成片(命令真实可合成、产物可播放);
              并验证 worker._infer_broll_type 按扩展名(含 OSS ?sign= 查询串)识别图片/视频。
          不依赖任何模型网关:用 lavfi 合成测试视频/音频即可,纯本地 ffmpeg 验证。

@运行    :cd worker && python scripts/validate_render_audio_subtitle.py
@退出码  :0 全部通过;1 任一项失败(含 ffmpeg 不可用)
'''
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 让脚本可直接 import worker 的 app 包
WORKER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKER_ROOT))

from app.core import align, compose  # noqa: E402
from app.tools.render_tool import RenderTool  # noqa: E402


def _run(cmd: list, timeout: int = 120, cwd: str = None) -> dict:
    """同步执行命令(脚本环境,非事件循环),返回结构化结果"""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=str(cwd) if cwd else str(WORKER_ROOT))
    except FileNotFoundError:
        return {"ok": False, "error": "命令不存在(ffmpeg/ffprobe 未安装)", "returncode": None}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stderr": proc.stderr[-1500:],
        "stdout": proc.stdout[-500:],
    }


def _probe_duration(path: str) -> float:
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    r = _run([ffprobe, "-v", "error", "-show_entries", "format=duration",
              "-of", "default=nokey=1:noprint_wrappers=1", path])
    if r["ok"] and r["stdout"].strip():
        try:
            return float(r["stdout"].strip())
        except ValueError:
            return 0.0
    return 0.0


def _probe_streams(path: str) -> dict:
    """返回 {video:bool, audio:bool, duration:float}"""
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    # 流类型单独查,避免与 duration 混在一段输出里被正则误抓
    r = _run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type",
              "-of", "default=nokey=1:noprint_wrappers=1", path])
    text = f"{r.get('stdout', '')}\n{r.get('stderr', '')}"
    return {
        "video": "video" in text,
        "audio": "audio" in text,
        "duration": _probe_duration(path),
    }


def _detect_speech(video: str, duration: float):
    """复刻 subtitle.detect_speech_segments 的纯逻辑(避免引入 oss 依赖):
    silencedetect → 解析静音段 → 取语音段"""
    r = _run(align.build_silence_cmd(video), timeout=120)
    if not r["ok"]:
        return []
    silences = align.parse_silence_ranges(f"{r['stderr']}\n{r['stdout']}")
    speech = align.speech_segments(silences, duration)
    return speech or []


def main() -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[验证] ffmpeg 不可用,跳过真实数据验证(容器内需安装 ffmpeg)")
        return 1

    print("=== 视频换口播:声音混音 ducking / 字幕风格 真实数据验证 ===")
    workdir = tempfile.mkdtemp(prefix="render_validate_")
    ok = True
    try:
        video = os.path.join(workdir, "video.mp4")
        voice = os.path.join(workdir, "voice.m4a")
        bgm = os.path.join(workdir, "bgm.m4a")
        out_bgm = os.path.join(workdir, "with_bgm.mp4")
        srt = os.path.join(workdir, "sub.srt")
        burned = os.path.join(workdir, "burned.mp4")

        # ① 合成测试素材:6s 视频 + 人声(2~4s 静音)+ BGM
        # 注意顺序:voice/bgm 必须先于 video 生成(video 要把 voice 混进音轨)
        # 人声:440Hz 整段,2~4s 处静音(模拟"说话-停顿-说话")
        mk_voice = _run([
            ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
            "-af", "volume=enable='between(t,2,4)':volume=0", voice,
        ])
        # BGM:220Hz 整段
        mk_bgm = _run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=6", bgm])
        mk_video = _run([
            ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25",
            "-i", voice, "-t", "6", "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", video,
        ])
        if not (mk_video["ok"] and mk_voice["ok"] and mk_bgm["ok"]):
            print(f"[验证] 测试素材合成失败: video={mk_video['stderr'][-300]} voice={mk_voice['stderr'][-300]} bgm={mk_bgm['stderr'][-300]}")
            return 1

        # ② ducking:检测人声段 → 用 compose.build_bgm_cmd 真实合成
        duration = _probe_duration(video)
        speech = _detect_speech(video, duration)
        print(f"[ducking] 检测到人声段(秒): {[(round(s,2), round(e,2)) for s, e in speech]}")
        if not speech:
            print("[验证] 未检测到人声段,ducking 无法验证(静音检测逻辑异常)")
            ok = False
        cmd = compose.build_bgm_cmd(video, bgm, out_bgm, compose.DEFAULT_BGM_VOLUME, speech, 0.12)
        r = _run(cmd, timeout=120)
        streams = _probe_streams(out_bgm)
        duck_ok = r["ok"] and streams["video"] and streams["audio"] and streams["duration"] > 0
        if not duck_ok:
            print(f"[ducking] 合成失败 stderr: {r['stderr'][-400]}")
        print(f"[ducking] 合成{'成功' if duck_ok else '失败'} "
              f"(video={streams['video']} audio={streams['audio']} duration={streams['duration']:.2f}s)")
        ok = ok and duck_ok

        # ③ caption_style:四种预设各烧一条,确认命令真实可合成
        from app.core.compose import Cue, build_srt, build_burn_subtitle_cmd, caption_style
        cues = [Cue(start_ms=0, end_ms=3000, text="欢迎来到本店"), Cue(start_ms=3000, end_ms=6000, text="招牌小龙虾现在特惠")]
        with open(srt, "w", encoding="utf-8") as f:
            f.write(build_srt(cues))
        font = "Microsoft YaHei"
        for name in ("default", "highlight", "minimal", "variety"):
            burned_name = os.path.join(workdir, f"burned_{name}.mp4")
            r = _run(build_burn_subtitle_cmd(video, "sub.srt", burned_name, caption_style(font, name)), timeout=120, cwd=workdir)
            st = _probe_streams(burned_name)
            style_ok = r["ok"] and st["video"] and st["audio"]
            print(f"[caption_style:{name}] 烧录{'成功' if style_ok else '失败'} "
                  f"(video={st['video']} audio={st['audio']})")
            ok = ok and style_ok

        # ④ broll:图片/视频素材在 [1.0,3.0] 时间窗叠加到成片(真实 ffmpeg 合成)
        # 先用 worker._infer_broll_type 验证类型识别(含 OSS 查询串场景),再按识别结果跑命令
        infer_cases = [
            ("img", RenderTool._infer_broll_type({}, "https://oss.x.com/b.png?sign=1"), "image"),
            ("vid", RenderTool._infer_broll_type({}, "https://oss.x.com/b.mp4?sign=1&t=2"), "video"),
            ("mov", RenderTool._infer_broll_type({}, "/a.MOV"), "video"),
        ]
        for label, got, exp in infer_cases:
            flag = got == exp
            print(f"[broll:infer:{label}] 识别为 {got} (期望 {exp}) {'OK' if flag else 'FAIL'}")
            ok = ok and flag

        broll_img = os.path.join(workdir, "broll_img.png")
        broll_vid = os.path.join(workdir, "broll_vid.mp4")
        mk_img = _run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=red:size=320x180",
                       "-frames:v", "1", broll_img])
        mk_vid = _run([ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25",
                       "-t", "4", "-c:v", "libx264", "-pix_fmt", "yuv420p", broll_vid])
        if not (mk_img["ok"] and mk_vid["ok"]):
            print(f"[broll] 素材合成失败 img={mk_img['stderr'][-200]} vid={mk_vid['stderr'][-200]}")
            ok = False
        else:
            for tag, asset, btype in (("image", broll_img, "image"), ("video", broll_vid, "video")):
                out_broll = os.path.join(workdir, f"broll_{tag}.mp4")
                # 复刻 worker 真实路径:type 未给时由 _infer_broll_type 决定
                btype_eff = btype if btype else RenderTool._infer_broll_type({}, asset)
                r = _run(compose.build_broll_cmd(video, asset, out_broll, start=1.0, end=3.0,
                                                 broll_type=btype_eff), timeout=120)
                st = _probe_streams(out_broll)
                b_ok = r["ok"] and st["video"] and st["audio"] and st["duration"] > 0
                if not b_ok:
                    print(f"[broll:{tag}] 叠加失败 stderr: {r['stderr'][-400]}")
                print(f"[broll:{tag}] 叠加{'成功' if b_ok else '失败'} "
                      f"(video={st['video']} audio={st['audio']} duration={st['duration']:.2f}s)")
                ok = ok and b_ok
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    if ok:
        print("=== 真实数据验证全部通过(ducking + 4 种字幕风格 + B-roll 图片/视频叠加 均可合成播放) ===")
        return 0
    print("=== 真实数据验证存在失败项,请检查上方输出 ===")
    return 1


if __name__ == "__main__":
    sys.exit(main())
