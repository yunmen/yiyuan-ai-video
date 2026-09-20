# -*- coding: utf-8 -*-
'''
@文件    :oss.py
@说明    :对象存储(腾讯云 COS)客户端 — worker 侧结果转存
@时间    :2026/09/20 19:30:00
@作者    :一源AI
@版本    :1.2
@说明    :实现移植自 ai-creator(腾讯 COS,SDK 为 qcloud_cos,延迟导入)。
          region/bucket/密钥均由 app/settings.py 从 env 文件读取后传入,插件层不读配置。
'''
from pathlib import Path
from typing import Optional

from loguru import logger


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

    def _build_url(self, key: str) -> str:
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"

    def put_object(self, key: str, data: bytes) -> str:
        """上传字节流,返回可访问 URL"""
        self.client.put_object(Bucket=self.bucket, Body=data, Key=key)
        logger.info(f"腾讯 COS 字节流上传完成 object_key={key}")
        return self._build_url(key)

    def put_local_file(self, key: str, path: str) -> str:
        """上传本地文件,返回可访问 URL"""
        local_path = Path(path)
        if not local_path.is_file():
            raise FileNotFoundError("腾讯 COS 待上传本地文件不存在")
        self.client.put_object_from_local_file(
            Bucket=self.bucket,
            LocalFilePath=str(local_path),
            Key=key,
        )
        logger.info(f"腾讯 COS 本地文件上传完成 object_key={key}")
        return self._build_url(key)

    def object_exists(self, key: str) -> bool:
        """判断对象是否存在"""
        return self.client.object_exists(Bucket=self.bucket, Key=key)
