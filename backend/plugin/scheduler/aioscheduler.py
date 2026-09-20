# -*- coding: utf-8 -*-
'''
@文件    :aioscheduler.py
@说明    :
@时间    :2025/08/25 17:10:16
@作者    :睿
@版本    :1.0
'''

import importlib
from loguru import logger
from datetime import datetime, timedelta
from typing import Callable, Union, List, Dict, Tuple
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from asyncio import iscoroutinefunction


class AIOScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def configure(self):
        """配置任务调度器"""
        jobstores = { # 储存器
            'default': MemoryJobStore(),
            'memory': MemoryJobStore()
        }
        executors = { # 执行器
            'default': AsyncIOExecutor(),     # 默认
            'asyncio': AsyncIOExecutor(),       # 协程
            'thread': ThreadPoolExecutor(),     # 线程
            'process': ProcessPoolExecutor()    # 进程
        }     
        job_defaults = {
            'misfire_grace_time': None,
            'coalesce': True,  # 是否合并执行
            'max_instances': 3,  # 最大实例数
        }
        timezone = 'Asia/Shanghai'
        self.scheduler.configure(
            jobstores=jobstores, 
            executors=executors, 
            job_defaults=job_defaults,
            timezone=timezone
        )
    
    def add_listener(self, listener: Callable) -> None:
        self.scheduler.add_listener(listener, EVENT_JOB_ERROR | EVENT_JOB_MISSED | EVENT_JOB_EXECUTED)
    
    def add_jobstore(self, jobstore: str, config: Union[dict, None] = None):
        """添加任务储存器"""
        if jobstore == "redis":
            config['jobs_key'] = 'apscheduler:jobs'
            config['run_times_key'] = 'apscheduler:run_times'
            self.scheduler.add_jobstore(RedisJobStore(**config), alias=jobstore)
    
    def add_executor(self, executor: str):
        """添加执行器"""
        if executor == "asyncio":
            self.scheduler.add_executor(AsyncIOExecutor, alias=executor)

    def add_job(self, task_id: str, task_name: str, task_trigger: str, trigger_args: str, func_path: str, func_args: Union[List, None] = None, func_kwargs: Union[Dict, None] = None, start_time: Union[str, None, datetime] = None, end_time: Union[str, None, datetime] = None, executor: str = None, jobstore: str = None) -> Union[None, Job]:
        """添加任务"""
        trigger = self.load_trigger(task_trigger, trigger_args, start_time, end_time)
        job = self.scheduler.add_job(id=task_id, name=task_name, func=self.load_function(func_path), args=func_args, kwargs=func_kwargs, trigger=trigger, executor=executor, jobstore=jobstore)
        return job
    
    def remove_job(self, job_id: str):
        """移除任务"""
        job = self.get_job(job_id)
        if job:
            self.scheduler.remove_job(job.id)

    
    def modify_job(self, task_id: str, task_name: str, task_trigger: str, trigger_args: str, func_path: str, func_args: List = [], func_kwargs: Dict = {}, start_time: Union[str, None, datetime] = None, end_time: Union[str, None, datetime] = None, executor: str = None, jobstore: str = None) -> Union[None, Job]:
        """修改任务"""
        job = self.get_job(task_id)
        if job:
            trigger = self.load_trigger(task_trigger, trigger_args, start_time, end_time)
            job = self.scheduler.modify_job(job_id=task_id, name=task_name, func=self.load_function(func_path), args=func_args, kwargs=func_kwargs, trigger=trigger, executor=executor, jobstore=jobstore)
            return job
        else:
            raise ValueError(f"Task with ID {task_id} does not exist.")

    def get_job(self, job_id: str) -> Union[None, Job]:
        """获取任务"""
        job = self.scheduler.get_job(job_id)
        return job
    
    def run_job(self, job_id: str):
        """运行任务"""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now()+timedelta(seconds=2))
        else:
            raise ValueError(f"Task with ID {job_id} does not exist.")
    
    def pause_job(self, job_id: str):
        """暂停任务"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.pause_job(job_id)
        else:
            raise ValueError(f"Task with ID {job_id} does not exist.")

    def resume_job(self, job_id: str):
        """恢复任务"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.resume_job(job_id)
        else:
            raise ValueError(f"Task with ID {job_id} does not exist.")
    
    def reschedule_job(self, job_id: str):
        """重启任务"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.reschedule_job(job_id)
        else:
            raise ValueError(f"Task with ID {job_id} does not exist.")

    def get_jobs(self) -> Union[None, List[Job]]:
        """获取任务"""
        jobs = self.scheduler.get_jobs()
        return jobs

    def remove_jobs(self):
        """移除所有任务"""
        self.scheduler.remove_all_jobs()

    def start(self):
        """启动定时任务"""
        self.scheduler.start()
        
    def shutdown(self):
        """关闭定时任务"""
        self.scheduler.shutdown(wait=True)

    @staticmethod
    def load_function(func_path: str) -> Callable:
        """
        根据字符串路径动态加载函数
        :param func_path: 函数路径（如 "app.tasks.testfunc"）
        :return: 可调用函数对象
        :raises: ImportError（模块不存在）、AttributeError（函数不存在）
        """
        try:
            # 分割模块路径和函数名（最后一部分是函数名）
            module_path, func_name = func_path.rsplit(".", 1)
            # 导入模块
            module = importlib.import_module(module_path)
            # 获取函数对象
            func = getattr(module, func_name)
            # 验证是否为可调用对象
            if not callable(func):
                raise ValueError(f"{func_path} 不是可调用对象")
            return func
        except (ValueError, ImportError, AttributeError) as e:
            raise RuntimeError(f"加载函数 {func_path} 失败: {str(e)}") from e

    @staticmethod
    def load_trigger(trigger_type: str, trigger_args: str, start_time: Union[None, str, datetime] = None, end_time: Union[None, str, datetime] = None) -> BaseTrigger:
        """
        根据触发器类型和参数返回触发器对象
        :param trigger: 触发器类型，如 "date"、"interval"、"cron"等
        :param args: 触发器参数，以逗号分隔的字符串形式传递
        :return: 触发器对象
        :raises: ValueError（无效的触发器类型或参数）
        """
        if trigger_type == "date":
            trigger = DateTrigger(run_date=trigger_args)
        elif trigger_type == "interval":
            # 秒、分、时、天、周（* * * * 1）
            values = [int(field) if field != '*' else 0 for field in trigger_args.split()]
            if len(values) != 5:
                raise ValueError(f"Wrong number of fields; got {len(values)}, expected 5")
            second, minute, hour, day, week = values
            trigger = IntervalTrigger(
                weeks=week,
                days=day,
                hours=hour,
                minutes=minute,
                seconds=second,
                start_date=start_time,
                end_date=end_time
            )
        elif trigger_type == "cron":
            # 秒、分、时、天、月、星期几、年 ()
            values = [None if field in ("*", "?") else field  for field in trigger_args.split()]
            if len(values) not in (6,7):
                raise ValueError(f"Wrong number of fields; got {len(values)}, expected 6-7")
            if len(values) == 6:
                values.append(None)
            second, minute, hour, day, month, week, year = values
            trigger = CronTrigger(
                second=second,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=week,
                year=year,
                start_date=start_time,
                end_date=end_time
            )
        else:
            raise ValueError(f"错误的触发器类型:{trigger_type}.")
        return trigger


if __name__ == "__main__":
    import sys
    from datetime import datetime
    sys.path.append("/home/langjin/workhome/hongyunkeji")

    aps = AIOScheduler()
    print(aps.scheduler._executors)
    aps.add_job(task_id="task_02", task_name="逾期检查", task_trigger="date", func_path="app.tasks.test", run_date=datetime.now())
    res = aps.scheduler.get_jobs()
    print(res)