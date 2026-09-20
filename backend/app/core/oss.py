# -*- coding: utf-8 -*-
'''
@文件    :oss.py
@说明    :对象存储(腾讯云 COS)客户端 — 上传素材/结果持久化
@时间    :2026/09/20 19:30:00
@作者    :一源AI
@版本    :1.1
@说明    :实现移植自 ai-creator(腾讯 COS,SDK 为 qcloud_cos,延迟导入);
          OSS 未启用时返回 None,不引入强依赖、不影响服务启动。
'''
from typing import Optional

from app.settings import config

_oss = None


class TencentCos(object):
    """腾讯云 COS 客户端封装"""

    def __init__(
        self,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        token: Optional[str] = None,
        region: Optional[str] = None,
        scheme: str = "https",
        bucket: Optional[str] = None,
        timeout: int = 300,
        accelerate: bool = False,
    ):
        from qcloud_cos import CosConfig, CosS3Client

        if not secret_id or not secret_key:
            raise ValueError("腾讯 COS SecretId/SecretKey 未配置")
        if not bucket or not region:
            raise ValueError("腾讯 COS Bucket/Region 未配置")
        self.bucket = bucket
        self.region = region
        kwargs = dict(
            Region=region,
            SecretId=secret_id,
            SecretKey=secret_key,
            Token=token,
            Scheme=scheme,
            Timeout=timeout,
        )
        if accelerate:
            # 服务器在海外而桶在中国大陆时,区域域名国际链路劣化会导致大包
            # 上传超时/SSL EOF;改用全球加速域名,走腾讯内部网络完成上传。
            kwargs["Domain"] = f"{bucket}.cos.accelerate.myqcloud.com"
        self.client = CosS3Client(CosConfig(**kwargs), retry=0)

    def put_object(self, key: str, data: bytes) -> str:
        """上传字节流,返回可访问 URL"""
        self.client.put_object(Bucket=self.bucket, Body=data, Key=key)
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"


def get_oss() -> Optional[TencentCos]:
    """获取全局 OSS 客户端;未启用返回 None"""
    global _oss
    if not config.OSS_ENABLED:
        return None
    if _oss is None:
        _oss = TencentCos(**config.OSS_CONFIG)
    return _oss
