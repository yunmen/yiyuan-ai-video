# -*- coding: utf-8 -*-
'''
@文件    :task.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from tortoise.transactions import atomic
from fastapi.exceptions import HTTPException
from app.cruds.system.task import crud, Total
from app.schemas.system.task import QuerySchema, CreateSchema, UpdateSchema
from app.core.plugin import scheduler, logger


class Service:

    async def all(self, payload: QuerySchema) -> List[Dict]:
        search = Q()
        if payload.active is not None:
            search &= Q(active=payload.active)
        order = ["-create_time"]
        objs = await crud.query(search=search, order=order)
        result = []
        for obj in objs:
            item = obj.to_dict()
            result.append(item)
        return result

    async def create(self, data: CreateSchema) -> Dict:
        obj =  await crud.create(data)
        job = scheduler.add_job(task_id=f"task_{obj.id}", task_name=obj.name, task_trigger=obj.trigger, trigger_args=obj.trigger_args, func_path=obj.func, func_args=obj.args, func_kwargs=obj.kwargs, start_time=obj.start_date, end_time=obj.end_date, executor=obj.executor, jobstore=obj.jobstore)
        if not obj.active:
            job.pause()
        return obj.to_dict()
    
    async def update(self, data: UpdateSchema) -> Optional[Dict]:
        obj = await crud.get_by_id(data.id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        data_dict = data.model_dump(exclude={'id'})
        obj = await crud.update(obj, data_dict)
        job = scheduler.modify_job(task_id=f"task_{obj.id}", task_name=obj.name, task_trigger=obj.trigger, trigger_args=obj.trigger_args, func_path=obj.func, func_args=obj.args, func_kwargs=obj.kwargs, start_time=obj.start_date, end_time=obj.end_date, executor=obj.executor, jobstore=obj.jobstore)
        if not obj.active:
            job.pause()
        return obj.to_dict()

    @atomic()
    async def active(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        obj = await crud.update(obj, {
            "active": not obj.active
        })
        if obj.active:
            scheduler.resume_job(f"task_{obj.id}")
        else:
            scheduler.pause_job(f"task_{obj.id}")
    
    async def delete(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        await crud.delete(obj)
        scheduler.remove_job(f"task_{obj.id}")

    async def run(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="数据不存在")
        if not obj.active:
            obj = await crud.update(obj, {
                "active": not obj.active
            })
            scheduler.resume_job(f"task_{obj.id}")
        scheduler.run_job(f"task_{obj.id}")

    async def init_task(self):
        objs = await crud.query()
        for obj in objs:
            job = scheduler.add_job(task_id=f"task_{obj.id}", task_name=obj.name, task_trigger=obj.trigger, trigger_args=obj.trigger_args, func_path=obj.func, func_args=obj.args, func_kwargs=obj.kwargs, start_time=obj.start_date, end_time=obj.end_date, executor=obj.executor, jobstore=obj.jobstore)
            if not obj.active:
                job.pause()
                
service = Service()