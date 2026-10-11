# -*- coding: utf-8 -*-
"""P1 能力探测:词级对齐(词级时间戳)到底能不能拿到。

为什么先探测:
  P0 的锚点只有「词序号」,转成真实时间靠按词数摊分估算(estimate_timing,estimated=true)。
  锚点要真正卡在台词上,必须有「词 → 秒」的对齐数据;而对齐方案的成本差异极大,
  拍脑袋选错要么白做、要么上重依赖。候选:

  A. TTS 直出时间戳 —— 零额外调用(网关支持时最省)
     OpenAI 官方 Speech API **不返回**时间戳(只回音频二进制),
     但部分 OpenAI 兼容网关支持 timestamp_granularities / verbose_json 等私有扩展。
  B. ASR 回灌 —— 用口播音频跑一次 STT,取词级时间戳(多一次调用,官方原生支持)
     transcriptions.create(response_format="verbose_json", timestamp_granularities=["word"])
  C. 强制对齐 —— whisperx / Montreal Forced Aligner 等,需重依赖与模型下载,部署成本高

本脚本只探测、不改业务代码;结果打印为 JSON(可重定向存档)。

用法:
  python worker/scripts/probe_alignment.py --plan    # 只打印探测计划与当前配置(不联网)
  python worker/scripts/probe_alignment.py           # 真实探测(需网关可用)
  python worker/scripts/probe_alignment.py --text "招牌小龙虾现在特惠"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os_env = __import__("os")
os_env.environ.setdefault("ENVIRONMENT", "dev")

from app.settings import config  # noqa: E402

PROBE_TEXT = "招牌小龙虾现在特惠,赶紧下单"
# 词级时间戳相关的字段名(不同网关命名不一,全量看一遍)
TIMESTAMP_KEYS = ("words", "segments", "timestamps", "word_timestamps", "alignment")
# ASR 探测默认模型:未配置 asr_model 时用 OpenAI 兼容网关普遍支持的 whisper-1
DEFAULT_ASR_MODEL = "whisper-1"


def plan() -> Dict[str, Any]:
    """打印探测计划与当前配置(离线可执行,用于确认探测的是哪个网关)"""
    return {
        "probe_text": PROBE_TEXT,
        "tts_model": config.AUDIO_MODEL,
        "tts_voice": config.AUDIO_VOICE,
        "asr_model": os_env.environ.get("ASR_MODEL") or DEFAULT_ASR_MODEL,
        "audio_base_url": (config.AUDIO_LLM_BASE_URL or "").rstrip("/") or "(回退网关解析)",
        "candidates": {
            "A": "TTS 直出时间戳(零额外调用,需网关扩展支持)",
            "B": "ASR 回灌词级时间戳(多一次 STT 调用,官方原生支持)",
            "C": "强制对齐(whisperx 等重依赖,兜底方案)",
        },
    }


def _has_timestamps(payload: Any) -> bool:
    if isinstance(payload, dict):
        if any(k in payload for k in TIMESTAMP_KEYS):
            return True
        return any(_has_timestamps(v) for v in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(_has_timestamps(v) for v in payload)
    return False


def _collect_timestamp_keys(payload: Any, found: set | None = None) -> set:
    found = found if found is not None else set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in TIMESTAMP_KEYS:
                found.add(key)
            _collect_timestamp_keys(value, found)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _collect_timestamp_keys(item, found)
    return found


async def probe(text: str, audio_file: str | None = None) -> Dict[str, Any]:
    """真实探测:先 TTS 看是否直出时间戳,再用音频跑 ASR 看能否回灌词级时间戳

    --audio 传入本地音频时跳过 TTS:账号额度紧张时,用已有的口播音频单独验证方案 B。
    """
    from app.tools.audio_tool import AudioGenTool

    tool = AudioGenTool()
    result: Dict[str, Any] = {"tts": {}, "asr": {}}
    audio_bytes: Any = None

    if audio_file:
        path = Path(audio_file)
        if not path.exists():
            return {"error": f"音频文件不存在: {path}"}
        audio_bytes = path.read_bytes()
        result["tts"] = {"ok": None, "skipped": f"使用本地音频 {path.name}({len(audio_bytes)} 字节)"}
    # A. TTS:带私有扩展参数尝试(网关不支持时通常忽略,不会报错)
    else:
        try:
            resp = await tool.client.audio.speech.create(
                model=config.AUDIO_MODEL,
                input=text,
                voice=config.AUDIO_VOICE,
                response_format=os_env.environ.get("AUDIO_FORMAT") or config.AUDIO_FORMAT,
                extra_body={"timestamp_granularities": ["word"]},
            )
            content = getattr(resp, "content", None)
            audio_bytes = content
            payload: Any = None
            if isinstance(content, bytes):
                try:
                    payload = json.loads(content.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    payload = None      # 纯音频二进制 → 官方行为:不带时间戳
            result["tts"] = {
                "ok": True,
                "audio_bytes": len(content) if isinstance(content, bytes) else 0,
                "response_is_json": isinstance(payload, (dict, list)),
                "timestamp_keys": sorted(_collect_timestamp_keys(payload)),
                "has_timestamps": _has_timestamps(payload),
            }
        except Exception as exc:  # noqa: BLE001
            result["tts"] = {"ok": False, "error": str(exc)}

    # B. ASR 回灌:用任意可解析音频跑一次 verbose_json,看是否返回词级时间戳
    try:
        if not isinstance(audio_bytes, bytes) or not audio_bytes:
            # TTS 失败(如网关额度不足)时 ASR 无输入,明确说明原因,避免误判为「不支持词级时间戳」
            result["asr"] = {"ok": False, "error": "跳过: TTS 未产出可解析音频,原因见 tts.error"}
            result["conclusion"] = "探测未完成(TTS 阶段失败),请修复后重跑再下结论"
            return result
        model = os_env.environ.get("ASR_MODEL") or DEFAULT_ASR_MODEL
        transcript = await tool.client.audio.transcriptions.create(
            file=("probe.mp3", audio_bytes, "audio/mpeg"),
            model=model,
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )
        data = transcript.model_dump() if hasattr(transcript, "model_dump") else transcript
        if not isinstance(data, dict):
            data = {"raw": str(data)}
        words = data.get("words")
        result["asr"] = {
            "ok": True,
            "model": model,
            "has_words": bool(words),
            "word_count": len(words) if isinstance(words, list) else 0,
            "sample": (words or [])[:3] if isinstance(words, list) else None,
            "text": str(data.get("text") or "")[:80],
        }
    except Exception as exc:  # noqa: BLE001
        result["asr"] = {"ok": False, "error": str(exc)}

    tts_ok = bool(result["tts"].get("has_timestamps"))
    asr_ok = bool(result["asr"].get("has_words"))
    result["conclusion"] = (
        "方案A:TTS 直出词级时间戳,零额外调用" if tts_ok
        else "方案B:ASR 回灌词级时间戳,每任务多一次 STT 调用" if asr_ok
        else "A/B 均不可用 → 评估方案C(强制对齐)或维持 P0 估算兜底"
    )
    return result


def main() -> int:
    # Windows 控制台默认 GBK,网关返回的文本可能含 ¥ 等字符,直接 print 会崩
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description="P1 词级对齐能力探测")
    parser.add_argument("--plan", action="store_true", help="只打印探测计划与当前配置(不联网)")
    parser.add_argument("--text", default=PROBE_TEXT, help="探测用文本")
    parser.add_argument("--audio", help="用本地音频直接探测 ASR(跳过 TTS,省一次合成)")
    args = parser.parse_args()

    if args.plan:
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
        return 0

    try:
        result = asyncio.run(probe(args.text, args.audio))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
