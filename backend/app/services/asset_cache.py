# -*- coding: utf-8 -*-
"""
生成资产缓存服务(P2)— 跨任务复用中间产物,直接降本。

与 checkpoint 的区别:
  checkpoint 是「同一任务」的断点,重跑/换主播时依然会重新调用付费接口;
  本缓存按**输入内容哈希**键控,同一份输入在 TTL 内只调一次真实接口 ——
  换主播重跑(文案未变)时 TTS 音频直接命中,不必重新合成。

worker 侧有同名镜像实现(worker/app/core/asset_cache.py),两端键必须一致,
由 test_cross_worker_contract.py 用同一样例钉死。
"""
import hashlib
import json
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.models.asset_cache import GenAssetCacheModel

# 产物类型(与 worker/app/core/asset_cache.py 保持一致,由 test_cross_worker_contract.py 钉死)
#   tts_audio         语音合成音频(文案+音色+声纹+语速+方言+模型+格式)
#   optimized_prompt  提示词改写结果
#   image             图片生成结果(文生图/图生图/形象图派生)
#   digital_video     数字人口型驱动成片
ASSET_TTS_AUDIO = "tts_audio"
ASSET_OPTIMIZED_PROMPT = "optimized_prompt"
ASSET_IMAGE = "image"
ASSET_DIGITAL_VIDEO = "digital_video"

# 默认缓存天数(可被系统配置 gen.cache.ttl_days 覆盖)
DEFAULT_TTL_DAYS = 7
CFG_KEY_ENABLED = "gen.cache.enabled"
CFG_KEY_TTL_DAYS = "gen.cache.ttl_days"


def build_cache_key(asset_type: str, payload: Dict[str, Any]) -> str:
    """缓存键 = 产物类型 + 决定产物的全部入参(稳定哈希)。

    payload 按 key 排序序列化:dict 顺序不同不影响结果(worker 与 backend 组装方式可能不同)。
    """
    body = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    raw = f"{asset_type}|{body}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def is_expired(expire_time, now) -> bool:
    """过期判定(纯函数,便于单测);无过期时间视为不过期"""
    if expire_time is None:
        return False
    return expire_time <= now


# 缓存天数短缓存:写缓存时会读配置,避免每次都查库(与 generate_task 的成本配置同一套路)
_TTL_CACHE: Dict[str, Any] = {"ts": 0.0, "days": None}


async def load_ttl_days() -> int:
    """读取缓存天数配置(gen.cache.ttl_days);读库失败用默认值,缓存配置不是链路依赖"""
    now = time.time()
    if _TTL_CACHE.get("days") is not None and now - float(_TTL_CACHE.get("ts") or 0) < 60:
        return int(_TTL_CACHE["days"])
    days = DEFAULT_TTL_DAYS
    try:
        from app.cruds.system_config import crud as config_crud
        row = await config_crud.model.filter(key=CFG_KEY_TTL_DAYS).first()
        value = str(getattr(row, "value", "") or "").strip()
        if value:
            days = max(0, int(value))
    except Exception:  # noqa: BLE001
        pass
    _TTL_CACHE["ts"], _TTL_CACHE["days"] = now, days
    return days


def compute_hit_stats(by_type: List[Dict[str, Any]]) -> Dict[str, Any]:
    """由「按类型聚合结果」算总览指标(纯函数,便于单测)

    语义:一条缓存 = 一次未命中(那次真实调用了付费接口);命中则 hit_count += 1。
    所以 请求数 = 条目数 + 命中次数,命中率 = 命中次数 / 请求数。
    """
    total = sum(int(x.get("count") or 0) for x in by_type or [])
    hits = sum(int(x.get("hits") or 0) for x in by_type or [])
    requests = total + hits
    return {
        "total": total, "hits": hits, "requests": requests,
        "hit_rate": round(hits / requests, 4) if requests else 0.0,
    }


