# -*- coding: utf-8 -*-
'''
@文件    :gen_template.py
@说明    :用户工程模板(参数模板化 / 一套结构百变体)接口。
          前缀 /user/v1/task/template,与 /user/v1/template(平台售卖模板)互不冲突。
'''
from fastapi import APIRouter, Depends
from app.core.routeclass import OperationLogRoute
from app.core.dependencies import DeepValidationUserToken
from app.schemas.gen_template import (
    GenTemplateBatchSchema,
    GenTemplateGenerateSchema,
    GenTemplateIdSchema,
    GenTemplateQuerySchema,
    GenTemplateSaveSchema,
)
from app.services.gen_template import service
from app.core.response import Success

logger = __name__

router = APIRouter(route_class=OperationLogRoute)


@router.post("/save", summary="保存工程模板(参数模板化)")
async def template_save(payload: GenTemplateSaveSchema, g=Depends(DeepValidationUserToken)):
    """保存当前创意配置为模板;只存配置快照,不存素材。"""
    data = await service.save(g.id if g else None, payload)
    return Success(data=data)


@router.post("/list", summary="我的工程模板")
async def template_list(payload: GenTemplateQuerySchema, g=Depends(DeepValidationUserToken)):
    """列出我的模板 + 平台公共模板(按标题可搜)。"""
    total, items = await service.list(
        g.id if g else None, payload.keyword, payload.pageNum, payload.pageSize
    )
    return Success(data={"total": total, "list": items})


@router.post("/delete", summary="删除工程模板")
async def template_delete(payload: GenTemplateIdSchema, g=Depends(DeepValidationUserToken)):
    ok = await service.delete(payload.id, g.id if g else None)
    return Success(data={"ok": ok})


@router.post("/generate", summary="按工程模板生成单个变体")
async def template_generate(payload: GenTemplateGenerateSchema, g=Depends(DeepValidationUserToken)):
    """换素材 + 可选覆盖项,复用模板结构出一片成片。"""
    data = await service.generate(
        payload.template_id, g, payload.materials, payload.overrides, payload.remark
    )
    return Success(data=data)


@router.post("/batch", summary="按工程模板批量出变体(百变体)")
async def template_batch(payload: GenTemplateBatchSchema, g=Depends(DeepValidationUserToken)):
    """一次下发多组变体(换主播/排名/语言/画幅),逐组入队;超 20 组截断。"""
    results = await service.batch(payload.template_id, g, [v.model_dump() for v in payload.variants])
    return Success(data={"count": len(results), "list": results})
