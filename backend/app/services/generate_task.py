# -*- coding: utf-8 -*-
'''
@文件    :generate_task.py
@说明    :生成任务Service(后端只负责建单+下发 ARQ,AI 生成由 worker 异步执行并回调)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.generate_task import crud, Total
from app.cruds.video_template import crud as template_crud
from app.models.video import GenerateTaskModel
from app.enums.business import TaskStatusEnum
from app.schemas.generate_task import (
    CreateSchema,
    QuerySchema,
    CallbackSchema,
    ImageCreateSchema,
    AudioCreateSchema,
    TextCreateSchema,
)
from app.core.task_queue import enqueue_generate_task
from app.settings import config


# 各任务类型的阶段划分与预估总时长(仅用于前端展示进度/剩余时间)
TASK_PROFILES = {
    "video": {
        "seconds": 300,
        # 与 worker 真实执行节点对齐(心跳进度为 10 的倍数)
        "stages": [(0, "解析模板结构"), (10, "AI改写视频脚本"), (30, "提交生成任务"), (40, "模型生成视频"), (80, "回传成片")],
    },
    "image": {
        "seconds": 60,
        "stages": [(0, "解析提示词"), (40, "AI绘制画面"), (80, "优化输出")],
    },
    "audio": {
        "seconds": 60,
        "stages": [(0, "解析文本"), (40, "合成音频"), (80, "优化输出")],
    },
    "text": {
        "seconds": 30,
        "stages": [(0, "解析提示词"), (50, "生成文本"), (85, "润色输出")],
    },
}
DEFAULT_PROFILE = TASK_PROFILES["video"]


def _gen_task_no() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return "GY" + datetime.now().strftime("%Y%m%d%H%M%S") + suffix


def calc_stage(progress: int, task_type: str = "video") -> str:
    stages = TASK_PROFILES.get(task_type, DEFAULT_PROFILE)["stages"]
    stage = stages[0][1]
    for threshold, name in stages:
        if progress >= threshold:
            stage = name
    return stage


def _build_notify_url() -> str:
    """worker 回写任务状态的回调地址(需与 routes/user/task.py 的 callback 路由一致)"""
    return f"{config.BACKEND_PUBLIC_URL}/api/user/v1/task/callback"


def _abs_url(url: str) -> str:
    """把上传素材的相对地址补成绝对地址,便于视频模型侧拉取"""
    if url and url.startswith("/"):
        return f"{config.BACKEND_PUBLIC_URL.rstrip('/')}{url}"
    return url


def _build_gen_params(template, materials: List[str], remark: Optional[str]) -> Dict:
    """组装下发给 worker 的真实生成参数(prompt 取模板描述/标题 + 用户备注)"""
    prompt = (template.desc or template.title or "").strip()
    if remark:
        prompt = f"{prompt}。补充要求:{remark.strip()}" if prompt else remark.strip()
    return {
        "template_id": template.id,
        "template_title": template.title,
        "prompt": prompt or "生成一段高质量短视频",
        "materials": [_abs_url(u) for u in (materials or [])],
        "duration": template.duration or 5,
    }


JOB_BY_TYPE = {
    "video": "process_video",
    "image": "process_image",
    "audio": "process_audio",
    "text": "process_text",
}

# 各任务类型单次生成消耗的额度次数
TASK_COST = {
    "video": 1,
    "image": 1,
    "audio": 1,
    "text": 1,
}
DEFAULT_COST = 1

# 各任务类型的消耗文案
TASK_COST_REMARK = {
    "video": "生成视频消耗",
    "image": "生成图片消耗",
    "audio": "生成音频消耗",
    "text": "生成文本消耗",
}


class Service:
    @staticmethod
    async def _consume(user, task_type: str) -> Optional[int]:
        """登录用户扣减额度(免费优先,不足再扣付费),返回流水Id供建单后回填"""
        if not user:
            return None
        from app.services.credit import service as credit_service
        cost = TASK_COST.get(task_type, DEFAULT_COST)
        return await credit_service.consume(
            user.id, cost=cost,
            remark=TASK_COST_REMARK.get(task_type, "生成消耗"),
        )

    async def create(self, data: CreateSchema, user=None, order_no: Optional[str] = None) -> Dict:
        template = await template_crud.get_by_id(data.template_id)
        if not template or not template.active:
            raise HTTPException(status_code=200, detail="模板不存在或已下架")
        # 登录用户且非付费订单任务 → 扣减额度(免费优先,不足再扣付费),建单后回填流水
        credit_log_id = None
        if user and not order_no:
            credit_log_id = await self._consume(user, "video")
        params = _build_gen_params(template, data.materials, data.remark)
        obj = await crud.create({
            "task_no": _gen_task_no(),
            "type": "video",
            "status": TaskStatusEnum.PROCESSING.value,
            "progress": 0,
            "template_id": template.id,
            "materials": data.materials,
            "params": params,
            "remark": data.remark,
            "device": data.device,
            "user_id": user.id if user else None,
            "order_no": order_no,
        })
        # 下发给 ARQ,由 worker 调用真实视频模型生成并回调
        if credit_log_id:
            await self._attach(credit_log_id, obj.id)
        await enqueue_generate_task("process_video", obj.id, _build_notify_url(), params)
        return await self._to_detail(obj)

    @staticmethod
    async def _attach(credit_log_id: Optional[int], task_id: int) -> None:
        if credit_log_id:
            from app.services.credit import service as credit_service
            await credit_service.attach_task(credit_log_id, task_id)

    async def _create_and_enqueue(
        self, *, task_type: str, params: Dict, user, device: str,
        remark: Optional[str] = None, materials: Optional[List[str]] = None,
    ) -> Dict:
        """通用建单 + 下发:按任务类型下发对应的 ARQ 任务

        与视频任务一致:登录用户建单前扣减额度,建单后回填流水(失败由 callback 返还)。
        """
        job_name = JOB_BY_TYPE.get(task_type)
        if not job_name:
            raise HTTPException(status_code=200, detail=f"不支持的任务类型:{task_type}")
        credit_log_id = await self._consume(user, task_type)
        obj = await crud.create({
            "task_no": _gen_task_no(),
            "type": task_type,
            "status": TaskStatusEnum.PROCESSING.value,
            "progress": 0,
            "materials": materials or [],
            "params": params,
            "remark": remark,
            "device": device,
            "user_id": user.id if user else None,
        })
        await self._attach(credit_log_id, obj.id)
        await enqueue_generate_task(job_name, obj.id, _build_notify_url(), params)
        return await self._to_detail(obj)

    async def create_image(self, data: ImageCreateSchema, user=None) -> Dict:
        """创建图片生成任务(有素材则走图生图)"""
        materials = [_abs_url(u) for u in (data.materials or [])]
        params = {
            "prompt": (data.prompt or "").strip(),
            "ratio": data.ratio,
            "num_images": data.num_images,
            "materials": materials,
        }
        return await self._create_and_enqueue(
            task_type="image", params=params, user=user,
            device=data.device, remark=data.remark, materials=data.materials,
        )

    async def create_audio(self, data: AudioCreateSchema, user=None) -> Dict:
        """创建音频生成任务(tts 语音合成 / bgm 背景音乐)"""
        params = {
            "audio_type": data.audio_type,
            "text": data.text,
            "prompt": data.prompt,
            "lyrics": data.lyrics,
            "voice": data.voice,
            "is_instrumental": data.is_instrumental,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._create_and_enqueue(
            task_type="audio", params=params, user=user, device=data.device, remark=data.remark,
        )

    async def create_text(self, data: TextCreateSchema, user=None) -> Dict:
        """创建文本生成任务"""
        params = {"prompt": (data.prompt or "").strip()}
        return await self._create_and_enqueue(
            task_type="text", params=params, user=user, device=data.device, remark=data.remark,
        )

    async def my_list(self, user_id: int, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        """我的作品(按用户过滤),进度/状态由 worker 回调落库,这里只读取"""
        search = Q(user_id=user_id, deleted=False)
        if payload.status:
            search &= Q(status=payload.status)
        if payload.task_no:
            search &= Q(task_no__icontains=payload.task_no)
        if payload.type:
            search &= Q(type=payload.type)
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=["-create_time"])
        result = []
        for obj in objs:
            item = await self._to_detail(obj, save=False)
            result.append(item)
        return total, result

    async def detail(self, id: int, user=None) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="任务不存在")
        self._check_owner(obj, user)
        return await self._to_detail(obj)

    async def regenerate(self, id: int, user=None) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="任务不存在")
        self._check_owner(obj, user)
        if obj.status == TaskStatusEnum.PROCESSING.value:
            raise HTTPException(status_code=200, detail="任务正在生成中,请稍后")
        # 重新生成同样消耗额度(付费订单任务不重复扣减);失败由 callback 原路返还
        credit_log_id = None
        if user and not obj.order_no:
            credit_log_id = await self._consume(user, obj.type or "video")
        # 整任务重跑:清空断点,从零开始
        obj.status = TaskStatusEnum.PROCESSING.value
        obj.progress = 0
        obj.result_video = None
        obj.result_text = None
        obj.fail_reason = None
        obj.checkpoint = None
        await obj.save(update_fields=["status", "progress", "result_video", "result_text", "fail_reason", "checkpoint"])
        # 优先用建单时保存的原始参数;缺失时按类型兜底重建
        params = obj.params
        if not params:
            if obj.type == "video":
                template = await template_crud.get_by_id(obj.template_id) if obj.template_id else None
                params = _build_gen_params(template, obj.materials, obj.remark) if template else {
                    "template_id": obj.template_id,
                    "prompt": obj.remark or "生成一段高质量短视频",
                    "materials": [_abs_url(u) for u in (obj.materials or [])],
                    "duration": 5,
                }
            else:
                params = {"prompt": obj.remark or ""}
        job_name = JOB_BY_TYPE.get(obj.type or "video", "process_video")
        await self._attach(credit_log_id, obj.id)
        await enqueue_generate_task(job_name, obj.id, _build_notify_url(), params)
        return await self._to_detail(obj)

    async def get_checkpoint(self, task_id: int) -> Dict:
        """Worker 拉取断点检查点(内部接口)"""
        obj = await crud.get_by_id(task_id)
        if not obj:
            return {"checkpoint": None, "progress": 0}
        return {"checkpoint": obj.checkpoint or {}, "progress": obj.progress or 0}

    async def update_checkpoint(self, payload: "CheckpointSchema") -> None:
        """Worker 回写断点检查点(内部接口)。

        仅在任务仍处于 processing 时落库,防止终态/被人工变更的任务被过期检查点覆盖。
        """
        from app.schemas.generate_task import CheckpointSchema as _Cp
        if not isinstance(payload, _Cp):
            return
        obj = await crud.get_by_id(payload.task_id)
        if not obj:
            return
        if obj.status != TaskStatusEnum.PROCESSING.value:
            return
        cp = dict(obj.checkpoint or {})
        cp["stage"] = payload.stage
        if payload.data:
            cp.update(payload.data)
        obj.checkpoint = cp
        update_fields = ["checkpoint"]
        if payload.progress is not None:
            obj.progress = payload.progress
            update_fields.append("progress")
        await obj.save(update_fields=update_fields)

    async def resume(self, id: int, user=None, ignore_owner: bool = False) -> Optional[Dict]:
        """断点续跑:从已有 checkpoint 继续,不重复扣额度。

        与 regenerate 的区别:regenerate 清空 checkpoint 并从零重跑(重新扣额度);
        resume 保留 checkpoint,worker 会跳过已完成阶段(例如复用已提交的外部任务 ID 继续轮询)。
        ignore_owner=True 供管理端调用(管理端无用户归属,可续跑任意任务)。
        """
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="任务不存在")
        if not ignore_owner:
            self._check_owner(obj, user)
        if obj.status == TaskStatusEnum.PROCESSING.value:
            raise HTTPException(status_code=200, detail="任务正在生成中,请稍后")
        if obj.status == TaskStatusEnum.SUCCESS.value:
            raise HTTPException(status_code=200, detail="任务已成功,无需续跑")
        # 续跑:保留 checkpoint,状态置为 processing,重新下发(不扣额度)
        obj.status = TaskStatusEnum.PROCESSING.value
        await obj.save(update_fields=["status"])
        params = obj.params or {}
        job_name = JOB_BY_TYPE.get(obj.type or "video", "process_video")
        await enqueue_generate_task(job_name, obj.id, _build_notify_url(), params)
        return await self._to_detail(obj)

    async def list(self, payload: QuerySchema) -> Tuple[Total, List[Dict]]:
        search = Q(deleted=False)
        if payload.status:
            search &= Q(status=payload.status)
        if payload.task_no:
            search &= Q(task_no__icontains=payload.task_no)
        if payload.type:
            search &= Q(type=payload.type)
        total, objs = await crud.list(page_num=payload.pageNum, page_size=payload.pageSize, search=search, order=["-create_time"])
        result = []
        for obj in objs:
            item = obj.to_dict()
            template = await template_crud.get_by_id(obj.template_id) if obj.template_id else None
            item["template_title"] = template.title if template else None
            result.append(item)
        return total, result

    async def delete(self, id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="任务不存在")
        await crud.delete(obj)

    async def delete_by_user(self, id: int, user_id: int):
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="任务不存在")
        if obj.user_id != user_id:
            raise HTTPException(status_code=200, detail="无权删除该作品")
        await crud.delete(obj)

    @staticmethod
    def _check_owner(obj, user) -> None:
        """归属校验:匿名任务(user_id 为空)任何人可访问;有归属的任务仅本人可访问。"""
        if obj.user_id and (not user or user.id != obj.user_id):
            raise HTTPException(status_code=200, detail="任务不存在")

    async def reconcile_stuck(self, timeout_seconds: int) -> int:
        """对账兜底:把超过 timeout_seconds 仍停留在 processing 的任务标记为失败

        用于 worker 崩溃 / 任务丢失 / 回调未到达时,避免任务永久卡在"生成中"。
        返回被更新的任务数。
        """
        deadline = datetime.now() - timedelta(seconds=int(timeout_seconds))
        stuck = await GenerateTaskModel.filter(
            status=TaskStatusEnum.PROCESSING.value,
            deleted=False,
            update_time__lt=deadline,
        ).all()
        if not stuck:
            return 0
        await GenerateTaskModel.filter(id__in=[t.id for t in stuck]).update(
            status=TaskStatusEnum.FAILED.value,
            fail_reason="生成超时,任务未完成",
            update_time=datetime.now(),
        )
        # 与 callback 失败分支一致:付费订单退款 / 额度任务返还额度
        for obj in stuck:
            if obj.order_no:
                from app.services.payment import service as payment_service
                await payment_service.auto_refund_by_task(obj)
            else:
                await self._refund_credit(obj)
        return len(stuck)

    async def _to_detail(self, obj, save: bool = True) -> Dict:
        """组装任务详情;进度/状态由 worker 异步回调落库,这里只读取并补充展示字段"""
        item = obj.to_dict()
        template = await template_crud.get_by_id(obj.template_id) if obj.template_id else None
        item["template_title"] = template.title if template else None
        item["template_cover"] = template.cover if template else None
        # 实际下发给模型的生成参数(与 worker 的 _clamp_duration / env 默认一致,供前端真实展示)
        raw_duration = (obj.params or {}).get("duration") or (template.duration if template else 5)
        try:
            gen_duration = max(3, min(int(raw_duration), 15))
        except (TypeError, ValueError):
            gen_duration = 5
        item["gen_duration"] = gen_duration
        item["gen_ratio"] = "9:16"
        item["gen_resolution"] = "1080P"
        if obj.status == TaskStatusEnum.PROCESSING.value:
            item["stage"] = calc_stage(obj.progress, obj.type or "video")
            # 剩余时间按"预估时长 - 已耗时"估算,比按进度百分比更贴近真实
            # 注意:DB 读出的 create_time 可能带时区,统一转本地朴素时间再相减
            if obj.create_time:
                ct = obj.create_time
                if ct.tzinfo is not None:
                    ct = ct.astimezone().replace(tzinfo=None)
                elapsed = (datetime.now() - ct).total_seconds()
            else:
                elapsed = 0
            expected = TASK_PROFILES.get(obj.type or "video", DEFAULT_PROFILE)["seconds"]
            item["remain_seconds"] = max(0, int(expected - elapsed))
        elif obj.status == TaskStatusEnum.SUCCESS.value:
            item["stage"] = "生成完成"
            item["remain_seconds"] = 0
        else:
            item["stage"] = "生成失败"
            item["remain_seconds"] = 0
        return item

    async def callback(self, payload: CallbackSchema) -> None:
        """Worker 回写任务状态(进度/成功/失败),由 /api/user/v1/task/callback 调用"""
        obj = await crud.get_by_id(payload.task_id)
        if not obj:
            return
        if obj.status != TaskStatusEnum.PROCESSING.value and payload.status == TaskStatusEnum.PROCESSING.value:
            # 任务已被删除或状态被人工变更,忽略过期的进度回写
            return
        if payload.status == TaskStatusEnum.PROCESSING.value:
            obj.progress = payload.progress if payload.progress is not None else obj.progress
            await obj.save(update_fields=["progress"])
        elif payload.status != TaskStatusEnum.PROCESSING.value and obj.status != TaskStatusEnum.PROCESSING.value:
            # 任务已是终态(成功/失败),忽略重复的终态回调,防止重复返还额度/重复退款
            return
        elif payload.status == TaskStatusEnum.SUCCESS.value:
            obj.status = TaskStatusEnum.SUCCESS.value
            obj.progress = 100
            update_fields = ["status", "progress", "checkpoint"]
            obj.checkpoint = None
            if payload.result_video:
                obj.result_video = payload.result_video
                update_fields.append("result_video")
            if payload.result:
                obj.result_text = payload.result
                update_fields.append("result_text")
            if payload.usage:
                obj.usage = payload.usage
                update_fields.append("usage")
            await obj.save(update_fields=update_fields)
        elif payload.status == TaskStatusEnum.FAILED.value:
            obj.status = TaskStatusEnum.FAILED.value
            obj.fail_reason = (payload.fail_reason or "")[:255]
            # 失败保留 checkpoint,供用户「断点续跑」从断点处继续(无需重新扣额度)
            await obj.save(update_fields=["status", "fail_reason"])
            if obj.order_no:
                # 付费任务失败 → 关联订单自动退款(付费任务不扣额度,无需返还)
                from app.services.payment import service as payment_service
                await payment_service.auto_refund_by_task(obj)
            else:
                # 额度任务失败 → 把已扣额度原路返还(按 task_id 幂等)
                await self._refund_credit(obj)

    @staticmethod
    async def _refund_credit(obj) -> None:
        """生成失败返还额度(异常不阻断回调)"""
        if not obj.user_id:
            return
        try:
            from app.services.credit import service as credit_service
            await credit_service.refund_by_task(obj.id, obj.user_id)
        except Exception as exc:  # noqa: BLE001
            from app.core.logger import logger
            logger.error(f"任务失败返还额度出错 task={obj.id}: {exc}")


service = Service()
