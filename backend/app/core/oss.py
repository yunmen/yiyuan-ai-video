# -*- coding: utf-8 -*-
'''
@文件    :oss.py
@说明    :对象存储(阿里云 OSS)客户端 — 上传素材/结果持久化
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
@说明    :SDK 延迟导入;OSS 未启用时返回 None,不引入强依赖、不影响服务启动。
'''
from typing import Optional

from app.settings import config

_oss = None


class AliOss(object):
    """阿里云 OSS 客户端封装"""

    def __init__(
        self,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        token: Optional[str] = None,
        region: Optional[str] = None,
        scheme: str = "https",
        bucket: Optional[str] = None,
        endpoint: Optional[str] = None,
        public_base_url: Optional[str] = None,
    ):
        import alibabacloud_oss_v2 as oss
        from alibabacloud_oss_v2.credentials import StaticCredentialsProvider

        self.bucket = bucket
        self.region = region
        self.endpoint = endpoint
        self.public_base_url = public_base_url
        self.disable_ssl = scheme == "http"
        cfg = oss.config.load_default()
        cfg.credentials_provider = StaticCredentialsProvider(
            access_key_id=secret_id,
            access_key_secret=secret_key,
            security_token=token,
        )
        cfg.region = region
        if endpoint:
            cfg.endpoint = endpoint
        if self.disable_ssl:
            cfg.disable_ssl = True
        self.config = cfg

    def _build_url(self, key: str) -> str:
        scheme = "http" if self.disable_ssl else "https"
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{key}"
        if self.endpoint:
            return f"{scheme}://{self.bucket}.{self.endpoint}/{key}"
        return f"{scheme}://{self.bucket}.oss-{self.region}.aliyuncs.com/{key}"

    def put_object(self, key: str, data: bytes) -> str:
        """上传字节流,返回可访问 URL"""
        import alibabacloud_oss_v2 as oss

        client = oss.Client(self.config)
        client.put_object(oss.PutObjectRequest(bucket=self.bucket, key=key, body=data))
        return self._build_url(key)


def get_oss() -> Optional[AliOss]:
    """获取全局 OSS 客户端;未启用返回 None"""
    global _oss
    if not config.OSS_ENABLED:
        return None
    if _oss is None:
        _oss = AliOss(**config.OSS_CONFIG)
    return _oss
