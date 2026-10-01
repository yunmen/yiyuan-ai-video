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
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple, List, Dict
from tortoise.expressions import Q
from fastapi.exceptions import HTTPException
from app.cruds.generate_task import crud, Total
from app.cruds.video_template import crud as template_crud
from app.cruds.digital import crud as digital_crud
from app.services.digital import resolve_pose_variant
from app.models.video import GenerateTaskModel, VideoTemplateModel
from app.enums.business import TaskStatusEnum
from app.core.logger import logger
from app.services.gen_rules import (
    CFG_KEY_DURATIONS,
    CFG_KEY_RATIO,
    CFG_KEY_RESOLUTION,
    DEFAULT_RATIO,
    DEFAULT_RESOLUTION,
    SUPPORTED_DURATIONS,
    SUPPORTED_RATIOS,
    SUPPORTED_RESOLUTIONS,
    MIN_REFERENCE_SECONDS,
    REPLICATE_DEFAULTS,
    clamp_duration,
    normalize_ratio,
    normalize_replicate_format,
    normalize_resolution,
    resolve_gen_defaults,
    set_duration_gears,
)
from app.services.cost_rules import describe as describe_cost
from app.services.cost_rules import estimate_cost
from app.services.prompt_builder import (
    intent_labels,
    normalize_creative_level,
    normalize_hook_boost,
    normalize_intent,
    split_materials,
)
from app.core.task_queue import enqueue_ai_task
from app.schemas.generate_task import (
    CreateSchema,
    PrecheckSchema,
    QuerySchema,
    CallbackSchema,
    ImageCreateSchema,
    AudioCreateSchema,
    TextCreateSchema,
    DigitalCreateSchema,
    DeconstructSchema,
    VideoReNarrateSchema,
)
from app.core.task_queue import enqueue_generate_task
from app.settings import config

import re as _re

# —— 失败原因脱敏(仅用户端) ——
# 管理端要直击重点,直接读 DB 里的原始 fail_reason(网关错误码/返回体/异常串);
# 用户端不该看到后端任务细节,统一给一句"请稍后重试或联系客服",不暴露额度/鉴权/超时等内部状态。
# 唯一例外:用户内容本身的问题(如"输入视频含真人")属于给用户的具体操作指引,不含后端细节,保留原文。
# 原始值始终保留在 DB(管理端可见)与 worker 日志里,排查不受影响。
_CJK_RE = _re.compile(r"[\u4e00-\u9fff]")
_NOISE_LINE_RE = _re.compile(
    r"Error code:\s*\d+"      # OpenAI 风格:Error code: 403 - {...}
    r"|\{['\"]"               # 内嵌 json 载荷 {'code': ...}
    r"|^\s*\{"                # 整行就是 json
    r"|https?://"             # URL
    r"|\bTraceback\b"         # 异常栈
    r"|\bHTTP\s*/?\s*\d"      # HTTP 状态行
)
# 分类话术:同为"后端内部状态",但用户据此能采取**不同动作** ——
# 一句"请稍后重试或联系客服"会让用户只能反复重试,既解决不了问题也推高客服量。
_REASON_CONTENT_BLOCKED = "内容未通过平台审核,请修改文案或素材后重试"
_REASON_TIMEOUT = "生成服务响应超时,请稍后重试(失败将自动返还额度)"
_REASON_NETWORK = "生成服务连接失败,请稍后重试(失败将自动返还额度)"
# 额度/鉴权/权限属内部状态,不得透出(用户看到"额度不足"只会来投诉平台),统一归到通用话术
_REASON_GENERIC = "生成服务暂时不可用,请稍后重试或联系客服"
_FAIL_RULES = [
    (_re.compile(r"sensitive|审核|敏感|content[ _-]?policy|risk", _re.I), _REASON_CONTENT_BLOCKED),
    (_re.compile(r"timeout|timed?[ _-]?out|超时", _re.I), _REASON_TIMEOUT),
    (_re.compile(r"connect|connection|network|unreachable|网络", _re.I), _REASON_NETWORK),
    (_re.compile(r"quota|额度不足|insufficient|balance", _re.I), _REASON_GENERIC),
    (_re.compile(r"401|unauthorized|invalid[ _-]?api[ _-]?key|authentication", _re.I), _REASON_GENERIC),
    (_re.compile(r"403|forbidden|permission", _re.I), _REASON_GENERIC),
]
_FALLBACK_REASON = _REASON_GENERIC


def friendly_fail_reason(error) -> str:
    """把原始报错归一成用户可读文案(管理端不受影响,仍读 DB 原始值)。

    ① 命中审核/超时/网络 → 给出对应的**可执行**话术(用户知道该改素材还是稍后重试);
    ② 命中额度/鉴权/权限等内部状态 → 统一通用话术(不暴露内部状态);
    ③ 其余情况剥掉技术载荷(错误码/URL/异常栈/JSON)后**保留其中文动作描述** ——
       例如"未配置视频编辑模型(gen.video_model_edit),无法按参考视频生成新片",
       这类原因本身就是给用户的修复指引,不能被一句通用话术吃掉;
    ④ 剥完没有中文 → 通用兜底。
    """
    msg = str(error or "").strip()
    if not msg:
        return _FALLBACK_REASON
    for pat, text in _FAIL_RULES:
        if pat.search(msg):
            return text
    kept = []
    for line in msg.splitlines():
        line = _NOISE_LINE_RE.sub("", line).strip(" :：,，;；()（）")
        if line and _CJK_RE.search(line):
            kept.append(line)
    text = _re.sub(r"[（(]\s*[)）]", "", " ".join(kept)).strip()
    return text or _FALLBACK_REASON


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
    "deconstruct": {
        # 拆解只做分析(下载→镜头检测→原片台词→逐镜头逆推),耗时明显短于生成
        "seconds": 90,
        "stages": [(0, "下载对标视频"), (25, "检测镜头边界"), (55, "归集原片台词"), (75, "逐镜头逆推画面")],
    },
}
DEFAULT_PROFILE = TASK_PROFILES["video"]


def estimate_seconds(task_type: str, duration: Optional[int] = None) -> int:
    """按任务类型与成片时长估算总耗时(秒),用于前端展示预计耗时 / 剩余时间。

    视频模型生成耗时随成片时长近似线性增长:基础开销(prompt 改写 + 提交任务
    + 下载/烧字幕/上传收尾)约 90s,模型生成部分约 25s/秒成片
    (实测 30s 编辑视频约 14 分钟,即 30*25+90≈840s),避免"页面预估 5 分钟、
    实际 14 分钟"的落差让用户误判任务卡死。
    其余类型沿用各自固定档位(TASK_PROFILES);该值仅为展示估算,非硬上限
    (真实轮询上限见 worker 的 VIDEO_POLL_TIMEOUT)。
    """
    if task_type == "video" and duration:
        return int(90 + int(duration) * 25)
    return TASK_PROFILES.get(task_type, DEFAULT_PROFILE)["seconds"]


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


