# -*- coding: utf-8 -*-
'''跨任务记忆:在 worker 进程内(同一 ARQ worker 生命周期)累积已执行计划的关键产物与用户偏好,
供后续计划规划(_llm_plan)与技能(如文案风格)复用,实现"经验"跨任务传递。

默认进程内 TTL 缓存(无需外部存储,零依赖);未来可接 Redis 做跨进程/跨重启持久化。
所有接口均为 async 以兼容编排器协程调用;纯内存操作成本极低。
'''
import json
import time
from typing import Any, Dict, List, Optional

from app.core.plugin import logger

_TTL = 1800  # 记忆存活 30 分钟(进程内)
_STORE: Dict[str, Dict[str, Any]] = {}  # scope -> { key: {"value":..., "exp":...} }


def _now() -> float:
    return time.time()


async def remember(scope: str, key: str, value: Any) -> None:
    """写入一条记忆(scope 维度,如计划名/用户标识)。空 scope 直接忽略。"""
    if not scope:
        return
    bucket = _STORE.setdefault(scope, {})
    bucket[key] = {"value": value, "exp": _now() + _TTL}
    # 简单限长,避免无限增长:超过上限时淘汰最早过期项
    if len(bucket) > 50:
        oldest = min(bucket, key=lambda k: bucket[k]["exp"])
        bucket.pop(oldest, None)


async def recall(scope: str, key: Optional[str] = None) -> Any:
    """读取记忆;key 为空返回该 scope 全部(已过滤过期),否则返回单条或 None。"""
    bucket = _STORE.get(scope)
    if not bucket:
        return {} if key is None else None
    now = _now()
    if key is None:
        return {k: v["value"] for k, v in bucket.items() if v["exp"] > now}
    item = bucket.get(key)
    if item and item["exp"] > now:
        return item["value"]
    return None


async def recall_prompt(scope: str, goal: str = "", limit: int = 3) -> str:
    """把该 scope 的近期记忆格式化为给 LLM 的提示片段;无记忆返回空串。"""
    data = await recall(scope) or {}
    if not data:
        return ""
    lines = []
    for k, v in list(data.items())[:limit]:
        try:
            s = json.dumps(v, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            s = str(v)
        lines.append(f"- [{k}] {s[:300]}")
    if not lines:
        return ""
    prefix = f"参考你此前处理类似目标时的经验(目标:{goal}):" if goal else "参考此前的经验:"
    return prefix + "\n" + "\n".join(lines)
