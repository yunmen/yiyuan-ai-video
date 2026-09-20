# -*- coding: utf-8 -*-
'''
@文件    :crud.py
@说明    :基础crud封装
@时间    :2025/08/27 17:56:53
@作者    :睿
@版本    :1.0
'''
from typing import Any, Dict, Generic, List, NewType, Tuple, Type, TypeVar, Union, Optional
from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.models import Model


Total = NewType("Total", int)
ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, id: int) -> Optional[ModelType]:
        return await self.model.get(id=id)

    async def count(self, search: Q = Q()) -> Total:
        return await self.model.filter(search).count()

    async def query(self, search: Q = Q(), order: list = []) -> List[ModelType]:
        return await self.model.filter(search).order_by(*order)

    async def list(self, page_num: int, page_size: int, search: Q = Q(), order: list = []) -> Tuple[Total, List[ModelType]]:
        query = self.model.filter(search)
        return await query.count(), await query.offset((page_num - 1) * page_size).limit(page_size).order_by(*order)

    async def create(self, obj_in: Union[CreateSchemaType, Dict[str, Any]]) -> ModelType:
        if isinstance(obj_in, Dict):
            kwargs = obj_in
        else:
            kwargs = obj_in.model_dump()
        obj = await self.model.create(**kwargs)
        return obj

    async def update(self, obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        if isinstance(obj_in, Dict):
            kwargs = obj_in
        else:
            kwargs = obj_in.model_dump(exclude_unset=True, exclude={"id"})
        obj = obj.update_from_dict(kwargs)
        await obj.save()
        return obj

    async def delete(self, obj: ModelType) -> None:
        await obj.delete()
