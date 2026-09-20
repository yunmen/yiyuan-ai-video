import json
from datetime import datetime, timedelta
from tortoise.transactions import atomic
from app.schemas.system.user import AccountLoginSchema
from app.services.system.user import service as system_user_service
from app.enums.base import LoginTypeEnum


@atomic()
async def admin_login_by_password(payload: AccountLoginSchema) -> str:
    """账号密码登录"""
    obj = await system_user_service.get(account=payload.account)
    obj = await system_user_service.authenticate(obj, input_password=payload.password)
    await system_user_service.update_login_data(obj, payload.client_ip, LoginTypeEnum.PASSWORD)
    token = await system_user_service.generate_token(obj)
    data = {
        "info": {
            "phone": obj.account,
            "nickname": obj.nickname,
            "avatar": obj.avatar,
        },
        "token": token
    }
    return data
