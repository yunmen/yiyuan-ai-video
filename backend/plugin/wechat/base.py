# -*- coding: utf-8 -*-
'''
@文件    :baseapi.py
@说明    :微信开发基础接口
@时间    :2024/12/19 22:26:39
@作者    :睿
@版本    :1.0
'''

import httpx
import hashlib
from typing import Optional
from loguru import logger
from . import config


class WeChatMPBaseClient:
    """微信开发基础接口"""
    def __init__(self, AppID: Optional[str] = None, AppSecret: Optional[str] = None):
        """微信公众号基本能力"""
        self.AppID = AppID or config.Offi_Account_AppID
        self.AppSecret = AppSecret or config.Offi_Account_AppSecret

    def configure(self, AppID: str, AppSecret: str):
        """重新配置公众号"""
        self.AppID = AppID
        self.AppSecret = AppSecret

    async def request(self, method, url, **kwargs):
        """httpx异步请求方法"""
        async with httpx.AsyncClient() as client:
            response  = await client.request(method, url, **kwargs)
            return response

    async def get_access_token(self):
        """
        获取接口调用凭据, 有效期为2小时。
        文档: https://developers.weixin.qq.com/doc/service/api/base/api_getaccesstoken.html
        """
        url = "https://api.weixin.qq.com/cgi-bin/token"
        payload = {
            "grant_type":"client_credential",
            "appid": self.AppID,
            "secret": self.AppSecret,
        }
        headers = {}
        response = await self.request("GET", url, headers=headers, params=payload)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()

    async def get_stable_token(self, refresh: bool = False):
        """
        获取稳定版接口调用凭据, 有效期为2小时。
        文档: https://developers.weixin.qq.com/doc/service/api/base/api_getstableaccesstoken.html
        """
        url = "https://api.weixin.qq.com/cgi-bin/stable_token"
        payload = {
            "grant_type": "client_credential",
            "appid": self.AppID,
            "secret": self.AppSecret,
            "force_refresh": refresh
        }
        headers = {}
        response = await self.request("POST", url, headers=headers, json=payload)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()
    
    async def get_jsapi_ticket(self, access_token):
        """
        获取js-sdk临时票据
        文档: https://developers.weixin.qq.com/doc/service/api/webdev/jssdk/api_getticket.html
        """
        url = "https://api.weixin.qq.com/cgi-bin/ticket/getticket"
        payload = {
            "access_token": access_token,  # 公众号的access_token
            "type":"jsapi"
        }
        headers = {}
        response = await self.request("GET", url, headers=headers, params=payload)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()
    

    def get_signature(self, noncestr, jsapi_ticket, timestamp, url):
        """
        生成调用js-sdk时候所需要的签名
        noncestr: 随机字符串
        jsapi_ticket: js-sdk的临时票据
        timestamp: 时间戳,
        url: 调用js-sdk的页面url
        文档: https://developers.weixin.qq.com/doc/service/guide/h5/jssdk.html
        """
        sortList = ["noncestr={}".format(noncestr),"jsapi_ticket={}".format(jsapi_ticket),"timestamp={}".format(timestamp),"url={}".format(url)]
        sortList.sort()
        sha1 = hashlib.sha1()
        sha1.update("&".join(sortList).encode("utf8"))
        signature = sha1.hexdigest()
        return signature
    


class WechatMessageBaseClient:
    """
    微信公众号聊天能力
    文档: https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Receiving_standard_messages.html
    """
    def __init__(self, AppID: Optional[str] = None, AppSecret: Optional[str] = None, Token: Optional[str] = None, EncodingAESKey: Optional[str] = None, CryptModel: Optional[str] = None):
        self.AppID = AppID or config.Offi_Account_AppID # AppID 从设置与开发->开发接口管理->账号开发信息中获取
        self.AppSecret = AppSecret or config.Mini_Program_AppSecret # AppSecret 从设置与开发->开发接口管理->账号开发信息中获取
        self.Token = Token or config.Offi_Account_Token  # Token 从设置与开发->开发接口管理->服务器配置中获取
        self.EncodingAESKey = EncodingAESKey or config.Offi_Account_EncodingAESKey  # EncodingAESKey 从设置与开发->开发接口管理->服务器配置中获取
        self.CryptModel = CryptModel or config.Offi_Account_CryptModel  # 消息加密模式, plaintext/ciphertext

    def configure(self, AppID: str, AppSecret: str, Token: str, EncodingAESKey: str, CryptModel: str):
        """重新配置公众号"""
        self.AppID = AppID
        self.AppSecret = AppSecret
        self.Token = Token
        self.EncodingAESKey = EncodingAESKey
        self.CryptModel = CryptModel