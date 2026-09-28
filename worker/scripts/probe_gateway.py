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

    # 验证「拟态化后的参考图能否过平台真人检测」:按「原图 拟态图」顺序传多张对比
    python worker/scripts/probe_gateway.py --base-url ... --api-key ... \
        --image-real-person https://oss/original.jpg https://oss/stylized.jpg --allow-costly

@作者    :一源AI
@版本    :1.1
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
    # 视频编辑(Seedance 2.x):以**视频**为参考(不是抽帧图)+ 商品图 + 新台词,
    # 模型输出自带 lip-synced 语音。命名各中转站不一,故关键词放宽。
    ("gen.video_model_edit", "视频编辑(参考视频→新片)",
     ["seedance-2", "seedance2", "seedance_v2", "seedance-v2", "seedance_2",
      "reference-to-video", "video-edit", "v2.0-reference"], []),
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


def probe_video_edit(base_url: str, api_key: str, model: str, timeout: float) -> None:
    """探测**视频编辑**能力:网关是否接受 videos[] / generate_audio 字段

    为什么单独探测:
      「复刻」的本质是视频编辑(参考视频 + 商品图 + 新台词),而不是把参考视频抽帧当图片传。
      但各中转站对 videos / generate_audio 的支持差异极大 —— 写死字段却不被支持,
      表现是提交直接 400,且错误信息往往不说是哪个字段的问题。

    判读方法(关键):对比三组请求的响应体
      ① 基线(只有 model+prompt)
      ② 带 videos[]
      ③ 带 videos[] + generate_audio
    若 ②/③ 的报错与 ① **不同且提到了对应字段** → 该字段被网关解析(支持);
    若报错完全相同 → 该字段大概率被忽略(不支持);
    若出现 unknown field / extra fields not permitted → 明确不支持。
    """
    base = base_url.rstrip("/")
    headers = _headers(api_key)
    # ⚠️ 所有用例一律**不带 prompt**:缺必填参数会被网关直接拒掉,
    # 避免"参数齐全"时真的创建生成任务(那样会扣费)。
    cases = [
        ("基线(仅 model)", {"model": model}),
        ("+videos[]", {"model": model, "videos": ["https://example.com/ref.mp4"]}),
        ("+generate_audio", {
            "model": model, "videos": ["https://example.com/ref.mp4"], "generate_audio": True,
        }),
        ("+duration=12", {"model": model, "videos": ["https://example.com/ref.mp4"], "duration": 12}),
    ]
    print(f"\n视频编辑字段探测(零成本:故意缺必填参数): {base}/videos   model={model or '(未指定)'}\n")
    print(f"{'用例':<20}{'判定':<11}{'状态':<6}响应片段")
    print("-" * 120)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for label, body in cases:
            try:
                resp = client.post(f"{base}/videos", headers=headers, json=body)
                verdict, _ = classify(resp.status_code)
                status, snippet = str(resp.status_code), _snippet(resp, limit=200)
            except Exception as exc:  # noqa: BLE001
                verdict, status, snippet = "FAIL", "-", f"请求异常: {exc}"
            print(f"{label:<20}{verdict:<11}{status:<6}{snippet}")

    print("\n判读要点(对比四组响应体):")
    print("  · 某组报错**提到 videos / generate_audio / duration** → 该字段被网关解析,支持;")
    print("  · 四组报错**完全相同**(都只说缺 prompt 之类) → 额外字段被忽略,视频编辑不可用;")
    print("  · 出现 unknown field / extra fields not permitted → 明确不支持该字段;")
    print("  · 401/402 → 端点在,但 key 无权限或余额不足(需充值后再判读);")
    print("  · duration=12 若未被拒 → 该模型支持 4~15s 任意时长(可放开 gen.video_durations)。")


def _image_probe_request(proto: str, model: str, image_url: str) -> Tuple[str, Dict[str, Any]]:
    """按协议组装「只含一张参考图」的最小生成请求,返回 (path, body)

    只放图片、不放别的素材,才能把"被拒"归因到这张图本身的真人检测上;
    时长固定 3 秒,尽量压低万一放行时的成本。
    """
    if proto == "ark":
        # 方舟原生:与 _ark_body 的 r2v 形态一致(text + image_url/reference_image)
        return "/contents/generations/tasks", {
            "model": model,
            "content": [
                {"type": "text", "text": "参考这张图生成一段短视频 --resolution 720p --duration 3"},
                {"type": "image_url", "image_url": {"url": image_url}, "role": "reference_image"},
            ],
        }
    return "/videos", {
        "model": model,
        "prompt": "参考这张图生成一段短视频",
        "image": image_url,
        "seconds": "3",
    }


def classify_image_real_person(status: int, text: str) -> str:
    """按响应判定这张图是否触发了平台真人检测(用于对比原图 / 拟态图)

    - BLOCKED          :明确返回"图片含真人"被拒(说明该图未过检测);
    - PASSED           :被放行并创建了任务(**会产生费用**);
    - PASSED_DETECTION :因其它原因被拒(缺参数/模型不对等),但**没有**触发真人检测 ——
                         这是"过了检测"的正面证据,且不产生费用;
    - AUTH / QUOTA     :鉴权失败 / 余额不足,与素材无关,不能据此判读;
    - UNKNOWN          :无法判定。
    """
    low = str(text or "").lower()
    if "inputimagesensitivecontentdetected" in low or ("real person" in low and "image" in low):
        return "BLOCKED"
    if 200 <= status < 300:
        return "PASSED"
    if status in (401, 403):
        return "AUTH"
    if status == 402:
        return "QUOTA"
    if status >= 400:
        return "PASSED_DETECTION"
    return "UNKNOWN"


