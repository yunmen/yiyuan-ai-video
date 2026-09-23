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
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.generate_task import crud, Total
from app.cruds.video_template import crud as template_crud
from app.cruds.digital import crud as digital_crud
from app.services.digital import resolve_pose_variant
from app.models.video import GenerateTaskModel, VideoTemplateModel
from app.enums.business import TaskStatusEnum
from app.services.gen_rules import (
    CFG_KEY_DURATIONS,
    CFG_KEY_RATIO,
    CFG_KEY_RESOLUTION,
    DEFAULT_RATIO,
    DEFAULT_RESOLUTION,
    set_duration_gears,
    clamp_duration,
    resolve_gen_defaults,
)
from app.services.cost_rules import describe as describe_cost
from app.services.cost_rules import estimate_cost
from app.services.prompt_builder import build_gen_params, split_materials
from app.services.product_vision import classify_subjects
from app.schemas.generate_task import (
    CreateSchema,
    QuerySchema,
    CallbackSchema,
    ImageCreateSchema,
    AudioCreateSchema,
    TextCreateSchema,
    DigitalCreateSchema,
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
    "digital": {
        "seconds": 420,
        "stages": [(0, "解析口播文案"), (20, "合成口播音频"), (40, "提交数字人任务"), (60, "口型驱动合成"), (85, "回传成片")],
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


def _expand_image_roles(image_roles, image_urls) -> List[str]:
    """把前端 image_roles(URL→角色,多角色用逗号拼接)展开成与 image_urls 对齐的角色列表。

    同一张图可被同时用作多个维度(一键三换:一张图同时作产品/人物/场景),
    按该图在 image_urls 中出现的顺序依次取角色,避免字典按 URL 去重丢维度。
    单角色旧契约(每 URL 一个角色串)也兼容。
    """
    role_map = {}
    for k, v in (image_roles or {}).items():
        role_map[str(k)] = [x.strip() for x in str(v).split(",") if x.strip()] or [""]
    seen = {}
    roles = []
    for u in image_urls or []:
        roles_for_u = role_map.get(str(u), [""])
        idx = seen.get(str(u), 0)
        roles.append(roles_for_u[idx % len(roles_for_u)] if roles_for_u else "")
        seen[str(u)] = idx + 1
    return roles


def _abs_url(url: str) -> str:
    """把上传素材的相对地址补成绝对地址,便于视频模型侧拉取"""
    if url and url.startswith("/"):
        return f"{config.BACKEND_PUBLIC_URL.rstrip('/')}{url}"
    return url


def _build_gen_params(
    template, materials: List[str], remark: Optional[str],
    ratio: Optional[str] = None, resolution: Optional[str] = None,
    durations: Optional[Any] = None, product_desc: str = "",
    material_type: str = "", intent=None,
    subjects: Optional[Dict[str, str]] = None,
) -> Dict:
    """组装下发给 worker 的真实生成参数(结构化版)。

    除兼容用的扁平 prompt 外,额外下发 prompt_context/structured/gen_mode/material_hint/intent,
    让 worker 的 LLM 改写能分清「模板结构 / 商家信息 / 生成模式」,
    对应前端进度里的"解析模板结构"这一阶段。

    durations:仅为兼容调用方 `**gen_defaults` 展开而声明的形参 —— 时长档位经
    `gen_rules.set_duration_gears` 全局生效,不随单次任务下发。
    (少声明这一个形参会让建单接口直接 500:unexpected keyword argument)
    material_type/intent:替换意图增强(视觉识别类型 + 显式选择),下发给 worker 区分换人/换产品/换场景。
    """
    return build_gen_params(
        template, materials, remark, ratio=ratio, resolution=resolution, abs_url=_abs_url,
        product_desc=product_desc, material_type=material_type, intent=intent,
        subjects=subjects,
    )


# 画幅/清晰度配置的短缓存:建单与详情都会读,避免每次都查库
_GEN_DEFAULTS_CACHE: Dict = {"ts": 0.0, "data": {}}
GEN_DEFAULTS_TTL = 60


async def _load_gen_defaults() -> Dict[str, str]:
    """读取系统配置中的画幅/清晰度(gen.video_ratio / gen.video_resolution)。

    读库失败时用内置默认值兜底 —— 画幅不是关键路径,不能因此阻断建单。
    """
    now = time.time()
    cached = _GEN_DEFAULTS_CACHE.get("data") or {}
    if cached and now - float(_GEN_DEFAULTS_CACHE.get("ts") or 0) < GEN_DEFAULTS_TTL:
        return cached
    data = resolve_gen_defaults()
    try:
        from app.cruds.system_config import crud as config_crud
        rows = await config_crud.model.filter(
            key__in=[CFG_KEY_RATIO, CFG_KEY_RESOLUTION, CFG_KEY_DURATIONS]
        ).all()
        cfg_map = {r.key: r.value for r in rows}
        data = resolve_gen_defaults(cfg_map)
        # 时长档位:配了 "4-15" 就放开(需模型确实支持连续时长),没配则保持默认 5/10
        set_duration_gears(cfg_map.get(CFG_KEY_DURATIONS))
    except Exception:  # noqa: BLE001
        pass
    _GEN_DEFAULTS_CACHE["ts"] = now
    _GEN_DEFAULTS_CACHE["data"] = data
    return data


# 成本配置(gen.cost.*)短缓存:建单与预估都会读,避免每次都查库
_COST_CACHE: Dict = {"ts": 0.0, "data": {}}


async def _load_cost_cfg() -> Dict[str, str]:
    """读取系统配置中的计费项(gen.cost.*)。

    读库失败时返回空 dict → 各类型回退代码默认值(均为 1 次),
    计费配置不是建单的阻塞项。
    """
    now = time.time()
    cached = _COST_CACHE.get("data") or {}
    if cached and now - float(_COST_CACHE.get("ts") or 0) < GEN_DEFAULTS_TTL:
        return cached
    data: Dict[str, str] = {}
    try:
        from app.cruds.system_config import crud as config_crud
        rows = await config_crud.model.filter(key__startswith="gen.cost.").all()
        data = {r.key: r.value for r in rows}
    except Exception:  # noqa: BLE001
        pass
    _COST_CACHE["ts"] = now
    _COST_CACHE["data"] = data
    return data


JOB_BY_TYPE = {
    "video": "process_video",
    "image": "process_image",
    "audio": "process_audio",
    "text": "process_text",
    "digital": "process_digital",
}

# 各任务类型的消耗文案(额度数由 app/services/cost_rules.py 统一计算,不再写死在这里)
TASK_COST_REMARK = {
    "video": "生成视频消耗",
    "image": "生成图片消耗",
    "audio": "生成音频消耗",
    "text": "生成文本消耗",
    "digital": "数字人口播消耗",
}


class Service:
    @staticmethod
    async def _estimate(task_type: str, **ctx) -> Dict:
        """按成本规则预估额度消耗(唯一入口:预估与实扣同源)"""
        return estimate_cost(task_type, cfg=await _load_cost_cfg(), **ctx)

    @staticmethod
    async def _consume(user, task_type: str, estimate: Optional[Dict] = None) -> Optional[int]:
        """登录用户按预估扣减额度(免费优先,不足再扣付费),返回流水Id供建单后回填

        cost 取自 cost_rules.estimate_cost,与前端「下单前可见花费」同源 ——
        此前写死 1 次,用户看到的价和实扣的价可能对不上。
        """
        if not user:
            return None
        cost = int((estimate or {}).get("cost") or 0)
        if cost <= 0:      # 配置为 0 表示免费,无需扣减
            return None
        from app.services.credit import service as credit_service
        remark = TASK_COST_REMARK.get(task_type, "生成消耗")
        if detail := (estimate or {}).get("detail"):
            remark = f"{remark}({describe_cost(detail)})"
        return await credit_service.consume(user.id, cost=cost, remark=remark)

    async def estimate(self, data, user=None) -> Dict:
        """下单前预估花费(预算前置第一步:让用户先看见价,再决定要不要生成)

        与建单扣减共用 estimate_cost,保证「所见即所扣」。
        """
        from app.schemas.generate_task import EstimateSchema
        payload = data if isinstance(data, EstimateSchema) else EstimateSchema(**dict(data))
        task_type = payload.type or "video"
        ctx: Dict[str, Any] = {}
        if task_type == "video" and payload.template_id:
            template = await template_crud.get_by_id(payload.template_id)
            if not template or not template.active:
                raise HTTPException(status_code=200, detail="模板不存在或已下架")
            gen_defaults = await _load_gen_defaults()
            ctx = {
                "duration": clamp_duration(getattr(template, "duration", None) or 5),
                "resolution": gen_defaults.get("resolution"),
            }
        elif task_type == "image":
            ctx = {"num_images": payload.num_images or 1}
        elif task_type == "digital":
            ctx = {"duration": payload.duration or 8}
        elif payload.duration:
            ctx = {"duration": payload.duration}

        est = await self._estimate(task_type, **ctx)
        result: Dict[str, Any] = {**est, "balance": None, "enough": None}
        if user:
            from app.services.credit import service as credit_service
            balance = await credit_service.balance(user.id)
            result["balance"] = balance
            result["enough"] = (balance.get("total") or 0) >= est["cost"]
        return result

    async def create(self, data: CreateSchema, user=None, order_no: Optional[str] = None) -> Dict:
        template = await template_crud.get_by_id(data.template_id)
        if not template or not template.active:
            raise HTTPException(status_code=200, detail="模板不存在或已下架")
        gen_defaults = await _load_gen_defaults()
        # 预算前置:建单前先算价,扣减与前端预估同一个函数
        cost_est = await self._estimate(
            "video", duration=clamp_duration(getattr(template, "duration", None) or 5),
            resolution=gen_defaults.get("resolution"),
        )
        # 登录用户且非付费订单任务 → 扣减额度(免费优先,不足再扣付费),建单后回填流水
        credit_log_id = None
        try:
            if user and not order_no:
                credit_log_id = await self._consume(user, "video", cost_est)
            # 商品/人物/场景识别:让提示词拿到主体语义,并判定参考图类型(驱动「换人/换产品」意图兜底)。
            # 识别失败/未配视觉模型返回空字典,链路与之前完全一致(参考图仍照常提交)。
            # 视觉网关需绝对地址才能拉图,故先补成绝对地址再识别(此前直接传相对地址是潜在隐患)。
            _imgs, _ = split_materials(data.materials)
            _img_urls = [_abs_url(u) for u in _imgs]
            # 全部参考图一起识别(不再只看第一张):用户可能同时传人物形象图与产品图,
            # 需要分别拿到"人物长什么样 / 产品长什么样",才能分段注入并让文案结合两者。
            # 角色从"原始地址→角色"映射里取(前端标注),能显著提高识别准确率。
            # 同图多角色(一键三换:一张图同时作产品/人物/场景):前端把多角色用逗号拼到同一 URL 上,
            # 这里按该图在 _imgs(=materials 的图片部分)中出现的顺序依次取角色,
            # 避免字典按 URL 去重把 product/person/scene 压成最后一个。
            _roles = _expand_image_roles(data.image_roles, _imgs)
            _subjects = await classify_subjects(_img_urls, _roles) if _img_urls else {}
            product_desc = _subjects.get("desc", "")
            material_type = _subjects.get("type", "")
            params = _build_gen_params(
                template, data.materials, data.remark, product_desc=product_desc,
                material_type=material_type, intent=data.intent, subjects=_subjects,
                **gen_defaults
            )
            # 落库便于事后核对「扣了多少、为什么」;P2 资产缓存后也可据此做局部重跑计价
            params["cost"] = cost_est
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
        except Exception:
            # 建单/入队失败必须把预扣额度退回:否则用户"扣了额度却没拿到任务",
            # 且流水 task_id 为空,后续按任务退还的补偿路径也找不到它。
            await self._refund_precharge(credit_log_id)
            raise

    @staticmethod
    async def _refund_precharge(credit_log_id: Optional[int]) -> None:
        """建单失败时退回预扣额度(退款自身失败只记日志,不掩盖原始异常)"""
        if not credit_log_id:
            return
        from app.core.logger import logger
        try:
            from app.services.credit import service as credit_service
            amount = await credit_service.refund_consume_log(
                credit_log_id, remark="建单失败,预扣额度已退回",
            )
            if amount:
                logger.warning(f"建单失败,已退回预扣额度 {amount} 次(流水 {credit_log_id})")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"退回预扣额度失败(需人工补偿)流水={credit_log_id}: {exc}")

    @staticmethod
    async def _attach(credit_log_id: Optional[int], task_id: int) -> None:
        if credit_log_id:
            from app.services.credit import service as credit_service
            await credit_service.attach_task(credit_log_id, task_id)

    async def _create_and_enqueue(
        self, *, task_type: str, params: Dict, user, device: str,
        remark: Optional[str] = None, materials: Optional[List[str]] = None,
        cost_estimate: Optional[Dict] = None,
    ) -> Dict:
        """通用建单 + 下发:按任务类型下发对应的 ARQ 任务

        与视频任务一致:登录用户建单前按预估扣减额度,建单后回填流水
        (失败由 callback 返还,成功按实际用量结算返还)。
        """
        job_name = JOB_BY_TYPE.get(task_type)
        if not job_name:
            raise HTTPException(status_code=200, detail=f"不支持的任务类型:{task_type}")
        if cost_estimate is None:
            cost_estimate = await self._estimate(task_type)
        credit_log_id = await self._consume(user, task_type, cost_estimate)
        params = {**params, "cost": cost_estimate}
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
            cost_estimate=await self._estimate("image", num_images=data.num_images),
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

    async def create_digital(self, data: DigitalCreateSchema, user=None) -> Dict:
        """创建数字人口播任务(数字人形象 + 口播文案/音频)。

        与其它类型一致:登录用户建单前扣减额度,建单后下发 ARQ(process_digital),
        由 worker 用数字人形象 + 口播音频调用数字人模型生成口型视频并回调落库。
        """
        digital = await digital_crud.get_by_id(data.digital_id)
        if not digital or not digital.active:
            raise HTTPException(status_code=200, detail="数字人不存在或已下架")
        script = (data.text or "").strip() or (digital.default_text or "").strip()
        audio = _abs_url(data.audio) if data.audio else None
        if not script and not audio:
            raise HTTPException(status_code=200, detail="请填写口播文案或提供口播音频")
        # 主视图派生:选中派生视图时用它作底图,但主图仍下发给 worker 作 reference
        pose = resolve_pose_variant(getattr(digital, "pose_variants", None), data.pose)
        base_image = _abs_url(digital.image or digital.avatar)
        params = {
            "digital_id": digital.id,
            "digital_name": digital.name,
            # 形象图:选中派生视图时用派生图,否则主图(优先取专用字段,未配置回退头像)
            "avatar": _abs_url(pose.get("image")) if (pose or {}).get("image") else base_image,
            # 保持同一张脸:无论用哪个派生视图,都以主图为参考
            "reference_image": base_image if pose else None,
            "pose": pose.get("name") if pose else None,
            "voice": data.voice or digital.voice,
            "model": digital.model,
            "text": script,
            "audio": audio,
            "duration": data.duration,
            # 画幅/清晰度取自唯一规则源:此前画幅写死 "9:16"、清晰度干脆没下发
            # (worker 读不到就回退 env 兜底,运营改配置对数字人无效)
            "ratio": DEFAULT_RATIO,
            "resolution": DEFAULT_RESOLUTION,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._create_and_enqueue(
            task_type="digital", params=params, user=user, device=data.device, remark=data.remark,
            materials=[m for m in [digital.image or digital.avatar] if m],
            cost_estimate=await self._estimate("digital", duration=data.duration),
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
        tpl_map = await self._template_map(objs)
        result = []
        for obj in objs:
            item = await self._to_detail(obj, template=tpl_map.get(obj.template_id))
            result.append(item)
        return total, result

    @staticmethod
    async def _template_map(objs: List) -> Dict[int, Any]:
        """批量取回任务关联的模板(列表页用,避免每条任务各查一次造成 N+1)"""
        ids = list({o.template_id for o in objs if getattr(o, "template_id", None)})
        if not ids:
            return {}
        rows = await VideoTemplateModel.filter(id__in=ids).all()
        return {r.id: r for r in rows}

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
        # 沿用建单时的预估价:重跑参数未变,价也不应浮动
        cost_est = (obj.params or {}).get("cost") or await self._estimate(obj.type or "video")
        credit_log_id = None
        if user and not obj.order_no:
            credit_log_id = await self._consume(user, obj.type or "video", cost_est)
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
                gen_defaults = await _load_gen_defaults()
                params = _build_gen_params(
                    template, obj.materials, obj.remark, **gen_defaults
                ) if template else {
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
        previous_status = obj.status
        obj.status = TaskStatusEnum.PROCESSING.value
        # 必须一并刷新 update_time:否则沿用失败时的旧时间,会被孤儿回收立刻判定为"僵尸任务"
        # 而反复续跑(实测踩过),也让 reconcile_stuck 的超时兜底失去意义。
        await obj.save(update_fields=["status", "update_time"])
        params = obj.params or {}
        job_name = JOB_BY_TYPE.get(obj.type or "video", "process_video")
        if not await enqueue_generate_task(job_name, obj.id, _build_notify_url(), params):
            # 入队未成功(该任务仍在队列/执行中):回滚状态并明确报错,
            # 避免任务卡在"生成中"既不跑也不失败,用户无从判断该不该重试。
            obj.status = previous_status
            await obj.save(update_fields=["status", "update_time"])
            raise HTTPException(
                status_code=200,
                detail="任务已在队列中执行,请稍后查看进度",
            )
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
        tpl_map = await self._template_map(objs)
        result = []
        for obj in objs:
            item = obj.to_dict()
            template = tpl_map.get(obj.template_id)
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

    async def recover_orphan_tasks(self, stale_seconds: int) -> int:
        """回收"僵尸任务":worker 崩溃/被重启/任务被超时杀掉时,ARQ 里的任务会永久丢失
        (ARQ 不自动重入队),任务就永久停在"生成中"、既跑不完也不失败。

        分两种,处理方式不同:

        ① **未提交外部生成任务**(checkpoint 无 external_task_id)→ 安全重跑:
           断点会复用已改写好的 prompt,不会重复生成、不会重复扣费。

        ② **已提交外部生成任务**(checkpoint 有 external_task_id)→ **续跑,不是重跑**:
           worker 侧 stage=2 会直接复用 external_task_id 继续轮询取结果
           (`worker/tests/test_video_tool_resume.py` 钉住了"不重复扣费"这个契约)。
           此前这里对②直接 `continue`,导致"外部任务已提交、ARQ job 却被超时杀掉"的僵尸任务
           **只能干等 TASK_STUCK_TIMEOUT(4 小时)才被判失败** —— 用户看到进度永远停在
           80% 一动不动(实测踩过:23s 长片编辑收尾被掐)。续跑成本仅为一次轮询。

        保险:ARQ 里仍在队列/执行 → 跳过;①有 `_orphan_recovered`、②有 `_resume_count` 上限,
        避免无限重入队。返回重新入队的任务数。
        """
        from app.core.logger import logger
        from app.core.task_queue import arq_pool, enqueue_generate_task, job_alive

        # 已提交外部任务的续跑次数上限:每次只是重新轮询(不产生生成费用),
        # 上限防止外部任务长期不返回时无限重入队;超过后交给 reconcile_stuck 兜底失败。
        max_resume = 3

        if arq_pool is None:
            return 0
        deadline = datetime.now() - timedelta(seconds=int(stale_seconds))
        candidates = await GenerateTaskModel.filter(
            status=TaskStatusEnum.PROCESSING.value,
            deleted=False,
            update_time__lt=deadline,
        ).all()
        if not candidates:
            return 0

        recovered = 0
        for obj in candidates:
            if await job_alive(obj.id):
                continue                       # 还在队列/正在跑,别重复入队
            checkpoint = obj.checkpoint or {}
            # 用副本:入队失败时不能把"次数已递增/已回收"落库,否则等于凭空消耗一次续跑机会
            params = dict(obj.params or {})
            submitted = bool(checkpoint.get("external_task_id"))
            if submitted:
                if int(params.get("_resume_count") or 0) >= max_resume:
                    continue                   # 续跑次数用尽 → 交给超时对账,不再重入队
                next_count = int(params.get("_resume_count") or 0) + 1
                params["_resume_count"] = next_count
                reason = f"外部任务已提交,续跑轮询(第 {next_count} 次)"
            else:
                if params.get("_orphan_recovered"):
                    continue                   # 已回收过,不再反复重试(避免死循环烧钱)
                params["_orphan_recovered"] = True
                reason = "worker 中断,断点续跑"
            # 先确认真正入队,再落库:入队可能失败(该任务仍在队列/执行中)。此时若仍递增
            # _resume_count 并刷新 update_time,续跑机会被白白耗尽、reconcile_stuck 的超时兜底
            # 又被无限推迟 —— 任务永久卡在"生成中"(实测踩过)。
            if not await enqueue_generate_task("process_video", obj.id, _build_notify_url(), params):
                logger.warning(
                    f"[对账] 僵尸任务重新入队未成功,保持原状态等待下次对账 task={obj.id}"
                )
                continue
            update_fields = ["params", "update_time"]
            if not submitted:
                obj.progress = 0               # 进度归零,前端重新进入进度态
                update_fields.append("progress")
            obj.params = params
            await obj.save(update_fields=update_fields)
            recovered += 1
            logger.warning(f"[对账] 僵尸任务已重新入队 task={obj.id}({reason})")
        return recovered

    async def _to_detail(self, obj, save: bool = True, template=None) -> Dict:
        """组装任务详情;进度/状态由 worker 异步回调落库,这里只读取并补充展示字段

        template 可由列表页批量预取后传入,避免 N+1 查询;不传时按单条回退查询。
        """
        item = obj.to_dict()
        if template is None:
            template = await template_crud.get_by_id(obj.template_id) if obj.template_id else None
        item["template_title"] = template.title if template else None
        item["template_cover"] = template.cover if template else None
        # 展示值与实际下发的生成参数同源:优先取建单时算好的档位/画幅,缺失再按统一规则推导
        params = obj.params or {}
        gen_defaults = await _load_gen_defaults()
        raw_duration = params.get("gen_duration") or params.get("duration") or (template.duration if template else 5)
        # 去身份化提示:worker 在输入视频含真人时本地打码重试,把结论写进 usage 回传,
        # 这里透出给前端,在成片页明确告知用户"已自动人脸打码"(不能静默)。
        usage = obj.usage or {}
        # 展示时长优先用 worker 上报的**成片真实时长**:视频编辑的成片跟随参考视频
        # (23.5s),而建单时的 gen_duration 是吸附档位(10s) —— 展示 10 秒与实际成片
        # 差一倍,用户会以为成片被截短了。未上报时回退吸附值。
        reported_seconds = 0
        try:
            reported_seconds = int(usage.get("seconds") or 0)
        except (TypeError, ValueError):
            reported_seconds = 0
        item["gen_duration"] = reported_seconds if reported_seconds > 0 else clamp_duration(raw_duration)
        item["gen_ratio"] = params.get("ratio") or gen_defaults.get("ratio") or DEFAULT_RATIO
        item["gen_resolution"] = params.get("resolution") or gen_defaults.get("resolution") or DEFAULT_RESOLUTION
        item["deidentify_note"] = usage.get("deidentify_note") or ""
        # 降级提示(可观测性):视频编辑失败后曾会静默降级成图片链路,成片只是
        # "用上传图重画"、并未替换原视频元素,用户却看到"生成成功"。
        # 这里把降级原因透出,让前端明确标注"未替换",避免把错片当对片用。
        item["degrade_note"] = (
            f"视频编辑失败,已降级为图片生成:{usage.get('degrade_reason') or '未知原因'}"
            if usage.get("degraded") else ""
        )
        # 成片自检结果:视频编辑的成片应与参考视频一致(画幅/时长),不一致基本等价于
        # "没复刻上原片"。worker 只打标不阻断,这里透出给用户与排查者。
        mismatch = usage.get("output_mismatch")
        item["output_note"] = (mismatch or {}).get("reason") if isinstance(mismatch, dict) else ""
        # 续跑是否真的"有断点可续":只有外部任务已提交时,续跑才是"重新轮询取结果"
        # (不重复扣费)。提交阶段就被上游拒绝的任务(参数不认/含真人)没有外部任务 ID,
        # 再点"继续生成"只会原样再提交一次、再失败一次 —— 前端据此把按钮改叫"重试"
        # 并提示换素材,避免用户把它当成"接着上次跑"而反复点。
        item["resumable"] = bool((obj.checkpoint or {}).get("external_task_id"))
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
            update_fields = ["status", "progress", "checkpoint", "fail_reason"]
            obj.checkpoint = None
            obj.fail_reason = None  # 成功时清空历史失败原因(断点续跑成功后不再残留)
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
            # 预算前置最后一步:worker 上报了实际用量则按实际结算,多扣的退回
            if isinstance(payload.usage, dict) and payload.usage.get("cost") is not None:
                await self._settle_credit(obj, payload.usage.get("cost"))
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
    async def _settle_credit(obj, actual_cost) -> None:
        """成功回调后按实际用量结算返还(异常不阻断回调)

        只有 worker 明确上报 usage.cost 才结算;未上报则维持预扣金额(等价于现状)。
        """
        if not obj.user_id or obj.order_no:
            return
        try:
            from app.services.credit import service as credit_service
            await credit_service.settle_by_task(obj.id, obj.user_id, actual_cost)
        except Exception as exc:  # noqa: BLE001
            from app.core.logger import logger
            logger.error(f"任务结算返还额度出错 task={obj.id}: {exc}")

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
