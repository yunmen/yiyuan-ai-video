# -*- coding: utf-8 -*-
'''
@文件    :aioredis.py
@说明    :redis的异步封装
@时间    :2025/08/25 17:21:53
@作者    :睿
@版本    :1.0
'''
import os
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional
from redis import asyncio as aioredis
from loguru import logger


class AIORedis:
    def __init__(self, username: str = "defualt", password: str = "", host: str = "loaclhost", port: int = 6379, db: int = 0, decode: bool = True):
        self.user = username
        self.pwd = password
        self.host = host
        self.port = port
        self.db = db
        self.decode = decode

    async def get(self, key) -> Optional[str]:
        return await self.pool.get(key)
    
    async def keys(self, key) -> List:
        return await self.pool.keys(key)
    
    async def mget(self, keys: List) -> List:
        return await self.pool.mget(keys)
    
    async def set(self, key, value, nx=False, ex=None):
        return await self.pool.set(key, value, nx=nx, ex=ex)

    async def delete(self, *keys):
        return await self.pool.delete(*keys)

    # ===== 队列(列表)相关操作,用于任务下发 =====
    async def rpush(self, key, *values):
        return await self.pool.rpush(key, *values)

    async def lpush(self, key, *values):
        return await self.pool.lpush(key, *values)

    async def lpop(self, key):
        return await self.pool.lpop(key)

    async def brpop(self, key, timeout: int = 0):
        return await self.pool.brpop(key, timeout=timeout)

    async def llen(self, key):
        return await self.pool.llen(key)

    def register_script(self, script: str):
        return self.pool.register_script(script)


    async def startup(self):
        """创建连接池"""
        url = f"redis://{self.user}:{self.pwd}@{self.host}:{self.port}/{self.db}"
        self.pool = aioredis.from_url(
            url=url,
            encoding="utf-8",
            decode_responses=self.decode
        )

    async def shutdown(self):
        """关闭连接池"""
        await self.pool.aclose()




class AsyncRedisLock:
    def __init__(self, redis_client: aioredis.Redis, prefix: str="apscheduler", timeout: int = 10):
        self.redis = redis_client
        self.prefix = prefix
        self.key = f"{self.prefix}:lock:identifier"
        self.timeout = timeout  # 锁过期时间（秒）
        self.identifier = str(uuid.uuid4())  # 唯一标识，避免误删其他客户端的锁


    async def acquire(self, prefix: Optional[str] = None) -> bool:
        """异步获取锁（原子操作：SET key identifier NX EX timeout）"""
        key = self.key if not prefix else f"{self.prefix}:lock:{prefix}"
        result = await self.redis.set(
            key, self.identifier, nx=True, ex=self.timeout
        )
        return result is True  # set 成功返回 True，失败返回 None

    async def release(self, prefix: Optional[str] = None) -> bool:
        """异步释放锁（Lua 脚本校验 identifier 后删除，原子操作）"""
        lua_script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        await asyncio.sleep(2) # 避免锁释放的太快导致重复上锁
        key = self.key if not prefix else f"{self.prefix}:lock:{prefix}"
        script = self.redis.register_script(lua_script)
        result = await script(keys=[key], args=[self.identifier])
        return result == 1  # 删除成功返回 1，失败返回 0

    async def auto_run_func(self, func, prefix: Optional[str] = None, *args, **kwargs):
        """在锁保护下运行函数"""
        acquired = await self.acquire(prefix)
        logger.info(f"实例{os.getpid()}获取锁结果为: {acquired}")
        if acquired:
            try:
                await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"实例{os.getpid()}执行锁任务失败: {e}")
            finally:
                await self.release(prefix)
        else:
            logger.info("定时任务已由其他实例初始化完成")

    @asynccontextmanager
    async def auto_release(self, prefix: Optional[str] = None):
        """异步上下文管理器：自动获取和释放锁"""
        acquired = await self.acquire(prefix)
        if not acquired:
            logger.info("定时任务已由其他实例初始化完成")
            yield None
            return
        try:
            yield self
        finally:
            await self.release(prefix)

if __name__ == "__main__":
    import asyncio

    async def demo():
        redis = AIORedis("")
        res = await redis.get("name")
        print(res)
    
    asyncio.run(demo())