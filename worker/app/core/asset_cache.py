# -*- coding: utf-8 -*-
'''
@文件    :asset_cache.py
@说明    :生成资产缓存客户端(P2)— 跨任务复用中间产物,直接降本
@时间    :2026/09/21 10:20:00
@作者    :一源AI
@版本    :1.0
@说明    :与 backend app/services/asset_cache.py 是两套部署包里的镜像实现:
          build_cache_key 必须逐字节一致,否则一端写、另一端永远读不到(静默失效,不报错),
          由 backend/tests/test_cross_worker_contract.py 用同一样例钉死。

          缓存是优化而非链路依赖:backend 不可达/超时/报错一律按「未命中」处理,
          继续正常调用付费接口,绝不因缓存故障让生成失败。
'''
import hashlib
import json
from typing import Any, Dict, Optional

# 产物类型(与 backend 保持一致)
ASSET_TTS_AUDIO = "tts_audio"
ASSET_OPTIMIZED_PROMPT = "optimized_prompt"
# P2 补强:媒体资产级复用 —— 「换主播/换文案重跑」时把未变的上游素材直接复用,只重跑真正变化的环节
ASSET_IMAGE = "image"                  # 图片生成结果(文生图/图生图/形象图派生),content 为 OSS 直链
ASSET_DIGITAL_VIDEO = "digital_video"  # 数字人口型驱动成片,content 为 OSS 直链


def build_cache_key(asset_type: str, payload: Dict[str, Any]) -> str:
    """缓存键 = 产物类型 + 决定产物的全部入参(稳定哈希)

    payload 按 key 排序序列化:dict 顺序不同不影响结果。
    """
    body = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    raw = f"{asset_type}|{body}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def enabled() -> bool:
    """缓存开关(gen.cache.enabled):关闭时全部按未命中处理"""
    try:
        from app.settings import config
        return str(getattr(config, "CACHE_ENABLED", "1")) not in ("0", "false", "False", "")
    except Exception:  # noqa: BLE001
        return True


def _base_url(notify_url: Optional[str]) -> str:
    """由 callback 地址推导同域名下的缓存接口地址(与 plugin.notice 同一套推导)"""
    try:
        from app.settings import config
        base = (notify_url or getattr(config, "NOTIFY_URL", "") or "").rstrip("/")
    except Exception:  # noqa: BLE001
        base = ""
    return base.rsplit("/callback", 1)[0]


def _token(token: Optional[str]) -> str:
    if token is not None:
        return token
    try:
        from app.settings import config
        return getattr(config, "NOTIFY_TOKEN", "") or ""
    except Exception:  # noqa: BLE001
        return ""


async def fetch(notify_url: Optional[str], cache_key: str, asset_type: str = "", token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """读取缓存:命中返回 {"content": ..., "meta": ..., "hit_count": n};未命中/异常返回 None"""
    if not enabled() or not cache_key:
        return None
    url = f"{_base_url(notify_url)}/cache"
    try:
        import httpx
        from app.core.plugin import logger
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                url, params={"cache_key": cache_key, "asset_type": asset_type},
                headers={"X-Worker-Token": _token(token)},
            )
        if resp.status_code >= 400:
            return None
        body = resp.json() or {}
        data = body.get("data")
        if not isinstance(data, dict) or not data.get("content"):
            return None
        logger.info(
            f"[AssetCache] 命中 type={asset_type or '-'} key={cache_key[:12]} "
            f"hits={data.get('hit_count')} → 跳过付费调用"
        )
        return data
    except Exception:  # noqa: BLE001 - 缓存不可用时静默降级,不影响生成
        return None


async def store(
    notify_url: Optional[str], cache_key: str, asset_type: str, content: str,
    task_type: str = "", meta: Optional[Dict[str, Any]] = None, token: Optional[str] = None,
) -> bool:
    """回写缓存;失败仅返回 False(不阻断生成)"""
    if not enabled() or not cache_key or not content:
        return False
    url = f"{_base_url(notify_url)}/cache"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                url,
                json={
                    "cache_key": cache_key, "asset_type": asset_type, "content": content,
                    "task_type": task_type, "meta": meta or {},
                },
                headers={"Content-Type": "application/json", "X-Worker-Token": _token(token)},
            )
        return resp.status_code < 400
    except Exception:  # noqa: BLE001
        return False
