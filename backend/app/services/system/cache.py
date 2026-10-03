# -*- coding: utf-8 -*-
'''
@文件    :cache.py
@说明    :
@时间    :2025/09/09 17:17:35
@作者    :睿
@版本    :1.0
'''
from app.core.plugin import redis
from app.core.plugin import jwt
from app.core.plugin import logger
from app.settings import config

class Service:

    async def get_admin_token(self):
        keys = await redis.keys(f"{config.REDIS_PREFIX_NAME}:admin:*")
        values = await redis.mget(keys)
        result = []
        for value in values:
            # 容错: 跳过因跨实例/旧 SECRET_KEY 写入而无法直接解密的失效 token,
            # 避免单个坏 token 拖垮整个"在线管理员"接口(500)。
            try:
                data = jwt.decrypt_token(value)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"admin token 解密失败(跳过): {repr(exc)}")
                continue
            if not isinstance(data, dict) or data.get('superuser'):
                continue
            result.append(data)
        return result

    async def delete_admin_token(self, *accounts):
        keys = []
        for account in accounts:
            keys.append(f"{config.REDIS_PREFIX_NAME}:admin:{account}")
        await redis.delete(*keys)
        

service = Service()