class AssetCacheService:
    """缓存读写:未命中/过期/异常一律返回 None —— 缓存是优化,不是链路依赖"""

    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        if not cache_key:
            return None
        from tortoise.timezone import now as tz_now

        obj = await GenAssetCacheModel.get_or_none(cache_key=cache_key, deleted=False)
        if not obj:
            return None
        if is_expired(obj.expire_time, tz_now()):
            await obj.delete()      # 惰性清理,避免表无限膨胀
            return None
        obj.hit_count = (obj.hit_count or 0) + 1
        # update_time 一并刷新:管理端看的「最近命中时间」就是它
        await obj.save(update_fields=["hit_count", "update_time"])
        return {"content": obj.content, "meta": obj.meta or {}, "hit_count": obj.hit_count}

    async def set(
        self, cache_key: str, asset_type: str, content: str,
        task_type: str = "", meta: Optional[Dict[str, Any]] = None, ttl_days: Optional[int] = None,
    ) -> bool:
        """写入缓存;已存在则刷新内容与过期时间(命中次数保留,用于统计复用收益)"""
        if not cache_key or not content:
            return False
        from tortoise.timezone import now as tz_now

        days = await load_ttl_days() if ttl_days is None else ttl_days
        expire = (tz_now() + timedelta(days=days)) if days and days > 0 else None
        obj = await GenAssetCacheModel.get_or_none(cache_key=cache_key, deleted=False)
        if obj:
            # update_from_dict:expire_time 可能为 None(不过期),直接赋值会被类型检查挡下
            obj.update_from_dict({
                "content": content, "asset_type": asset_type,
                "meta": meta or {}, "expire_time": expire,
            })
            await obj.save(update_fields=["content", "asset_type", "meta", "expire_time", "update_time"])
            return True
        await GenAssetCacheModel.create(
            cache_key=cache_key, asset_type=asset_type, task_type=task_type or "",
            content=content, meta=meta or {}, expire_time=expire,
        )
        return True

    async def purge_expired(self) -> int:
        """清理过期缓存(供运维/定时任务调用),返回清理条数"""
        from tortoise.timezone import now as tz_now

        return await GenAssetCacheModel.filter(expire_time__lte=tz_now()).update(deleted=True)

    async def stats(self) -> Dict[str, Any]:
        """命中统计(管理端可观测)

        只报**可验证的计数**,不编造金额:
          - 一次未命中会写一条缓存(total += 1),一次命中会让 hit_count += 1;
          - 因此 hit_rate = hits / (total + hits) 就是「缓存请求里有多少比例被复用」,
            这是能直接换算成"少调用了几次付费接口"的指标。
        """
        from tortoise.functions import Count, Sum

        rows = await (
            GenAssetCacheModel.filter(deleted=False)
            .group_by("asset_type")
            .annotate(count=Count("id"), hits=Sum("hit_count"))
            .values("asset_type", "count", "hits")
        )
        by_type = [
            {
                "asset_type": r.get("asset_type"),
                "count": int(r.get("count") or 0),
                "hits": int(r.get("hits") or 0),
            }
            for r in rows
        ]
        overview = compute_hit_stats(by_type)

        top_rows = await (
            GenAssetCacheModel.filter(deleted=False, hit_count__gt=0)
            .order_by("-hit_count")
            .limit(10)
            .values("asset_type", "task_type", "hit_count", "update_time", "content")
        )
        top = []
        for r in top_rows:
            updated = r.get("update_time")
            top.append({
                "asset_type": r.get("asset_type"),
                "task_type": r.get("task_type") or "",
                "hit_count": int(r.get("hit_count") or 0),
                "update_time": updated.strftime("%Y-%m-%d %H:%M:%S") if updated else "",
                "preview": str(r.get("content") or "")[:80],
            })
        overview.update({"by_type": by_type, "top": top, "ttl_days": await load_ttl_days()})
        return overview


service = AssetCacheService()
