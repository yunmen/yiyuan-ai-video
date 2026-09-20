# -*- coding: utf-8 -*-
'''
@文件    :sms.py
@说明    :短信服务(short message service)
@时间    :2024/12/12 14:18:31
@作者    :睿
@版本    :1.0
'''
import json
from typing import List, Optional, Dict
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models
from . import config


class TencentSMS:
    def __init__(self,SecretId: Optional[str] = None, SecretKey: Optional[str] = None, SmsSdkAppId: Optional[str] = None, SignName: Optional[str] = None):
        self.SecretId = SecretId or config.SecretId
        self.SecretKey = SecretKey or config.SecretKey
        self.SmsSdkAppId = SmsSdkAppId or config.SmsSdkAppId
        self.SignName = SignName or config.SignName

    def configure(self, SecretId: Optional[str] = None, SecretKey: Optional[str] = None, SmsSdkAppId: Optional[str] = None, SignName: Optional[str] = None):
        """重新配置OSS客户端"""
        self.SecretId = SecretId
        self.SecretKey = SecretKey
        self.SmsSdkAppId = SmsSdkAppId
        self.SignName = SignName

    def get_client(self):
        cred = credential.Credential(self.SecretId, self.SecretKey)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "sms.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        region = "ap-beijing"
        client = sms_client.SmsClient(cred, region, clientProfile)
        return client
    
    def send_template(self,phone: str, template: str, vars: Dict):
        """
        发送短信
        响应格式:{"SendStatusSet": [{"SerialNo": "3363:140938803417349340998207606", "PhoneNumber": "+8618202876063", "Fee": 1, "SessionContext": "", "Code": "Ok", "Message": "send success", "IsoCode": "CN"}], "RequestId": "c51c04ac-8af2-44aa-8d28-72309aa7e6af"}
        """
        client = self.get_client()
        req = models.SendSmsRequest()
        params = {
            "SmsSdkAppId": self.SmsSdkAppId,
            "SignName": self.SignName,
            "TemplateId": template,
            "PhoneNumberSet": [phone],
            "TemplateParamSet": [vars]
        }
        req.from_json_string(json.dumps(params))
        resp = client.SendSms(req)
        response = json.loads(resp.to_json_string())
        SendStatusSet = response.get("SendStatusSet", [])
        for SendStatus in SendStatusSet:
            result = {
                "code": 0,
                "message": SendStatus.get("Message", "")
            }
            if SendStatus.get("Code") == "Ok":
                result['code'] = 1
            return result

    def batch_send_template(self,template: str, multi: List[Dict]):
        """
        批量发送短信
        multi = [{"phone":"","vars":{}}]
        响应格式:{"SendStatusSet": [{"SerialNo": "3363:140938803417349340998207606", "PhoneNumber": "+8618202876063", "Fee": 1, "SessionContext": "", "Code": "Ok", "Message": "send success", "IsoCode": "CN"}], "RequestId": "c51c04ac-8af2-44aa-8d28-72309aa7e6af"}
        """
        phone_list = [item['phone'] for item in multi]
        param_list = [item['vars'] for item in multi]
        client = self.get_client()
        req = models.SendSmsRequest()
        params = {
            "SmsSdkAppId": self.SmsSdkAppId,
            "SignName": self.SignName,
            "TemplateId": template,
            "PhoneNumberSet": phone_list,
            "TemplateParamSet": param_list
        }
        req.from_json_string(json.dumps(params))
        resp = client.SendSms(req)
        response = json.loads(resp.to_json_string())
        SendStatusSet = response.get("SendStatusSet", [])
        for SendStatus in SendStatusSet:
            result = {
                "code": 0,
                "message": SendStatus.get("Message", "")
            }
            if SendStatus.get("Code") == "Ok":
                result['code'] = 1
            return result