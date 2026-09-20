# -*- coding: utf-8 -*-
'''
@文件    :ratelimit.py
@说明    :轻量频控(基于 Redis 计数窗口),用于保护免登录接口(AI 文案/上传)不被刷
@时间    :2026/09/20 19:40:00
@作者    :一源AI
@版本    :1.0
'''
from fastapi.exceptions import HTTPException

from app.core.plugin import redis
from app.settings import config


async def check(key: str, limit: int, window: int, message: str = "操作过于频繁,请稍后再试") -> None:
    """窗口内累计计数:超过 limit 直接抛业务异常

    说明:每次命中都会刷新 TTL,等价于「连续请求」滑动窗口,足以挡住脚本刷接口。
    """
    count = int(await redis.get(key) or 0)
    if count >= limit:
        raise HTTPException(status_code=200, detail=message)
    await redis.set(key, str(count + 1), ex=window)


def build_key(biz: str, identity: str) -> str:
    return f"{config.REDIS_PREFIX_NAME}:ratelimit:{biz}:{identity}"


def client_ip(request) -> str:
    """取客户端 IP(优先代理头,直连回退 host)"""
    if request is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
