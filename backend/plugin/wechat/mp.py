# -*- coding: utf-8 -*-
'''
@文件    :offiaccount.py
@说明    :微信公众号
@时间    :2024/12/19 22:26:39
@作者    :睿
@版本    :1.0
'''

import json
import urllib.parse
from typing import Optional
from loguru import logger
from typing import Dict
from .base import WeChatMPBaseClient


class WechatMPClient(WeChatMPBaseClient):
    """微信公众号能力接口"""
    async def menu_create(self, access_token: str, data: Dict):
        """
        创建自定义菜单
        该接口用于创建公众号/服务号的自定义菜单。
        文档: https://developers.weixin.qq.com/doc/service/api/custommenu/api_createcustommenu.html
        """
        url = "https://api.weixin.qq.com/cgi-bin/menu/create"
        params = {
            "access_token":access_token
        }
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        response = await self.request("POST", url, headers=headers, data=payload, params=params)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()


    async def message_template_send(self, access_token, openId, template_id, data):
        """
        发送模板消息
        文档: https://developers.weixin.qq.com/doc/service/api/notify/template/api_sendtemplatemessage.html
        """
        url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
        params = {
            "access_token": access_token
        }
        payload = json.dumps({
            "touser": openId,
            "template_id": template_id,     
            "data": data
        })
        headers = {'Content-Type': 'application/json'}
        response = await self.request("POST", url, headers=headers, data=payload, params=params)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()
    

    async def qrcode_create(self, access_token, content, pattern: str="permanent", mold: str = "str",expire: int|None = None):
        """
        生成带参数的二维码
        文档: https://developers.weixin.qq.com/doc/service/api/qrcode/qrcodes/api_createqrcode.html
        """
        url = "https://api.weixin.qq.com/cgi-bin/qrcode/create"
        params = {
            "access_token":access_token
        }
        if pattern == "temporary": # 临时二维码
            if mold == "int":
                action_name = "QR_SCENE"
                scene = {"scene_id":content}
            else:
                action_name = "QR_STR_SCENE"
                scene = {"scene_str":str(content)}
        else:      # 永久二维码
            if mold == "int":
                action_name = "QR_LIMIT_SCENE"
                scene = {"scene_id":content}
            else:
                action_name = "QR_LIMIT_STR_SCENE"
                scene = {"scene_str":str(content)}
        data = {
            "action_name": action_name,
            "action_info": {
                "scene": scene
            }
        }
        if expire:
            data["expire_seconds"] = expire
        payload = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        response = await self.request("POST", url, headers=headers, data=payload, params=params)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()

    def get_authorize_code(self, redirect_uri, scope: str = "snsapi_base", state = None):
        """
        构建用户授权url
        通过用户访问此url获取用户code
        scope: snsapi_base / snsapi_userinfo 
        """
        redirect_uri = urllib.parse.quote(redirect_uri)
        authorize_url = f"https://open.weixin.qq.com/connect/oauth2/authorize?appid={self.AppID}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
        if state:
            authorize_url += f"&state={state}"
        authorize_url += "#wechat_redirect"
        return authorize_url

    async def get_user_access_token(self, code):
        """
        换取用户授权凭证
        文档: https://developers.weixin.qq.com/doc/service/api/webdev/access/api_snsaccesstoken.html
        """
        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        payload = {
            "grant_type": "authorization_code",
            "appid": self.AppID,
            "secret": self.AppSecret,
            "code": code
        }
        headers = {}
        response = await self.request("GET", url, headers=headers, params=payload)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()


    async def get_user_info(self,access_token, openid):
        """
        获取已授权用户的基本信息
        文档: https://developers.weixin.qq.com/doc/service/api/webdev/access/api_snsuserinfo.html
        """
        url = "https://api.weixin.qq.com/sns/userinfo"
        params = {
            "access_token": access_token,  # 用户的access_token
            "openid": openid,
            "lang": "zh_CN"
        }
        response = await self.request("GET", url, params=params)
        logger.info(f"公众号请求结果:{response.text}")
        return response.json()
