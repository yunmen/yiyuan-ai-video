# -*- coding: utf-8 -*-
'''
@文件    :__init__.py
@说明    :短信
@时间    :2025/09/13 01:06:45
@作者    :睿
@版本    :1.0
'''
from typing import Dict, Union, Optional
from .aliyun import AliyunSMS
from .txyun import TencentSMS
from .submail import SubMailSMS


class SMSFactory:
    def __init__(self):
        self._services = {}
        self._init_services()

    def _init_services(self):
        """初始化所有短信服务实例"""
        self._services['aliyun'] = AliyunSMS()
        self._services['tencent'] = TencentSMS()
        self._services['submail'] = SubMailSMS()

    @property
    def aliyun(self) -> AliyunSMS:
        """阿里云短信服务"""
        return self._services['aliyun']

    @property
    def tencent(self) -> TencentSMS:
        """腾讯云短信服务"""
        return self._services['tencent']

    @property
    def submail(self) -> SubMailSMS:
        """赛邮云通信短信服务"""
        return self._services['submail']

    def configure(self, service_type: str, **config):
        """重新配置指定服务的参数"""
        service_map = {
            "aliyun": "aliyun",
            "tencent": "tencent",
            "submail": "submail",
        }
        if service_type not in service_map:
            raise ValueError(f"不支持的短信服务类型: {service_type}")
        service_name = service_map[service_type]
        self._services[service_name].configure(**config)


__all__ = ["SMSFactory"]