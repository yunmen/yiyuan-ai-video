# -*- coding: utf-8 -*-
'''
@文件    :gen_template.py
@说明    :用户工程模板(参数模板化 / 一套结构百变体)服务。
          只存「创意配置快照」,生成变体时由调用方补入新素材(materials)与覆盖项(overrides),
          经既有 create_video 链路入队 —— 复用同一套校验/计费/worker,不做旁路实现。
'''
from typing import Any, Dict, List, Optional

from tortoise.expressions import Q

from app.models.video import GenTaskTemplateModel
from app.schemas.gen_template import GenTemplateSaveSchema


def merge_template_params(
    template_params: Dict[str, Any],
    overrides: Dict[str, Any],
    materials: List[str],
    remark: Optional[str],
    allowed_fields: set,
) -> Dict[str, Any]:
    """把模板快照 + 覆盖项 + 新素材合并为生成参数;只保留 CreateSchema 合法字段,杜绝脏键污染。

    纯函数,便于契约测试,不触碰数据库 / 模型调用。
    """
    final: Dict[str, Any] = dict(template_params or {})
    final.update(overrides or {})
    final["materials"] = materials
    if remark is not None:
        final["remark"] = remark
    return {k: v for k, v in final.items() if k in allowed_fields}


class Service:
    """用户工程模板服务。"""

    async def save(self, user_id: Optional[int], data: GenTemplateSaveSchema) -> Dict[str, Any]:
        obj = await GenTaskTemplateModel.create(
            title=data.title,
            format=data.format or "",
            cover=data.cover,
            params=data.params or {},
            user_id=user_id,
        )
        return obj.to_dict()

    async def list(self, user_id: Optional[int], keyword: Optional[str], page_num: int, page_size: int):
        # 用户自己的模板(user_id 命中) + 平台公共模板(user_id 为空),二者取并集
        search = GenTaskTemplateModel.filter(deleted=False).filter(
            Q(user_id=user_id) | Q(user_id__isnull=True)
        )
        if keyword:
            search = search & GenTaskTemplateModel.filter(title__icontains=keyword)
        total = await search.count()
        objs = await search.order_by("-create_time").offset((max(1, page_num) - 1) * page_size).limit(page_size)
        return total, [o.to_dict() for o in objs]

    async def get(self, template_id: int) -> Optional[GenTaskTemplateModel]:
        return await GenTaskTemplateModel.filter(id=template_id, deleted=False).first()

    async def delete(self, template_id: int, user_id: Optional[int]) -> bool:
        obj = await self.get(template_id)
        if not obj:
            return False
        # 平台公共模板(id 为空)不允许普通用户删除
        if obj.user_id is None and user_id is not None:
            return False
        if obj.user_id is not None and user_id is not None and obj.user_id != user_id:
            return False
        obj.deleted = True
        await obj.save(update_fields=["deleted"])
        return True

    async def generate(
        self,
        template_id: int,
        user,
        materials: List[str],
        overrides: Dict[str, Any],
        remark: Optional[str],
    ) -> Dict[str, Any]:
        """按模板生成一个变体:合并参数后走既有 create_video 链路入队。"""
        from app.schemas.generate_task import CreateSchema
        # 复用既有任务服务单例(类名为 Service,模块末尾以 service=Service() 暴露),
        # 避免新建实例绕过其内部的额度/入队/状态逻辑。
        from app.services.generate_task import service as generate_service

        obj = await self.get(template_id)
        if not obj:
            raise ValueError("工程模板不存在或已删除")
        allowed = set(CreateSchema.model_fields.keys())
        final = merge_template_params(obj.params, overrides, materials, remark, allowed)
        data = CreateSchema(**final)
        return await generate_service.create(data, user=user)

    async def batch(
        self,
        template_id: int,
        user,
        variants: List[Dict[str, Any]],
        cap: int = 20,
    ) -> List[Dict[str, Any]]:
        """批量出变体(百变体):逐组入队,每组走同一校验/计费;超过 cap 的截断。"""
        items = variants[: max(1, cap)]
        results: List[Dict[str, Any]] = []
        for v in items:
            res = await self.generate(
                template_id, user, v.get("materials") or [], v.get("overrides") or {}, v.get("remark")
            )
            results.append(res)
        return results


service = Service()
