# -*- coding: utf-8 -*-
'''
@文件    :sms.py
@说明    :短信验证码工具(验证码生成/Redis 存储/限流/渠道发送)
          渠道:mock=仅写日志不发短信(开发自测) tencent=腾讯云短信(需配置 SecretId/SecretKey/SDKAppID/签名/模板ID)
@时间    :2026/09/20 18:00:00
@作者    :一源AI
@版本    :1.1
'''
import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi.exceptions import HTTPException

from app.core.plugin import redis, logger
from app.settings import config

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
CODE_LEN = 6


def validate_phone(phone: str) -> str:
    phone = (phone or "").strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=200, detail="手机号格式不正确")
    return phone


def _key_code(phone: str) -> str:
    return f"{config.REDIS_PREFIX_NAME}:sms:code:{phone}"


def _key_interval(phone: str) -> str:
    return f"{config.REDIS_PREFIX_NAME}:sms:interval:{phone}"


def _key_day_limit(phone: str) -> str:
    day = datetime.now().strftime("%Y%m%d")
    return f"{config.REDIS_PREFIX_NAME}:sms:limit:{phone}:{day}"


def _seconds_until_midnight() -> int:
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - datetime.now()).total_seconds()))


def _generate_code() -> str:
    return "".join(random.choices("0123456789", k=CODE_LEN))


def _tencent_send(phone: str, code: str) -> None:
    """腾讯云短信下发(同步 SDK,需放在线程里执行避免阻塞事件循环)"""
    from tencentcloud.common import credential
    from tencentcloud.sms.v20210111 import sms_client, models

    cred = credential.Credential(config.SMS_ACCESS_KEY_ID, config.SMS_ACCESS_KEY_SECRET)
    client = sms_client.SmsClient(cred, config.SMS_REGION or "ap-guangzhou")
    request = models.SendSmsRequest()
    request.SmsSdkAppId = config.SMS_SDK_APP_ID
    request.SignName = config.SMS_SIGN_NAME
    request.TemplateId = config.SMS_TEMPLATE_ID
    request.TemplateParamSet = [code]
    request.PhoneNumberSet = [f"+86{phone}"]
    response = client.SendSms(request)
    status_list = getattr(response, "SendStatusSet", None) or []
    if not status_list:
        raise RuntimeError("腾讯云短信未返回发送状态")
    status = status_list[0]
    if getattr(status, "Code", "") != "Ok":
        raise RuntimeError(f"{getattr(status, 'Code', '')}:{getattr(status, 'Message', '')}")


async def _send_by_provider(phone: str, code: str) -> None:
    """按配置渠道下发短信;真实渠道未配置齐全时直接报错(不允许静默降级,避免验证码泄漏到日志)"""
    provider = (config.SMS_PROVIDER or "mock").lower()
    if provider == "mock":
        logger.info(f"[SMS-MOCK] phone={phone} code={code} (未真实发送)")
        return
    if provider == "tencent":
        missing = [
            name for name, value in (
                ("SMS_ACCESS_KEY_ID", config.SMS_ACCESS_KEY_ID),
                ("SMS_ACCESS_KEY_SECRET", config.SMS_ACCESS_KEY_SECRET),
                ("SMS_SDK_APP_ID", config.SMS_SDK_APP_ID),
                ("SMS_SIGN_NAME", config.SMS_SIGN_NAME),
                ("SMS_TEMPLATE_ID", config.SMS_TEMPLATE_ID),
            ) if not value
        ]
        if missing:
            raise HTTPException(status_code=200, detail=f"短信渠道配置缺失:{','.join(missing)}")
        try:
            await asyncio.to_thread(_tencent_send, phone, code)
        except ImportError:
            raise HTTPException(status_code=200, detail="未安装腾讯云短信 SDK:tencentcloud-sdk-python-sms")
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(f"腾讯云短信发送失败 phone={phone}: {exc}")
            raise HTTPException(status_code=200, detail=f"短信发送失败:{exc}")
        return
    raise HTTPException(status_code=200, detail=f"不支持的短信渠道:{provider}")


async def send_code(phone: str) -> Dict:
    """发送登录/注册验证码(60s 重发间隔 + 每日上限 + 5 分钟有效)"""
    phone = validate_phone(phone)

    if await redis.get(_key_interval(phone)):
        raise HTTPException(status_code=200, detail=f"发送过于频繁,请 {config.SMS_CODE_INTERVAL} 秒后再试")

    used = int(await redis.get(_key_day_limit(phone)) or 0)
    if used >= config.SMS_DAY_LIMIT:
        raise HTTPException(status_code=200, detail="今日验证码发送已达上限,请明天再试")

    code = _generate_code()
    await _send_by_provider(phone, code)

    await redis.set(_key_code(phone), code, ex=config.SMS_CODE_EXPIRE)
    await redis.set(_key_interval(phone), "1", ex=config.SMS_CODE_INTERVAL)
    await redis.set(_key_day_limit(phone), str(used + 1), ex=_seconds_until_midnight())

    result = {"phone": phone, "expire": config.SMS_CODE_EXPIRE, "interval": config.SMS_CODE_INTERVAL}
    # 开发环境 mock 渠道可直接回显验证码,方便联调(生产务必关闭)
    if provider_is_mock() and config.SMS_DEV_RETURN_CODE:
        result["code"] = code
    return result


def provider_is_mock() -> bool:
    return (config.SMS_PROVIDER or "mock").lower() == "mock"


async def verify_code(phone: str, code: str) -> None:
    """校验验证码:通过后立即失效(一次性)"""
    phone = validate_phone(phone)
    saved = await redis.get(_key_code(phone))
    if not saved:
        raise HTTPException(status_code=200, detail="验证码已过期,请重新获取")
    if saved != (code or "").strip():
        raise HTTPException(status_code=200, detail="验证码错误")
    await redis.delete(_key_code(phone))


async def remain_seconds(phone: str) -> Optional[int]:
    """重发冷却剩余秒数(供前端提示)"""
    saved = await redis.get(_key_interval(phone))
    if not saved:
        return None
    return config.SMS_CODE_INTERVAL