def _timeline_segments(obj) -> List[Dict]:
    """局部重跑用的分段列表:优先**真实(对齐后)时间轴**,回退建单时的估算脚本。

    真实时间轴来自 worker 烧字幕时回写的 usage.subtitle_timing(词级/句子级对齐结果,
    见 worker subtitle.burn_subtitle_with_cues),比建单时按词数摊分的估算值准;
    没有它(未生成字幕/烧录被跳过/历史任务)才回退到 script.segments。
    """
    cues = (obj.usage or {}).get("subtitle_timing")
    if isinstance(cues, list):
        out: List[Dict] = []
        for index, item in enumerate(cues):
            if not isinstance(item, dict):
                continue
            start, end = item.get("start_ms"), item.get("end_ms")
            if start is None or end is None:
                continue
            out.append({
                "id": index,
                "text": str(item.get("text") or ""),
                "timing": {"start_ms": start, "end_ms": end},
            })
        if out:
            return out
    return ((obj.params or {}).get("script") or {}).get("segments") or []


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


async def _load_real_person_mode() -> str:
    """读取真人素材处理策略(短缓存);未配置时按默认 drop 处理,不阻塞建单"""
    now = time.time()
    cached = _CAP_CACHE.get("real_person")
    if cached and now - float(_CAP_CACHE.get("rp_ts") or 0) < GEN_DEFAULTS_TTL:
        return cached
    value = "drop"
    try:
        from app.cruds.system_config import crud as config_crud
        row = await config_crud.model.filter(key=CFG_KEY_REAL_PERSON_MODE).first()
        if row and str(row.value or "").strip():
            value = str(row.value).strip().lower()
    except Exception:  # noqa: BLE001
        pass
    _CAP_CACHE["real_person"] = value
    _CAP_CACHE["rp_ts"] = now
    return value


def _detect_missing(
    materials: Optional[List[str]],
    intents: Optional[List[str]],
    duration: Optional[float] = None,
    real_person_mode: str = "",
) -> List[Dict[str, str]]:
    """建单前素材完整性校验(纯函数):返回结构化缺失项,而不是一段报错文案

    每项包含:field(字段) / label(缺什么) / why(为什么必须补) / action(前端要做的动作) / hint(人话指引)。
    前端据此渲染"还缺什么 + 一键去补",用户不必读懂校验规则,也不必等生成失败才知道缺素材。

    覆盖四类可前置拦截的情形:完全没素材 / 要替换却没有对标视频 / 对标视频过短 /
    选了替换却没替换图;真人照片在当前供应商下不可用(换人物时)为**提示项**,由调用方决定是否阻断。

    判定边界(曾经踩过的坑):没选替换意图时,"没有对标视频"是**图/文生视频链路的正常输入**,
    不是缺失 —— 九宫格分镜图出片、选平台模板套用走的都是"模型按素材与描述重绘",
    早期版本把它当成硬缺失,导致"上传了素材、选了模板却提示缺对标视频,压根无法出片"。
    """
    imgs, ref_video = split_materials(materials or [])
    intents = list(intents or [])
    missing: List[Dict[str, str]] = []
    # 真人照片:gen.image_real_person_mode=drop 时人物图会被丢弃、改按文字描述生成,
    # 用户以为"换了人物"实际没换 —— 与其出片后失望,不如建单前说清替代方案。
    if "person" in intents and str(real_person_mode or "drop").strip().lower() == "drop":
        missing.append({
            "field": "real_person_unsupported",
            "label": "真人照片做不了「换人物」",
            "why": "当前视频供应商不接受真人照片作为成片素材,上传本人照片会被移除、只按文字描述生成非本人角色",
            "action": "open_digital",
            "hint": "改用插画/虚拟形象图,或用平台数字人形象出镜",
        })
    if ref_video and duration and float(duration) < MIN_REFERENCE_SECONDS:
        missing.append({
            "field": "reference_too_short",
            "label": "对标视频太短",
            "why": f"只有 {float(duration):.0f} 秒,镜头拆不出来,成片也无从复刻",
            "action": "upload_video",
            "hint": f"换一段 ≥ {MIN_REFERENCE_SECONDS} 秒的完整视频",
        })
    if not ref_video and not imgs:
        missing.append({
            "field": "material",
            "label": "还没有任何素材",
            "why": "至少要有一段对标视频或一张产品图,AI 才知道要做什么",
            "action": "upload_video",
            "hint": "上传一段 5-30 秒的参考视频,或从模板库选一个",
        })
        return missing
    if not ref_video and intents:
        # 替换必须发生在参考视频上:没有参考视频时链路只能按图片/描述重画,
        # "换产品/换人物"一律不会生效,用户却看到生成成功 —— 必须拦截并给出可补的一步。
        # 反过来:未选替换意图时正是"按图/按描述出片"的预期行为(九宫格出片、模板套用),
        # 缺对标视频不该阻断(见函数 docstring 的判定边界)。
        missing.append({
            "field": "reference_video",
            "label": "缺对标视频",
            "why": "替换只能发生在参考视频上:没有参考视频时,换产品/换人物都不会生效",
            "action": "upload_video",
            "hint": "上传一段 5-30 秒的参考视频,或从模板库选一个平台模板",
        })
    if intents and not imgs:
        missing.append({
            "field": "replace_image",
            "label": "缺替换素材图",
            "why": f"选择了「{'、'.join(intent_labels(intents))}」,但没有要替换进去的图,模型只能自由发挥",
            "action": "upload_image",
            "hint": "上传要替换进去的产品图 / 人物图 / 场景图",
        })
    return missing


async def _recognize_subjects(img_urls: List[str], roles: List[str]) -> Dict[str, str]:
    """建单前视觉识别委托 worker 执行(backend 不再直连模型)。

    任何失败/超时返回空字典,与 product_vision 的"增强项不阻断建单"语义一致
    —— 识别只是给提示词补主体语义,不能成为关键路径。
    """
    if not img_urls:
        return {}
    try:
        return await enqueue_ai_task(
            "ai_recognize", img_urls, roles,
            timeout=60,
        ) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[generate_task] 委托 worker 识别失败(不影响建单): {exc}")
        return {}


