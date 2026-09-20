# -*- coding: utf-8 -*-
'''
@文件    :oss.py
@说明    :对象存储服务(阿里云 OSS)— worker 侧结果转存
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.1
@说明    :依赖 alibabacloud_oss_v2(SDK 延迟导入,未安装且未启用 OSS 时不影响启动)。
          region/bucket/密钥均由 app/settings.py 从 env 文件读取后传入,插件层不读配置。
'''
from typing import Optional


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
        """按配置拼出对象的可访问 URL"""
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

    def put_local_file(self, key: str, path: str) -> str:
        """上传本地文件,返回可访问 URL"""
        import alibabacloud_oss_v2 as oss

        client = oss.Client(self.config)
        client.put_object_from_file(
            oss.PutObjectRequest(bucket=self.bucket, key=key),
            path,
        )
        return self._build_url(key)

    def object_exists(self, key: str) -> bool:
        """判断对象是否存在"""
        import alibabacloud_oss_v2 as oss

        client = oss.Client(self.config)
        return client.is_object_exist(bucket=self.bucket, key=key)
