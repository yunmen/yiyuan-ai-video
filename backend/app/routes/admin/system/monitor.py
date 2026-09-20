# -*- coding: utf-8 -*-
'''
@文件    :task.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from fastapi import APIRouter, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationAdminToken, AdminPermissionChecker
from app.services.system.monitor import service
from app.core.response import Success, Fail


router = APIRouter(route_class=OperationLogRoute, dependencies=[DeepValidationAdminToken])


@router.post("/detail",summary="获取系统详细信息", dependencies=[Depends(AdminPermissionChecker("system:monitor:detail"))])
async def task_detail():
    result = await service.detail()
    return Success(data=result)