def _build_raw_params(
    template, materials: List[str], remark: Optional[str],
    ratio: Optional[str] = None, resolution: Optional[str] = None,
    durations: Optional[Any] = None, duration: Optional[int] = None,
    product_desc: str = "",
    material_type: str = "", intent=None,
    subjects: Optional[Dict[str, str]] = None,
    real_person_strategy: Optional[str] = None,
    replicate_format: Optional[str] = None,
    lead_act: Optional[str] = None,
    creative_level: Optional[str] = None,
    hook_boost: Optional[str] = None,
    asset_override: Optional[str] = None,
) -> Dict:
    """构造「原始生成参数」下发给 worker:不在此组装 prompt_context,只携带业务输入 + 序列化模板。
    worker 在 process_video 里调用 prompt_builder 组装(backend 不再持有组装逻辑)。

    durations:仅为兼容调用方 `**gen_defaults` 展开而声明的形参 —— 时长档位经
    `set_duration_gears` 全局生效,不随单次任务下发。
    materials 需为绝对地址(worker 视觉网关才能拉图)。
    """
    return {
        "template_id": getattr(template, "id", None),
        "materials": [_abs_url(u) for u in (materials or [])],
        "remark": remark,
        "ratio": ratio,
        "resolution": resolution,
        "duration": duration,
        "product_desc": product_desc,
        "material_type": material_type,
        "intent": intent,
        "subjects": subjects or {},
        "real_person_strategy": real_person_strategy,
        "replicate_format": replicate_format,
        "lead_act": lead_act,
        "creative_level": creative_level,
        "hook_boost": hook_boost,
        "asset_override": asset_override,
        "_template": {
            "id": getattr(template, "id", None),
            "title": getattr(template, "title", "") or "",
            "duration": getattr(template, "duration", None),
            "prompt_parts": getattr(template, "prompt_parts", None) or {},
        },
    }


# 画幅/清晰度配置的短缓存:建单与详情都会读,避免每次都查库
_GEN_DEFAULTS_CACHE: Dict = {"ts": 0.0, "data": {}}
GEN_DEFAULTS_TTL = 60

# 能力开关类配置键(与 app/services/system_config.py 的 DEFAULT_CONFIGS 一致):
# 值为空表示该能力未接入 —— 建单前据此拦截,避免"扣了额度才发现能力没开"。
CFG_KEY_VIDEO_MODEL_EDIT = "gen.video_model_edit"
CFG_KEY_DIGITAL_MODEL = "gen.digital_model"
# 真人素材处理方式:drop=丢弃真人图改按文字描述生成(默认);stylize=先拟态化再提交
CFG_KEY_REAL_PERSON_MODE = "gen.image_real_person_mode"

# 能力开关短缓存(与画幅配置同 TTL):建单前置校验会读,避免每次都查库
_CAP_CACHE: Dict = {"ts": 0.0, "data": {}}


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


async def _load_capability_flags() -> Dict[str, str]:
    """读取「能力是否已接入」类配置(视频编辑模型 / 数字人模型)。

    返回 {"video_model_edit": "", "digital_model": ""} 形态;读库失败或未配置时为空串,
    调用方据此在下单前明确拦截 —— 而不是让用户扣了额度、等几分钟后
    才拿到一条"其实没做替换"的成片(详见 VideoGenTool 的失败语义)。
    """
    now = time.time()
    cached = _CAP_CACHE.get("data") or {}
    if cached and now - float(_CAP_CACHE.get("ts") or 0) < GEN_DEFAULTS_TTL:
        return cached
    data: Dict[str, str] = {"video_model_edit": "", "digital_model": ""}
    try:
        from app.cruds.system_config import crud as config_crud
        rows = await config_crud.model.filter(
            key__in=[CFG_KEY_VIDEO_MODEL_EDIT, CFG_KEY_DIGITAL_MODEL]
        ).all()
        cfg_map = {r.key: r.value for r in rows}
        data = {
            "video_model_edit": str(cfg_map.get(CFG_KEY_VIDEO_MODEL_EDIT) or "").strip(),
            "digital_model": str(cfg_map.get(CFG_KEY_DIGITAL_MODEL) or "").strip(),
        }
    except Exception:  # noqa: BLE001
        pass
    _CAP_CACHE["ts"] = now
    _CAP_CACHE["data"] = data
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
    "deconstruct": "process_deconstruct",
    "render": "process_render",
}

