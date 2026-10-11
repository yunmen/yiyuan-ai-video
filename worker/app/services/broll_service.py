# -*- coding: utf-8 -*-
'''
@文件    :broll_service.py
@说明    :自动 B-roll 轨(对齐 Hypit 的 B-roll 素材镜头承接):根据时间轴/关键词自动决定插入点,
          复用 compose.build_broll_cmd 把商品图/场景图/指定素材按时间窗叠到成片之上。
          这是增强层:任一环节失败一律回退原片,绝不因"加 B-roll"让已付费生成变失败。
          设计上承接 script_schema 预留的 {"type":"broll","during":"selection:product"} 轨道思想 ——
          "讲到商品时切产品特写"即 strategy="mention" + keywords=商品名。
          P3-3 起可直接用 strategy="anchor" + anchors=["selection:product"]:按**词锚点的真实秒**
          插窗(改台词后时间轴自动重排,无需维护关键词),是 mention 的「锚点版」。
'''
import asyncio
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from app.core import compose
from app.core import subtitle
from app.core.plugin import logger
from app.utils.oss import download_to_local, upload_local_file


def _resolve_source(cfg: Dict[str, Any], params: Dict[str, Any]) -> Optional[str]:
    """解析 B-roll 素材来源:goods(商品图)/scene(场景图)/显式 http(s) URL;解析不到再回退商品图→场景图。"""
    src = cfg.get("source")
    if src in ("goods", "scene"):
        url = str(params.get(src) or "").strip()
        return url or None
    if isinstance(src, str) and src.lower().startswith("http"):
        return src.strip() or None
    # 未显式指定 source 时,带货场景最自然的是商品图,其次场景图
    goods = str(params.get("goods") or "").strip()
    if goods:
        return goods
    scene = str(params.get("scene") or "").strip()
    return scene or None


async def _generate_broll_source(cfg: Dict[str, Any], task_id: str) -> Optional[str]:
    """source="gen" 时调用文生图工具自动产出 B-roll 素材。

    返回生成的首张图片 URL;任何失败(提示词缺失 / 图片网关未配 / 生成空 / 异常)均返回 None,
    由调用方回退到 goods/scene/URL,再不行回退原片 —— 增强层不阻断主流程。
    """
    prompt = _build_gen_prompt(cfg)
    if not prompt:
        logger.warning(f"[Broll] 自动生成素材缺少提示词,跳过 gen task={task_id}")
        return None
    try:
        from app.tools.image_tool import ImageGenTool

        tool = ImageGenTool()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Broll] 图片网关未配置,无法自动生成 B-roll 素材 task={task_id}: {exc}")
        return None
    try:
        ratio = str(cfg.get("ratio") or "1:1")
        res = await tool.text_to_image(prompt, ratio=ratio, num_images=1, task_id=f"broll_{task_id}")
        if res and getattr(res, "metadata", {}).get("success") and getattr(res, "content", ""):
            urls = [u.strip() for u in str(res.content).split(",") if u.strip()]
            return urls[0] if urls else None
        logger.warning(f"[Broll] 文生图未返回素材,回退 task={task_id}")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Broll] 自动生成 B-roll 素材异常,回退 task={task_id}: {exc}")
        return None


def _build_gen_prompt(cfg: Dict[str, Any]) -> Optional[str]:
    """构造自动生成 B-roll 素材的提示词:优先用调用方显式给的 prompt;否则用通用电商特写提示词。

    不臆造商品信息 —— 兜底提示词只描述画面观感,保证"无素材也能出 B-roll"的同时不编造内容。
    """
    prompt = str(cfg.get("prompt") or "").strip()
    if prompt:
        return prompt
    return "电商产品宣传穿插画面,高清质感,干净高级背景,柔和光影,适合作为视频转场或特写镜头"


def derive_broll_windows(
    cues: List[Any], cfg: Dict[str, Any], duration: float,
    anchor_windows: Optional[List[Tuple[float, float]]] = None,
) -> List[Tuple[float, float]]:
    """推导 B-roll 插入时间窗(秒)。纯函数,便于契约测试,不依赖 ffmpeg/网络。

    - strategy="anchor"(P3-3,对齐"讲到商品切特写"的真实秒版):用调用方按词锚点解析出的
      真实时间窗 anchor_windows 依次插窗;无窗时按 fallback_even(默认 True)退回 even,否则返回空。
    - strategy="mention"(对齐"讲到商品切特写"):在字幕文本命中所给关键词的句子时间窗插入;
      无关键词或无可命中句时,按 fallback_even(默认 True)退回 even,否则返回空。
    - strategy="even":按 interval 间隔、window 时长在 [start_offset, duration] 内均匀铺窗。
    """
    strategy = str(cfg.get("strategy") or "even").lower()
    if strategy == "anchor":
        wins = [
            (max(0.0, float(s)), min(duration, float(e)))
            for s, e in (anchor_windows or [])
        ]
        wins = [(s, e) for s, e in wins if e > s]
        if wins or not cfg.get("fallback_even", True):
            return wins
        strategy = "even"
    if strategy == "mention":
        keywords = [str(k).strip() for k in (cfg.get("keywords") or []) if str(k).strip()]
        wins: List[Tuple[float, float]] = []
        if keywords and cues:
            for c in cues:
                text, start_ms, end_ms = "", 0.0, 0.0
                if isinstance(c, dict):
                    text = str(c.get("text") or "")
                    start_ms = float(c.get("start_ms") or 0)
                    end_ms = float(c.get("end_ms") or 0)
                else:
                    text = str(getattr(c, "text", "") or "")
                    start_ms = float(getattr(c, "start_ms", 0) or 0)
                    end_ms = float(getattr(c, "end_ms", 0) or 0)
                if any(k in text for k in keywords):
                    wins.append((max(0.0, start_ms / 1000.0), min(duration, end_ms / 1000.0)))
        if wins or not cfg.get("fallback_even", True):
            return wins
        strategy = "even"
    # even: 均匀铺窗(无字幕也能用,按时间轴均匀插 B-roll)
    interval = max(2.0, float(cfg.get("interval") or 8.0))
    window = max(1.0, min(float(cfg.get("window") or 3.0), interval * 0.9))
    start_off = max(0.0, float(cfg.get("start_offset") or 1.0))
    wins = []
    t = start_off
    while t + window <= duration:
        wins.append((t, t + window))
        t += interval
    return wins


