#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@文件    :probe_gateway.py
@说明    :中转站(OpenAI 兼容网关)能力探测 —— 切换网关前一次性核对各能力端点是否被支持。

默认 probe 模式只做"端点存在性"探测:故意发送缺少参数的请求,按返回码判断:
    200/201/400/422 → 端点存在(参数校验失败属预期),该能力可用
    401/403         → 端点存在,但当前 key 无效或无权限
    404/405         → 端点不存在,该网关不支持此能力
    429             → 端点存在但被限流
    5xx / 超时      → 网关异常,需人工确认

这样可在不产生费用、不真正生成内容的前提下,判断中转站是否实现了该端点。
`--real` 模式会真实调用 chat / 图片(小参数)验证端到端链路;
视频 / 语音 / 音乐默认仍跳过,需额外加 `--allow-costly`(会产生真实费用)。

用法:
    # 只打印配置模板(不发任何请求)
    python worker/scripts/probe_gateway.py --print-config

    # 探测端点可用性 + 拉模型清单并按能力推荐模型名(零成本,建议先跑这个)
    python worker/scripts/probe_gateway.py --base-url https://aitoken.capitalai.cn/v1 --api-key sk-xxx --models

    # 再真实验证 chat / 图片链路(少量消耗)
    python worker/scripts/probe_gateway.py --base-url ... --api-key ... --real

    # 含视频 / 音乐 / 语音的真实调用(会产生真实费用)
    python worker/scripts/probe_gateway.py --base-url ... --api-key ... --real --allow-costly

