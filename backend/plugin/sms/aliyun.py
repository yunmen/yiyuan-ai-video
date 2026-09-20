# -*- coding: utf-8 -*-
'''
@文件    :sms.py
@说明    :短信服务(short message service)
@时间    :2024/12/12 14:18:31
@作者    :睿
@版本    :1.0
'''
from typing import List, Optional, Dict
from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
from . import config


class AliyunSMS:
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

    def get_client(self) -> Dysmsapi20170525Client:
        """
        使用凭据初始化账号Client
        @return: Client
        @throws Exception
        """
        # 工程代码建议使用更安全的无AK方式，凭据配置方式请参见：https://help.aliyun.com/document_detail/378659.html。
        config = open_api_models.Config(
            access_key_id=self.SecretId,
            access_key_secret=self.SecretKey
        )
        # Endpoint 请参考 https://api.aliyun.com/product/Dysmsapi
        config.endpoint = 'dysmsapi.aliyuncs.com'
        client = Dysmsapi20170525Client(config)
        return client
    
    def send_template(self, phone: str, template: str, vars: Dict):
        """
        发送短信
        响应格式:{"SendStatusSet": [{"SerialNo": "3363:140938803417349340998207606", "PhoneNumber": "+8618202876063", "Fee": 1, "SessionContext": "", "Code": "Ok", "Message": "send success", "IsoCode": "CN"}], "RequestId": "c51c04ac-8af2-44aa-8d28-72309aa7e6af"}
        """
        client = self.get_client()
        send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
            sign_name=self.SignName,
            phone_numbers=phone,
            template_code=template,
            template_param=str(vars)
        )
        runtime = util_models.RuntimeOptions()
        response = client.send_sms_with_options(send_sms_request, runtime)
        result = {
            "code": 0,
            "message": response.body.message
        }
        if response.body.code == "OK":
            result['code'] = 1
        return result



    def batch_send_template(self, template: str, multi: List[Dict]):
        """
        批量发送短信
        multi = [{"phone":"","vars":{}}]
        """
        sign_list = [self.SignName] * len(multi)
        phone_list = [item['phone'] for item in multi]
        param_list = [item['vars'] for item in multi]
        client = self.get_client()
        send_sms_request = dysmsapi_20170525_models.SendBatchSmsRequest(
            sign_name_json=str(sign_list),
            phone_number_json=str(phone_list),
            template_code=template,
            template_param_json=str(param_list)
        )
        runtime = util_models.RuntimeOptions()
        response = client.send_batch_sms_with_options(send_sms_request, runtime)
        result = {
            "code": 0,
            "message": response.body.message
        }
        if response.body.code == "OK":
            result['code'] = 1
        return result