async def apply_auto_broll(
    content: str, params: Dict[str, Any], duration: float, task_id: str
) -> str:
    """自动 B-roll 增强层:成功返回新 URL;任何失败/无需插入返回原 content(增强层不阻断主流程)。

    顺序叠加多个时间窗(同一素材只下载一次,本地链式叠加,最后整体回传一次 OSS),
    与 compose.build_broll_cmd 的淡入淡出 / enable 边界一致。
    """
    cfg = params.get("auto_broll") if isinstance(params.get("auto_broll"), dict) else None
    if not cfg or not cfg.get("enabled"):
        return content
    if not compose.available():
        return content
    # 自动生成素材来源:source="gen" 时优先用文生图产出 B-roll 素材;失败再回退 goods/scene/URL,
    # 仍失败则回退原片(增强层绝不因"加 B-roll"让已付费生成变失败)。
    gen_url = None
    if str(cfg.get("source") or "").lower() == "gen":
        gen_url = await _generate_broll_source(cfg, task_id)
    source = gen_url or _resolve_source(cfg, params)
    if not source:
        logger.warning(f"[Broll] 自动 B-roll 缺少可用素材来源,跳过 task={task_id}")
        return content
    try:
        duration = float(duration or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        return content
    # 关键词命中 / 锚点两种策略都需要字幕时间轴(真实对齐);无 cues 时 derive 会自动 fallback 到 even
    strategy = str(cfg.get("strategy") or "even").lower()
    anchors = [str(a).strip() for a in (cfg.get("anchors") or []) if str(a).strip()]
    cues: List[Any] = []
    if (strategy == "mention" and cfg.get("keywords")) or (strategy == "anchor" and anchors):
        try:
            raw = await asyncio.wait_for(
                subtitle.compute_cues(content, params, duration), timeout=600,
            )
            cues = list(raw) if raw else []
        except Exception:  # noqa: BLE001
            cues = []
    # P3-3:锚点策略把「锚点引用」解析成真实秒窗(优先真实对齐,退化到估算)
    anchor_windows: Optional[List[Tuple[float, float]]] = None
    if strategy == "anchor" and anchors:
        try:
            anchor_windows = subtitle.anchor_windows(params, cues, duration, anchors)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[Broll] 锚点窗口解析失败,回退 even task={task_id}: {exc}")
            anchor_windows = None
    wins = derive_broll_windows(cues, cfg, duration, anchor_windows)
    if not wins:
        return content
    workdir = tempfile.mkdtemp(prefix="auto_broll_")
    try:
        local_asset = await asyncio.to_thread(download_to_local, source, ".mp4")
        if not local_asset:
            return content
        btype = "video" if os.path.splitext(source.split("?", 1)[0])[1].lower().lstrip(".") \
            in ("mp4", "webm", "mov", "m4v", "avi", "mkv") else "image"
        local_main = await asyncio.to_thread(download_to_local, content, ".mp4")
        if not local_main:
            return content
        applied = False
        cur = local_main
        for i, (s, e) in enumerate(wins):
            out = os.path.join(workdir, f"ab_{i}.mp4")
            cmd = compose.build_broll_cmd(
                cur, local_asset, out, start=s, end=e,
                fade=float(cfg.get("fade") or 0.3),
                scale=float(cfg.get("scale") or 1.0),
                position=str(cfg.get("position") or "center"),
                broll_type=btype,
            )
            res = await compose.run(cmd, timeout=600, cwd=workdir)
            if res.get("ok") and os.path.exists(out):
                cur = out
                applied = True
            else:
                logger.warning(f"[Broll] 第{i}窗叠加失败,停止后续窗 task={task_id}: {res.get('stderr')}")
                break
        if not applied:
            return content
        url = await asyncio.to_thread(
            upload_local_file, cur, f"generate/result/auto_broll_{task_id}.mp4"
        )
        if not url:
            logger.warning(f"[Broll] 自动 B-roll 回传失败,保留原片 task={task_id}")
            return content
        logger.info(f"[Broll] 自动 B-roll 叠加完成 {len(wins)} 窗 task={task_id}")
        return url
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Broll] 自动 B-roll 异常,保留原片 task={task_id}: {exc}")
        return content