# 各任务类型的消耗文案(额度数由 app/services/cost_rules.py 统一计算,不再写死在这里)
TASK_COST_REMARK = {
    "video": "生成视频消耗",
    "image": "生成图片消耗",
    "audio": "生成音频消耗",
    "text": "生成文本消耗",
    "digital": "数字人口播消耗",
    "render": "视频换口播消耗",
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
        同时把「可选规格 / 预计耗时 / 视频编辑能力是否可用」一并回给前端 ——
        前端据此渲染真实选项,不再写死"约 2 分钟""消耗 1 次"这类与后端不同源的文案。
        """
        from app.schemas.generate_task import EstimateSchema
        payload = data if isinstance(data, EstimateSchema) else EstimateSchema(**dict(data))
        task_type = payload.type or "video"
        ctx: Dict[str, Any] = {}
        gen_defaults = await _load_gen_defaults()
        # 规格的当前生效值:请求未带时回退系统默认(gen.video_ratio / gen.video_resolution)
        ratio = normalize_ratio(payload.ratio, gen_defaults.get("ratio") or DEFAULT_RATIO)
        resolution = normalize_resolution(payload.resolution, gen_defaults.get("resolution") or DEFAULT_RESOLUTION)
        duration = clamp_duration(payload.duration or 5)
        if task_type == "video" and payload.template_id:
            template = await template_crud.get_by_id(payload.template_id)
            if not template or not template.active:
                raise HTTPException(status_code=200, detail="模板不存在或已下架")
            duration = clamp_duration(payload.duration or getattr(template, "duration", None) or 5)
            ctx = {"duration": duration, "resolution": resolution}
        elif task_type == "image":
            ctx = {"num_images": payload.num_images or 1}
        elif task_type == "digital":
            duration = payload.duration or 8
            ctx = {"duration": duration}
        elif task_type == "render":
            duration = payload.duration or 8
            ctx = {"duration": duration}
        elif payload.duration:
            duration = clamp_duration(payload.duration)
            ctx = {"duration": duration}

        est = await self._estimate(task_type, **ctx)
        result: Dict[str, Any] = {**est, "balance": None, "enough": None}
        if user:
            from app.services.credit import service as credit_service
            balance = await credit_service.balance(user.id)
            result["balance"] = balance
            result["enough"] = (balance.get("total") or 0) >= est["cost"]
        # 预计耗时与可选规格(与 TASK_PROFILES / gen_rules 同源,前端不再各自写死)
        # 视频任务按成片时长动态估算,避免固定 5 分钟与实际十几分钟落差过大
        result["estimate_seconds"] = estimate_seconds(task_type, duration)
        result["options"] = {
            "durations": list(SUPPORTED_DURATIONS),
            "ratios": list(SUPPORTED_RATIOS),
            "resolutions": list(SUPPORTED_RESOLUTIONS),
        }
        result["gen_duration"] = duration
        result["gen_ratio"] = ratio
        result["gen_resolution"] = resolution
        if task_type == "video":
            # 视频编辑能力开关 + 本次是否携带参考视频:前端据此在下单前明确告知
            # "参考视频不会被使用",而不是等生成完才发现没做替换。
            result["edit_available"] = bool((await _load_capability_flags()).get("video_model_edit"))
            result["edit_required"] = bool(getattr(payload, "has_reference_video", False))
        return result

    async def create(self, data: CreateSchema, user=None, order_no: Optional[str] = None) -> Dict:
        # 模板可选:普通生成(选平台模板视频)必传并校验;视频复刻链路用户自带对标视频,无需模板。
        # 仅当「传了 template_id」时才做存在性/上架校验;未传则 template=None,
        # 时长/画幅/清晰度一律回退系统默认(有参考视频时 worker 按原片时长成片)。
        template = None
        if data.template_id:
            template = await template_crud.get_by_id(data.template_id)
            if not template or not template.active:
                raise HTTPException(status_code=200, detail="模板不存在或已下架")
        gen_defaults = await _load_gen_defaults()
        # 规格覆盖:前端可选时长/画幅/清晰度(未传则回退模板时长与系统默认)。
        # 此前这些全部写死在模板/系统配置里,用户无从选择,是与成熟产品差距最大的一项。
        ratio = normalize_ratio(data.ratio, gen_defaults.get("ratio") or DEFAULT_RATIO)
        resolution = normalize_resolution(data.resolution, gen_defaults.get("resolution") or DEFAULT_RESOLUTION)
        # 无模板时(复刻链路)以系统默认时长为预算基准;有参考视频时 worker 会按原片时长成片。
        duration = clamp_duration(data.duration or getattr(template, "duration", None) or 5)
        # 预算前置:建单前先算价,扣减与前端预估同一个函数
        cost_est = await self._estimate("video", duration=duration, resolution=resolution)
        # 能力前置校验(必须在扣额度之前):有参考视频(用户上传或模板示例视频)时,
        # 必须已配置视频编辑模型 —— 否则 worker 只能把参考视频整个丢弃,成片变成
        # "用上传图/文案重画",用户却看到"生成成功"。宁可在此明确失败并说清怎么修。
        _imgs, _ref_video = split_materials(data.materials)
        # 替换意图可达性校验(同样必须在扣额度之前):替换只能发生在**参考视频**上,
        # 没有参考视频时链路只能退化成"用上传图重画整片" —— 成片里既没有原片情节,
        # 也谈不上"换掉原片里的某个人/物",用户却看到"生成成功"(实测:选了换人物,
        # 成片主角没出现、原片画面也全没了)。宁可在此明确失败并给出可执行的修法。
        _intents = normalize_intent(data.intent)
        # 缺失校验与 /precheck 同源(_detect_missing):前端已按结构化缺失项引导用户补齐,
        # 这里只作为"绕过前端直连"的兜底,文案取自同一份结构,不会两边说法不一致。
        _missing = _detect_missing(data.materials, _intents)
        # 只阻断"硬缺失"(没素材 / 要替换却没有对标视频 / 没有替换图)。真人照片那一项是**提示而非阻断**:
        # 用户可能传的是插画/虚拟形象图,后端无法从地址判断,硬拦会误伤合法用法 ——
        # 由 /precheck 提前告知替代方案,交由用户决定。
        _blocking = [m for m in _missing if m["field"] != "real_person_unsupported"]
        if _blocking:
            raise HTTPException(
                status_code=200,
                detail=";".join(f"{m['label']}:{m['why']}。{m['hint']}" for m in _blocking),
            )
        if _ref_video and not (await _load_capability_flags()).get("video_model_edit"):
            raise HTTPException(
                status_code=200,
                detail="当前未启用视频编辑能力(未配置 gen.video_model_edit),无法按参考视频生成;"
                       "请移除参考视频或改用图片素材,或联系管理员配置视频编辑模型",
            )
        # 登录用户且非付费订单任务 → 扣减额度(免费优先,不足再扣付费),建单后回填流水
        credit_log_id = None
        try:
            if user and not order_no:
                credit_log_id = await self._consume(user, "video", cost_est)
            # 商品/人物/场景识别:让提示词拿到主体语义,并判定参考图类型(驱动「换人/换产品」意图兜底)。
            # 识别失败/未配视觉模型返回空字典,链路与之前完全一致(参考图仍照常提交)。
            # 视觉网关需绝对地址才能拉图,故先补成绝对地址再识别(此前直接传相对地址是潜在隐患)。
            _img_urls = [_abs_url(u) for u in _imgs]
            # 全部参考图一起识别(不再只看第一张):用户可能同时传人物形象图与产品图,
            # 需要分别拿到"人物长什么样 / 产品长什么样",才能分段注入并让文案结合两者。
            # 角色从"原始地址→角色"映射里取(前端标注),能显著提高识别准确率。
            # 同图多角色(一键三换:一张图同时作产品/人物/场景):前端把多角色用逗号拼到同一 URL 上,
            # 这里按该图在 _imgs(=materials 的图片部分)中出现的顺序依次取角色,
            # 避免字典按 URL 去重把 product/person/scene 压成最后一个。
            _roles = _expand_image_roles(data.image_roles, _imgs)
            _subjects = await _recognize_subjects(_img_urls, _roles) if _img_urls else {}
            product_desc = _subjects.get("desc", "")
            material_type = _subjects.get("type", "")
            # 小白默认方案兜底:用户没显式指定的旋钮按 REPLICATE_DEFAULTS 补齐。
            # 「不传」不等于"忠实复刻"——那会落到改造前的全量方法论注入,成片风格不可预期;
            # 显式传的值(含前端按 /gen-config 预填的值)始终优先。
            _creative = normalize_creative_level(data.creative_level) or str(
                REPLICATE_DEFAULTS.get("creative_level") or ""
            )
            _hook = normalize_hook_boost(data.hook_boost) or str(
                REPLICATE_DEFAULTS.get("hook_boost") or ""
            )
            params = _build_raw_params(
                template, data.materials, data.remark, ratio=ratio, resolution=resolution,
                duration=duration, product_desc=product_desc,
                material_type=material_type, intent=data.intent, subjects=_subjects,
                real_person_strategy=data.real_person_strategy,
                replicate_format=data.format, lead_act=data.lead_act,
                creative_level=_creative, hook_boost=_hook,
                asset_override=data.asset_override,
            )
            # 一句话目标:随任务下发,worker 在结构化旋钮缺失时据此推断方案
            _goal = str(getattr(data, "goal", "") or "").strip()
            if _goal:
                params["goal"] = _goal
            # 低分镜头自动重跑:仅在前端显式传入时覆盖 worker 全局配置 —— 重跑会产生
            # 新的模型费用,绝不能在代码里静默改成默认开启。
            if getattr(data, "qc_auto_retry", None) is not None:
                params["qc_auto_retry"] = bool(data.qc_auto_retry)
            # 落库便于事后核对「扣了多少、为什么」;P2 资产缓存后也可据此做局部重跑计价
            params["cost"] = cost_est
            obj = await crud.create({
                "task_no": _gen_task_no(),
                "type": "video",
                "status": TaskStatusEnum.PROCESSING.value,
                "progress": 0,
                "template_id": template.id if template else None,
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

    async def precheck(self, data: PrecheckSchema) -> Dict:
        """建单前预检:只做素材完整性校验,不扣额度、不调模型

        返回 {ok, missing}:missing 是结构化缺失项,前端据此渲染"还缺什么 + 一键去补",
        让用户不必等生成失败才知道缺素材,也不必读懂后端校验规则。
        """
        materials = list(data.materials or [])
        if data.reference_video:
            materials = materials + [data.reference_video]
        # 真人策略读系统配置:stylize 模式下换人物仍可用(先拟态化),只有 drop 才提示不可用
        mode = await _load_real_person_mode()
        missing = _detect_missing(
            materials, normalize_intent(data.intent), data.duration, mode,
        )
        return {"ok": not missing, "missing": missing}

    async def deconstruct(
        self, data: DeconstructSchema, user=None
    ) -> Dict:
        """拆解对标视频分镜(带货视频复刻前置):仅做分析,不消耗生成额度

        与 create 的区别:不预判价、不扣额度、不依赖模板;结果由 worker 经 result_text 回写,
        前端轮询 /task/detail 读取。复用同一张任务表(type="deconstruct")与回调/详情链路,
        避免为分析单独建表与一套轮询基础设施。
        """
        # 参考视频需绝对地址:worker 侧多模态/ffmpeg 都靠绝对地址拉流
        ref_video = _abs_url(data.reference_video)
        params = {
            "reference_video": ref_video,
            "intent": data.intent or [],
            "duration": data.duration,
            "device": data.device,
            # 复刻目标形态(可选):与生成建单传同一个形态,保证"理解原片"与"重塑出片"一致。
            # 不指定时为空串,worker 读到空串即跳过形态注入(与历史行为一致)。
            "format": normalize_replicate_format(getattr(data, "format", None)),
            # 创意档位/钩子强化(可选):必须与生成建单同源 —— 拆解按"忠实复刻"理解原片、
            # 生成却按"爆款改造"出片时,用户看到的分镜描述与实际成片会对不上。
            # 空串=不指定,worker 沿用改造前的全量方法论注入;键必须存在(契约测试按"是否下发"校验)。
            # 拆解侧同样按推荐默认值兜底,保证"理解原片"与"出片"口径一致
            "creative_level": normalize_creative_level(getattr(data, "creative_level", None))
            or str(REPLICATE_DEFAULTS.get("creative_level") or ""),
            "hook_boost": normalize_hook_boost(getattr(data, "hook_boost", None))
            or str(REPLICATE_DEFAULTS.get("hook_boost") or ""),
        }
        # 一句话目标:与生成侧同源,让分镜描述按同一目标组织
        _decon_goal = str(getattr(data, "goal", "") or "").strip()
        if _decon_goal:
            params["goal"] = _decon_goal
        obj = await crud.create({
            "task_no": _gen_task_no(),
            "type": "deconstruct",
            "status": TaskStatusEnum.PROCESSING.value,
            "progress": 0,
            # materials 仅作记录,真正拆解只认 params.reference_video
            "materials": [ref_video],
            "params": params,
            "remark": "对标视频分镜拆解",
            "device": data.device,
            "user_id": user.id if user else None,
        })
        await enqueue_generate_task("process_deconstruct", obj.id, _build_notify_url(), params)
        return await self._to_detail(obj)

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
            # 复刻替换意图(可选):非空表示"按参考图复刻、换掉该元素",worker 据此用
            # 「图像方向」方法论改写提示词;留空则普通文生图/图生图,行为完全不变。
            "intent": [str(i).strip() for i in (data.intent or []) if str(i).strip()],
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
        # 数字人模型未接入时前置失败(必须在扣额度之前):否则用户扣了额度、等几分钟
        # 才拿到失败,原因还要靠 worker 兜底。这里在下单前给出同一明确原因。
        flags = await _load_capability_flags()
        if not (str(getattr(digital, "model", "") or "").strip() or flags.get("digital_model")):
            raise HTTPException(
                status_code=200,
                detail="当前未接入数字人模型(未配置 gen.digital_model),数字人口播暂不可用;请联系管理员配置",
            )
        script = (data.text or "").strip() or (digital.default_text or "").strip()
        audio = _abs_url(data.audio) if data.audio else None
        if not script and not audio:
            raise HTTPException(status_code=200, detail="请填写口播文案或提供口播音频")
        # 规格覆盖:画幅/清晰度此前写死 9:16/1080P,用户无从选择;现读取请求参数并归一化,
        # 非法值回退系统默认(与视频 generate 同一套规则源,运营改配置对数字人同样生效)。
        gen_defaults = await _load_gen_defaults()
        ratio = normalize_ratio(data.ratio, gen_defaults.get("ratio") or DEFAULT_RATIO)
        resolution = normalize_resolution(data.resolution, gen_defaults.get("resolution") or DEFAULT_RESOLUTION)
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
            # 声纹复用:请求级 voice_reference 优先,否则取数字人绑定的声纹样本(同一数字人跨任务声音一致)
            "voice_reference": data.voice_reference or getattr(digital, "voice_reference", None),
            "model": digital.model,
            "text": script,
            "audio": audio,
            "duration": data.duration,
            # 画幅/清晰度:走唯一规则源,非法值已在上文归一化回退默认
            "ratio": ratio,
            "resolution": resolution,
            # 背景/场景参考图:用户上传则带入,留空表示使用数字人默认场景
            "background": _abs_url(data.background) if data.background else None,
            # talking-head 进阶:多段脚本(逐段生成后拼接)与画中画(数字人缩窗叠到背景视频)
            "segments": data.segments,
            "overlay": _abs_url(data.overlay) if data.overlay else None,
            "pip": data.pip if data.overlay else None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._create_and_enqueue(
            task_type="digital", params=params, user=user, device=data.device, remark=data.remark,
            materials=[m for m in [digital.image or digital.avatar] if m],
            cost_estimate=await self._estimate("digital", duration=data.duration),
        )

    async def create_render(self, data: VideoReNarrateSchema, user=None) -> Dict:
        """创建视频换口播任务(上传视频 + 提示词 → 换声 / 换数字人 / 换场景 / 组合)。

        路线由字段组合派生(与 schema 注释一致):
          - digital_id 存在           → 数字人路线;
          - digital_id 缺失且 scene 存在 → 换场景路线(需抠像);
          - 两者都缺失                → 只换声音。
        关键校验在前置(扣额度之前)完成:数字人模型接入、口播文案/音频至少一项、换场景必填 scene。
        """
        source_video = _abs_url(data.source_video)
        if not source_video:
            raise HTTPException(status_code=200, detail="请上传源视频")

        prompt = (data.prompt or "").strip()
        audio = _abs_url(data.audio) if data.audio else None

        # —— 数字人路线 ——
        if data.digital_id:
            digital = await digital_crud.get_by_id(data.digital_id)
            if not digital or not digital.active:
                raise HTTPException(status_code=200, detail="数字人不存在或已下架")
            flags = await _load_capability_flags()
            if not (str(getattr(digital, "model", "") or "").strip() or flags.get("digital_model")):
                raise HTTPException(
                    status_code=200,
                    detail="当前未接入数字人模型(未配置 gen.digital_model),数字人口播暂不可用;请联系管理员配置",
                )
            script = prompt or (digital.default_text or "").strip()
            if not script and not audio:
                raise HTTPException(status_code=200, detail="请填写口播提示词或提供口播音频")
            gen_defaults = await _load_gen_defaults()
            ratio = normalize_ratio(data.ratio, gen_defaults.get("ratio") or DEFAULT_RATIO)
            resolution = normalize_resolution(data.resolution, gen_defaults.get("resolution") or DEFAULT_RESOLUTION)
            pose = resolve_pose_variant(getattr(digital, "pose_variants", None), data.pose)
            base_image = _abs_url(digital.image or digital.avatar)
            params = {
                "route": "digital_human",
                "source_video": source_video,
                "prompt": prompt,
                "digital_id": digital.id,
                "digital_name": digital.name,
                "avatar": _abs_url(pose.get("image")) if (pose or {}).get("image") else base_image,
                "reference_image": base_image if pose else None,
                "pose": pose.get("name") if pose else None,
                "voice": data.voice or digital.voice,
                "voice_reference": data.voice_reference or getattr(digital, "voice_reference", None),
                "model": digital.model,
                "text": script,
                "audio": audio,
                "duration": data.duration,
                "ratio": ratio,
                "resolution": resolution,
                "background": _abs_url(data.background) if data.background else None,
                # 换场景+数字人组合:scene 作为数字人背景(场景 B),成片即为「数字人立于场景 B」
                "scene": _abs_url(data.scene) if data.scene else None,
                "motion": (data.motion or "").strip() or None,
            }
            materials = [m for m in [source_video, data.scene, digital.image or digital.avatar] if m]
            return await self._create_and_enqueue(
                task_type="render", params={k: v for k, v in params.items() if v is not None},
                user=user, device=data.device, remark=data.remark, materials=materials,
                cost_estimate=await self._estimate("render", duration=data.duration),
            )

        # —— 换场景路线(保留真人,抠出贴到场景 B) ——
        if data.scene:
            scene = _abs_url(data.scene)
            if not prompt and not audio:
                raise HTTPException(status_code=200, detail="换场景需要口播提示词或口播音频")
            gen_defaults = await _load_gen_defaults()
            ratio = normalize_ratio(data.ratio, gen_defaults.get("ratio") or DEFAULT_RATIO)
            resolution = normalize_resolution(data.resolution, gen_defaults.get("resolution") or DEFAULT_RESOLUTION)
            params = {
                "route": "scene_swap",
                "source_video": source_video,
                "scene": scene,
                "prompt": prompt,
                "text": prompt,
                "audio": audio,
                "voice": data.voice,
                "voice_reference": data.voice_reference,
                "duration": data.duration,
                "ratio": ratio,
                "resolution": resolution,
                # 抠像色键:绿幕素材可直接抠出;AI 语义抠像需配置 gen.route.matting(预留)
                "matte_color": "0x00FF00",
            }
            materials = [source_video, scene]
            return await self._create_and_enqueue(
                task_type="render", params=params, user=user, device=data.device, remark=data.remark,
                materials=materials, cost_estimate=await self._estimate("render", duration=data.duration),
            )

        # —— 只换声音(保留真人画面,仅重新配音) ——
        if not prompt and not audio:
            raise HTTPException(status_code=200, detail="请填写口播提示词或提供口播音频")
        params = {
            "route": "voice_only",
            "source_video": source_video,
            "prompt": prompt,
            "text": prompt,
            "audio": audio,
            "voice": data.voice,
            "voice_reference": data.voice_reference,
            "duration": data.duration,
        }
        return await self._create_and_enqueue(
            task_type="render", params=params, user=user, device=data.device, remark=data.remark,
            materials=[source_video], cost_estimate=await self._estimate("render", duration=data.duration),
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
        # 列表页剔除「只在详情页使用」的重字段:原片分镜表与逐镜头逆推描述单条可达数 KB
        # (最多 30 个镜头 + 每个镜头的复刻描述),整页响应会成倍膨胀;详情接口仍完整返回,
        # 前端从 /detail 读取。这里显式构造新 dict,不改动 ORM 对象上的原始 JSON。
        trim_keys = ("shots", "shot_prompts")
        result = []
        for obj in objs:
            item = await self._to_detail(obj, template=tpl_map.get(obj.template_id))
            usage = item.get("usage")
            if isinstance(usage, dict) and any(key in usage for key in trim_keys):
                item["usage"] = {k: v for k, v in usage.items() if k not in trim_keys}
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

    async def detail(self, id: int, user=None, for_admin: bool = False) -> Optional[Dict]:
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="任务不存在")
        self._check_owner(obj, user)
        return await self._to_detail(obj, for_admin=for_admin)

    async def regenerate(self, id: int, user=None, style: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """重新生成:整任务重跑(清空断点)。

        style(可选)用于「换个效果」:只覆盖 creative_level / hook_boost 两个效果旋钮,
        其余参数(素材、时长、形态、意图)保持建单原值 —— 用户不理解"档位",
        只需要"再给我一个不同感觉的版本",因此这里不接受任意参数覆盖,避免误改素材口径。
        不传 style 时行为与改造前完全一致。
        """
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
                params = _build_raw_params(
                    template, obj.materials, obj.remark,
                    ratio=gen_defaults.get("ratio"), resolution=gen_defaults.get("resolution"),
                    duration=getattr(template, "duration", None),
                ) if template else {
                    "template_id": obj.template_id,
                    "prompt": obj.remark or "生成一段高质量短视频",
                    "materials": [_abs_url(u) for u in (obj.materials or [])],
                    "duration": 5,
                }
            else:
                params = {"prompt": obj.remark or ""}
        # 「换个效果」:只覆盖效果旋钮,且必须落在白名单内(非法值归一化,不报错)
        if style:
            params = dict(params or {})
            if style.get("creative_level") is not None:
                params["creative_level"] = normalize_creative_level(style.get("creative_level"))
            if style.get("hook_boost") is not None:
                params["hook_boost"] = normalize_hook_boost(style.get("hook_boost"))
        job_name = JOB_BY_TYPE.get(obj.type or "video", "process_video")
        await self._attach(credit_log_id, obj.id)
        await enqueue_generate_task(job_name, obj.id, _build_notify_url(), params)
        return await self._to_detail(obj)

    async def regenerate_segment(
        self, id: int, segment_index: int, new_text: str,
        user=None, ignore_owner: bool = False,
    ) -> Optional[Dict]:
        """局部重跑(O7,预留接口):只重生成某分段口播并拼回原片,省额度与时延。

        仅视频任务支持;复用整任务重跑的额度预扣与下发链路,只把 params 标记为"局部重跑"
        (带 original_video / segment_index / new_text / _regenerate_segment),由 worker 的
        process_video 分支改走 VideoGenTool.regenerate_segment。
        ignore_owner=True 供管理端调用(管理端无用户归属,可重跑任意任务)。
        """
        obj = await crud.get_by_id(id)
        if not obj:
            raise HTTPException(status_code=200, detail="任务不存在")
        if not ignore_owner:
            self._check_owner(obj, user)
        if obj.type != "video":
            raise HTTPException(status_code=200, detail="仅视频任务支持局部重跑")
        if obj.status == TaskStatusEnum.PROCESSING.value:
            raise HTTPException(status_code=200, detail="任务正在生成中,请稍后")
        original_video = obj.result_video or (obj.params or {}).get("result_video")
        if not original_video:
            raise HTTPException(status_code=200, detail="该任务无成片,无法局部重跑")
        # 分段列表:优先烧字幕时对齐出来的**真实时间轴**,回退建单时的估算脚本。
        # 旧任务可能两者都没有,若不提前拦截,worker 会以"分段下标越界"失败并白跑一轮。
        segments = _timeline_segments(obj)
        if not segments:
            raise HTTPException(status_code=200, detail="该任务缺少分段脚本,无法局部重跑(仅支持带时间轴的新任务)")
        if not (0 <= int(segment_index) < len(segments)):
            raise HTTPException(status_code=200, detail=f"分段下标越界(可选范围 0-{len(segments) - 1})")

        # 局部重跑同样消耗额度(付费订单任务不重复扣减),失败由 callback 原路返还
        cost_est = (obj.params or {}).get("cost") or await self._estimate("video")
        credit_log_id = None
        if user and not obj.order_no:
            credit_log_id = await self._consume(user, "video", cost_est)

        obj.status = TaskStatusEnum.PROCESSING.value
        obj.progress = 0
        obj.result_video = None
        obj.fail_reason = None
        obj.checkpoint = None
        await obj.save(update_fields=["status", "progress", "result_video", "fail_reason", "checkpoint"])

        # 复用原始生成参数,叠加局部重跑标记
        params = dict(obj.params or {})
        if not params:
            template = await template_crud.get_by_id(obj.template_id) if obj.template_id else None
            gen_defaults = await _load_gen_defaults()
            params = _build_raw_params(
                template, obj.materials, obj.remark,
                ratio=gen_defaults.get("ratio"), resolution=gen_defaults.get("resolution"),
                duration=getattr(template, "duration", None),
            ) if template else {
                "template_id": obj.template_id,
                "prompt": obj.remark or "生成一段高质量短视频",
                "materials": [_abs_url(u) for u in (obj.materials or [])],
                "duration": 5,
            }
        # 把真实时间轴覆盖进脚本:worker 的 regenerate_segment 按
        # params.script.segments[i].timing 定位时间窗,不覆盖就会用估算值,
        # 与已烧进成片的字幕时间轴不一致(重跑出来的那一段会与原片错位)。
        if isinstance((obj.usage or {}).get("subtitle_timing"), list) and (obj.usage or {}).get("subtitle_timing"):
            script = dict(params.get("script") or {})
            script["segments"] = segments
            params["script"] = script
        params["original_video"] = original_video
        params["segment_index"] = int(segment_index)
        params["new_text"] = str(new_text or "")
        # 若用户此前编辑过该镜头的复刻描述(已回写到 usage.shot_prompts),则把最新提示词
        # 透传给 worker,使局部重跑采用编辑后的画面描述而非原始台词。
        for it in ((obj.usage or {}).get("shot_prompts") or []):
            if isinstance(it, dict) and int(it.get("index", -1)) == int(segment_index) and it.get("prompt"):
                params["edited_prompt"] = str(it["prompt"])
                break
        params["_regenerate_segment"] = True
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

    async def resume(self, id: int, user=None, ignore_owner: bool = False, for_admin: bool = False) -> Optional[Dict]:
        """断点续跑:从已有 checkpoint 继续,不重复扣额度。

        与 regenerate 的区别:regenerate 清空 checkpoint 并从零重跑(重新扣额度);
        resume 保留 checkpoint,worker 会跳过已完成阶段(例如复用已提交的外部任务 ID 继续轮询)。
        ignore_owner=True 供管理端调用(管理端无用户归属,可续跑任意任务);此时 for_admin=True
        保留原始 fail_reason 供管理端直击重点。
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
        return await self._to_detail(obj, for_admin=for_admin)

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

    async def list_silent_tasks(self, silent_seconds: int) -> List[Dict]:
        """列出"长时间一个回调都没有"的 processing 任务(只观测,不改状态)

        判定口径与 reconcile_stuck 一致(看 update_time,心跳回调会顺带刷新它),但阈值短得多:
        用于在对账真正动作(判失败/续跑)之前先留下告警痕迹。任务可能仍在正常运行
        (如 worker 卡在同步阻塞、或回调链路异常),所以这里只报不动。
        """
        deadline = datetime.now() - timedelta(seconds=int(silent_seconds))
        rows = await GenerateTaskModel.filter(
            status=TaskStatusEnum.PROCESSING.value,
            deleted=False,
            update_time__lt=deadline,
        ).all()
        out: List[Dict] = []
        # update_time 是 timestamptz(Tortoise 返回带时区的 datetime),必须用同类的 UTC 时间相减,
        # 否则 naive/aware 混算直接抛 TypeError(实测会退化成"静默 -1s"这种没法看的告警)。
        now = datetime.now(timezone.utc)
        for obj in rows:
            ref = obj.update_time
            if ref is not None and ref.tzinfo is None:
                ref = ref.replace(tzinfo=timezone.utc)
            try:
                silent = max(0, int((now - ref).total_seconds()))
            except Exception:  # noqa: BLE001 - 兜底:算不出时长也要把任务报出来
                silent = -1
            out.append({
                "id": obj.id,
                "type": obj.type,
                "progress": obj.progress,
                "silent_seconds": silent,
                "update_time": str(obj.update_time),
            })
        return out

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

    async def _to_detail(self, obj, save: bool = True, template=None, for_admin: bool = False) -> Dict:
        """组装任务详情;进度/状态由 worker 异步回调落库,这里只读取并补充展示字段

        template 可由列表页批量预取后传入,避免 N+1 查询;不传时按单条回退查询。
        for_admin=True 时保留 DB 原始 fail_reason 供管理端直击重点;否则对用户脱敏。
        """
        item = obj.to_dict()
        # 用户端脱敏:原始 fail_reason(含网关错误码/返回体)只给管理端看,用户端归一成话术
        if not for_admin and item.get("fail_reason"):
            item["fail_reason"] = friendly_fail_reason(item["fail_reason"])
        # 结构化失败码只在失败态暴露:重跑/续跑后若残留上一次的码,前端会给出过期的动作
        if isinstance(item.get("usage"), dict) and item.get("status") != TaskStatusEnum.FAILED.value:
            item["usage"].pop("fail_code", None)
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
        # 参考图含真人时的处理提示:worker 会把"已丢弃该图(图转文)/已拟态化"写进 usage,
        # 这里透出给 C 端 —— 处理改变了"替换目标"的呈现方式(拟态化后的人物非本人),必须让用户知情。
        item["image_note"] = usage.get("image_note") or ""
        # 降级提示(可观测性):视频编辑失败后会降级成图片链路,成片只是"用上传图重画"、
        # 并未替换原视频元素,用户却看到"生成成功"。这里给用户**可读的结论 + 可执行动作**,
        # 原始原因(usage.degrade_reason)仍完整保留在 DB 供管理端排查。
        item["degrade_note"] = (
            "本条成片由图片参考生成,未替换参考视频中的原有元素;"
            "如需真正的替换效果,可点击「重新生成」重试"
            if usage.get("degraded") else ""
        )
        # 成片自检结果:视频编辑的成片应与参考视频一致(画幅/时长/画质),
        # 不一致基本等价于"没复刻上原片"。worker 只打标不阻断(成片已付费,残缺也比没有强),
        # 这里转成用户看得懂的结论,而不是把"960x960 ≠ 目标 9:16"这类探测值直接抛给用户;
        # 原始探测值放 output_detail,供前端排查入口/管理端展示。
        mismatch = usage.get("output_mismatch")
        if isinstance(mismatch, dict) and mismatch.get("reason"):
            # 画幅已由 worker 自动修正:用户要的是"我的片是竖版了",而不是一句笼统的"有差异"。
            # 修正只覆盖画幅,其余差异(时长/画质)仍要照实说 —— 否则会漏掉真正的复刻失败。
            if mismatch.get("fixed"):
                expected_ratio = str((mismatch.get("expected") or {}).get("ratio") or "")
                actual_size = str((mismatch.get("actual") or {}).get("size") or "")
                note = f"成片画幅已自动转换为 {expected_ratio}(模型原始输出 {actual_size})"
                others = [
                    p for p in str(mismatch.get("reason") or "").split("；")
                    if p.strip() and not p.strip().startswith("画幅")
                ]
                if others:
                    note += ";其余仍与参考视频存在差异,可点击「重新生成」重试"
                item["output_note"] = note
            else:
                item["output_note"] = "成片与参考视频存在差异,可能未完全复刻原片;可点击「重新生成」重试"
            item["output_detail"] = str(mismatch.get("reason") or "")
        else:
            item["output_note"] = ""
            item["output_detail"] = ""
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
            expected = estimate_seconds(obj.type or "video", raw_duration)
            item["remain_seconds"] = max(0, int(expected - elapsed))
            # 已用时长:进度封顶在 88% 后不再变化,前端靠它显示"生成中 12:34",
            # 用户才能区分"仍在跑"与"已卡死"(worker 侧已同时回写 heartbeat)。
            item["elapsed_seconds"] = max(0, int(elapsed))
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
            # 心跳必须顺带刷新 update_time:reconcile_stuck 靠它判定任务是否卡死,
            # 只更新 progress 时 auto_now 字段不在 update_fields 中不会落库,
            # 会把仍在正常心跳的长任务误判为超时。
            await obj.save(update_fields=["progress", "update_time"])
        elif payload.status != TaskStatusEnum.PROCESSING.value and obj.status != TaskStatusEnum.PROCESSING.value:
            # 任务已是终态(成功/失败),忽略重复的终态回调,防止重复返还额度/重复退款
            return
        elif payload.status == TaskStatusEnum.SUCCESS.value:
            obj.status = TaskStatusEnum.SUCCESS.value
            obj.progress = 100
            # update_time 显式落库:指定 update_fields 后 auto_now 不会自动进 UPDATE 语句
            update_fields = ["status", "progress", "checkpoint", "fail_reason", "update_time"]
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
            try:
                await obj.save(update_fields=update_fields)
            except Exception as exc:  # noqa: BLE001
                # 兜底:落库偶发失败(如历史库的 result_video 仍为 VARCHAR(512) 且成片直链超长)
                # 不应让任务永久卡 processing。先剔除可疑大字段、只落「终态」,确保状态能落库;
                # 若仍失败才把异常抛给 route(让 worker 走有限重试),而不是静默卡死。
                logger.error(
                    f"任务成功回写失败 task={payload.task_id}: {exc};尝试仅落终态"
                )
                minimal = [
                    f for f in update_fields
                    if f in ("status", "progress", "checkpoint", "fail_reason")
                ]
                try:
                    await obj.save(update_fields=minimal)
                except Exception as exc2:  # noqa: BLE001
                    logger.error(f"任务终态回写仍失败 task={payload.task_id}: {exc2}")
                    raise
            # 分镜/镜头持久化:把 worker 回写的 usage.shots/shot_prompts/shot_qc 沉淀为可查询实体。
            # 增强能力,任何异常都不影响主任务回调(分镜缺失只意味着无法做分镜级编辑)。
            # 拆解任务(deconstruct)落的是「复刻逆推分镜」,与多段生成的结构记录区分开:
            # 前者是给用户编辑后出片的创作起点,后者是成片核对。
            try:
                from app.services.storyboard import service as storyboard_service
                sb_source = "replicate" if obj.type == "deconstruct" else "multi_segment"
                await storyboard_service.persist_from_usage(
                    payload.task_id, payload.usage, source=sb_source
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"分镜持久化异常(不影响主任务) task={payload.task_id}: {exc}")
            # 预算前置最后一步:按实际用量结算,多扣的退回。
            # 实际用量优先取 worker 上报的 usage.cost(将来接真实 token/时长计费时使用);
            # worker 当前不产出该字段,则回退建单时落库在 params.cost 的预估值 ——
            # 此前只读 usage.cost,该分支永远不触发,「成功结算」形同虚设。
            actual_cost = None
            if isinstance(payload.usage, dict) and payload.usage.get("cost") is not None:
                actual_cost = payload.usage.get("cost")
            elif isinstance(obj.params, dict) and (obj.params.get("cost") or {}).get("cost") is not None:
                actual_cost = (obj.params.get("cost") or {}).get("cost")
            if actual_cost is not None:
                await self._settle_credit(obj, actual_cost)
        elif payload.status == TaskStatusEnum.FAILED.value:
            obj.status = TaskStatusEnum.FAILED.value
            obj.fail_reason = (payload.fail_reason or "")[:255]
            # 结构化失败码随 usage 落库:用户端文案只说"失败了",前端要靠 fail_code 才能
            # 给出可执行的下一步(换素材 / 去数字人 / 直接重试)。成功分支会用 worker 的
            # usage 整体覆盖,失败码自然被清掉,不会残留到下一次重跑。
            if payload.fail_code:
                obj.usage = {**(obj.usage or {}), "fail_code": payload.fail_code}
            # 失败保留 checkpoint,供用户「断点续跑」从断点处继续(无需重新扣额度)
            # 同步刷新 update_time,与成功/心跳分支保持一致,供卡死巡检判断活性
            await obj.save(update_fields=["status", "fail_reason", "usage", "update_time"])
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
