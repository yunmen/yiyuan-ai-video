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
from app.settings import config

class Service:

    async def get_admin_token(self):
        keys = await redis.keys(f"{config.REDIS_PREFIX_NAME}:admin:*")
        values = await redis.mget(keys)
        result = []
        for value in values:
            data = jwt.decrypt_token(value)
            if data['superuser']:
                continue
            result.append(data)
        return result

    async def delete_admin_token(self, *accounts):
        keys = []
        for account in accounts:
            keys.append(f"{config.REDIS_PREFIX_NAME}:admin:{account}")
        await redis.delete(*keys)
        

service = Service()