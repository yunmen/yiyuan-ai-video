# -*- coding: utf-8 -*-
'''
@文件    :config.py
@说明    :微信公众号/小程序配置:凭据统一从 Settings(环境变量/环境文件)读取,禁止在源码写死。
@时间    :2024/12/19 22:26:39
@作者    :睿
@版本    :2.0
'''
from app.settings import config as _settings

# 微信公众号(服务号/订阅号)凭据:缺失时为空串,由调用方在使用微信接口前暴露明确错误,
# 不再内置任何明文默认值(消除硬编码凭据泄露风险)。
# 配置项定义见 backend/app/settings.py 的 WECHAT_OFFI_* / WECHAT_MINI_*。
Offi_Account_AppID = _settings.WECHAT_OFFI_APPID
Offi_Account_AppSecret = _settings.WECHAT_OFFI_APPSECRET
Offi_Account_Token = _settings.WECHAT_OFFI_TOKEN
Offi_Account_EncodingAESKey = _settings.WECHAT_OFFI_ENCODING_AES_KEY
Offi_Account_CryptModel = _settings.WECHAT_OFFI_CRYPT_MODEL

# 小程序凭据
Mini_Program_AppID = _settings.WECHAT_MINI_APPID
Mini_Program_AppSecret = _settings.WECHAT_MINI_APPSECRET


oplatform = None
