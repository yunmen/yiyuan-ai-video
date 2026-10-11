#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地批量试听脚本(独立,不改动生产流程)。

背景: 本项目接入的 119 个豆包预设音色(zh_xxx / saturn_xxx)走的是生产 aitoken 网关;
而当前用于本地试听的火山直连 key 仅开通了 `seed-audio-1.0` 的 `tts/create` 资源,
该模型 *忽略* voice_type(预设音色),且未开通 voice_design(自定义 speaker)。

因此本脚本采用 seed-audio-1.0 的「文字描述驱动」能力: 把每个音色的说话人特征
写进 text_prompt, 生成 20 段可区分的音色, 每段文案均为: "一源AI, 祝你身体健康"。

用法:
  python scripts/tts_dump_voices.py
  VOLCANO_TTS_API_KEY=xxx python scripts/tts_dump_voices.py --out ./tts_dump --limit 5
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://openspeech.bytedance.com/api/v3/tts/create"
# key 优先级: 环境变量 > 脚本内置(用户给定的本地试听 key)
DEFAULT_KEY = "fdc85586-533a-47ac-8be2-dda60bd96e29"
TEXT = "一源AI, 祝你身体健康"

# 20 个数字人板块常用音色(侧重 专业播音/客服/解说/角色), 男女平衡。
# 每项: (文件名label, 说话人描述, 语气描述)
VOICES = [
    # 中文女声 - 自然/专业
    ("01_vivi",          "声音清亮自然的年轻女性",       "亲切清晰"),
    ("02_xiaohe",        "活泼开朗的年轻女孩",           "自然友好"),
    ("03_sophie",        "优雅知性的都市女性",           "从容得体"),
    ("04_qingxin",       "声音清新的年轻女性",           "干净清爽"),
    ("05_wenrou_shunv",  "温柔贤淑的女性",               "柔美端庄"),
    ("06_zhixing_nv",    "知性干练的职业女性",           "专业清晰"),
    ("07_qinqie_nv",     "亲切近人的邻家女孩",           "友好自然"),
    ("08_kefu_nv",       "温暖贴心的客服女性",           "耐心细致"),
    ("09_gaoleng_yujie", "高冷成熟的御姐",               "冷峻优雅"),
    ("10_cancan",        "聪明伶俐的知性女生",           "自信清亮"),
    # 中文男声 - 播音/解说/客服
    ("11_yunzhou",       "沉稳可靠的青年男性",           "自然大方"),
    ("12_ruya_qingnian","儒雅温和的年轻男士",           "文雅得体"),
    ("13_cixing_jieshuo","磁性低沉的男解说员",           "专业沉稳"),
    ("14_yangguang",     "阳光开朗的年轻男生",           "明快有活力"),
    ("15_wenrou_xiaoge", "温柔细腻的男生",               "温和耐心"),
    ("16_yuanbo",        "渊博成熟的男士",               "从容博学"),
    ("17_jieshuo_xm",    "干练利落的解说男声",           "清晰专业"),
    ("18_ad_jieshuo",    "富有感染力的广告男声",         "热情有力"),
    # 风格化(Saturn) - 角色数字人
    ("19_chengshu_jj",   "成熟稳重的大姐姐",             "体贴从容"),
    ("20_chengshu_ceo",  "沉稳霸气的男性总裁",           "从容笃定"),
]


def synthesize(key: str, text_prompt: str, timeout: int = 300) -> bytes:
    body = {
        "model": "seed-audio-1.0",
        "text_prompt": text_prompt,
        "audio_config": {
            "format": "mp3",
            "sample_rate": 48000,
            "pitch_rate": 0,
            "speech_rate": 0,
            "loudness_rate": 0,
        },
        "watermark": {},
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Api-Key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        j = json.loads(r.read())
    audio = j.get("audio")
    if not audio:
        raise RuntimeError(f"空音频, 响应: {json.dumps(j, ensure_ascii=False)[:200]}")
    return base64.b64decode(audio)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_dump"))
    ap.add_argument("--key", default=os.environ.get("VOLCANO_TTS_API_KEY", DEFAULT_KEY))
    ap.add_argument("--limit", type=int, default=len(VOICES), help="生成前 N 个(默认全部 20)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    items = VOICES[: args.limit]
    print(f"开始批量合成: 共 {len(items)} 个音色, 文案='{TEXT}', 模型=seed-audio-1.0(描述驱动), 并发={args.workers}")
    print(f"输出目录: {args.out}\n")

    def worker(item):
        label, spk, tone = item
        prompt = f"一位{spk}，用{tone}的语气说道：{TEXT}"
        try:
            data = synthesize(args.key, prompt)
            path = os.path.join(args.out, f"{label}.mp3")
            with open(path, "wb") as f:
                f.write(data)
            return (label, True, f"{len(data)} bytes -> {path}")
        except Exception as e:  # noqa: BLE001
            return (label, False, str(e)[:160])

    ok = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(worker, it): it[0] for it in items}
        for fut in as_completed(futs):
            label, success, msg = fut.result()
            mark = "  [成功] " if success else "  [失败] "
            print(mark + label.ljust(18) + msg)
            ok += 1 if success else 0

    print(f"\n完成: 成功 {ok}, 失败 {len(items) - ok}, 输出目录 {args.out}")


if __name__ == "__main__":
    main()
