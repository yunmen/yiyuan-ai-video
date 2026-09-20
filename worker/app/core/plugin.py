# -*- coding: utf-8 -*-
'''
@文件    :plugin.py
@说明    :全局单例门面 — 统一实例化 logger,供各层复用
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
from plugin.logger import UniLogManager
from plugin.oss import AliOss
from app.settings import config


# 全局日志单例(各层统一从此处取 logger)
logger = UniLogManager(level="DEBUG")

# 全局 OSS 客户端(未启用时为 None,转存工具会自动跳过并保留原始直链)
oss = AliOss(**config.OSS_CONFIG) if config.OSS_ENABLED else None
if oss is None:
    logger.warning("OSS 未启用(OSS_ENABLE/密钥/Bucket 不完整),生成结果将保留模型原始直链")