def probe_image_real_person(
    base_url: str, api_key: str, model: str, images: List[str], *,
    proto: str = "ark", timeout: float = 60.0,
) -> None:
    """探测「含真人的参考图」是否被平台拒绝,以及处理后的图能否放行

    为什么需要它:
      参考视频可以本地去身份化(打码),但参考图**不能打码**(它就是要被替换成的目标),
      只能「丢弃改按文字描述生成」或「拟态化后再提交」。拟态化能否真的过检测是经验问题,
      必须在真实网关实测后才能决定是否把 gen.image_real_person_mode 调成 stylize。

    用法:按「原图 → 拟态图」顺序传入多张对比:
      原图 BLOCKED + 拟态图 PASSED/PASSED_DETECTION → 拟态化有效,可开启该策略;
      两者都 BLOCKED                                 → 拟态化强度不足,应保持 drop;
      原图已 PASSED/PASSED_DETECTION                 → 该网关未对图片做真人检测(或该图未被判定为真人)。

    ⚠️ 成本:被拦的请求返回 400,不创建任务、不扣费;但**未被拦的图会真的创建生成任务**。
    因此本探测必须显式加 --allow-costly,并建议只在小额度环境跑一次。
    """
    base = base_url.rstrip("/")
    headers = _headers(api_key)
    path, _ = _image_probe_request(proto, model, images[0] if images else "")
    print(f"\n参考图真人检测探测(协议 {proto}): {base}{path}   model={model or '(未指定)'}")
    print("按「原图 → 拟态图」顺序对比判定;被拦=未过检测,放行=已过检测\n")
    print(f"{'图片':<58}{'判定':<18}{'状态':<6}响应片段")
    print("-" * 140)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for url in images:
            req_path, body = _image_probe_request(proto, model, url)
            try:
                resp = client.post(f"{base}{req_path}", headers=headers, json=body)
                verdict = classify_image_real_person(resp.status_code, resp.text)
                status, snippet = str(resp.status_code), _snippet(resp, limit=200)
            except Exception as exc:  # noqa: BLE001
                verdict, status, snippet = "FAIL", "-", f"请求异常: {exc}"
            shown = url if len(url) <= 56 else url[:53] + "..."
            print(f"{shown:<58}{verdict:<18}{status:<6}{snippet}")

    print("\n判读要点:")
    print("  BLOCKED          → 该图仍被判定含真人(拟态化强度不足 / 未处理);")
    print("  PASSED           → 已放行并创建任务(**会产生费用**),说明该图过了检测;")
    print("  PASSED_DETECTION → 因其它原因被拒但未触发真人检测,同样算'过了检测',且不产生费用;")
    print("  AUTH / QUOTA     → key 无效、无权限或余额不足,与素材无关,需先解决再判读;")
    print("  FAIL             → 端点不可达(地址/网络/协议不对),需先解决再判读。")


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
    print("(路径: 管理端左侧菜单「业务配置」→ 找到对应 KEY 改 VALUE)")
    for key, _cap, matched in rows:
        print(f"  {key:<24}= {matched[0] if matched else '<人工填写>'}")


def print_config_template() -> None:
    """打印网关配置模板(不发请求)"""
    print("\n===== 网关配置(全压一个中转站时只需前 2 项) =====")
    print("  路径: 管理端左侧菜单「业务配置」")
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
    parser.add_argument("--video-edit", action="store_true",
                        help="探测视频编辑字段(videos[]/generate_audio/任意时长)是否被网关接受")
    parser.add_argument("--image-real-person", nargs="+", default=None, metavar="URL",
                        help="探测参考图是否被判定含真人(可传多张对比,如:原图 拟态图);"
                             "未被拦的图会创建真实任务,需同时加 --allow-costly")
    parser.add_argument("--proto", choices=["ark", "openai"], default="ark",
                        help="图片真人探测使用的协议(默认 ark,与线上方舟原生一致)")
    parser.add_argument("--image-probe-model", default="",
                        help="图片真人探测用的模型(需支持图片输入,如 r2v/i2v/编辑模型);留空复用 --video-model")
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
    if args.video_edit:
        probe_video_edit(args.base_url, args.api_key, args.video_model, args.timeout)
    if args.image_real_person:
        # 未被拦的图会真的创建生成任务 → 与其他"会产生费用"的探测一样,需显式确认
        if not args.allow_costly:
            print("\n[跳过] 参考图真人检测探测在图片被放行时会创建真实任务,"
                  "请显式加 --allow-costly 后再跑。")
        else:
            probe_image_real_person(
                args.base_url, args.api_key,
                args.image_probe_model or args.video_model,
                args.image_real_person, proto=args.proto, timeout=args.timeout,
            )
    if args.real:
        run_real(args.base_url, args.api_key, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
