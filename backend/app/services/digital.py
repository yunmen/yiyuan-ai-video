# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :数字人Service
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.digital import crud, Total
from app.schemas.digital import QuerySchema, CreateSchema, UpdateSchema, UserCreateSchema

DEFAULT_ORDER = ["-sort", "-create_time"]


def resolve_pose_variant(variants, pose: Optional[str]) -> Optional[Dict]:
    """按名称取派生视图;未指定或未命中时返回 None(用主视图)。

    主视图派生:派生视图只换姿势/景别,不换人 —— 生成时仍以主图作 reference,
    避免「换个姿势就变脸」。命中不了就安静回退主视图,不报错阻断生成。
    """
    if not pose or not isinstance(variants, list):
        return None
    target = str(pose).strip()
    for item in variants:
        if isinstance(item, dict) and str(item.get("name") or "").strip() == target:
            return item
    return None


class Service:
    async def list(self, payload: QuerySchema, only_active: bool = False) -> Tuple[Total, List[Dict]]:
        """数字人列表。

        only_active=True 供用户端使用:强制只返回已上架数据,避免下架数字人仍出现在
        用户可选列表中(管理端传 False,可查看全部并按下架状态筛选)。
        """
        search = Q()
        if payload.keyword:
            # tags 是 JSONField,不支持 icontains(会抛 Unknown filter param → 接口 500),
            # 关键词只匹配名称与简介。
            search &= Q(name__icontains=payload.keyword) | Q(desc__icontains=payload.keyword)
        if payload.gender:
            search &= Q(gender=payload.gender)
        if only_active:
            search &= Q(active=True)
            # 平台列表只展示平台数字人(user_id 为空);用户专属数字人(user_id 非空)不对外公开,
            # 仅本人可在「我的形象」中查看与使用,避免私密形象泄漏到公共列表。
            search &= Q(user_id__isnull=True)
        elif payload.active is not None:
            search &= Q(active=payload.active)
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=DEFAULT_ORDER)
        return total, [obj.to_dict() for obj in objs]

    async def detail(self, id: int, only_active: bool = False, user=None) -> Optional[Dict]:
        """数字人详情;only_active=True 供用户端使用,已下架数字人视为不存在。

        user 用于专属形象隔离:专属数字人(user_id 非空)仅本人可查看,匿名或他人查看
        一律视为不存在,避免私密形象被 id 枚举泄漏基础信息(名称/形象图)。
        """
        obj = await crud.get_by_id(id)
        if not obj or (only_active and not obj.active):
            raise HTTPException(status_code=200, detail="数字人不存在")
        owner = getattr(obj, "user_id", None)
        if owner and (not user or user.id != owner):
            raise HTTPException(status_code=200, detail="数字人不存在")
        return obj.to_dict()

    async def create(self, data: CreateSchema) -> Dict:
        obj = await crud.create(data)
        return obj.to_dict()

    async def update(self, data: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        obj = await crud.update(obj, data.model_dump(exclude={"id"}))
        return obj.to_dict()

    async def active(self, id: int) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        obj = await crud.update(obj, {"active": not obj.active})
        return obj.to_dict()

    async def delete(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        await crud.delete(obj)

    async def create_personal(self, data: UserCreateSchema, user_id: int) -> Dict:
        """创建用户专属数字人(用户自助上传形象)。

        归属当前用户,自动上架(active=True)、排序 0;模型留空由全局 gen.digital_model 提供,
        不允许用户自选模型;标签/派生视图/预览视频等由运营侧维护,用户侧不开放(从入参剔除)。
        """
        payload = data.model_dump()
        payload["user_id"] = user_id
        payload["active"] = True
        payload["sort"] = 0
        for key in ("model", "tags", "pose_variants", "preview_video"):
            payload.pop(key, None)
        obj = await crud.create(payload)
        return obj.to_dict()

    async def list_personal(self, user_id: int) -> List[Dict]:
        """当前用户的专属数字人列表(含下架,用户自己能看到创建过的所有形象)"""
        objs = await crud.query(search=Q(user_id=user_id), order=DEFAULT_ORDER)
        return [obj.to_dict() for obj in objs]

    async def delete_personal(self, id: int, user_id: int) -> None:
        """删除用户专属数字人:仅限本人,越权删除或无主记录一律拒绝。

        删除走既有 crud.delete(与后台数字人删除一致);已生成的口播视频资产
        独立于数字人记录,不受影响。
        """
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数字人不存在")
        if getattr(obj, "user_id", None) != user_id:
            raise HTTPException(status_code=200, detail="只能删除自己的专属形象")
        await crud.delete(obj)

    async def assert_usable(self, digital, user) -> None:
        """专属数字人归属校验:平台数字人(user_id 为空)任何人可用;
        专属数字人仅本人可用,越权使用时明确拦截。
        """
        owner = getattr(digital, "user_id", None)
        if owner and (not user or user.id != owner):
            raise HTTPException(status_code=200, detail="该专属数字人不属于当前账号,无法使用")


service = Service()
