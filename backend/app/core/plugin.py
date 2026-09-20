# -*- coding: utf-8 -*-
'''
@文件    :plugin.py
@说明    :为了避免循环导入,插件统一在此进行实例化
@时间    :2025/08/25 16:00:23
@作者    :睿
@版本    :1.0
'''
from plugin.ctx import ContextVarManager
from plugin.database.aioredis import AIORedis, AsyncRedisLock
from plugin.database.aioorm import OrmDB
from plugin.scheduler.aioscheduler import AIOScheduler
from plugin.encryption.password import Password
from plugin.encryption.jwts import JWT
from plugin.logger import UniLogManager
from app.settings import config


ctx = ContextVarManager(config.CTX_LIST)
logger = UniLogManager(**config.LOGGER_CONFIG)
redis = AIORedis(**config.REDIS_CONFIG)
locker = AsyncRedisLock(redis, timeout=30)
database = OrmDB(config=config.ORM_CONFIG, engine=config.ORM_ENGINE)
scheduler = AIOScheduler()
password = Password(config.PASSWORD_HASH_ALGORITHM)
jwt = JWT(config.SECRET_KEY)
