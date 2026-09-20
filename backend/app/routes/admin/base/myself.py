# -*- coding: utf-8 -*-
'''
@文件    :myself.py
@说明    :
@时间    :2025/08/08 02:07:08
@作者    :睿
@版本    :1.0
'''
from fastapi import APIRouter
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken
from app.core.response import Success, Fail
from app.services.system.user import service as user_service
from app.services.system.menu import service as menu_service
from app.schemas.system.user import EditSchema, RepwdSchema
from app.core.plugin import ctx


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.get("/info",summary="获取用户资料")
async def myself_info():
    g = ctx.get("g")
    obj = await user_service.get(id=g.id)
    data = obj.to_dict(exclude=["password"])
    return Success(data=data)


@router.get("/menus",summary="获取用户菜单权限")
async def myself_menus():
    g = ctx.get("g")
    if g.superuser:
        result = await menu_service.get_superuser_menus()
    else:
        result = await user_service.get_user_menus(g.id)
    return Success(data=result)


@router.post("/repwd",summary="修改密码")
async def myself_repwd(
    payload: RepwdSchema
):
    g = ctx.get("g")
    await user_service.reset_myself_pwd(g.id, payload)
    return Success()


@router.post("/edit",summary="修改资料")
async def myself_edit(
    payload: EditSchema
):
    g = ctx.get("g")
    result = await user_service.update_myself_data(g.id, payload)
    return Success(data=result)