# -*- coding: utf-8 -*-
'''
@文件    :submail.py
@说明    :赛邮云通信短信模块
@时间    :2025/09/25 17:22:23
@作者    :睿
@版本    :1.0
'''

import httpx
from loguru import logger
from typing import Optional, Dict, List
from . import config


class SubMailSMS:
    def __init__(self,SecretId: Optional[str] = None, SecretKey: Optional[str] = None, SmsSdkAppId: Optional[str] = None, SignName: Optional[str] = None):
        self.SecretId = SecretId or config.SecretId
        self.SecretKey = SecretKey or config.SecretKey
        self.SmsSdkAppId = SmsSdkAppId or config.SmsSdkAppId
        self.SignName = SignName or config.SignName

    def configure(self, SecretId: Optional[str] = None, SecretKey: Optional[str] = None, SmsSdkAppId: Optional[str] = None, SignName: Optional[str] = None):
        """重新配置OSS客户端"""
        self.SecretId = SecretId or config.SecretId
        self.SecretKey = SecretKey or config.SecretKey
        self.SmsSdkAppId = SmsSdkAppId or config.SmsSdkAppId
        self.SignName = SignName or config.SignName


    def send_content(self, phone, content):
        url = "https://api-v4.mysubmail.com/sms/send"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {
            "appid": self.SecretId,
            "signature": self.SecretKey,
            "to": phone,
            "content": f"【{self.SignName}】{content}"
        }
        r = httpx.request("POST", url, headers=headers, json=data)
        logger.info(f"赛邮云发送短信结果: {r.text}")
        response = r.json()
        result = {
            "code": 0,
            "message": response.get("msg", "")
        }
        if response.get("status") == "success":
            result['code'] = 1
        return result


    def send_template(self, phone: str, template: str, vars: Optional[Dict] = None):
        url = "https://api-v4.mysubmail.com/sms/xsend"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {
            "appid": self.SecretId,
            "signature": self.SecretKey,
            "to": phone,
            "project": template,
            "vars": vars
        }
        r = httpx.request("POST", url, headers=headers, json=data)
        logger.info(f"赛邮云发送短信结果: {r.text}")
        response = r.json()
        result = {
            "code": 0,
            "message": response.get("msg", "")
        }
        if response.get("status") == "success":
            result['code'] = 1
        return result
        

    def batch_send_content(self, content: str, multi: List[Dict]):
        """
        content=【SUBMAIL】您好，@var(name)，您的取货码为 @var(code)
        multi=[{
            "to":"15*********",
            "vars":{
                "name":"kevin",
                "code":123456
            }
        }]
        """
        url = "https://api-v4.mysubmail.com/sms/multisend"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {
            "appid": self.SecretId,
            "signature": self.SecretKey,
            "content": f"【{self.SignName}】{content}",
            "multi": multi
        }
        r = httpx.request("POST", url, headers=headers, json=data)
        logger.info(f"赛邮云发送短信结果: {r.text}")
        responses = r.json()
        for response in responses:
            result = {
                "code": 0,
                "message": response.get("msg", "")
            }
            if response.get("status") == "success":
                result['code'] = 1
            return result


    def batch_send_template(self, template: str, multi: List[Dict]):
        """
        multi=[{
            "to":"15*********",
            "vars":{
                "name":"kevin",
                "code":123456
            }
        }]
        """
        url = "https://api-v4.mysubmail.com/sms/multixsend"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {
            "appid": self.SecretId,
            "signature": self.SecretKey,
            "project": template,
            "multi": multi
        }
        r = httpx.request("POST", url, headers=headers, json=data)
        logger.info(f"赛邮云发送短信结果: {r.text}")
        responses = r.json()
        for response in responses:
            result = {
                "code": 0,
                "message": response.get("msg", "")
            }
            if response.get("status") == "success":
                result['code'] = 1
            return result