@作者    :一源AI
@版本    :1.0
'''
import argparse
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (能力, method, path, probe body, 说明)
ENDPOINTS: List[Tuple[str, str, str, Optional[Dict[str, Any]], str]] = [
    ("models", "GET", "/models", None, "模型清单(核对各能力模型名是否存在)"),
    ("chat/text", "POST", "/chat/completions", {}, "文本/对话(gen.route.chat / gen.route.text)"),
    ("image", "POST", "/images/generations", {}, "文生图(gen.route.image)"),
    ("image_edit", "POST", "/images/edits", {}, "图生图/图片编辑"),
    ("video_submit", "POST", "/videos", {}, "视频生成提交(gen.route.video)"),
    ("video_query", "GET", "/videos/probe-nonexistent-id", None, "视频任务查询(轮询阶段)"),
    ("speech", "POST", "/audio/speech", {}, "语音合成 TTS(gen.route.audio)"),
    ("music", "POST", "/audio/music/generations", {}, "背景音乐(gen.route.music)"),
]

# 能力 → 从 /models 清单挑选模型名的关键词(include 任一命中 且 exclude 全部不命中)
MODEL_HINTS: List[Tuple[str, str, List[str], List[str]]] = [
    ("gen.chat_model", "prompt改写/文案润色",
     ["qwen", "deepseek", "gpt", "claude", "glm", "kimi", "chat"], ["image", "video", "tts", "music", "embed"]),
    ("gen.text_model", "文本生成",
     ["qwen", "deepseek", "gpt", "glm", "kimi"], ["image", "video", "tts", "music", "embed"]),
    ("gen.image_model", "文生图",
     ["image", "seedream", "flux", "dall", "kolors", "draw"], ["video", "edit", "chat"]),
    ("gen.image_model_edit", "图生图/图片编辑",
     ["edit", "seededit"], ["video"]),
    ("gen.video_model_t2v", "文生视频",
     ["t2v", "text2video", "seedance", "wan", "video"], ["i2v", "r2v", "image2video", "ref2video"]),
    ("gen.video_model_i2v", "图生视频",
     ["i2v", "image2video", "img2video"], []),
    ("gen.video_model_r2v", "参考生视频",
     ["r2v", "ref2video", "reference"], []),
    ("gen.audio_model", "语音合成TTS",
     ["tts", "speech", "voice"], ["music"]),
    ("gen.music_model", "背景音乐",
     ["music", "song", "bgm"], []),
]


def classify(status: int) -> Tuple[str, str]:
    """按 HTTP 状态码判定端点是否被支持"""
    if status in (200, 201, 400, 422):
        return "SUPPORTED", "端点存在"
    if status in (401, 403):
        return "AUTH", "端点存在但鉴权失败(key 无效或权限不足)"
    if status in (404, 405):
        return "MISSING", "端点不存在,该能力不被支持"
    if status == 429:
        return "RATE", "端点存在但被限流"
    if status >= 500:
        return "ERROR", "网关异常"
    return "UNKNOWN", "需人工确认"


def _snippet(resp: httpx.Response, limit: int = 100) -> str:
    """截取响应体片段用于人工判断"""
    try:
        text = resp.text
    except Exception:  # noqa: BLE001
        return ""
    return " ".join(text.split())[:limit]


def _headers(api_key: str) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def probe(base_url: str, api_key: str, timeout: float) -> None:
    """零成本探测各能力端点是否存在"""
    base = base_url.rstrip("/")
    headers = _headers(api_key)
    print(f"\n探测网关: {base}    (probe 模式:零成本端点存在性探测)\n")
    print(f"{'能力':<13}{'方法':<6}{'路径':<32}{'判定':<11}{'状态':<6}{'耗时':<8}响应片段")
    print("-" * 130)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for name, method, path, body, _desc in ENDPOINTS:
            started = time.time()
            try:
                if method == "GET":
                    resp = client.get(f"{base}{path}", headers=headers)
                else:
                    resp = client.post(f"{base}{path}", headers=headers, json=body)
                verdict, _detail = classify(resp.status_code)
                status, snippet = str(resp.status_code), _snippet(resp)
            except Exception as exc:  # noqa: BLE001
                verdict, status, snippet = "FAIL", "-", f"请求异常: {exc}"
            elapsed = f"{time.time() - started:.2f}s"
            print(f"{name:<13}{method:<6}{path:<32}{verdict:<11}{status:<6}{elapsed:<8}{snippet}")

    print("\n判读要点:")
    print("  SUPPORTED → 端点存在,该能力可用")
    print("  MISSING   → 端点不存在,该能力在此网关不可用(需单独配置专用网关)")
    print("  AUTH      → key 无效或权限不足,先确认 key 是否正确 / 是否开通对应模型")
    print("  video_query 用不存在的任务 ID 探测;若返回 404 且提示'任务不存在',同样说明端点存在。")


def fetch_models(base_url: str, api_key: str, timeout: float) -> List[str]:
    """拉取 /models 清单(OpenAI 兼容:data[].id)"""
    base = base_url.rstrip("/")
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(f"{base}/models", headers=_headers(api_key))
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    ids: List[str] = []
    for it in items:
        if isinstance(it, dict) and it.get("id"):
            ids.append(str(it["id"]))
        elif isinstance(it, str):
            ids.append(it)
    return sorted(set(ids))


def recommend_models(ids: List[str]) -> List[Tuple[str, str, List[str]]]:
    """按能力关键词从模型清单里挑选候选模型名"""
    lowered = {i: i.lower() for i in ids}
    rows: List[Tuple[str, str, List[str]]] = []
    for key, cap, includes, excludes in MODEL_HINTS:
        matched = [
            i for i in ids
            if any(h in lowered[i] for h in includes) and not any(x in lowered[i] for x in excludes)
        ]
        rows.append((key, cap, matched))
    return rows


def print_model_catalog(base_url: str, api_key: str, timeout: float) -> None:
    """打印模型清单 + 各能力推荐 + 可直接回填管理端的配置清单"""
    try:
        ids = fetch_models(base_url, api_key, timeout)
    except Exception as exc:  # noqa: BLE001
        print(f"\n[模型清单] 拉取失败: {exc}")
        return
    if not ids:
        print("\n[模型清单] 未返回模型(检查 /models 是否可用、key 是否有权限)")
        return

    print(f"\n===== 模型清单 (GET /models, 共 {len(ids)} 个) =====")
    for i in ids:
        print(f"  {i}")

    rows = recommend_models(ids)
    print("\n===== 各能力候选模型(关键词匹配,需人工确认) =====")
    for key, cap, matched in rows:
        text = ", ".join(matched) if matched else "未匹配到,请从上面清单人工挑选"
        print(f"  {key:<24}{cap:<20}{text}")

    print("\n===== 可直接回填管理端的模型配置 =====")
    print("(路径: 管理端「系统设置」页 → 扩展配置 标签页 → 找到对应 KEY 改 VALUE)")
    for key, _cap, matched in rows:
        print(f"  {key:<24}= {matched[0] if matched else '<人工填写>'}")


def print_config_template() -> None:
    """打印网关配置模板(不发请求)"""
    print("\n===== 网关配置(全压一个中转站时只需前 2 项) =====")
    print("  路径: 管理端「系统设置」页 → 扩展配置 标签页")
    print("  gen.llm_base_url        = https://aitoken.capitalai.cn/v1")
    print("  gen.llm_api_key         = <你的中转站 key>")
    print("  gen.worker_llm_base_url = <备用中转站地址;留空则复用主网关,等于无备选>")
    print("  gen.worker_llm_api_key  = <备用 key>")
    print("  gen.audio_llm_base_url  = <留空:音频回退媒体网关>")
    print("  gen.audio_llm_api_key   = <留空>")
    print("  gen.gw.*                = <留空:全压单网关时不需要>")
    print("  gen.route.*             = <留空:全压单网关时不需要>")
    print("\n  非模型参数(保持默认即可):")
    print("  gen.image_ratio = 1:1    gen.video_ratio = 9:16    gen.video_resolution = 1080P")


def run_real(base_url: str, api_key: str, args: argparse.Namespace) -> None:
    """真实调用关键能力,验证端到端链路(会产生真实消耗)"""
    base = base_url.rstrip("/")
    headers = _headers(api_key)
    print(f"\n真实调用验证: {base}    (--real)\n")

    with httpx.Client(timeout=args.timeout, follow_redirects=True) as client:
        print("[1/3] chat/completions ...")
        try:
            resp = client.post(
                f"{base}/chat/completions", headers=headers,
                json={"model": args.chat_model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            )
            print(f"  HTTP {resp.status_code}  {_snippet(resp, 200)}")
            print("  若报 model not found,说明 gen.chat_model 要改成该网关实际支持的模型名")
        except Exception as exc:  # noqa: BLE001
            print(f"  异常: {exc}")

        print("\n[2/3] images/generations ...")
        try:
            resp = client.post(
                f"{base}/images/generations", headers=headers,
                json={"model": args.image_model, "prompt": "a red dot", "n": 1, "size": "1024x1024"},
            )
            print(f"  HTTP {resp.status_code}  {_snippet(resp, 200)}")
        except Exception as exc:  # noqa: BLE001
            print(f"  异常: {exc}")

        print("\n[3/3] audio/speech ...")
        if not args.allow_costly:
            print("  跳过(加 --allow-costly 开启,会产生真实费用)")
        else:
            try:
                resp = client.post(
                    f"{base}/audio/speech", headers=headers,
                    json={"model": args.audio_model, "input": "你好", "voice": "alloy", "response_format": "mp3"},
                )
                print(f"  HTTP {resp.status_code}  返回 {len(resp.content)} 字节")
            except Exception as exc:  # noqa: BLE001
                print(f"  异常: {exc}")

        if not args.allow_costly:
            print("\n已跳过 视频 / 音乐 的真实调用(会产生真实费用)。")
            print("确认要跑请追加 --allow-costly,或直接在业务里小额度验证一次。")
            return

        print("\n[costly] videos 提交与轮询 ...")
        try:
            resp = client.post(
                f"{base}/videos", headers=headers,
                json={"model": args.video_model, "prompt": "a cat", "seconds": "3"},
            )
            print(f"  提交 HTTP {resp.status_code}  {_snippet(resp, 200)}")
            task_id = None
            if resp.status_code < 300:
                data = resp.json()
                task_id = data.get("id") or data.get("task_id")
            if not task_id:
                print("  未拿到任务 ID,跳过轮询")
            else:
                for i in range(args.poll_times):
                    time.sleep(args.poll_interval)
                    r = client.get(f"{base}/videos/{task_id}", headers=headers)
                    print(f"  轮询#{i + 1} HTTP {r.status_code}  {_snippet(r, 160)}")
                    if r.status_code < 300 and ("completed" in r.text or "succeeded" in r.text):
                        break
        except Exception as exc:  # noqa: BLE001
            print(f"  异常: {exc}")

        print("\n[costly] audio/music/generations ...")
        try:
            resp = client.post(
                f"{base}/audio/music/generations", headers=headers,
                json={"model": args.music_model, "prompt": "calm piano", "format": "mp3"},
            )
            print(f"  HTTP {resp.status_code}  {_snippet(resp, 200)}")
        except Exception as exc:  # noqa: BLE001
            print(f"  异常: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="中转站(OpenAI 兼容网关)能力探测")
    parser.add_argument("--base-url", default="", help="网关地址,如 https://aitoken.capitalai.cn/v1")
    parser.add_argument("--api-key", default="", help="网关密钥")
    parser.add_argument("--timeout", type=float, default=30, help="单次请求超时(秒)")
    parser.add_argument("--real", action="store_true", help="真实调用 chat/图片 验证链路(有少量消耗)")
    parser.add_argument("--allow-costly", action="store_true", help="允许真实调用 视频/音乐/语音(会产生费用)")
    parser.add_argument("--poll-times", type=int, default=5, help="视频轮询次数")
    parser.add_argument("--poll-interval", type=float, default=10, help="视频轮询间隔(秒)")
    parser.add_argument("--chat-model", default="qwen3.7-max")
    parser.add_argument("--image-model", default="qwen-image-2.0")
    parser.add_argument("--video-model", default="happyhorse-1.1-t2v")
    parser.add_argument("--audio-model", default="qwen-audio-3.0-tts-plus")
    parser.add_argument("--music-model", default="fun-music-v1")
    parser.add_argument("--models", action="store_true", help="拉取 /models 清单并按能力推荐模型名(零成本)")
    parser.add_argument("--print-config", action="store_true", help="只打印配置模板,不发任何请求")
    args = parser.parse_args()

    if args.print_config:
        print_config_template()
        return 0
    if not args.base_url:
        parser.error("--base-url 是必需的(仅 --print-config 可省略)")

    if not args.api_key:
        print("警告: 未提供 --api-key,鉴权相关探测会返回 401\n")

    probe(args.base_url, args.api_key, args.timeout)
    if args.models:
        print_model_catalog(args.base_url, args.api_key, args.timeout)
    if args.real:
        run_real(args.base_url, args.api_key, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
