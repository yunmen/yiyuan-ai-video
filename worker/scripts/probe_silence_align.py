# -*- coding: utf-8 -*-
"""P1 降级方案探测:静音检测对齐(silencedetect)到底准不准。

为什么先探测:
  当前字幕时间轴是「按词数摊分」的估算(estimate_timing),假设说话匀速 —— 真实口播有停顿,
  于是字幕会错位。本方案不猜语速,只找停顿:用 ffmpeg silencedetect 找出静音区间,
  取补集得到语音段,把句子铺在语音段上。

  但它能不能用,取决于**检出的停顿位置准不准** —— 这是可以量化的,所以先测再决定要不要接。

做法:
  合成一段**已知真实停顿位置**的音频 → 跑 silencedetect → 对比检出边界与真实边界的误差;
  再用 align 的纯函数把句子铺上去,检查字幕是否落在"真的在说话"的区间里。

用法:
  python worker/scripts/probe_silence_align.py          # 真实探测(本地 ffmpeg,不联网)
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.align import (  # noqa: E402
    DEFAULT_MIN_SILENCE,
    DEFAULT_NOISE_DB,
    align_sentences,
    build_silence_cmd,
    parse_silence_ranges,
    speech_segments,
)

FFMPEG = "ffmpeg"

# 音频:语音(0~2s) 停顿(2~2.5s) 语音(2.5~5s) 停顿(5~5.6s) 语音(5.6~8s)
# 用音量门控模拟"说话/停顿",真实边界是已知的,便于量化误差
DURATION = 8.0
TRUE_SILENCES: List[Tuple[float, float]] = [(2.0, 2.5), (5.0, 5.6)]
TRUE_SPEECH: List[Tuple[float, float]] = [(0.0, 2.0), (2.5, 5.0), (5.6, 8.0)]
# 三句口播(词数不同,用于检验按比例分配)
SENTENCES: List[Tuple[str, int]] = [("第一句比较短", 6), ("第二句内容明显更长一些", 11), ("第三句", 3)]


def _make_audio(path: str) -> None:
    gate = "if(between(t,2.0,2.5),0,if(between(t,5.0,5.6),0,1))"
    subprocess.run(
        [FFMPEG, "-y", "-f", "lavfi",
         "-i", f"sine=frequency=440:d={DURATION},volume='{gate}':eval=frame",
         "-c:a", "aac", path],
        check=True, capture_output=True,
    )


def detect() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "true_silences": TRUE_SILENCES,
        "params": {"noise": DEFAULT_NOISE_DB, "min_silence": DEFAULT_MIN_SILENCE},
    }
    with tempfile.TemporaryDirectory() as tmp:
        audio = str(Path(tmp) / "voice.m4a")
        _make_audio(audio)

        proc = subprocess.run(
            build_silence_cmd(audio), capture_output=True, text=True, timeout=120,
        )
        haystack = f"{proc.stdout}\n{proc.stderr}"
        silences = parse_silence_ranges(haystack)
        result["detected_silences"] = silences

        # 误差:把检出区间与真实区间按序一一对比
        errors: List[Dict[str, Any]] = []
        for i, (true_start, true_end) in enumerate(TRUE_SILENCES):
            if i >= len(silences):
                errors.append({"index": i, "error": "未检出"})
                continue
            det_start, det_end = silences[i]
            errors.append({
                "index": i,
                "start_error_ms": round(abs(det_start - true_start) * 1000, 1),
                "end_error_ms": round(abs(det_end - true_end) * 1000, 1),
            })
        result["boundary_errors"] = errors
        worst = max(
            (max(e.get("start_error_ms", 9999), e.get("end_error_ms", 9999)) for e in errors),
            default=None,
        )
        result["worst_error_ms"] = worst

        speech = speech_segments(silences, DURATION)
        result["speech_segments"] = [[round(a, 3), round(b, 3)] for a, b in speech]

        cues = align_sentences(SENTENCES, speech, DURATION)
        result["cues"] = [
            {"start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text} for c in cues
        ]

        # 关键断言一:每条字幕的**起点**必须落在语音段里(不能飘到停顿上)
        def _in_speech(sec: float) -> bool:
            return any(a <= sec <= b for a, b in TRUE_SPEECH)

        offenders = [c.text for c in cues if not _in_speech(c.start_ms / 1000)]

        # 关键断言二:字幕区间不该**穿过停顿**(否则观众会看到"话已停、字还在")
        def _crosses_pause(cue: Any) -> bool:
            lo, hi = cue.start_ms / 1000, cue.end_ms / 1000
            return any(lo < s and e < hi for s, e in TRUE_SILENCES)

        crossing = [c.text for c in cues if _crosses_pause(c)]
        result["cues_crossing_pause"] = crossing
        result["cues_outside_speech"] = offenders

        ok = (
            bool(cues) and not offenders and not crossing
            and worst is not None and worst < 150
        )
        result["conclusion"] = (
            f"静音检测对齐可用:最大边界误差 {worst}ms,字幕既落在语音段内也不穿过停顿"
            if ok else
            f"不可用或精度不足:最大误差 {worst}ms,越界字幕 {offenders},穿停顿 {crossing}"
        )
    return result


if __name__ == "__main__":
    print(json.dumps(detect(), ensure_ascii=False, indent=2))
