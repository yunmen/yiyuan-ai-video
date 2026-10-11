# -*- coding: utf-8 -*-
'''
@文件    :video_tool.py
@说明    :视频生成工具(真实接入)— OpenAI 兼容网关 /videos 提交 + 轮询到终态
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :2.0
@说明    :底层使用 AsyncOpenAI 异步 SDK,全链路 async。
          支持文生视频(t2v)/图生视频(i2v)/参考生视频(r2v);
          生成结果通过 ToolResult.metadata 携带 success/error_type/用量,
          失败不抛异常,由上层 service 统一转成 failed 回调。
'''
import asyncio
import base64
import copy
import json
import os
import re
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

from app.schemas.base import ToolResult, Usage
from app.tools.base import BaseGenTool
from app.tools.prompt_template import build_prompt_optimize_system
from skills.prompt_library import (
    INTENT_FALLBACK_LABEL,
    _append_replicate_format,
    build_asset_script_prompt,
    build_shot_qc_prompt,
    build_shot_reverse_prompt,
    build_video_generation_prompt,
    intent_labels,
    parse_asset_script,
    parse_shot_prompts,
    parse_shot_qc,
    parse_video_prompts,
)
# 主角表现等后端可选增强资产经 skills.prompts 加载(资产缺失时回退内联兜底,不阻断主链路)
from skills.prompts import safe_render
from app.tools.script_anchor import (
    build_script,
    estimate_timing,
    render_anchor_hint,
    resolve_tracks,
)
from app.settings import config
from app.services.element_binding import build_binding_directive
from app.core import compose
from app.core import deidentify
from app.core import frame_quality
from app.core import gateway
from app.core.retry import with_transient_retry
from app.core import media_prep
from app.core import metrics
from app.core import multiseg
from app.core import shots
from app.core import subtitle
from app.core.asset_cache import ASSET_OPTIMIZED_PROMPT, build_cache_key
from app.core import asset_cache
from app.core.plugin import logger
from app.utils.oss import download_to_local, persist_url_list, upload_local_file

# 九宫格分镜运镜镜头语言:逐镜循环注入,让 i2v 模型理解"推拉摇移"意图。
# 与 i2v 后的轻度 Ken Burns 兜底(zoompan)构成"提示词 + 后处理"双保险。
STORYBOARD_CAMERA_MOVES: List[str] = [
    "镜头缓慢向前推近(push in),聚焦主体细节",
    "镜头缓慢向左横移(pan left),展现主体与环境关系",
    "镜头缓慢拉远(pull out / zoom out),呈现整体场景",
    "镜头向右横移(pan right),带出下一个视觉重点",
    "镜头轻微环绕(orbit),增强空间立体感",
    "镜头向上摇移(tilt up),从产品过渡到使用场景",
    "镜头向下摇移(tilt down),从场景落到产品主体",
    "固定机位微距特写,缓慢呼吸式推拉,突出质感",
    "镜头缓慢环绕主体(slow orbit),制造电影感运镜",
]

# 主角表现档位 → (提示词资产名, 内联兜底正文)。与 backend app/services/prompt_builder.py 的
# LEAD_ACT_PROMPT_NAMES / DEFAULT_LEAD_ACT_TEXTS 同源;正文单一来源是
# backend/skills/prompts/generation/replace/gen_lead_act_<key>.md,worker 经 skills.prompts 引用。
# "跟随原片"(inherit)不需要任何指令,故不在表内 —— 缺键即不追加。
LEAD_ACT_ASSETS: Dict[str, Tuple[str, str]] = {
    "dance": (
        "gen_lead_act_dance",
        "在完整保留参考视频动作与情节走向的前提下,让新主角在原片关键节点加入舞蹈/律动式表演,"
        "不得删除、缩短或改写原片的镜头、事件与节奏",
    ),
    "pitch": (
        "gen_lead_act_pitch",
        "在完整保留参考视频动作与情节走向的前提下,让新主角在原片关键节点自然转入展示与推广表演"
        "(展示商品、口播卖点、行动号召),不得删除原片镜头与事件,也不得改造成无关的纯广告片",
    ),
}

# 视频模型支持的时长档位(秒):方舟 seedance 只认 5/10,传 15 会直接 400(InvalidParameter)
# 与 backend app/services/gen_rules.py 的 SUPPORTED_DURATIONS 保持一致(有契约测试兜底)
# 换到支持连续时长的模型(Seedance 2.x 支持 4~15s)后,由系统配置 gen.video_durations 放开。
SUPPORTED_DURATIONS = (5, 10)

# 分辨率档位(由高到低):模型不接受当前档位时按此顺序降档重试。
# 与 backend app/services/gen_rules.py 的 SUPPORTED_RESOLUTIONS 保持一致(唯一事实源),
# 不得自行多出 backend 不接受的档位(如 480p)——否则降档链会白提交一次必然被拒的请求。
_RESOLUTION_LADDER = ("1080p", "720p")


def _is_resolution_error(exc: Exception) -> bool:
    """异常是否为「该分辨率不被模型支持」

    方舟的报错形如:
      The parameter `contents[0].text.resolution` specified in the request is not valid:
      the specified resolution is not supported for model doubao-seedance-2-0-fast-r2v
    这类错误换参数就能过,值得降档重试;其他错误(余额/鉴权/素材)重试也没意义。
    """
    return "resolution" in str(exc).lower()


# 网关对「视频编辑请求体」形态的偏好(键:能力@网关地址 → 上次成功的形态)。
# 顶层 videos 是**内部约定**,部分中转站会静默丢弃它 → 编辑请求退化成"按 prompt 重新生成":
# 成片画幅/时长/内容都不像原片,而且**不报错**(实测:原片 540x1168 竖屏,成片 1280x720 横屏)。
# 方舟原生形态(content[] 内 video_url + 顶层 ratio=adaptive / duration=-1)才带得动参考视频,
# 但中转站未必认得。故两种形态都试,并记住真正可用的那一种,避免每单都白试一次。
_BODY_SHAPE_PREF: Dict[str, str] = {}

# 请求体形态被网关拒绝时的状态码(参数/端点不符),区别于鉴权/限流/内容审核等业务错误
_BODY_SHAPE_STATUS = (404, 405, 415, 422)
# 400 同时承载"形态不符"与"内容审核"两种语义:命中这些关键词时按审核处理,不换形态重试
_CONTENT_ERROR_HINTS = ("sensitive", "privacy", "real person", "risk", "audit", "content")


def _status_of(exc: Exception) -> Optional[int]:
    """从异常里取 HTTP 状态码(SDK 异常带 status_code,兼容 response.status_code)"""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _is_body_shape_error(exc: Exception) -> bool:
    """异常是否为「请求体形态不被该网关接受」(换形态有机会成功)

    只认参数/端点类错误:鉴权、限流、余额、内容审核换形态也是原样失败,白试一次而已。
    400 混用两种语义 —— 命中审核关键词时按业务错误处理(真人拦截依赖这个判定去走兜底)。
    """
    status = _status_of(exc)
    if status in _BODY_SHAPE_STATUS:
        return True
    if status != 400:
        return False
    text = str(exc).lower()
    return not any(hint in text for hint in _CONTENT_ERROR_HINTS)


# 参考视频最低像素要求(未在后台按模型配置时的兜底门槛)。
# 取 407696 = 方舟 r2v/v2v 明确要求的下限(task 58/59 的 400 原文数字)。
# 这是**保守兜底**:后台 gen.video_min_reference_pixels 配了更宽松/更严格的值就以后台为准;
# 拿不到确切门槛(模型名未命中)时直接关闭校验,绝不猜门槛误杀正常任务。
_DEFAULT_MIN_REFERENCE_PIXELS = 407696

# 参数类错误的特征词:请求体本身不合模型要求(分辨率/像素数/时长/字段名/取值范围)。
# 命中即认为「换网关也是同一份参数、结果必然一样」,不再做故障转移。
_PARAM_ERROR_HINTS = (
    "invalidparameter",
    "invalid parameter",
    "parameter",
    "must be",
    "must not",
    "not valid",
    "exceed",
    "out of range",
    "unsupported",
    "invalid_value",
    "invalidvalue",
)


def _is_request_param_error(exc: Exception) -> bool:
    """异常是否为「参数类错误」——换网关也不会变好,故不做故障转移。

    只认 400/422:这两码承载的是「请求体不合要求」而非服务端/鉴权/限流问题。
    以下仍**必须**转移,因为换个网关确实可能通:
      - 401/403 鉴权失败(该网关的 key 没权限,换一把 key 有用);
      - 429 限流(换网关/换地区有用);
      - 5xx 服务端错误(换网关有用);
      - 404/405/415 端点或请求体形态不符(不同网关暴露的端点不同,换网关有用)。

    实测代价(task 58/59):方舟报 400「参考视频像素数不足」→ 仍切到中转站重打一次 →
    同样失败 → 最终对外报的仍是方舟那句错误,中转站那次纯属白打(还多花约 5s 与一份配额)。
    """
    if _status_of(exc) not in (400, 422):
        return False
    # 400/422 也可能是审核类业务错误(真人拦截等),那属于"换个网关也许能过",
    # 判定权仍交给既有的 _is_body_shape_error / 审核关键词逻辑,这里不做否决。
    text = str(exc).lower()
    return any(hint in text for hint in _PARAM_ERROR_HINTS)


# 已知的模型分辨率上限(键为模型名子串):方舟 Seedance 2.0 的 r2v/v2v 变体**只支持 720p**,
# 传 1080p/1080P 会被 400 拒绝。提前压档,既省掉一次注定失败的提交,也避免白跑一轮网关故障转移。
# 该默认仅作回退;真实生效的上限来自后台可配 gen.video_resolution_cap(见 _resolution_caps),
# 切换到支持 1080P 的编辑模型时运维直接放开即可,无需改代码。
_MODEL_RESOLUTION_CAP = {
    "seedance-2": "720p",
}


def _resolution_caps() -> Dict[str, str]:
    """解析清晰度上限映射:优先读后台 gen.video_resolution_cap(模型名子串:档位,分号分隔),
    如 'seedance-2:720p;some-1080p-model:1080p';未配或非法回退内置 _MODEL_RESOLUTION_CAP。
    """
    raw = (getattr(config, "VIDEO_RESOLUTION_CAP", "") or "").strip()
    caps: Dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if ":" not in part:
            continue
        name, cap = part.split(":", 1)
        # 档位统一小写,与 _RESOLUTION_LADDER(1080p/720p/480p)及 _MODEL_RESOLUTION_CAP 保持同形,
        # 否则 _cap_resolution 里 _RESOLUTION_LADDER.index(cap) 会因大小写不一致抛 ValueError
        name, cap = name.strip().lower(), cap.strip().lower()
        if name and cap in ("720p", "1080p"):
            caps[name] = cap
    return caps or dict(_MODEL_RESOLUTION_CAP)


# prompt 改写(chat)单次请求超时(秒)。实测方舟上的 GLM 端点偶发抖动:
# 30s 会直接 timeout 并静默回退原始 prompt(丢掉改写收益),放宽到 90s。
# 注意:openai SDK 默认还会重试 2 次,所以最坏耗时 ≈ 90s × 3。
CHAT_REWRITE_TIMEOUT = 90

# 成片转存 OSS 的整体超时(秒):转存 = 下载模型直链 + 同步 SDK 上传自有 COS。
# 后者(oss.put_object)会从"慢"退化成"静默挂起"(task 5 实测:5.9MB 走了 5m37s),
# 而它跑在 asyncio.to_thread 里、没有外层超时 —— 一旦挂住,任务就永久停在 processing,
# 且此时进度已到 88、心跳已退出,后端与前端完全看不到动静,与真卡死无从区分。
# 超时按失败处理:由下面 persist_error 分支交回 service 层重试(实测日志"第 1/3 次,10s 后重试"),
# checkpoint 此时已停在 stage=3,重试只重新转存、不重新提交外部任务(不重复扣生成费)。
# 取 120s:正常转存(下载直链 + 上传)3~9s,但实测出现过一次走完 80s 才成功的情况(task 17),
# 90s 与它只差 10s、余量偏紧,放宽到 120s 保留约 1.5 倍余量;且必须**大于 SDK 超时(60s)** ——
# 让"慢"先由 SDK 自己失败(SDK 失败会真正结束请求、释放线程),外层只兜底。
# ⚠️ 为什么不能取 15~20s:wait_for 超时只是取消协程,杀不掉 asyncio.to_thread 里的线程,
# 被掐断的上传会变成僵尸继续跑到 SDK 超时为止,占住线程池(默认 8 个)不放 ——
# 重试的新上传还要和它抢带宽,越重试越慢;重试很快耗尽 → 任务失败、成片丢失(已扣费)。
# 快速失败的实际收益由 SDK 60s 超时拿到,外层不需要再激进。
PERSIST_TIMEOUT = 120
# 转存的内层尝试次数与间隔。注意上面还有一层:service 层的整体重试(日志"第 1/3 次,10s 后重试",
# 且它复用 stage=3 的 checkpoint —— 只重新转存、不重新生成、不重复扣费,task 16 实测走通)。
# 所以这里取 2 次做**就地**自愈就够了:偶发挂起多半第 2 次就成,间隔比 service 层(10s)更短;
# 再往上叠加只会拉长最坏耗时,而不会提高最终成功率。最坏 2×120+5=245s,仍小于原单次 480s。
PERSIST_ATTEMPTS = 2
PERSIST_RETRY_GAP = 5.0
# 转存耗时告警阈值(秒):正常 3~9s,实测出现过 80s。超过就打 WARNING 并带上"距超时还剩多少",
# 用来判断 PERSIST_TIMEOUT 的余量是否还够 —— 若日志里频繁出现剩余余量逼近 0,
# 说明 COS/带宽侧有波动,该排查链路而不是继续加大超时。日志统一带"转存耗时"便于检索。
PERSIST_SLOW_THRESHOLD = 30

# 逐镜头逆推送多模态模型的画面宽度(px):逆推只需要看清景别/主体/构图,
# 原分辨率会把图片 token 放大数倍,收益极小。
SHOT_FRAME_WIDTH = 512

# 逐镜头质检的"低分"线(0-100):低于它就在日志里点名,便于快速定位是哪个镜头没复刻上。
# 刻意不据此自动重跑 —— 重跑会产生新的模型费用,属于必须单独确认的行为变更。
SHOT_QC_LOW_SCORE = 70


def _cap_resolution(model: Optional[str], resolution: Optional[str]) -> Optional[str]:
    """把分辨率压到该模型实际支持的上限内(不改变认不出的档位,交给降档逻辑兜底)"""
    if not model or not resolution:
        return resolution
    current = resolution.strip().lower()
    if current not in _RESOLUTION_LADDER:
        return resolution
    name = model.lower()
    for key, cap in _resolution_caps().items():
        # 档位表由高到低,索引越大档位越低;当前高于上限就压到上限
        if key in name and _RESOLUTION_LADDER.index(current) < _RESOLUTION_LADDER.index(cap):
            return cap
    return resolution

# 连续区间的上限保护:超过这个秒数多半是配置写错(如 4-150)
MAX_DURATION = 60


def parse_duration_gears(text: Any) -> tuple:
    """解析时长档位配置:"5,10"(离散档) / "4-15"(连续区间)

    与 backend gen_rules.parse_duration_gears 同一语义;空或非法返回空元组,
    表示"不覆盖" —— 配置写错不会让任务提交必然失败的时长。
    """
    raw = str(text or "").strip()
    if not raw:
        return ()
    if "-" in raw or "~" in raw:
        parts = re.split(r"[-~]", raw, maxsplit=1)
        try:
            lo, hi = int(parts[0].strip()), int(parts[1].strip())
        except (TypeError, ValueError, IndexError):
            return ()
        if lo <= 0 or hi > MAX_DURATION or lo > hi:
            return ()
        return tuple(range(lo, hi + 1))
    gears = []
    for part in raw.split(","):
        item = part.strip()
        if not item.isdigit():
            return ()
        gears.append(int(item))
    gears = sorted({g for g in gears if 0 < g <= MAX_DURATION})
    return tuple(gears)

# 内网/本机素材地址:模型侧无法拉取(方舟会报 resource download failed),需先转成可访问形式
_PRIVATE_URL_RE = re.compile(
    r"^https?://("
    r"localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
    r"|169\.254\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+"
    r"|host\.docker\.internal|\[::1\]"
    r")([:/]|$)",
    re.I,
)

# 视频素材扩展名:这类素材**不能**作为参考图塞进 r2v 的 images 字段 ——
# 上游收到 images 里的视频地址会直接判任务失败(实测:任务 19 秒即返回 upstream_task_failed)。
_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv"}


def _is_video_url(url: str) -> bool:
    """按扩展名判断素材是否为视频(忽略查询串与锚点,大小写不敏感)"""
    path = str(url or "").split("?")[0].split("#")[0]
    return os.path.splitext(path)[1].lower() in _VIDEO_EXTS


def _split_media(materials: List[str]) -> tuple:
    """把素材按类型拆成(图片列表, 视频列表),各自保持原有顺序"""
    images: List[str] = []
    videos: List[str] = []
    for item in materials:
        (videos if _is_video_url(item) else images).append(item)
    return images, videos


def _replace_assets(params: dict) -> List[str]:
    """取本任务的**替换素材**(图片资产):凡是要下发 images 的生成入口共用同一取法

    为什么必须收敛成一个函数:首轮生成、超时长多段、局部重跑是三条独立入口。
    此前各自读一遍 `params["materials"]` —— 局部重跑的**视频编辑分支甚至完全没传 images**,
    于是「改一句台词重生成」会把首轮替换进去的商品/人物换回原片元素,
    用户看到的就是"重跑一次,复刻白做了"。P1-6 要修的正是这个:同一任务内资产必须一致。

    视频素材一律剔除:它由 reference_video 单独承载,混进 images 会被上游直接判任务失败。
    """
    assets: List[str] = []
    for item in params.get("materials") or []:
        url = str(item or "").strip()
        if url and not _is_video_url(url) and url not in assets:
            assets.append(url)
    return assets


def _should_edit_first(ref_len: Optional[float], max_seconds: float) -> bool:
    """是否优先走单段视频编辑(而非多段拼接):

    - 时长探测失败(ref_len 为 None)不假设成短片,改走多段拼接 —— 多段对未知时长更稳,
      避免按模板吸附时长错误把长片裁短(D9)。
    - 探测成功且 ≤ 上限 → 单段编辑;超过上限 → 多段拼接。
    """
    return ref_len is not None and ref_len <= max_seconds


def _intent_text(intent: List[str]) -> str:
    """替换意图 → 「商品」/「商品、人物」这类中文短语;识别不出时回退「元素」

    标签表放在 skills.prompt_library:用户看到的失败原因与逐镜头逆推里的
    「要替换/要保留」措辞共用同一份,避免两处各写一套标签而漂移。
    失败原因必须用用户看得懂的说法,不能只回一串英文错误码。
    """
    return "、".join(intent_labels(intent)) or INTENT_FALLBACK_LABEL


# 参考图含真人时的处理策略(后台 gen.image_real_person_mode 可热更新):
#   drop    = 丢弃被拦的图,改按已有的视觉识别文字描述生成(零额外成本、必然过检测)
#   stylize = 先用图生图把真人图拟态化为非写实风格再提交(保留"有个人"但非本人形象)
# 注意:不能像视频那样直接打码 —— 图片正是要被替换成的目标,糊掉等于没有目标。
IMAGE_FIX_DROP = "drop"
IMAGE_FIX_STYLIZE = "stylize"


def _image_fix_mode() -> str:
    """参考图真人处理策略:读后台 gen.image_real_person_mode,非法值一律回退 drop

    系统默认已为 stylize(拟态化);仅当配置值非法时回退 drop 作为安全侧 ——
    stylize 依赖图片生成能力且多一次付费调用,配置写错不能让它静默生效。
    """
    raw = str(getattr(config, "IMAGE_REAL_PERSON_MODE", "") or "").strip().lower()
    return raw if raw in (IMAGE_FIX_DROP, IMAGE_FIX_STYLIZE) else IMAGE_FIX_DROP


def _normalize_real_person_strategy(v) -> Optional[str]:
    """把前端/后端下发的真人处理策略归一化为 worker 内部取值。

    auto/未传 → None(表示"沿用系统配置 gen.image_real_person_mode");
    stylize/drop → 原样返回,用于 per-task 显式覆盖系统默认;其余非法值一并回退 None。
    """
    if not v:
        return None
    v = str(v).strip().lower()
    if v == "auto":
        return None
    return v if v in (IMAGE_FIX_DROP, IMAGE_FIX_STYLIZE) else None


# LLM 脚本改写系统提示由 app/tools/prompt_template.py 按本次任务的画幅/清晰度渲染,
# 这里不再写死画幅(此前硬编码「竖版 9:16」,与可配置的 gen.video_ratio 会互相矛盾)。


class VideoGenTool(BaseGenTool):
    """视频生成工具 — 三种模式:文生/图生/参考生,提交任务 + 轮询完成。

    成功:ToolResult.content 为视频 URL,metadata.success=True 并附用量;
    失败:ToolResult.content 为错误信息,metadata.success=False 并附 error_type/error。
    """

    name = "video"
    description = "视频生成(文生/图生/参考生)"
    # 能力路由名:子类可覆盖(如数字人口播走 gen.route.digital),复用同一套提交+轮询机制
    capability = "video"
    # 参数类错误不做网关故障转移:同一份请求体打给下一个网关必然同样失败,
    # 继续转移只是白打一次、拖慢几秒,并把真实错误埋进备选网关的报错里
    # (实测 task 58/59:方舟 400 像素数不足 → 仍白切一次中转站 → 才失败)。
    # 鉴权/限流/服务端错误/端点形态不符仍要转移 —— 那些换个网关确实可能通。
    failover_stop_on = staticmethod(_is_request_param_error)

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        poll_interval: Optional[int] = None,
        poll_timeout: Optional[int] = None,
    ):
        gw = gateway.resolve(self.capability)
        self.api_key = api_key or gw["key"] or config.LLM_BASE_API_KEY
        self.base_url = (base_url or gw["url"] or config.LLM_BASE_API_URL).rstrip("/")
        # 协议:显式配置优先;若构造时传入 base_url(如测试),按 URL 嗅探
        self.proto = gw["proto"] if not base_url else gateway.auto_proto(self.base_url)
        self._pinned = bool(base_url)
        self.poll_interval = poll_interval or config.VIDEO_POLL_INTERVAL
        self.poll_timeout = poll_timeout or config.VIDEO_POLL_TIMEOUT
        if not self.api_key:
            raise RuntimeError("未配置视频网关 API_KEY,无法调用视频生成接口")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        self.task_prefix = uuid4().hex  # 结果转存 OSS 时的文件名前缀
        self._chat_clients: Dict[str, AsyncOpenAI] = {}  # prompt 改写专用 client 缓存(按 chat 网关地址)
        self._notify_url: Optional[str] = None  # P2:资产缓存接口基址(由 generate 从 params 注入)
        self._real_person_strategy: Optional[str] = None  # per-task 真人处理策略(由 generate 从 params 注入)
        # 多图分组识别结果(role → 描述,由 generate 从 params.subjects 注入):
        # 给强制替换指令提供「新主体长什么样」的文字语义,替代纯"看图意会"。
        self._replace_subjects: Dict[str, Any] = {}
        # 主角表现档位(由 generate 从 params.lead_act 注入):仅"换人物"时生效,
        # 决定新主角以什么方式表演(跳舞/推广);空串=跟随原片(不追加任何指令)。
        self._lead_act: str = ""
        # 低分镜头自动重跑开关:默认关闭(重跑会产生额外模型费用,绝不在代码里静默开启)。
        # 真实取值由 generate 按「任务显式 qc_auto_retry → 全局配置」覆盖;此处给默认值,
        # 保证直接调用内部方法(如单测直调 _generate_multi_segment)也不会因属性未定义而崩。
        self._qc_auto_retry: bool = False

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        """按素材数量自动选择生成模式:1 张图→图生,多张图→参考生,无素材→文生。

        支持断点续跑:checkpoint 携带已完成阶段(stage)与中间产物,各阶段完成后通过 on_stage 回写。
        阶段划分:1=改写 prompt 完成;2=已提交外部任务(external_task_id);3=已轮询拿到 raw_url(仅需转存)。
        """
        checkpoint = checkpoint or {}
        stage = int(checkpoint.get("stage", 0) or 0)

        # backend 已按结构化上下文组装好 prompt_context(模板结构/商家信息/生成模式),
        # 旧任务没有该字段时回退扁平 prompt,行为与改造前一致。
        prompt_context = (params.get("prompt_context") or "").strip()
        prompt = prompt_context or params.get("prompt") or params.get("template_title") or "生成一段高质量短视频"
        materials: List[str] = [m for m in (params.get("materials") or []) if m]
        # 原始请求时长:优先取**未吸附**的 duration。
        # duration 与 gen_duration 同源(都来自模板时长),但 gen_duration 是"模型档位" ——
        # 在档位配置尚未生效(新增配置、服务刚启动、缓存未刷新)时会把 30 压成 10,
        # 那样多段分支永远进不来(实测踩过:backend 侧配置是好的,但存在加载窗口)。
        raw_duration = params.get("duration") or params.get("gen_duration")
        duration = self._clamp_duration(raw_duration)
        # **原始**请求时长(未吸附):多段生成必须用它 —— 吸附是按"模型单段档位"设计的,
        # 30s 会被吸附成 10s,那样永远进不了多段分支(实测踩过)。
        try:
            requested_duration = int(float(raw_duration))
        except (TypeError, ValueError):
            requested_duration = duration
        # 上界保护:超大值多半是脏数据,按"最多 4 段"处理,避免拆成几十段
        requested_duration = min(requested_duration, multiseg.MAX_SEGMENT_SECONDS * 4)
        ratio = params.get("ratio") or config.VIDEO_RATIO
        resolution = params.get("resolution") or config.VIDEO_RESOLUTION
        gen_mode = params.get("gen_mode") or ("t2v" if not materials else ("i2v" if len(materials) == 1 else "r2v"))
        material_hint = params.get("material_hint") or f"{len(materials)} 张素材"
        # 词锚点脚本(P0,旧任务无此字段时为空 → 全流程不受影响)
        script_anchors = params.get("script") or {}
        self.task_prefix = str(params.get("_task_id") or uuid4().hex)
        self._notify_url = params.get("_notify_url")
        # per-task 真人处理策略(覆盖系统配置 gen.image_real_person_mode):auto/未传 → 沿用系统默认
        self._real_person_strategy = _normalize_real_person_strategy(params.get("real_person_strategy"))
        # 替换主体的文字语义(backend classify_subjects 识别,随 params.subjects 下发):
        # 强制替换指令据此写出「把商品换成什么样」,而不是只说"换成参考图里的东西"。
        _raw_subjects = params.get("subjects")
        self._replace_subjects = dict(_raw_subjects) if isinstance(_raw_subjects, dict) else {}
        self._image_slots = params.get("image_slots") or {}
        self._material_groups = params.get("material_groups") or []
        self._reference_elements = params.get("reference_elements") or []
        # 新旧后端字段兼容；空串表示沿用原片表演结构。
        self._replicate_format = str(params.get("replicate_format") or params.get("format") or "").strip()
        # 主角表现档位(仅"换人物"生效):白名单外的值一律视为"不指定"= 跟随原片,
        # 行为与改造前完全一致(老任务/老客户端不受影响)。
        self._lead_act = str(params.get("lead_act") or "").strip().lower()
        # 创意档位/开头钩子/专家追加要求(可选):透传自 backend 建单参数,
        # 生成链路(单段编辑 + 多段逆推)据此注入确定性指令,不指定则沿用原片结构。
        self._creative_level = str(params.get("creative_level") or "").strip().lower()
        self._hook_boost = str(params.get("hook_boost") or "").strip().lower()
        self._asset_override = str(params.get("asset_override") or "").strip()
        # 低分镜头自动重跑:默认沿用全局配置(关闭)。建单显式传 qc_auto_retry 时按任务覆盖 ——
        # 重跑会产生新的模型费用,因此只接受"显式开启",绝不在代码里静默改成默认开启。
        _qa = params.get("qc_auto_retry")
        self._qc_auto_retry = bool(config.VIDEO_QC_AUTO_RETRY) if _qa is None else bool(_qa)

        logger.info(
            f"[VideoGenTool] 生成模式选择 gen_mode={gen_mode} materials={len(materials)} duration={duration} "
            f"ratio={ratio} resolution={resolution} hint={material_hint} prompt={prompt[:60]}"
        )
        # 九宫格分镜编排:9 张分镜图 → 逐图 i2v + 运镜 + 转场合成一条视频。
        # 必须优先于通用单/多图链路:素材为 9 图时,自动选择逻辑会误判为 r2v(多图融合成一段),
        # 与"每个分镜各自成片再拼接"的诉求相悖。
        if gen_mode == "storyboard":
            return await self._generate_storyboard(
                prompt, materials, duration, ratio, resolution,
                checkpoint=checkpoint, on_stage=on_stage,
            )
        # 阶段1:prompt 改写(可复用缓存,跳过 LLM 调用)
        if stage >= 1 and checkpoint.get("optimized_prompt"):
            prompt = checkpoint["optimized_prompt"]
            logger.info(f"[VideoGenTool] 断点续跑:复用缓存 prompt,跳过 LLM 改写 task={self.task_prefix}")
        else:
            # 结构化上下文里已含 [生成模式] 段(含素材语义),不再重复拼接「素材:」行,
            # 否则同一句素材说明出现两次,稀释模型注意力;旧任务回退扁平 prompt 时才补上。
            user_content = prompt if prompt_context else f"{prompt}\n素材:{material_hint}"
            # 词锚点(P0):把叙事分段与「第 N-N 词」窗口喂给改写模型,
            # 让它知道哪句台词是重点窗口,而不是整段等权处理。
            if script_anchors.get("segments"):
                user_content = f"{user_content}\n{render_anchor_hint(script_anchors)}"
            # 画幅按本次任务实际参数注入;i2v 的画幅由首帧图片决定,提示词里不指定
            # 视频编辑/复刻(gen_mode=v2v)改用编辑专用系统提示:保持原片结构与体裁、只按替换指令改元素,
            # 否则带货营销基调会把非广告原片强行改写成广告片(实测:换人物出广告片)
            system_prompt = build_prompt_optimize_system(
                ratio=None if len(materials) == 1 else ratio, resolution=resolution,
                edit=(gen_mode == "v2v"),
            )
            prompt = await self._optimize_prompt(user_content, system_prompt)
            if on_stage:
                await on_stage(1, {"optimized_prompt": prompt})

        reference_video = str(params.get("reference_video") or "").strip()
        # 替换意图(换产品/换人物/换场景):用户明确要求替换**参考视频里的元素**。
        # 有替换意图时,视频编辑是唯一能达成该意图的链路 —— 降级到图片链路会退化成
        # "用上传图重画整片":参考视频被整个丢弃,成片画幅/时长/场景/运镜全都跟着上传图走,
        # 看似成功、实则没做替换,用户既拿不到想要的效果也拿不回额度(实测踩过,
        # 见 docs/换产品问题排查.md)。故有意图时编辑失败即失败,不再降级。
        replace_intent = [str(i).strip() for i in (params.get("intent") or []) if str(i).strip()]
        # 复刻目标形态(可选):与拆解链路同源(同样读 params.format),后端建单与拆解都会下发。
        # 保证"理解原片"与"重塑出片"用的是同一个形态,否则两次逆推会互相打架。
        replicate_format = str(params.get("format") or "").strip()
        # 复刻脚本兜底:纯复刻常只有对标视频、没有口播文案 —— 没有文案就没有 TTS 配音,
        # 也没有字幕。补一份后重建词锚点,让配音与字幕都能用上(否则锚点仍指向空脚本,
        # 字幕照样烧不出来)。生成失败保持"无文案"的历史行为。
        if reference_video and not self._script_text(params, script_anchors):
            generated_script = await self._build_replicate_script(
                reference_video, requested_duration, replace_intent, params,
            )
            if generated_script:
                params["script_text"] = generated_script
                script_anchors = build_script({"script": generated_script}) or script_anchors
                logger.info(f"[VideoGenTool] 复刻脚本兜底生成成功: {len(generated_script)} 字")
        # 素材里混入的视频**不能**当参考图传给 r2v(上游会直接判任务失败),
        # 这里与 reference_video 同源处理:提升为参考视频、交给视频编辑链路;
        # 未配置编辑模型时明确失败并说明原因,不静默丢弃视频素材
        # (丢掉视频只拿图生成 = 成片与用户上传意图不符,比直接失败更糟)。
        material_images, material_videos = _split_media(materials)
        if material_videos and not reference_video:
            if not config.VIDEO_MODEL_EDIT:
                return self._fail(
                    f"素材含 {len(material_videos)} 个视频,但未配置视频编辑模型"
                    "(gen.video_model_edit),无法按参考视频生成,请配置后重试",
                    "config_error",
                )
            logger.info(
                f"[VideoGenTool] 素材含视频,提升为参考视频走视频编辑 task={self.task_prefix}: "
                f"videos={len(material_videos)} images={len(material_images)}"
            )
            reference_video = material_videos[0]
            materials = material_images
        # 编辑链路优先于多段拼接:编辑模型用 duration=-1,成片时长**跟随被编辑视频** ——
        # 这正是"上传多长就生成多长"的语义。
        # 若先按模板时长走多段拼接,23s 的参考视频会被切成 15+8 生成两段再拼:
        # 多花一次钱,还破坏跨段一致性(镜头衔接处最明显)。
        # 只有参考视频超出编辑上限(30s,超出部分会被裁掉)时,才退回多段拼接以保住总时长。
        from app.core import media_prep
        # 参考视频真实时长(秒):编辑成片时长与字幕基准都用它,探测失败时保持 None
        ref_len: Optional[float] = None
        # 字幕/时间轴的时长基准。图片链路成片就是吸附档位;编辑链路成片**跟随参考视频**
        # (方舟 duration=-1),用吸附档位会让 23.5s 成片的字幕全挤在前 10s。
        script_duration = duration
        edit_first = False
        if reference_video and config.VIDEO_MODEL_EDIT:
            ref_len = await media_prep.probe_duration(reference_video)
            # 参考视频真实时长作为编辑/多段的总时长基准,实现"上传多长生成多长";
            # 模板时长仅在无参考视频(图生视频/参考生视频)时作为默认值。
            # 否则 >30s 的原片会被多段分支用模板时长(如 15s)截断,丢失后半段。
            if ref_len:
                requested_duration = min(ref_len, multiseg.MAX_SEGMENT_SECONDS * 4)
            edit_first = _should_edit_first(ref_len, media_prep.video_edit_max_seconds())
        # 逐镜出片(九宫格链路):N 张分镜图 → 每张独立成段 → 拼接。
        # 触发必须显式 shot_mode=per_shot:历史行为「多图 → r2v(参考图生视频)」
        # 不能被新增分支改变,老任务/其它入口的多图链路必须保持原样。
        if (
            not reference_video
            and len(material_images) >= 2
            and str(params.get("shot_mode") or "").strip() == "per_shot"
        ):
            result = await self._generate_per_shot(
                material_images, prompt,
                per_shot_seconds=int(params.get("per_shot_seconds") or 5),
                ratio=ratio, resolution=resolution,
                shot_prompts=[str(p) for p in (params.get("shot_prompts") or [])] or None,
                script_text=self._script_text(params, script_anchors),
            )
            if (result.metadata or {}).get("success", True):
                # 字幕/时间轴按成片真实总时长(段数 × 每段),不能用单段吸附值,
                # 否则 30s 成片的字幕会全部挤在前 5s。
                total = int((result.metadata or {}).get("seconds") or 0) or duration
                self._attach_script_meta(result, script_anchors, total)
                self._set_output_seconds(result, total)
            return result
        # 时长超出模型单段上限(Seedance 2.x ≈15s)→ 分段生成再拼接。
        # 独立路径:只在「有参考视频 + 超上限」时触发,原有单段链路行为完全不变。
        if reference_video and not edit_first and requested_duration > multiseg.MAX_SEGMENT_SECONDS:
            result = await self._generate_multi_segment(
                prompt, reference_video, materials, requested_duration, ratio, resolution,
                script_text=self._script_text(params, script_anchors),
                # 替换意图决定逆推时"哪些元素不能描述"——必须一路传到逆推,否则会把原片元素写回画面
                intent=list(replace_intent),
                # 形态决定逆推按什么结构组织画面;不传则"选了短剧形态"仍拿到与原片同构的描述
                fmt=replicate_format,
                creative_level=self._creative_level, hook_boost=self._hook_boost,
                asset_override=self._asset_override,
                checkpoint=checkpoint, on_stage=on_stage,
            )
            # 字幕时间轴要用**真实总时长**(requested_duration),不是单段吸附值 ——
            # 否则 30s 成片的字幕会按 10s 铺,全部挤在前 1/3
            self._attach_script_meta(result, script_anchors, requested_duration)
            return result
        # 视频编辑优先:有参考视频且配了编辑模型时走它(复刻的本质),失败自动降级回图片参考链路,
        # 避免"网关不认 videos 字段"就把整单任务打成失败。
        if reference_video and config.VIDEO_MODEL_EDIT:
            # 编辑可独立配网关(如走中转站的 doubao-seedance-2.x);未配则跟随 video
            self._use_capability("video_edit")
            # 提交前先校验参考视频像素数:部分模型(如方舟 r2v/v2v)对参考视频有最低像素要求,
            # 不足必然 400。提前校验可把「注定失败的提交 + 一轮无谓网关故障转移」换成一句
            # 可执行提示(task 58/59 实测:像素不足 → 方舟 400 → 仍白切一次中转站 → 才失败)。
            pixel_issue = await frame_quality.check_reference_video_pixels(
                reference_video, self._min_reference_pixels(),
            )
            if pixel_issue:
                logger.error(
                    f"[VideoGenTool] 参考视频不满足模型要求,终止生成 task={self.task_prefix}: {pixel_issue}"
                )
                # 计数:这类拦截成批出现 = 某批素材分辨率普遍偏低,或门槛配错了
                metrics.incr("video.reference_pixels_blocked", detail=pixel_issue[:120])
                return self._fail(
                    f"参考视频不满足生成要求:{pixel_issue}。"
                    f"已终止本次生成并原路返还额度/退款",
                    "invalid_reference",
                )
            result = await self.edit_video(
                prompt, reference_video=reference_video, duration=duration, ratio=ratio,
                resolution=resolution, images=materials or None, generate_audio=True,
                checkpoint=checkpoint, on_stage=on_stage, replace_intent=replace_intent,
                fmt=replicate_format,
                creative_level=self._creative_level, hook_boost=self._hook_boost,
                asset_override=self._asset_override,
            )
            if not (result.metadata or {}).get("success", True):
                edit_error = str((result.metadata or {}).get("error") or "视频编辑失败")
                if replace_intent:
                    # 有替换意图 → **不降级**:降级出来的成片只是"用上传图重画",
                    # 与原片无关、也没做任何替换,比失败更糟(失败会返还额度并给出可执行原因)。
                    logger.error(
                        f"[VideoGenTool] 视频编辑失败,任务含替换意图({_intent_text(replace_intent)}),"
                        f"按失败处理不做降级 task={self.task_prefix}: {edit_error}"
                    )
                    return self._fail(
                        # 原始 edit_error 不拼进用户文案(会展示到 C 端),完整报错已在上一行 logger.error 落日志
                        f"替换{_intent_text(replace_intent)}失败:未能按参考视频完成编辑。"
                        f"已终止本次生成并原路返还额度/退款,请调整素材(如不含真人的原片)后重试",
                        (result.metadata or {}).get("error_type") or "edit_failed",
                    )
                logger.warning(
                    f"[VideoGenTool] 视频编辑失败,降级为图片参考链路 task={self.task_prefix}: "
                    f"{edit_error}"
                )
                # 降级回图片链路时网关也要切回:编辑网关(如中转站)未必有 r2v 的模型
                self._use_capability("video")
                # O3:纯复刻(无上传图、无替换意图)且视频编辑失败(常因参考视频含真人被平台拦截)
                # → 抽参考帧走 r2v 保留原片场景(丢运镜),而不是退化成纯文生(完全丢掉原片,比失败更糟)。
                degrade_materials = list(materials or [])
                used_frames = False
                if not degrade_materials and reference_video and not replace_intent:
                    frames = await media_prep.extract_reference_frames(reference_video)
                    if frames:
                        # 降级前必须验参考帧本身是不是「有内容的画面」:测试卡/彩条/纯色/黑屏
                        # 喂给模型只会原样复刻出一片彩条 —— 实测 task 58/59 就是这样交付了
                        # 一段有声无画的彩条片。宁可在此判失败退额度,也不花钱生成废片。
                        degenerate = await frame_quality.detect_degenerate_frames(frames)
                        if degenerate:
                            logger.error(
                                f"[VideoGenTool] 参考视频画面无实际内容(彩条/测试图/纯色),"
                                f"降级重生成只会产出同样无意义的画面,终止生成 "
                                f"task={self.task_prefix}: {degenerate}"
                            )
                            shutil.rmtree(os.path.dirname(frames[0]), ignore_errors=True)
                            # 计数:检出即说明有人在用无内容的素材,批量出现要回头查素材来源
                            metrics.incr("frame.degenerate_blocked", detail=f"参考帧:{degenerate}"[:160])
                            return self._fail(
                                f"参考视频画面无实际内容({degenerate})。"
                                f"已终止本次生成并原路返还额度/退款,请更换有真实画面的参考视频",
                                "invalid_reference",
                            )
                        frame_urls = await self._upload_reference_frames(frames)
                        if frame_urls:
                            degrade_materials = frame_urls
                            used_frames = True
                # 降级链路同样要带上复刻目标形态:否则选了"短剧/口播"等形态、编辑又失败时,
                # 降级成片仍是照抄原片结构、形态形同虚设。_append_replicate_format 在形态为空时
                # 原样返回 prompt,不影响无形态的历史降级行为。
                result = await self._generate_by_materials(
                    _append_replicate_format(prompt, replicate_format),
                    degrade_materials, duration, ratio, resolution, checkpoint, on_stage,
                )
                # 降级不静默:把降级原因并入 metadata 随 usage 回写 backend 落库。
                # 否则编辑失败(如参数不被模型接受)会退化成"看似成功、其实没做元素替换"的成片,
                # 用户与排查者都无从察觉 —— 正是踩过的坑。
                if (result.metadata or {}).get("success", True):
                    result.metadata["degraded"] = True
                    result.metadata["degrade_from"] = "video_edit"
                    result.metadata["degrade_reason"] = edit_error[:255]
                    if used_frames:
                        result.metadata["degrade_note"] = "视频编辑失败,已抽参考帧保留场景重新生成(r2v)"
            else:
                # 编辑成功:成片时长跟随参考视频,字幕时间轴与烧录都要按它来。
                # 统一取整一次,保证 metadata.seconds 与脚本时间轴用的是同一个值。
                script_duration = int(requested_duration)
                self._set_output_seconds(result, script_duration)
                ref_size = await media_prep.probe_size(reference_video)
                await self._check_output_against_reference(result, ratio, script_duration, ref_size=ref_size)
                # 编辑"成功"但成片画幅既不像目标、也不像原片 → 参考视频没生效,替换必然没发生。
                # 有替换意图时按失败处理:交付一个"看起来成功、其实没替换"的片子比失败更糟
                # (失败会原路返还额度,并给出用户可执行的原因)。与上面编辑失败的处理口径一致。
                if replace_intent and self._output_reference_ignored(result):
                    logger.error(
                        f"[VideoGenTool] 成片未跟随参考视频,替换({_intent_text(replace_intent)})必然未生效,"
                        f"按失败处理 task={self.task_prefix}: "
                        f"{(result.metadata.get('output_mismatch') or {}).get('reason')}"
                    )
                    return self._fail(
                        f"替换{_intent_text(replace_intent)}失败:成片未按参考视频生成"
                        f"(画幅与原片不符,说明编辑模型没有采用原片)。"
                        f"已终止本次生成并原路返还额度/退款,请稍后重试",
                        "output_mismatch",
                    )
        else:
            # 有原片却用不上编辑模型 → 无论是否带替换意图,都**明确失败**并说清怎么修。
            # 为什么不再降级:降级出来的成片只是"用上传图/文案重画",参考视频整个被丢弃,
            # 用户却看到"生成成功",以为原片已被复刻或替换 —— 这比直接失败更糟
            # (失败会原路返还额度,并给出用户可执行的修复方向)。
            if reference_video and not config.VIDEO_MODEL_EDIT:
                if replace_intent:
                    return self._fail(
                        f"替换{_intent_text(replace_intent)}失败:系统未配置视频编辑模型"
                        "(gen.video_model_edit),无法在参考视频上做替换,请配置后重试",
                        "config_error",
                    )
                return self._fail(
                    "未配置视频编辑模型(gen.video_model_edit),无法按参考视频生成新片;"
                    "请配置该模型,或改传图片素材后重试",
                    "config_error",
                )
            # 无编辑模型可用时的纯图/文生链路也要带上复刻目标形态,避免该链路下形态失效。
            result = await self._generate_by_materials(
                _append_replicate_format(prompt, replicate_format),
                materials, duration, ratio, resolution, checkpoint, on_stage,
            )
        self._attach_script_meta(result, script_anchors, script_duration)
        self._attach_decision_log(result)
        return result

    @staticmethod
    def _aspect_of_ratio(ratio: Optional[str]) -> Optional[float]:
        """画幅字符串 → 宽/高;认不出(adaptive/空/自定义)返回 None(不做该项校验)"""
        try:
            w, h = str(ratio or "").replace("：", ":").split(":")[:2]
            wf, hf = float(w), float(h)
            return wf / hf if hf else None
        except (ValueError, IndexError, AttributeError):
            return None

    async def _check_output_against_reference(
        self, result: ToolResult, ratio: Optional[str], expected_seconds: int,
        ref_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        """成片自检:视频编辑的成片必须"像"参考视频(画幅/时长),不像就打标

        为什么需要这道自检:换产品那次的成片是 960×960 / 10s,原片是 1440×2560 / 23.5s,
        差得极其明显却没有任何环节发现,最后靠人工 ffprobe 才定性。有了它,
        "产出错片"会在发生的那一刻被打标,而不是等用户投诉后再抽帧比对。

        只标记、**不阻断**:成片已经付费,残缺的成片也比没有强。
        探测失败(网络/格式)一律跳过 —— 自检不能反过来把任务搞失败。

        唯一的例外是 `reference_ignored`:成片画幅既不匹配目标、也不匹配原片,说明编辑模型
        压根没吃参考视频(替换必然没发生)。这一项由调用方决定是否判失败 ——
        裁成目标画幅会把证据抹掉,所以这里只如实记录,不替调用方做"掩盖"。
        """
        url = str(getattr(result, "content", "") or "")
        if not url.startswith("http") or expected_seconds <= 0:
            return
        try:
            size = await media_prep.probe_size(url)
            seconds = await media_prep.probe_duration(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[VideoGenTool] 成片自检探测失败,跳过 task={self.task_prefix}: {exc}")
            return

        problems: List[str] = []
        ratio_mismatch = False
        expected_aspect = self._aspect_of_ratio(ratio)
        actual_aspect = size[0] / float(size[1]) if (size and size[1]) else 0
        if actual_aspect and expected_aspect:
            # 画幅偏差阈值由 5% 收紧到 3%:复刻成片必须与参考视频同画幅,
            # 轻微偏差(如被压成接近正方形的竖屏)也应暴露,而非静默放过。
            if abs(actual_aspect - expected_aspect) / expected_aspect > 0.03:
                problems.append(f"画幅 {size[0]}x{size[1]} ≠ 目标 {ratio}")
                ratio_mismatch = True
        # 参考视频到底有没有生效:成片画幅要么落在目标画幅,要么落在**原片画幅**上。
        # 两者都不是 → 编辑模型没把参考视频当编辑输入,而是按 prompt 重新生成了,
        # 那么"替换"必然没发生。这是硬证据,必须单独暴露给上层去判失败 ——
        # 靠裁成目标画幅把它抹平,就是把一个"没做替换"的错片当成功交付
        # (实测 task=20:横版重生成片被居中裁成竖版后交付,主角与原片动作全丢)。
        ref_aspect = ref_size[0] / float(ref_size[1]) if (ref_size and ref_size[1]) else 0
        reference_ignored = False
        if actual_aspect and ref_aspect and expected_aspect:
            def _near(a: float, b: float) -> bool:
                return abs(a - b) / b <= 0.03
            if not _near(actual_aspect, expected_aspect) and not _near(actual_aspect, ref_aspect):
                reference_ignored = True
                problems.append(
                    f"成片画幅 {size[0]}x{size[1]} 既不匹配目标 {ratio}、"
                    f"也不匹配参考视频 {ref_size[0]}x{ref_size[1]},参考视频未生效"
                )
        if seconds and abs(seconds - expected_seconds) / float(expected_seconds) > 0.3:
            problems.append(f"时长 {seconds:.1f}s ≠ 参考视频 {expected_seconds}s")
        # 分辨率低于参考视频:复刻成片画质不应比原片差;探测失败(ref_size 为 None)时跳过
        if size and ref_size and min(size) < min(ref_size):
            problems.append(f"分辨率 {size[0]}x{size[1]} < 参考视频 {ref_size[0]}x{ref_size[1]}")
        if not problems:
            return

        # 画幅跑偏时**自动修正再交付**:模型会静默无视画幅(参考视频已裁成 9:16、
        # 成片仍是 1280x720,实测),只打标等于把横版片交给要竖版的用户。成片已付费,
        # 本地重编码一次的成本远低于重跑一单;失败则原样交付,退化为"只标记"。
        fixed_url = ""
        if ratio_mismatch:
            fixed_url = await self._fix_output_ratio(url, ratio)

        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        metadata["output_mismatch"] = {
            "expected": {"ratio": ratio, "seconds": expected_seconds},
            "actual": {"size": f"{size[0]}x{size[1]}" if size else "", "seconds": round(seconds or 0, 1)},
            "reason": "；".join(problems),
        }
        if reference_ignored:
            metadata["output_mismatch"]["reference_ignored"] = True
        if fixed_url:
            metadata["output_mismatch"]["fixed"] = True
            result.content = fixed_url
        result.metadata = metadata
        logger.warning(
            f"[VideoGenTool] 成片与参考视频不一致 task={self.task_prefix}: {'；'.join(problems)}"
            + ("(画幅已自动修正)" if fixed_url else "")
        )

    async def _fix_output_ratio(self, url: str, ratio: Optional[str]) -> str:
        """成片画幅跑偏时本地转成目标画幅,返回新 URL;失败/无需转一律返回空串

        复用参考视频的规整逻辑(同样的居中/保主体裁切),但**绝不裁时长** ——
        成片时长就是用户要的时长,截短等于毁片(max_seconds=None)。
        失败只记告警:修正属于增益,不能因为它把已付费的成片弄丢。
        """
        if not url or not ratio:
            return ""
        try:
            # allow_center_crop=False:成片已付费、不可重来。主体位置识别失败时居中硬裁
            # (16:9→9:16 只留约 31% 宽度)会把主体整段切走,而用户看不出成片已被切坏 ——
            # 宁可不修正、保留原画幅,让上层据 output_mismatch 判失败。
            new_url = await media_prep.fit_reference_video(
                url, max_seconds=None, ratio=str(ratio),
                key_prefix="generate/result", label="成片",
                allow_center_crop=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[VideoGenTool] 成片画幅修正异常,保留原片 task={self.task_prefix}: {exc}")
            return ""
        if not new_url or new_url == url:
            return ""
        logger.info(f"[VideoGenTool] 成片画幅已修正为 {ratio} task={self.task_prefix}: {new_url}")
        return new_url

    @staticmethod
    def _output_reference_ignored(result: ToolResult) -> bool:
        """成片自检结论:参考视频是否未生效(编辑实际没把原片当编辑输入)"""
        meta = result.metadata if isinstance(result.metadata, dict) else {}
        return bool((meta.get("output_mismatch") or {}).get("reference_ignored"))

    @staticmethod
    def _set_output_seconds(result: ToolResult, seconds: Any) -> None:
        """把成片真实时长写回 metadata.seconds(字幕烧录与时间轴都读这个字段)

        _submit_and_poll 里写入的是**提交用的吸附档位**(如 10s),而视频编辑的成片
        时长跟随参考视频(23.5s)。不覆写的话字幕会按 10s 摊分,全部挤在成片前 1/3。
        """
        try:
            value = int(float(seconds))
        except (TypeError, ValueError):
            return
        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        metadata["seconds"] = value
        result.metadata = metadata

    def _use_capability(self, capability: str) -> None:
        """切换本次任务的能力网关(视频编辑可独立指向中转站)

        构造时已按 video 解析过网关,这里只在编辑场景临时切换;
        显式传入 base_url(测试/直连调用)时不切,避免覆盖调用方意图。
        """
        if self._pinned or capability == self.capability:
            return
        gw = gateway.resolve(capability)
        if not gw.get("url"):
            return
        self.capability = capability
        self.base_url = gw["url"].rstrip("/")
        self.api_key = gw.get("key") or self.api_key
        self.proto = gw["proto"]
        logger.info(
            f"[VideoGenTool] 切换能力网关 capability={capability} → {self.base_url}(协议 {self.proto})"
        )

    @staticmethod
    def _payload_images(payload: Dict[str, Any]) -> List[Tuple[str, int]]:
        """按方舟 content 顺序列出 payload 里的图片位置 [(字段名, 下标), ...]

        顺序必须与 _ark_body 组装 content 的顺序一致(text 之后先单图 image、
        再参考图 images),否则无法把报错里的 content[N] 正确映射回某一张图。
        """
        items: List[Tuple[str, int]] = []
        if payload.get("image"):
            items.append(("image", 0))
        for i in range(len(payload.get("images") or [])):
            items.append(("images", i))
        return items

    def _locate_blocked_image(self, payload: Dict[str, Any], error: str) -> Optional[Tuple[str, int]]:
        """定位被判定含真人的那张参考图:返回 (字段名, 字段内下标);无法确定返回 None

        定位策略:
          ① 优先按报错里的 content[N] 换算(text 占 content[0],故图片从序列下标 N-1 起);
          ② 解析不到下标时,**只有一张图**才认定它(无歧义);多图不猜 ——
             猜错会把正常的商品图一起丢掉,替换直接失效,宁可按失败处理给出可读原因。
        """
        items = self._payload_images(payload)
        if not items:
            return None
        index = deidentify.parse_blocked_index(error)
        if index is not None:
            pos = index - 1
            return items[pos] if 0 <= pos < len(items) else None
        return items[0] if len(items) == 1 else None

    async def _stylize_reference_image(self, url: str) -> str:
        """把含真人的参考图转成非写实风格化形象后返回新 URL;失败返回空串

        走既有的图片生成能力(图生图),不额外引入模型依赖。任何失败都返回空串,
        由调用方回退到「丢弃该图」—— 拟态化是增强项,失败不该让任务彻底失败。

        提示词目标:把真人照转成**非写实风格化**(插画 / 三维 CG 角色),保留同一人的
        姿态、构图、发型与衣着特征,但明显不是照片级实拍。这样既能过方舟真人隐私审核
        (不再是可识别的实拍人脸),又保留"有这个人、长这样"的语义,用于视频替换目标时
        成片主角是该人的风格化形象而非另一张脸 —— 与术语"拟态化"一致。
        """
        if not url:
            return ""
        try:
            # 延迟导入:图片工具与视频工具互不依赖,放模块顶层也无环,但保持按需加载更省启动
            from app.tools.image_tool import ImageGenTool
            prompt = (
                "将这张照片转换为非写实风格化形象(精致插画 / 三维 CG 角色风格),"
                "保留人物的姿态、构图、发型与衣着特征,使其仍可识别为同一人,"
                "但明显为风格化形象而非照片级实拍;线条清晰、色彩饱满、避免过度写实。"
                "整体呈高质量风格化渲染质感"
            )
            res = await ImageGenTool().image_to_image(prompt, input_image=url, task_id=self.task_prefix)
            if (res.metadata or {}).get("success") and res.content:
                # 图生图可能返回多张,取第一张即可(参考图只需要一张)
                return str(res.content).split(",")[0].strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[VideoGenTool] 参考图拟态化失败,回退为丢弃该图: {exc}")
        return ""

    async def _apply_blocked_image_fix(
        self, payload: Dict[str, Any], error: str, keep_person: bool = False,
        prefer_stylize: bool = False, image_mode: str = IMAGE_FIX_DROP,
    ) -> str:
        """就地处理 payload 里被判定含真人的参考图,返回处理说明;无法定位/处理返回空串

        默认「丢弃该图」(即"图转文"):被丢的图仍以**视觉识别的文字描述**形式留在
        prompt 的 [人物信息]/[商品信息] 段里,模型仍有"换成什么"的文字依据,只是没有像素目标。

        处理分两步、由调用方驱动(prefer_stylize 控制本次优先拟态化还是直接丢弃):
          · 拟态化(保人):把真人照转成非写实风格化形象(见 _stylize_reference_image),争取过审核;
            适合"要被替换/要保留的人"—— 丢弃会让成片没有这个人。
          · 丢弃(图转文):拟态化后仍被拦、或不适合保人时的兜底,保证能出片。
        后台 gen.image_real_person_mode=drop 时强制丢弃(运营显式选择),优先级高于 prefer_stylize。
        """
        located = self._locate_blocked_image(payload, error)
        if not located:
            logger.warning(
                f"[VideoGenTool] 参考图含真人但无法定位是哪一张,不做处理 task={self.task_prefix}"
            )
            return ""
        field, idx = located
        images = list(payload.get("images") or [])
        url = str(payload.get("image") or "") if field == "image" else str(images[idx] or "")

        # 本次是否尝试拟态化:调用方要求优先保人(prefer_stylize),且未显式强制 drop。
        # 显式 drop 时即使要保人也丢弃 —— 运营配置/per-task 策略优先,避免绕过隐私策略。
        #
        # 用户要求:检测到真人一律「拟态化后重提」,不直接丢弃素材。故不再排除替换目标
        # (keep_person):被拦的图(无论是辅助参考还是替换目标)都先走拟态化。拟态化提示词
        # 已改为「非写实风格化、保留同一人的姿态/构图/衣着」,产出的是该人的风格化形象而非
        # 另一张照片级人脸,既过隐私审核又保留"有这个人"的语义;仍被拦/失败才回退图转文(丢弃)。
        explicit_mode = image_mode
        use_stylize = prefer_stylize and explicit_mode != IMAGE_FIX_DROP
        if use_stylize and url:
            new_url = await self._stylize_reference_image(url)
            if new_url and new_url != url:
                if field == "image":
                    payload["image"] = new_url
                else:
                    images[idx] = new_url
                    payload["images"] = images
                logger.info(f"[VideoGenTool] 参考图含真人,已拟态化后重试 task={self.task_prefix}")
                return "参考图含真人,已自动将其拟态化为非写实风格后重新提交"

        # 丢弃该图(未选择写实化、或写实化失败/仍被拦时的默认与回退)
        if field == "image":
            payload.pop("image", None)
        else:
            images.pop(idx)
            if images:
                payload["images"] = images
            else:
                payload.pop("images", None)
        # 图没了,模型对"换成什么"就只剩像素外的文字这一个依据:把该主体的文字描述
        # 确定性补进 prompt 末尾(见 _append_subject_desc),替换依据不丢。
        desc_labels = self._append_subject_desc(payload)
        logger.info(f"[VideoGenTool] 参考图含真人,已移除该图(改按文字描述生成) task={self.task_prefix}")
        note = "参考图含真人,已自动移除该图并改为按文字描述生成"
        if desc_labels:
            note += f";已把{'/'.join(desc_labels)}的文字描述补进提示词,替换依据不丢"
        return note

    def _append_subject_desc(self, payload: Dict[str, Any]) -> List[str]:
        """参考图被移除后,把该主体的文字描述确定性补进 prompt 末尾;返回补进去的维度名

        图被丢掉后,模型对"要换成什么"就只剩像素之外的文字这一个依据了。描述必须追加在
        prompt **最末尾且不经 LLM 改写** —— 上游改写会把这句弱化/丢弃,替换就等于没做
        (与 _build_replace_directive 同一手法、同一原因)。重复调用幂等。
        """
        subjects = self._replace_subjects if isinstance(self._replace_subjects, dict) else {}
        labels = (("person", "人物"), ("product", "商品"), ("scene", "场景"))
        present = [(key, label) for key, label in labels if str(subjects.get(key) or "").strip()]
        if not present:
            return []
        marker = "【被移除素材的文字描述(以本段为准)】"
        prompt = str(payload.get("prompt") or "")
        if marker not in prompt:
            body = ";".join(f"{label}:{str(subjects.get(key) or '').strip()}" for key, label in present)
            payload["prompt"] = f"{prompt.rstrip()}\n{marker}{body}"
        return [label for _, label in present]

    async def _submit_and_fix_real_person(
        self, payload: Dict[str, Any], label: str, duration: int,
        resolution: Optional[str], ratio: Optional[str], route: str = "",
        checkpoint: Optional[dict] = None, on_stage=None, *,
        allow_video_fix: bool = False, no_image_fallback=None,
        decision: Optional[Dict[str, Any]] = None, keep_person: bool = False,
        real_person_strategy: Optional[str] = None,
    ) -> ToolResult:
        """提交并轮询;素材被平台判定含真人时做**有界**本地修正后重试

        方舟把"输入素材含真人"当隐私问题直接拒绝,与提示词无关。参考视频已能自动去身份化,
        这里把**参考图**补成对称能力,并覆盖"真人视频 + 真人形象图"的组合:
          · 参考图含真人 → 先拟态化保人(非写实风格化),仍被拦则丢弃(图转文)兜底;
          · 参考视频含真人 → 本地去身份化后重试(仅 allow_video_fix),方舟已确认含真人则
            增强检测/强制兜底打码,不再"漏检即放弃"。
        处理结果写入 metadata,绝不静默。

        keep_person:被拦的参考图是出镜人物/替换目标时为真,驱动 _apply_blocked_image_fix
        优先写实化保留人物(而非丢弃),详见该方法的说明。

        no_image_fallback:图片被全部处理掉时的兜底可调用对象(如 i2v 无首帧 → 改走文生视频);
        不传则用同一 payload 重提交(v2v 去掉商品图后仍可编辑)。

        real_person_strategy:per-task 真人处理策略覆盖(stylize/drop 显式覆盖系统配置);
        auto/未传 → 沿用 _image_fix_mode()(系统配置 gen.image_real_person_mode)。
        """
        # per-task 策略覆盖:stylize/drop 显式覆盖系统配置;其余(auto/未传)沿用系统默认
        effective_mode = (
            real_person_strategy if real_person_strategy in (IMAGE_FIX_DROP, IMAGE_FIX_STYLIZE)
            else _image_fix_mode()
        )

        async def _submit() -> ToolResult:
            return await self._submit_and_poll(
                payload, label, duration, resolution, ratio, route,
                checkpoint=checkpoint, on_stage=on_stage, decision=decision,
            )

        result = await _submit()
        fixed_video = False
        image_phase = 0   # 0:未处理 1:已写实化保人 2:已丢弃图转文(两阶段上限)
        notes: Dict[str, Any] = {}
        while True:
            if (result.metadata or {}).get("success", True):
                break
            # 断点续跑已提交外部任务:重提交等于重复扣费,不再做素材修正
            if (checkpoint or {}).get("external_task_id"):
                break
            error = str((result.metadata or {}).get("error") or "")

            # 视频含真人:本地去身份化后重试(force=True,方舟已确认含真人则增强检测/强制兜底打码,不放弃)
            if allow_video_fix and not fixed_video and deidentify.is_input_video_blocked(error):
                urls = [u for u in (payload.get("videos") or []) if u]
                if urls:
                    new_url = await media_prep.deidentify_reference_video(urls[0], force=True)
                    if new_url and new_url != urls[0]:
                        payload["videos"] = [new_url]
                        fixed_video = True
                        notes["deidentified"] = True
                        notes["deidentify_note"] = "输入视频含真人,已本地去身份化后重新提交"
                        # 去身份化后同样拨回首选网关再重试(避免沿用故障转移后的备选网关)
                        self._reset_gateway()
                        result = await _submit()
                        continue
                    # 即便方舟确认含真人,本地仍无法定位(强制兜底也救不回)→ 诚实失败,不再伪装成功
                    logger.error(
                        f"[VideoGenTool] 参考视频含真人但本地无法定位,放弃去身份化重试 task={self.task_prefix}"
                    )
                break

            # 图片含真人:先写实化保人(阶段0),仍被拦则丢弃图转文(阶段1)兜底,最多两阶段
            if deidentify.is_input_image_blocked(error) and image_phase < 2:
                # 阶段0才尝试写实化,且**仅限"非替换目标"的辅助图**(keep_person=False):
                # 被拦的图正是要换进去的主体时,重画等于把目标换成另一张脸,必须直接走图转文保语义。
                prefer_stylize = image_phase == 0 and effective_mode == IMAGE_FIX_STYLIZE
                note = await self._apply_blocked_image_fix(
                    payload, error, keep_person=keep_person, prefer_stylize=prefer_stylize,
                    image_mode=effective_mode,
                )
                if note:
                    image_phase = 1 if prefer_stylize else 2
                    notes["image_fixed"] = True
                    notes["image_note"] = note
                    # 仅当被拦图被"丢弃(图转文)"时才标记人物丢失:此时成片人物确实不会与上传
                    # 照片一致。若已走拟态化(非写实风格化)保住了该人,则不再标记 —— 人物以风格化
                    # 形象出现在成片里,语义仍在(用户要求真人素材一律拟态化而非丢弃)。
                    if keep_person and "移除该图" in note:
                        notes["person_identity_lost"] = True
                    # ⚠️ 修正后必须拨回首选网关再重试:上一轮提交已故障转移到备选(如 aitoken),
                    # 若直接沿用当前网关,修正后的素材会先打到备选,既绕开能接收的主网关(方舟),
                    # 又可能触发备选网关的解析异常(如 aitoken 的 unpack),导致"其实改好了却仍失败"。
                    self._reset_gateway()
                    if payload.get("image") or payload.get("images"):
                        result = await _submit()
                    elif no_image_fallback is not None:
                        result = await no_image_fallback()
                    else:
                        result = await _submit()
                    continue
            break
        # 只有成功才回写标记:失败时结果不落库(失败原因另走 fail_reason),标记无处附着
        if notes and (result.metadata or {}).get("success"):
            result.metadata.update(notes)
        return result

    async def _generate_by_materials(
        self, prompt: str, materials: List[str], duration: int, ratio: str, resolution: str,
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """按素材数量选择链路:1 张 → i2v(首帧);多张 → r2v(参考图);无素材 → t2v

        兜底:视频素材一律不得进入 images 字段(上游会直接判任务失败),
        调用方(generate)应已把视频素材提升为参考视频,这里只做最后一道拦截。
        """
        images, videos = _split_media(materials)
        if videos:
            return self._fail(
                f"参考生视频失败:素材含 {len(videos)} 个视频,不能作为参考图片使用",
                "invalid_request",
            )
        materials = images
        if len(materials) == 1:
            return await self.image_to_video(
                prompt, duration=duration, ratio=ratio, resolution=resolution,
                input_image=materials[0], checkpoint=checkpoint, on_stage=on_stage,
            )
        if len(materials) > 1:
            return await self.reference_to_video(
                prompt, duration=duration, ratio=ratio, resolution=resolution,
                reference_images=materials, checkpoint=checkpoint, on_stage=on_stage,
            )
        return await self.text_to_video(
            prompt, duration=duration, ratio=ratio, resolution=resolution,
            checkpoint=checkpoint, on_stage=on_stage,
        )

    async def _generate_storyboard(
        self, prompt: str, materials: List[str], duration: int, ratio: str, resolution: str,
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """九宫格分镜编排:9 张分镜图各自图生视频(i2v) + 运镜 + xfade 转场合成一条视频。

        输入 materials 期望为 9 张分镜图地址(前端把 3x3 九宫格裁成 9 格后下发);
        不足 9 张时循环复用、超过时截断,保证九宫格结构完整。

        运镜采用「提示词注入镜头语言 + i2v 后轻度 Ken Burns 兜底」两者结合,
        兼顾自然与可控;任一环节失败都**明确失败并带原因**,不交付残缺成片。
        """
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            return self._fail("九宫格分镜生成需要 ffmpeg,当前环境不可用(容器需安装 ffmpeg)", "config_error")
        workdir = tempfile.mkdtemp(prefix="storyboard_")
        try:
            images = [m for m in (materials or []) if str(m).strip()]
            if not images:
                return self._fail("九宫格分镜生成失败:未提供分镜图", "invalid_request")
            # 规整到 9 张:不足循环复用,超过截断,保证九宫格九镜结构
            if len(images) < 9:
                images = (images * ((9 // len(images)) + 1))[:9]
            images = images[:9]
            # 仅对基础 prompt 做一次 LLM 改写;逐镜只追加运镜描述,避免 9 次改写开销
            base_prompt = await self._optimize_prompt(
                prompt, build_prompt_optimize_system(ratio=None, resolution=resolution, edit=False),
            )
            if on_stage:
                await on_stage(1, {"optimized_prompt": base_prompt})
            # 每镜时长:均分总时长并下限 3s、上限 5s,保证每个分镜都有足够展示
            seg_duration = max(3, min(5, int(round((duration or 15) / 9)) or 3))
            seg_files: List[str] = []
            for idx, img in enumerate(images):
                camera = STORYBOARD_CAMERA_MOVES[idx % len(STORYBOARD_CAMERA_MOVES)]
                shot_prompt = (
                    f"{base_prompt}\n运镜要求:{camera};镜头平滑、画面稳定、主体清晰、避免穿帮。"
                )
                shot = await self.image_to_video(
                    shot_prompt, duration=seg_duration, ratio=ratio, resolution=resolution,
                    input_image=img, real_person_strategy=self._real_person_strategy,
                )
                meta = shot.metadata or {}
                if not meta.get("success", True):
                    return self._fail(
                        f"九宫格分镜第 {idx + 1}/9 镜生成失败:{meta.get('error') or '模型返回失败'}",
                        str(meta.get("error_type") or "compose_error"),
                    )
                url = str(getattr(shot, "content", "") or "")
                if not url.startswith("http"):
                    return self._fail(f"九宫格分镜第 {idx + 1}/9 镜无结果地址", "compose_error")
                local = await asyncio.to_thread(download_to_local, url, ".mp4")
                if not local:
                    return self._fail(f"九宫格分镜第 {idx + 1}/9 镜下载失败", "request_error")
                # 运镜兜底:轻度 Ken Burns 推近;失败回退原片段,不影响整片
                kb = await self._apply_kenburns(ffmpeg, local, workdir, idx)
                seg_files.append(kb or local)
            final_url = await self._concat_storyboard(ffmpeg, seg_files, workdir)
            if not final_url:
                return self._fail("九宫格分镜合成失败", "compose_error")
            usage = self._usage(config.VIDEO_MODEL_I2V, seg_duration * len(seg_files), resolution, ratio)
            result = ToolResult(content=final_url, metadata={"success": True, **usage, "storyboard": True})
            self._attach_decision_log(result)
            return result
        finally:
            # 清理临时目录(下载/Ken Burns/拼接中间产物),避免占磁盘
            shutil.rmtree(workdir, ignore_errors=True)

    async def _apply_kenburns(
        self, ffmpeg: str, clip: str, workdir: str, idx: int,
        zoom_start: float = 1.0, zoom_end: float = 1.08,
    ) -> Optional[str]:
        """轻度 Ken Burns 运镜兜底:给分镜片段叠加缓慢推近,增强运镜感。

        失败(ffmpeg 异常/滤镜不支持/探测失败)时返回 None,调用方回退使用原片段。
        """
        try:
            size = await media_prep.probe_size(clip)
            dur = await media_prep.probe_duration(clip)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[VideoGenTool] 运镜前探测失败,回退原片段 task={self.task_prefix}: {exc}")
            return None
        if not size or not dur or dur <= 0:
            return None
        out = os.path.join(workdir, f"kb_{idx}.mp4")
        cmd = compose.build_kenburns_cmd(
            clip, out, duration=dur, width=size[0], height=size[1],
            zoom_start=zoom_start, zoom_end=zoom_end, ffmpeg=ffmpeg,
        )
        try:
            res = await compose.run(cmd, timeout=300)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[VideoGenTool] 运镜后处理异常,回退原片段 task={self.task_prefix}: {exc}")
            return None
        if res.get("ok") and os.path.exists(out):
            return out
        logger.warning(f"[VideoGenTool] 运镜后处理失败,回退原片段 task={self.task_prefix}: {res.get('stderr')}")
        return None

    async def _concat_storyboard(self, ffmpeg: str, seg_files: List[str], workdir: str) -> str:
        """九宫格分镜转场合成:优先 xfade 交叉淡化(丝滑过渡),段数不足或异常时退回流复制硬切。"""
        names: List[str] = []
        for i, path in enumerate(seg_files):
            name = f"s{i}.mp4"
            shutil.copy(path, os.path.join(workdir, name))
            names.append(name)
        with open(os.path.join(workdir, "list.txt"), "w", encoding="utf-8") as fh:
            fh.write(compose.build_concat_list(names))
        merged = os.path.join(workdir, "merged.mp4")
        if len(names) >= 2:
            try:
                durations = [
                    (await media_prep.probe_duration(os.path.join(workdir, n))) or 0.0 for n in names
                ]
                transition = 0.4
                if all(d > transition for d in durations):
                    xf = compose.build_xfade_concat_cmd(names, durations, "merged.mp4", transition, ffmpeg)
                    res = await compose.run(xf, cwd=workdir, timeout=600)
                    if res.get("ok") and os.path.exists(merged):
                        url = await asyncio.to_thread(
                            upload_local_file, merged, f"generate/result/{self.task_prefix}.mp4",
                        )
                        return url or ""
                    logger.warning(f"[VideoGenTool] 转场合成失败,退回流复制 task={self.task_prefix}")
                else:
                    logger.warning("[VideoGenTool] 存在段时长不足转场时长,退回流复制拼接")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[VideoGenTool] 转场合成异常,退回流复制 task={self.task_prefix}: {exc}")
        res = await compose.run(compose.build_concat_cmd("list.txt", "merged.mp4"), cwd=workdir, timeout=300)
        if not res.get("ok") or not os.path.exists(merged):
            logger.error(f"[VideoGenTool] 分镜拼接失败: {res.get('stderr')}")
            return ""
        url = await asyncio.to_thread(upload_local_file, merged, f"generate/result/{self.task_prefix}.mp4")
        return url or ""

    async def _upload_reference_frames(self, frames: List[str]) -> List[str]:
        """把本地抽帧上传 OSS,返回可用 URL(任一失败则跳过该帧);最后清理临时目录。

        抽帧是 O3 降级链路的一环,帧文件为本地临时文件,上传成功后即过期,必须清理避免占磁盘。
        """
        urls: List[str] = []
        try:
            for path in frames:
                url = await asyncio.to_thread(
                    upload_local_file, path, f"reference/frame_{uuid4().hex}.jpg",
                )
                if url:
                    urls.append(url)
        finally:
            if frames:
                shutil.rmtree(os.path.dirname(frames[0]), ignore_errors=True)
        return urls

    async def _extract_local_frames(
        self, ffmpeg: str, video: str, workdir: str, times: List[float], cleanup: List[str],
        width: int = SHOT_FRAME_WIDTH, prefix: str = "shot",
    ) -> List[str]:
        """按时间点抽帧到本地(不上传 OSS),供多模态请求内联图片使用

        与多段续接用的 _extract_and_upload_frame 的区别:这里不需要可访问地址 ——
        图片以 base64 内联送出,只落本地,并交给调用方的 cleanup 统一清理。
        **数量必须完整**:少一张就会让「图片顺序 ↔ 镜头序号」错位,
        因此任何一张失败都返回空列表,由调用方放弃本次视觉分析 ——
        宁可没有镜头描述,也不要一份描述错画面的结果。

        prefix 用于区分同一 workdir 下多组抽帧(如质检的原片侧与成片侧)。
        """
        paths: List[str] = []
        for idx, at in enumerate(times):
            out = os.path.join(workdir, f"{prefix}_{idx}.jpg")
            result = await compose.run(
                compose.build_extract_frame_cmd(video, out, at, width, ffmpeg), timeout=120,
            )
            if not result.get("ok") or not os.path.exists(out):
                logger.warning(f"[VideoGenTool] 逆推抽帧失败(第 {idx + 1}/{len(times)} 张),放弃逐镜头逆推")
                return []
            paths.append(out)
            cleanup.append(out)
        return paths

    @staticmethod
    def _image_data_url(path: str) -> str:
        """本地图片 → base64 data URL(多模态请求内联图片用,避免为分析再上传一次 OSS)"""
        with open(path, "rb") as fp:
            return f"data:image/jpeg;base64,{base64.b64encode(fp.read()).decode()}"

    @staticmethod
    def _vision_messages(system_prompt: str, content: List[dict]) -> List[Any]:
        """组装多模态消息:系统提示 + 「文字 + 内联图片」的用户消息

        为什么单独抽出来:用户消息的 content 是文字与图片交错的部件列表,
        OpenAI SDK 的 ChatCompletionContentPartParam 联合类型覆盖不到这种混合形态,
        两处调用各写一遍既重复、又各自产生一次类型告警 —— 收敛到这里按 Any 返回
        (运行时就是标准的多模态 messages 结构,各网关都接受)。
        """
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

    async def _review_shots_with_vision(
        self, output_url: str, cache_source: str, local_ref: str, workdir: str,
        shot_table: List[Dict[str, Any]], intent: List[str], cleanup: List[str],
    ) -> List[Dict[str, Any]]:
        """逐镜头质检(P1-7):原片与成片在**同一时间位置**配对比对,产出逐镜头分数

        为什么按同一时间位置比对:多段复刻的目标就是复刻原片的镜头结构,成片第 k 镜
        理应出现在原片第 k 镜的时间位置上 —— 两侧同点抽帧即可比对。刻意**不对成片再跑
        一次镜头检测**:那会引入第二套镜头切分,两侧结果无法一一对齐。

        只标记**不重跑**:自动重跑会产生新的模型费用,属于必须由用户/运营确认的行为变更,
        因此这里只把结论写进 metadata,由前端展示(与成片自检 output_mismatch 同一策略)。

        任何失败返回空列表 —— 质检是增强能力,不能把一次已付费的成片弄成失败任务。
        """
        if len(shot_table) < 2:
            return []
        if not config.CHAT_MODEL:
            logger.info("[VideoGenTool] 跳过逐镜头质检:未配置 chat 模型")
            return []
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg or not output_url:
            return []
        targets = shots.review_targets(shot_table)
        if not targets:
            return []
        times = [row["time"] for row in targets]
        ref_frames = await self._extract_local_frames(
            ffmpeg, local_ref, workdir, times, cleanup, prefix="qc_ref",
        )
        if len(ref_frames) != len(times):
            return []
        output_local = await asyncio.to_thread(download_to_local, output_url, ".mp4")
        if not output_local:
            logger.warning("[VideoGenTool] 逐镜头质检跳过:成片下载失败")
            return []
        cleanup.append(output_local)
        out_frames = await self._extract_local_frames(
            ffmpeg, output_local, workdir, times, cleanup, prefix="qc_out",
        )
        if len(out_frames) != len(times):
            return []

        indexes = [row["index"] for row in targets]
        system_prompt = build_shot_qc_prompt(len(targets), intent)
        cache_key = build_cache_key(ASSET_OPTIMIZED_PROMPT, {
            "model": config.CHAT_MODEL, "system": "shot_qc",
            "user": f"{cache_source}|{output_url}|{_intent_text(intent)}|{times}",
        })
        cached = await asset_cache.fetch(self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT)
        if cached and cached.get("content"):
            parsed = parse_shot_qc(str(cached["content"]), indexes)
            if parsed:
                return self._qc_rows(parsed)
        # 图片按镜头顺序**成对**给出:先原片、后成片(提示词里已声明该顺序)
        content: List[dict] = [{
            "type": "text",
            "text": f"共 {len(targets)} 组图片,每组 2 张(第 1 张原片、第 2 张成片),按镜头顺序排列。",
        }]
        for pos in range(len(targets)):
            for path in (ref_frames[pos], out_frames[pos]):
                content.append({"type": "image_url", "image_url": {"url": self._image_data_url(path)}})

        candidates = gateway.resolve_all("chat") or [{
            "name": "env",
            "url": (config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/"),
            "key": config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY,
            "proto": "openai",
        }]
        last_exc: Optional[Exception] = None
        for gw in candidates:
            try:
                resp = await self._chat_client(gw).chat.completions.create(
                    model=config.CHAT_MODEL,
                    messages=self._vision_messages(system_prompt, content),
                    timeout=CHAT_REWRITE_TIMEOUT,
                )
                text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
                if not text:
                    continue
                parsed = parse_shot_qc(text, indexes)
                if not parsed:
                    logger.warning("[VideoGenTool] 逐镜头质检结果解析不出内容,跳过质检")
                    return []
                await asset_cache.store(
                    self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT, text,
                    task_type="video", meta={"model": config.CHAT_MODEL},
                )
                rows = self._qc_rows(parsed)
                low = [row["index"] for row in rows if row["score"] < SHOT_QC_LOW_SCORE]
                logger.info(
                    f"[VideoGenTool] 逐镜头质检完成: {len(rows)} 个镜头,"
                    f"低分镜头 {low or '无'}(仅标记,不自动重跑)"
                )
                return rows
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(f"[VideoGenTool] 逐镜头质检经 [{gw['name']}] 失败,尝试下一个: {exc}")
        if last_exc:
            logger.warning(f"[VideoGenTool] 逐镜头质检失败(跳过): {last_exc}")
        return []

    @staticmethod
    def _qc_rows(parsed: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """质检结果 → 按镜头序号升序的列表

        · 用列表而不是 {序号: 结论}:JSON 的整数键回读会变成字符串,形状不稳定;
        · 同时下发 `low` 标记,让前端的"低分高亮"与 worker 的低分线同源 ——
          阈值各写一份必然漂移(改了 worker 忘了前端,高亮就跟日志对不上)。
        """
        return [
            {"index": index, "low": parsed[index]["score"] < SHOT_QC_LOW_SCORE, **parsed[index]}
            for index in sorted(parsed)
        ]

    async def _build_shot_prompts(
        self, cache_source: str, local_ref: str, workdir: str,
        shot_table: List[Dict[str, Any]], intent: List[str], cleanup: List[str],
        fmt: str = "", creative_level: str = "", hook_boost: str = "", asset_override: str = "",
    ) -> Dict[int, str]:
        """逐镜头逆推(P0-3):读原片每个镜头的画面 → 该镜头的画面与运镜描述

        为什么需要它:此前的逐段提示词只来自「用户备注 + 本段台词」,模型看不到这一段
        是**怎么拍的**(景别/运镜/主体分布);逆推把这些显式写进提示词,复刻的结构
        一致性才有依据 —— 这也是外部复刻工作流(分镜拆解 → 逆推提示词)的共同做法。

        fmt 为复刻目标形态(短剧/口播/街采/…),与拆解链路同源:不传会让"理解原片"
        按形态组织、而"重塑出片"仍照抄原片结构,两次逆推互相打架。

        返回 {镜头序号: 描述};**任何一步失败都返回空字典**,调用方回退到既有逐段提示词。
        逆推是增强能力,不能因为一次多模态调用失败就把已付费的生成弄失败。
        """
        if len(shot_table) < 2:
            # 单镜头原片没有"镜头结构"可逆推,多花一次调用没有意义
            return {}
        if not config.CHAT_MODEL:
            logger.info("[VideoGenTool] 跳过逐镜头逆推:未配置 chat 模型")
            return {}
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            return {}
        targets = shots.analysis_targets(shot_table)
        if not targets:
            return {}
        times = [at for row in targets for at in row["times"]]
        frames = await self._extract_local_frames(ffmpeg, local_ref, workdir, times, cleanup)
        if len(frames) != len(times):
            return {}

        indexes = [row["index"] for row in targets]
        # 镜头清单:序号/时长/原片台词。台词只作"这镜在讲什么"的参考,
        # 提示词里已明确要求模型不要把台词写进画面描述(台词属于被替换的内容)。
        summary = json.dumps(
            {
                "shots": [
                    {"index": row["index"], "duration": row["duration"], "narration": row["narration"]}
                    for row in targets
                ]
            },
            ensure_ascii=False, indent=2,
        )
        system_prompt = build_shot_reverse_prompt(
            len(targets), intent, frames_per_shot=2, fmt=fmt,
            creative_level=creative_level, hook_boost=hook_boost,
        )
        # 逆推依赖原片内容,缓存键必须带上原片标识 + 替换意图 + 镜头清单;
        # 复用 optimized_prompt 这一产物类型(不新增类型:backend 侧有镜像常量与跨端契约测试,
        # 键由 payload 哈希区分,不存在串用)。
        # 形态会改变逆推产出(按形态组织画面,而非照抄原片结构),必须进键:
        # 否则选了不同形态的两个任务会命中同一份逆推结果,形态等于白选。
        user_key = f"{cache_source}|{_intent_text(intent)}|{summary}"
        if fmt:
            user_key = f"{cache_source}|{_intent_text(intent)}|{fmt}|{summary}"
        cache_key = build_cache_key(ASSET_OPTIMIZED_PROMPT, {
            "model": config.CHAT_MODEL, "system": "shot_reverse",
            "user": user_key,
        })
        cached = await asset_cache.fetch(self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT)
        if cached and cached.get("content"):
            parsed = parse_shot_prompts(str(cached["content"]), indexes)
            if parsed:
                logger.info(f"[VideoGenTool] 逐镜头逆推命中缓存: {len(parsed)}/{len(indexes)} 个镜头")
                return parsed

        content: List[dict] = [{
            "type": "text",
            "text": (
                f"{summary}\n\n图片按镜头清单的顺序成对给出,每个镜头 2 张"
                f"(先开始帧、后结束帧),共 {len(frames)} 张。"
            ),
        }]
        for path in frames:
            content.append({"type": "image_url", "image_url": {"url": self._image_data_url(path)}})

        candidates = gateway.resolve_all("chat") or [{
            "name": "env",
            "url": (config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/"),
            "key": config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY,
            "proto": "openai",
        }]
        last_exc: Optional[Exception] = None
        for gw in candidates:
            try:
                resp = await self._chat_client(gw).chat.completions.create(
                    model=config.CHAT_MODEL,
                    messages=self._vision_messages(system_prompt, content),
                    timeout=CHAT_REWRITE_TIMEOUT,
                )
                text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
                if not text:
                    continue
                parsed = parse_shot_prompts(text, indexes)
                if parsed:
                    await asset_cache.store(
                        self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT, text,
                        task_type="video", meta={"model": config.CHAT_MODEL},
                    )
                    logger.info(f"[VideoGenTool] 逐镜头逆推完成: {len(parsed)}/{len(indexes)} 个镜头")
                    return parsed
                logger.warning("[VideoGenTool] 逐镜头逆推结果解析不出内容,回退原有逐段提示词")
                return {}
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(f"[VideoGenTool] 逐镜头逆推经 [{gw['name']}] 失败,尝试下一个: {exc}")
        if last_exc:
            logger.warning(f"[VideoGenTool] 逐镜头逆推失败(回退原有提示词): {last_exc}")
        return {}

    @staticmethod
    def _script_text(params: dict, script_anchors: dict) -> str:
        """取原始口播文案:分段生成时用来给每段分配各自的台词"""
        for key in ("script_text", "copywriting", "text"):
            value = params.get(key)
            if value:
                return str(value).strip()
        # 旧任务只有词锚点脚本,退回从分段文本拼
        return "".join(str(s.get("text") or "") for s in (script_anchors or {}).get("segments") or [])

    async def _build_replicate_script(
        self, reference_video: str, duration: int, intent: List[str], params: dict,
    ) -> str:
        """纯复刻没有口播文案时,按原片生成一份(承载声音方向 + 字幕方法论)。

        触发条件刻意收窄:**有参考视频 + 完全没有任何文案**。此时成片没有 TTS 配音、
        也没有字幕,只剩画面;补一份口播文案可同时盘活配音与字幕两条链路。

        声音方向(选角/递送)与字幕(语义短语断句)都作用在**文案本身**上,故在此注入,
        而不是塞给 TTS(会被念出来)或烧字幕环节(纯文本,无 LLM 环节)。

        任何失败(无 chat 模型 / 网关全挂 / 解析为空)都返回空串,
        回退到"无文案"的历史行为,绝不因这一次增强影响主链路。
        """
        if not reference_video or not config.CHAT_MODEL:
            return ""
        assets_text = "\n".join(
            part for part in (
                f"对标视频:{reference_video}",
                f"可用素材:{params.get('material_hint') or ''}",
                f"用户备注:{str(params.get('prompt') or '').strip()}",
            ) if part.split(":", 1)[-1].strip()
        )
        system_prompt = build_asset_script_prompt(
            intent="、".join(intent) or "同款复刻", duration=duration, assets_text=assets_text,
        )
        # 复用 _optimize_prompt:已含缓存、chat 网关故障转移、失败回退原 prompt。
        # 失败时它原样返回下面这句指令 → parse_asset_script 解析为空 → 安全回退。
        text = await self._optimize_prompt("请严格按输出格式输出 JSON。", system_prompt)
        return parse_asset_script(text)

    @staticmethod
    def _segment_prompt(prompt: str, script_parts: List[str], idx: int, shot_hint: str = "", asset_override: str = "") -> str:
        """给某一段的 prompt 加上「本段台词」边界,以及该段对应的原片镜头结构

        - 台词边界:不加的话每段都会把整篇文案念一遍,成片里同一句话重复两次。
        - 镜头结构(P0-3):来自原片的逐镜头逆推,让模型知道这一段**该怎么拍**
          (景别/运镜/主体位置),而不是只按用户备注自由发挥。
          末尾必须显式声明"元素以替换要求为准":逆推描述里保留了原片的场景与构图,
          若不声明,模型会把原片商品/人物也一并复刻回来 —— 那正是「复刻白做」的成因。
        - 专家追加要求(asset_override)挂到段末,确保不被上游改写模型吞掉。
        """
        part = script_parts[idx] if idx < len(script_parts) else ""
        sections = [prompt]
        if shot_hint:
            sections.append(f"[原片镜头结构] {shot_hint}")
            sections.append("以上只描述原片的画面与运镜,用于保持镜头结构一致;画面元素一律以替换要求为准。")
        if part:
            sections.append(f"[本段台词] {part}")
            sections.append("请只表现本段台词的内容,不要念其他段落的台词。")
        if asset_override:
            sections.append(f"[额外创作要求] {asset_override}")
        return "\n".join(sections)

    @staticmethod
    def _shot_hint(shot_prompts: Dict[int, str], shot_map: List[List[int]], idx: int) -> str:
        """把某一段覆盖镜头的逆推描述拼成一行提示;没有可用描述时返回空串

        一段可能覆盖多个镜头(按镜头切分就是把相邻镜头并成一段),逐个拼起来,
        模型才能知道这一段里画面要变几次、怎么变。
        """
        if not shot_prompts or idx >= len(shot_map):
            return ""
        return "；".join(shot_prompts[i] for i in shot_map[idx] if i in shot_prompts)

    async def _generate_one_segment(
        self, *, ffmpeg: str, seg_prompt: str, ref_duration: float, local_ref: str,
        reference_video: str, materials: List[str], ratio: str, resolution: str,
        intent: Optional[List[str]], cursor: float, seg_duration: int,
        workdir: str, cleanup: List[str], prev_next_frame: str, extract_next: bool,
        fmt: str = "", creative_level: str = "", hook_boost: str = "", asset_override: str = "",
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> Tuple[str, str]:
        """生成多段链路里的单一段(抽出供主循环与「低分自动重跑」复用,逻辑完全一致)

        返回 (本地成片路径, 供下一段续接的首帧)。任何一步失败抛出 RuntimeError,
        由调用方转成明确的任务失败 —— 绝不"凑一段交差"。

        extract_next=False(最后一段)时不再抽续接首帧:没有下一段可续,省一次上传。
        """
        from app.core.asset_cache import build_cache_key, fetch as fetch_asset, store as store_asset
        # 同任务重试复用成功段；上一段尾帧和完整绑定纳入键，避免错用旧素材。
        cache_key = build_cache_key("replica_segment", {
            "task_id": getattr(self, "_task_id", None), "video": reference_video,
            "cursor": cursor, "duration": seg_duration, "prompt": seg_prompt,
            "materials": materials, "groups": getattr(self, "_material_groups", []),
            "elements": getattr(self, "_reference_elements", []), "slots": getattr(self, "_image_slots", {}),
            "ratio": ratio, "resolution": resolution, "first_frame": prev_next_frame if config.VIDEO_MULTISEG_FIRST_FRAME else "",
            "creative_level": creative_level, "hook_boost": hook_boost, "asset_override": asset_override,
        })
        checkpoint = checkpoint if checkpoint is not None else {}
        cached = ({"content": checkpoint["result_url"], "meta": checkpoint}
                  if checkpoint.get("result_url") else
                  await fetch_asset(getattr(self, "_notify_url", None), cache_key, "replica_segment")
                  if getattr(self, "_task_id", None) else None)
        if cached:
            local_seg = await asyncio.to_thread(download_to_local, cached["content"], ".mp4")
            next_frame = (cached.get("meta") or {}).get("next_frame", "")
            if local_seg and (not extract_next or next_frame):
                cleanup.append(local_seg)
                logger.info(f"多镜头恢复成功段：起点={cursor}，时长={seg_duration}")
                if on_stage:
                    await on_stage(3, {"result_url": cached["content"], "next_frame": next_frame, "status": "success"})
                return local_seg, next_frame
            if local_seg:
                cleanup.append(local_seg)
        seg_ref = ""
        if ref_duration >= cursor + seg_duration:
            seg_ref = await self._trim_reference(ffmpeg, local_ref, workdir, cursor, seg_duration)
        if not seg_ref and (getattr(self, "_image_slots", {}) or getattr(self, "_material_groups", [])) and getattr(self, "_reference_elements", []):
            raise RuntimeError("定向复刻无法取得对应原片切片，已停止；不降级为自由生成")
        if seg_ref:
            # 尾帧续接:把上一段尾帧作为本段编辑的首帧约束(需显式开启,网关不支持时 edit_video 自动降级)。
            # 首段 cursor==0 时 prev_next_frame 为空,自然不传。
            first_frame = (
                prev_next_frame if (config.VIDEO_MULTISEG_FIRST_FRAME and prev_next_frame) else None
            )
            result = await self.edit_video(
                seg_prompt, reference_video=seg_ref, duration=seg_duration,
                ratio=ratio, resolution=resolution, images=materials or None, generate_audio=True,
                replace_intent=list(intent or []), fmt=fmt,
                first_frame=first_frame,
                source_window=(cursor, cursor + seg_duration),
                creative_level=creative_level, hook_boost=hook_boost, asset_override=asset_override,
                checkpoint=checkpoint, on_stage=on_stage,
            )
        elif cursor == 0:
            # 首段必须走编辑(它是整片的起点);切片失败退回完整参考视频
            result = await self.edit_video(
                seg_prompt, reference_video=reference_video, duration=seg_duration,
                ratio=ratio, resolution=resolution, images=materials or None, generate_audio=True,
                replace_intent=list(intent or []), fmt=fmt,
                creative_level=creative_level, hook_boost=hook_boost, asset_override=asset_override,
                checkpoint=checkpoint, on_stage=on_stage,
            )
        else:
            # 原片不够长,裁不出本段切片 → 退回尾帧续接,至少保住总时长不缺口
            result = await self.image_to_video(
                seg_prompt, duration=seg_duration, ratio=ratio, resolution=resolution,
                input_image=prev_next_frame,
                checkpoint=checkpoint, on_stage=on_stage,
            )
        if not (result.metadata or {}).get("success", True):
            meta = result.metadata or {}
            raise RuntimeError(
                f"多段生成段失败: {meta.get('error') or result.content}"
            )
        local_seg = await asyncio.to_thread(download_to_local, result.content, ".mp4")
        if not local_seg:
            raise RuntimeError("多段生成段成片下载失败")
        cleanup.append(local_seg)
        next_frame = ""
        if extract_next:
            next_frame = await self._extract_and_upload_frame(ffmpeg, local_seg, workdir, len(cleanup), cleanup)
            if not next_frame:
                raise RuntimeError("抽取续接首帧失败(画面会断裂)")
        if getattr(self, "_task_id", None):
            saved = await store_asset(getattr(self, "_notify_url", None), cache_key, "replica_segment", result.content,
                                      task_type="video", meta={"next_frame": next_frame, "start": cursor, "end": cursor + seg_duration})
            if not saved:
                logger.warning(f"多镜头成功段检查点保存失败：起点={cursor}，后续重试可能重新生成")
        if on_stage:
            await on_stage(3, {"result_url": result.content, "next_frame": next_frame, "status": "success"})
        return local_seg, next_frame

    async def _generate_multi_segment(
        self, prompt: str, reference_video: str, materials: List[str], duration: int,
        ratio: str, resolution: str, script_text: str = "", intent: Optional[List[str]] = None,
        fmt: str = "", creative_level: str = "", hook_boost: str = "", asset_override: str = "",
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """超出模型单段上限时:切分参考视频 → 逐段生成(尾帧续接)→ 拼接成整片

        三个为什么:
          · 为什么分段 —— Seedance 2.x 单次上限约 15s(实测 15.2s),30s 一次生成不出来;
          · 为什么续接 —— 两段独立生成会出现人物/光线/场景突变,直接拼像两条片子;
            接缝处用 xfade 交叉淡化转场(默认开启)做平滑过渡;在此之上,可选地把上一段
            **尾帧**作为下一段编辑的首帧约束注入(VIDEO_MULTISEG_FIRST_FRAME,网关不支持时
            自动降级),让主体/光线在接缝处连续;原片不足裁不出本段切片时,再退回
            image_to_video 用尾帧作首帧兜底 —— 三者共同保证"接得上、不突变"。
          · 为什么能流复制拼接 —— 各段同模型同参数,concat 直接 copy,秒级完成、不重编码。

        任何一步失败都**明确失败并带原因**,不做"凑一段交差"的降级:残缺的成片
        比失败更糟(用户会以为成功了)。
        """
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            return self._fail("多段生成需要 ffmpeg,当前环境不可用(容器需安装 ffmpeg)", "config_error")

        self._preserve_source_timeline = True
        workdir = tempfile.mkdtemp(prefix="multiseg_")
        cleanup: List[str] = []
        try:
            # 参考视频落本地:切片、时长探测与镜头检测都需要本地文件。
            # 下载提到切分之前,是因为「按镜头切分」必须先拿到分镜表(不再多一次下载)。
            local_ref = await asyncio.to_thread(download_to_local, reference_video, ".mp4")
            if not local_ref:
                return self._fail("多段生成失败:参考视频下载失败", "request_error")
            cleanup.append(local_ref)
            ref_duration = await media_prep.probe_duration(local_ref) or 0.0
            # 分镜表(P0):检测原片镜头边界,并按镜头归集原片台词。
            # 切分改走镜头边界后,同一个镜头不会被拆到两段里分别生成 ——
            # 那正是按秒均衡切分最容易出现画面突变的位置。
            # 检测/识别失败时 shot_table 为空,plan_segments_by_shots 自动回退按秒切分。
            checkpoint = checkpoint if checkpoint is not None else {}
            manifest = checkpoint.setdefault("multi_segment", {})
            shot_table = manifest.get("shots") if manifest.get("durations") else await shots.detect_shots(local_ref, ref_duration)
            if shot_table and not manifest.get("durations"):
                shot_table = await shots.narrate_shots(local_ref, shot_table)
            durations = manifest.get("durations") or multiseg.plan_segments_by_shots(shot_table, duration)
            script_parts = multiseg.split_script_for_segments(script_text, len(durations))
            # 逐镜头逆推(P0-3):把原片每个镜头的画面/运镜描述按段注入提示词。
            # 必须放在切分之后 —— 要知道"哪几个镜头属于哪一段",描述才能归位。
            shot_map = multiseg.segment_shot_map(durations, shot_table) if shot_table else []
            shot_prompts = await self._build_shot_prompts(
                reference_video, local_ref, workdir, shot_table, list(intent or []), cleanup,
                fmt=fmt, creative_level=creative_level, hook_boost=hook_boost,
                asset_override=asset_override,
            )
            # Pixelle 引擎(可选,默认 native 不触发):用 narration→英文分镜 重建逐段提示词;
            # 仅在显式开启且成功解析出与段落数一致的提示词时启用,否则保持原生中文逐段提示词。
            pixelle_prompts: Optional[List[str]] = None
            if config.VIDEO_PROMPT_ENGINE == "pixelle" and script_parts:
                pixelle_prompts = await self._build_pixelle_video_prompts(script_parts)
            logger.info(
                f"[VideoGenTool] 时长 {duration}s 超单段上限,拆为 {len(durations)} 段: {durations}"
                f"(分镜表 {len(shot_table)} 个镜头,逆推描述 {len(shot_prompts)} 个)"
            )

            checkpoint = checkpoint if checkpoint is not None else {}
            manifest = checkpoint.setdefault("multi_segment", {})
            if manifest.get("durations"):
                durations = manifest["durations"]
                shot_table = manifest["shots"]
                shot_map = manifest["shot_map"]
            else:
                manifest.update(durations=durations, shots=shot_table, shot_map=shot_map, segments={})
            states = manifest.setdefault("segments", {})

            async def segment_stage(index, attempt, stage, data):
                state = states.setdefault(f"{index}:{attempt}", {"index": index, "attempt": attempt})
                state.update(data or {})
                state["stage"] = stage
                if on_stage:
                    await on_stage(1, {"multi_segment": manifest})

            async def run_segment(index, attempt, **kwargs):
                state = states.setdefault(f"{index}:{attempt}", {"index": index, "attempt": attempt})
                kwargs["seg_prompt"] = state.setdefault("prompt", kwargs["seg_prompt"])
                async def save_segment(stage, data):
                    await segment_stage(index, attempt, stage, data)
                await segment_stage(index, attempt, state.get("stage", 0), {"status": "processing"})
                try:
                    return await self._generate_one_segment(**kwargs, checkpoint=state, on_stage=save_segment)
                except RuntimeError as exc:
                    await segment_stage(index, attempt, state.get("stage", 0), {"status": "failed", "error": str(exc)})
                    raise

            seg_files: List[str] = []
            seg_next_frames: List[str] = []
            next_frame = ""
            cursor = 0
            for idx, seg_duration in enumerate(durations):
                seg_prompt = (
                    pixelle_prompts[idx] if pixelle_prompts and idx < len(pixelle_prompts)
                    else self._segment_prompt(
                        prompt, script_parts, idx, self._shot_hint(shot_prompts, shot_map, idx),
                        asset_override=asset_override,
                    )
                )
                try:
                    seg_file, next_frame = await run_segment(idx, 0,
                        ffmpeg=ffmpeg, seg_prompt=seg_prompt, ref_duration=ref_duration,
                        local_ref=local_ref, reference_video=reference_video, materials=materials,
                        ratio=ratio, resolution=resolution, intent=intent, cursor=cursor,
                        seg_duration=seg_duration, workdir=workdir, cleanup=cleanup,
                        prev_next_frame=next_frame, extract_next=(idx < len(durations) - 1),
                        fmt=fmt, creative_level=creative_level, hook_boost=hook_boost,
                        asset_override=asset_override,
                    )
                except RuntimeError as exc:
                    # 保留旧的错误文案形态(含段序号),便于前端/日志按既有格式解析
                    return self._fail(f"多段生成第 {idx + 1}/{len(durations)} 段失败: {exc}", "compose_error")
                seg_files.append(seg_file)
                seg_next_frames.append(next_frame)
                cursor += seg_duration

            final_url = await self._concat_segments(ffmpeg, seg_files, workdir)
            if not final_url:
                return self._fail("多段生成失败:分段拼接失败", "compose_error")
            logger.info(f"[VideoGenTool] 多段生成完成 {len(durations)} 段 {durations} → {final_url}")
            usage = self._usage(config.VIDEO_MODEL_EDIT, duration, resolution, ratio)
            result = ToolResult(content=final_url, metadata={"success": True, **usage})
            # 与单段链路一致:多段成片同样做技术自检(画幅/时长/分辨率偏差 → 打标)。
            # 此前只有单段视频编辑会自检,多段成片的画幅错了不会被任何环节发现 ——
            # 而这恰恰是本轮把 replace_intent 补进多段后最需要观测的一项(见文档 §9)。
            # 仍然**只标记不阻断**:成片已付费,残缺也比没有强。
            await self._check_output_against_reference(
                result, ratio, int(duration), ref_size=await media_prep.probe_size(reference_video),
            )
            # 与单段链路同口径:成片画幅既不像目标也不像原片 → 参考视频没生效,替换必然没发生。
            # 有替换意图时判失败,不交付"看着成功、其实没替换"的片子。
            if intent and self._output_reference_ignored(result):
                logger.error(
                    f"[VideoGenTool] 多段成片未跟随参考视频,替换({_intent_text(list(intent))})必然未生效,"
                    f"按失败处理 task={self.task_prefix}: "
                    f"{(result.metadata.get('output_mismatch') or {}).get('reason')}"
                )
                return self._fail(
                    f"替换{_intent_text(list(intent))}失败:成片未按参考视频生成"
                    f"(画幅与原片不符,说明编辑模型没有采用原片)。"
                    f"已终止本次生成并原路返还额度/退款,请稍后重试",
                    "output_mismatch",
                )
            metadata = result.metadata if isinstance(result.metadata, dict) else {}
            # 分镜表随用量回写 backend:它是「原片结构」唯一的持久化产物,
            # 供后续逐镜头质检与人工核对(改哪一镜)使用;解析失败时为空,不影响本段逻辑。
            if shot_table:
                metadata["shots"] = shot_table
            # 逆推描述同样落库:它决定了每一段实际拿到的提示词,出问题时必须可回溯
            # (列表形式而非 {序号: 描述} —— JSON 的整数键回读会变成字符串,形状不稳定)。
            if shot_prompts:
                metadata["shot_prompts"] = [
                    {"index": index, "prompt": shot_prompts[index]} for index in sorted(shot_prompts)
                ]
            # 逐镜头质检(P1-7):原片 vs 成片同位置比对,只标记不重跑(默认行为,重跑涉及额外费用)。
            # 放在拼接之后 —— 质检对象是最终成片,不是任何中间段。
            shot_qc = await self._review_shots_with_vision(
                final_url, reference_video, local_ref, workdir, shot_table, list(intent or []), cleanup,
            )

            # 自动重跑(P1-7,**默认关闭**,见 config.VIDEO_QC_AUTO_RETRY):质检低分的镜头,
            # 仅重新生成低分镜头所在段，保留其余产物，再复检整体连贯性，
            # 再拼接、再质检一次。仍低分则放弃 —— 只标记不阻断,因为重跑会额外花一次模型费用,
            # 属"需确认才开启"的行为变更,绝不能默认开启。
            if self._qc_auto_retry and shot_qc:
                low_indexes = {row["index"] for row in shot_qc if row.get("low")}
                if low_indexes:
                    low_segments = [
                        seg for seg, shot_idxs in enumerate(shot_map)
                        if any(i in low_indexes for i in shot_idxs)
                    ]
                    if low_segments:
                        logger.warning(f"逐镜头质检低分，仅修复段 {low_segments}，保留成功后缀")
                        retained = list(seg_files)
                        repairs_complete = True
                        for j in low_segments:
                            prev_nf = seg_next_frames[j - 1] if j > 0 else ""
                            cursor = float(sum(durations[:j]))
                            seg_prompt = (
                                pixelle_prompts[j] if pixelle_prompts and j < len(pixelle_prompts)
                                else self._segment_prompt(
                                    prompt, script_parts, j, self._shot_hint(shot_prompts, shot_map, j),
                                    asset_override=asset_override,
                                )
                            )
                            seg_prompt += "\n本段为质检修复重生成，请修正主体一致性及镜头结构，不复用首轮低分产物。"
                            try:
                                seg_file, prev_nf = await run_segment(j, 1,
                                    ffmpeg=ffmpeg, seg_prompt=seg_prompt, ref_duration=ref_duration,
                                    local_ref=local_ref, reference_video=reference_video, materials=materials,
                                    ratio=ratio, resolution=resolution, intent=intent, cursor=cursor,
                                    seg_duration=durations[j], workdir=workdir, cleanup=cleanup,
                                    prev_next_frame=prev_nf, extract_next=(j < len(durations) - 1),
                                    fmt=fmt, creative_level=creative_level, hook_boost=hook_boost,
                                    asset_override=asset_override,
                                )
                            except RuntimeError as exc:
                                logger.warning(
                                    f"[VideoGenTool] 低分自动重跑第 {j + 1} 段失败,放弃自动重跑: {exc}"
                                )
                                repairs_complete = False
                                break
                            retained[j] = seg_file
                            seg_next_frames[j] = prev_nf
                        if repairs_complete:
                            re_url = await self._concat_segments(ffmpeg, retained, workdir)
                            if re_url:
                                # 复检与交付必须指向同一份重跑成片，避免评分属于新片而用户拿到旧片。
                                result.content = re_url
                                shot_qc = await self._review_shots_with_vision(
                                    re_url, reference_video, local_ref, workdir, shot_table,
                                    list(intent or []), cleanup,
                                )
                                logger.info(
                                    f"[VideoGenTool] 自动重跑后复检: {len(shot_qc)} 个镜头,"
                                    f"低分 {[r['index'] for r in shot_qc if r.get('low')] or '无'}"
                                )

            if shot_qc:
                metadata["shot_qc"] = shot_qc
            metadata["segment_states"] = list(states.values())
            metadata["segment_shot_map"] = shot_map
            result.metadata = metadata
            self._attach_decision_log(result)
            return result
        finally:
            for path in cleanup:
                try:
                    os.remove(path)
                except OSError:
                    pass
            shutil.rmtree(workdir, ignore_errors=True)

    async def _trim_reference(self, ffmpeg: str, local_ref: str, workdir: str, start: int, duration: int) -> str:
        """按时间窗裁一段参考视频并上传;裁不动返回空串(调用方退回完整参考视频,不阻断)"""
        out = os.path.join(workdir, f"ref_{start}_{duration}.mp4")
        result = await compose.run(
            compose.build_trim_cmd(video=local_ref, out=out, start=start, duration=duration, ffmpeg=ffmpeg),
            timeout=300,
        )
        if not result.get("ok") or not os.path.exists(out):
            logger.warning(f"[VideoGenTool] 参考视频切片失败,退回完整参考: {result.get('stderr')}")
            return ""
        url = await asyncio.to_thread(upload_local_file, out, f"multiseg/ref_{uuid4().hex}.mp4")
        return url or ""

    async def _extract_and_upload_frame(
        self, ffmpeg: str, local_video: str, workdir: str, idx: int, cleanup: List[str],
    ) -> str:
        """抽本段最后一帧并上传,作为下一段首帧(续接成败就靠这一帧)"""
        frame_path = os.path.join(workdir, f"last_{idx}.jpg")
        result = await compose.run(
            compose.build_extract_last_frame_cmd(video=local_video, out=frame_path, ffmpeg=ffmpeg),
            timeout=120,
        )
        if not result.get("ok") or not os.path.exists(frame_path):
            logger.warning(f"[VideoGenTool] 抽取尾帧失败: {result.get('stderr')}")
            return ""
        cleanup.append(frame_path)
        url = await asyncio.to_thread(upload_local_file, frame_path, f"multiseg/frame_{uuid4().hex}.jpg")
        return url or ""

    @staticmethod
    def _per_shot_prompt(
        base: str, shot_prompts: Optional[List[str]], script_parts: List[str], idx: int,
    ) -> str:
        """逐镜第 idx 段的提示词:整体 prompt + 该镜画面描述 + 该镜台词

        为什么必须分段给:每段只看到自己的画面与台词,才不会把整段口播在每一镜里各念一遍。
        """
        parts = [str(base or "").strip()]
        if shot_prompts and idx < len(shot_prompts) and str(shot_prompts[idx]).strip():
            parts.append(f"本镜画面:{str(shot_prompts[idx]).strip()}")
        if script_parts and idx < len(script_parts) and str(script_parts[idx]).strip():
            parts.append(f"本镜台词:{str(script_parts[idx]).strip()}")
        return "\n".join([p for p in parts if p])

    async def _generate_per_shot(
        self, images: List[str], prompt: str, per_shot_seconds: int,
        ratio: str, resolution: str, shot_prompts: Optional[List[str]] = None,
        script_text: str = "",
    ) -> ToolResult:
        """N 张分镜图 → 每张独立图生视频(一段) → 拼接成片(逐镜出片)

        为什么不用「整张 3x3 拼图直接 i2v」:模型面对一张九宫格拼图,通常整格一起微动
        或只动其中一格,分镜语义完全丢失 —— 这正是当前九宫格成片观感差的原因。
        为什么不用「切 3x3 拼图再逐格 i2v」:拼图单格只有整图约 1/9 的像素
        (1024 拼图 → 每格约 341px),i2v 输入低清必然糊;逐镜独立出图才是各自全分辨率。

        任一段失败即明确失败:残缺成片比失败更糟(用户会以为生成成功了)。
        """
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            return self._fail("逐镜生成需要 ffmpeg,当前环境不可用(容器需安装 ffmpeg)", "config_error")
        seg_seconds = self._clamp_duration(per_shot_seconds or 5)
        workdir = tempfile.mkdtemp(prefix="pershot_")
        cleanup: List[str] = []
        try:
            script_parts = multiseg.split_script_for_segments(script_text, len(images)) if script_text else []
            seg_files: List[str] = []
            for idx, image in enumerate(images):
                seg_prompt = self._per_shot_prompt(prompt, shot_prompts, script_parts, idx)
                logger.info(
                    f"[VideoGenTool] 逐镜生成 {idx + 1}/{len(images)} 段 {seg_seconds}s task={self.task_prefix}"
                )
                seg = await self.image_to_video(
                    seg_prompt, duration=seg_seconds, ratio=ratio, resolution=resolution,
                    input_image=image,
                )
                meta = seg.metadata or {}
                if not meta.get("success", True):
                    return self._fail(
                        f"逐镜生成第 {idx + 1}/{len(images)} 段失败: {meta.get('error') or seg.content}",
                        meta.get("error_type") or "request_error",
                    )
                local = await asyncio.to_thread(download_to_local, str(seg.content), ".mp4")
                if not local:
                    return self._fail(f"逐镜生成第 {idx + 1}/{len(images)} 段下载失败", "request_error")
                cleanup.append(local)
                seg_files.append(local)
            final_url = await self._concat_segments(ffmpeg, seg_files, workdir)
            if not final_url:
                return self._fail("逐镜生成失败:分段拼接失败", "compose_error")
            total_seconds = seg_seconds * len(images)
            usage = self._usage(config.VIDEO_MODEL_I2V, total_seconds, resolution, ratio)
            logger.info(
                f"[VideoGenTool] 逐镜生成完成 {len(images)} 段 × {seg_seconds}s = {total_seconds}s → {final_url}"
            )
            return ToolResult(
                content=final_url,
                metadata={
                    "success": True, **usage,
                    "shot_count": len(images), "seconds": total_seconds,
                },
            )
        finally:
            for path in cleanup:
                try:
                    os.remove(path)
                except OSError:
                    pass
            shutil.rmtree(workdir, ignore_errors=True)

    async def _concat_segments(self, ffmpeg: str, seg_files: List[str], workdir: str) -> str:
        """拼接各段:同源同参数,流复制(秒级);清单用相对文件名 + cwd,规避 Windows 盘符冒号。

        转场后处理(可配置,默认关):多段之间做 xfade 交叉淡化需重编码,开启会显著增加耗时;
        段时长不足转场时长、探测失败或合成异常时自动退回流复制硬切,保证成片一定能出来。
        """
        try:
            seg_files = await media_prep.normalize_segments(seg_files, workdir, ffmpeg)
        except RuntimeError as exc:
            logger.error(f"合成输入归一化失败：{exc}")
            return ""
        expected_duration = sum([(await media_prep.probe_duration(path)) or 0 for path in seg_files])
        names: List[str] = []
        for i, path in enumerate(seg_files):
            name = f"seg_{i}.mp4"
            shutil.copy(path, os.path.join(workdir, name))
            names.append(name)
        with open(os.path.join(workdir, "list.txt"), "w", encoding="utf-8") as fh:
            fh.write(compose.build_concat_list(names))
        # 默认走流复制硬切(最快、最稳);仅当显式开启转场且段数>=2 才尝试 xfade 重编码
        transition_applied = False
        if config.TRANSITION_ENABLE and len(names) >= 2 and not getattr(self, "_preserve_source_timeline", False):
            try:
                durations = [(await media_prep.probe_duration(os.path.join(workdir, n))) or 0.0 for n in names]
                if all(d > config.TRANSITION_DURATION for d in durations):
                    # 逐镜 i2v 段可能偶发无音轨:acrossfade 会因缺音轨整条失败 → 静默降级成硬切。
                    # 先把缺音轨的段补一条静音音轨(保留视频流),确保 xfade 一定生效、接缝平滑。
                    safe_names = []
                    for n in names:
                        if await media_prep.has_audio_stream(os.path.join(workdir, n)):
                            safe_names.append(n)
                        else:
                            aud = n[:-4] + "_a.mp4"
                            r = await compose.run(
                                compose.build_ensure_audio_cmd(
                                    os.path.join(workdir, n), os.path.join(workdir, aud), ffmpeg,
                                ), cwd=workdir, timeout=120,
                            )
                            safe_names.append(
                                aud if (r.get("ok") and os.path.exists(os.path.join(workdir, aud))) else n
                            )
                    xf = compose.build_xfade_concat_cmd(
                        safe_names, durations, "merged.mp4", config.TRANSITION_DURATION,
                        transition_type=config.TRANSITION_TYPE,
                        transition_types=config.TRANSITION_TYPES or None,
                        ffmpeg=ffmpeg,
                    )
                    result = await compose.run(xf, cwd=workdir, timeout=600)
                    transition_applied = bool(result.get("ok") and os.path.exists(os.path.join(workdir, "merged.mp4")))
                else:
                    result = None
                    logger.warning("[VideoGenTool] 存在段时长不足转场时长,退回流复制拼接")
            except Exception as exc:  # noqa: BLE001
                result = None
                logger.warning(f"[VideoGenTool] 转场拼接异常,退回流复制拼接: {exc}")
            if not (result and result.get("ok") and os.path.exists(os.path.join(workdir, "merged.mp4"))):
                result = await compose.run(
                    compose.build_concat_cmd("list.txt", "merged.mp4"), cwd=workdir, timeout=300,
                )
        else:
            result = await compose.run(
                compose.build_concat_cmd("list.txt", "merged.mp4"), cwd=workdir, timeout=300,
            )
        merged = os.path.join(workdir, "merged.mp4")
        if not result.get("ok") or not os.path.exists(merged):
            logger.error(f"[VideoGenTool] 分段拼接失败: {result.get('stderr')}")
            return ""
        if transition_applied:
            expected_duration -= config.TRANSITION_DURATION * (len(names) - 1)
        actual_duration = await media_prep.probe_duration(merged)
        decoded = await compose.run([ffmpeg, "-v", "error", "-i", merged, "-f", "null", "-"], timeout=600)
        if (not actual_duration or abs(actual_duration - expected_duration) > max(0.2, len(names) * 0.08)
                or not decoded.get("ok") or (decoded.get("stderr") or "").strip()):
            logger.error("合成成片时长或解码检查失败")
            return ""
        url = await asyncio.to_thread(upload_local_file, merged, f"generate/result/{self.task_prefix}.mp4")
        return url or ""

    @staticmethod
    def _attach_script_meta(result: ToolResult, script: dict, duration: int) -> None:
        """把词锚点结果挂到 metadata(随 usage 回写 backend)。

        无合成层(P3)前,词锚点的价值是「局部重跑」与「字幕文本导出」:
        这里导出分段词数、编排 cue 与估算时间窗,P1 接真实对齐后只需替换 timing。
        """
        if not script or not script.get("segments"):
            return
        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        metadata["script"] = {
            "version": script.get("version"),
            "segments": [
                {"id": s.get("id"), "role": s.get("role"), "words": len(s.get("words") or [])}
                for s in script.get("segments") or []
            ],
            "cues": resolve_tracks(script, script.get("tracks")),
            "timing": estimate_timing(script, duration),
        }
        result.metadata = metadata

    def _chat_client(self, gw: Dict[str, str]) -> AsyncOpenAI:
        """prompt 改写专用 client(chat 能力网关):按网关地址缓存;与视频网关同址时复用主 client。"""
        url = (gw.get("url") or "").rstrip("/") or (config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/")
        if url == self.base_url.rstrip("/"):
            return self.client
        if url not in self._chat_clients:
            self._chat_clients[url] = AsyncOpenAI(
                api_key=gw.get("key") or config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY,
                base_url=url,
            )
        return self._chat_clients[url]

    async def _optimize_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """LLM 改写视频 prompt(钩子→卖点→CTA)。改写失败不影响主流程,回退原始 prompt。

        prompt 为待改写内容:结构化上下文(模板结构/商家信息/生成模式),
        或旧任务回退的扁平 prompt(此时调用方已补上素材语义行)。
        system_prompt 由调用方按本次任务的画幅/清晰度渲染(见 prompt_template),
        未传时按默认竖版渲染,仅供直连调用/旧代码路径兜底。

        改写走 chat 能力网关(gen.route.chat),在候选网关间做故障转移。
        这里刻意不调用 _with_failover:它不会改动视频网关状态,
        避免 prompt 改写失败把后续视频轮询带到别的网关上查任务。
        """
        system_prompt = system_prompt or build_prompt_optimize_system()
        if not config.CHAT_MODEL:
            return prompt
        # P2 资产缓存:同一份上下文 + 同一系统提示 + 同一模型 → 复用上次改写结果。
        # 换素材/改文案时上下文变了自然 miss;批量生成同模板任务则稳定命中。
        cache_key = build_cache_key(ASSET_OPTIMIZED_PROMPT, {
            "model": config.CHAT_MODEL, "system": system_prompt, "user": prompt,
        })
        cached = await asset_cache.fetch(self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT)
        if cached and cached.get("content"):
            return str(cached["content"])

        candidates = gateway.resolve_all("chat")
        if not candidates:
            candidates = [{
                "name": "env",
                "url": (config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/"),
                "key": config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY,
                "proto": "openai",
            }]

        last_exc: Optional[Exception] = None
        for gw in candidates:
            try:
                resp = await self._chat_client(gw).chat.completions.create(
                    model=config.CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    timeout=CHAT_REWRITE_TIMEOUT,
                )
                text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
                if text:
                    logger.info(f"[VideoGenTool] prompt 改写完成: {text[:60]}")
                    await asset_cache.store(
                        self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT, text, task_type="video",
                        meta={"model": config.CHAT_MODEL},
                    )
                    return text
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(f"[VideoGenTool] prompt 改写经 [{gw['name']}] 失败,尝试下一个: {exc}")
        if last_exc:
            logger.warning(f"[VideoGenTool] prompt 改写失败(回退原始 prompt): {last_exc}")
        return prompt

    async def _build_pixelle_video_prompts(self, narrations: List[str]) -> Optional[List[str]]:
        """Pixelle 引擎:把分段台词(narrations)交给 chat LLM 生成逐段英文视频提示词。

        仅当 config.VIDEO_PROMPT_ENGINE == "pixelle" 时由多段生成调用。
        任何失败(无 chat 模型 / 网关全挂 / 解析失败 / 条数不符)都返回 None,
        调用方据此回退到既有中文逐段提示词,不影响主流程。
        """
        if not config.CHAT_MODEL:
            return None
        system_prompt = build_video_generation_prompt(narrations)
        cache_key = build_cache_key(ASSET_OPTIMIZED_PROMPT, {
            "model": config.CHAT_MODEL, "system": "pixelle_video", "user": "||".join(narrations),
        })
        cached = await asset_cache.fetch(self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT)
        if cached and cached.get("content"):
            parsed = parse_video_prompts(str(cached["content"]))
            if parsed and len(parsed) == len(narrations):
                return parsed
        candidates = gateway.resolve_all("chat") or [{
            "name": "env",
            "url": (config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/"),
            "key": config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY,
            "proto": "openai",
        }]
        last_exc: Optional[Exception] = None
        for gw in candidates:
            try:
                resp = await self._chat_client(gw).chat.completions.create(
                    model=config.CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "请严格按输出格式输出 JSON。"},
                    ],
                    timeout=CHAT_REWRITE_TIMEOUT,
                )
                text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
                if not text:
                    continue
                parsed = parse_video_prompts(text)
                if parsed and len(parsed) == len(narrations):
                    await asset_cache.store(
                        self._notify_url, cache_key, ASSET_OPTIMIZED_PROMPT, text,
                        task_type="video", meta={"model": config.CHAT_MODEL},
                    )
                    return parsed
                logger.warning(
                    f"[VideoGenTool] Pixelle 视频提示词条数不符(期望 {len(narrations)},"
                    f"实得 {len(parsed) if parsed else 0}),回退原生"
                )
                return None
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(f"[VideoGenTool] Pixelle 视频提示词经 [{gw['name']}] 失败,尝试下一个: {exc}")
        if last_exc:
            logger.warning(f"[VideoGenTool] Pixelle 视频提示词生成失败(回退原生): {last_exc}")
        return None

    async def text_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "9:16",
        resolution: str = "1080P", checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """根据文字描述生成一段视频"""
        payload = {
            "model": model or config.VIDEO_MODEL_T2V,
            "prompt": prompt,
            "seconds": str(duration),
            "metadata": {"parameters": {"resolution": resolution, "ratio": ratio, "duration": duration}},
        }
        decision = self._new_decision("t2v", payload["model"], duration, resolution, ratio)
        result = await self._submit_and_poll(
            payload, "文生视频", duration, resolution, ratio, "t2v",
            checkpoint=checkpoint, on_stage=on_stage, decision=decision,
        )
        self._record_decision(decision)
        return result

    async def image_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "9:16",
        resolution: str = "1080P", input_image: Optional[str] = None,
        checkpoint: Optional[dict] = None, on_stage=None,
        real_person_strategy: Optional[str] = None,
    ) -> ToolResult:
        """基于首帧图片 + 文字描述生成视频。

        画幅**必须显式下发**:首帧图未必就是目标画幅(实测:素材图是 1024×1024 正方形),
        不传 ratio 时成片画幅完全跟随首帧图,出来就是正方形 —— 与系统配置的
        gen.video_ratio(9:16) 不符,用户看到的是"画幅不对"(实测踩过)。
        旧注释「i2v 模型不支持 ratio 参数」针对的是已停用的 happyhorse-1.1-i2v;
        当前 i2v 与 r2v/t2v 同属 seedance 2.0 系,而 r2v/t2v 一直带 ratio 且正常出片。
        """
        if not input_image:
            return self._fail("图生视频失败:未提供首帧图片 URL", "invalid_request")
        payload = {
            "model": model or config.VIDEO_MODEL_I2V,
            "prompt": prompt,
            "image": input_image,
            "seconds": str(duration),
            "metadata": {"parameters": {"resolution": resolution, "ratio": ratio, "duration": duration}},
        }
        # 单图被判定含真人(方舟隐私策略)时:图生视频无首帧可用 → 退化为文生视频
        # (prompt 里仍有视觉识别出的文字描述作画面依据),而不是整单失败。
        # per-task 真人处理策略:未显式传则沿用 generate() 注入的 self._real_person_strategy
        strategy = real_person_strategy or getattr(self, "_real_person_strategy", None)
        decision = self._new_decision("i2v", payload["model"], duration, resolution, ratio)
        result = await self._submit_and_fix_real_person(
            payload, "图生视频", duration, resolution, ratio, "i2v",
            checkpoint=checkpoint, on_stage=on_stage, decision=decision,
            keep_person=True, real_person_strategy=strategy,
            no_image_fallback=lambda: self.text_to_video(
                prompt, duration=duration, ratio=ratio, resolution=resolution,
                checkpoint=checkpoint, on_stage=on_stage,
            ),
        )
        self._record_decision(decision)
        return result

    async def reference_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "9:16",
        resolution: str = "1080P", reference_images: Optional[List[str]] = None,
        checkpoint: Optional[dict] = None, on_stage=None,
        real_person_strategy: Optional[str] = None,
    ) -> ToolResult:
        """基于参考图片 + 文字描述生成视频"""
        if not reference_images:
            return self._fail("参考生视频失败:未提供参考图片", "invalid_request")
        payload = {
            "model": model or config.VIDEO_MODEL_R2V,
            "prompt": prompt,
            "images": reference_images,
            "seconds": str(duration),
            "metadata": {"parameters": {"resolution": resolution, "ratio": ratio, "duration": duration}},
        }
        # 参考图被判定含真人时:处理掉那张图后重试;若因此一张不剩,退化为文生视频
        # (仍保留 prompt 中视觉识别出的文字描述),而不是整单失败。
        # per-task 真人处理策略:未显式传则沿用 generate() 注入的 self._real_person_strategy
        strategy = real_person_strategy or getattr(self, "_real_person_strategy", None)
        decision = self._new_decision("r2v", payload["model"], duration, resolution, ratio)
        result = await self._submit_and_fix_real_person(
            payload, "参考生视频", duration, resolution, ratio, "r2v",
            checkpoint=checkpoint, on_stage=on_stage, decision=decision,
            keep_person=True, real_person_strategy=strategy,
            no_image_fallback=lambda: self.text_to_video(
                prompt, duration=duration, ratio=ratio, resolution=resolution,
                checkpoint=checkpoint, on_stage=on_stage,
            ),
        )
        self._record_decision(decision)
        return result

    def _build_replace_directive(
        self, replace_intent: Optional[List[str]], images: Optional[List[str]],
    ) -> str:
        """把替换意图转成「确定性强、追加在 prompt 末尾」的编辑指令。

        为什么必须追加在改写之后、且逐维度显式写出:
        - backend 已在 prompt_context 的 [补充要求] 里写过替换语义,但 worker 上游会用 LLM
          把整段 prompt 重写成『钩子→卖点→CTA』,改写模型常把『替换参考视频原有元素』这类
          指令弱化/丢弃,导致成片保留原片商品/人物 —— 正是用户反馈『换产品/换人物/换场景无效』的根因。
        - 因此在真正提交编辑模型前,把替换意图确定性地拼到 prompt 最末尾,确保模型最后看到的
          一定是强制替换指令,不受上游改写影响。
        - 有上传图时指示『用提供的参考图替换』;换人物/换场景若未提供专门图,则指示『生成新元素』。
          指令只针对被替换维度,其余维度保持原片。

        追加一条「复刻形态」相关约束:形态要求"让出镜者演"(口播/短剧/街采…),而默认尾巴写的是
        "其余所有维度严格保持一致" —— 动作也被算进去,两条指令直接打架,模型多半听后者,
        成片就是"原片动作 + 换了张脸",观感上"一点创意也没有"(用户投诉原话)。
        因此选了形态时必须显式**放开对动作的约束**,而不是指望模型自己权衡。
        """
        fmt = self._replicate_format
        if not replace_intent and not fmt:
            return ""
        has_img = bool(images)
        # 各维度的新主体描述(backend 视觉识别下发):有文字描述时模型对「换成什么」有明确锚点,
        # 只靠参考图时编辑模型经常"看图但不换"(实测 task=43:意面沙拉图 + 汉堡原片 → 成片仍汉堡)。
        subjects = self._replace_subjects if isinstance(self._replace_subjects, dict) else {}
        clauses: List[str] = []
        for raw in (replace_intent or []):
            key = str(raw).strip().lower()
            desc = str(subjects.get(key) or "").strip()
            desc_tail = f"(主体特征:{desc})" if desc else ""
            if key == "product":
                if has_img:
                    clauses.append(
                        "将参考视频中的原有【商品/产品】整体替换为提供的参考图里的商品"
                        f"{desc_tail}:商品本体、包装、颜色、Logo 等所有视觉细节以参考图为准;"
                    )
                else:
                    clauses.append(f"将参考视频中的原有【商品/产品】替换为新商品{desc_tail};")
                # 原片内嵌字幕/文字是烧录在像素里的,不显式指示就必然原样保留 ——
                # 这正是『商品换了、画面字幕还在说原商品』(意面沙拉配"汉堡"字幕)的独立成因。
                clauses.append(
                    "原视频中商品出现的每一个画面(手持、特写、品尝、摆放)都必须换成新商品,"
                    "不得残留原商品的任何画面;"
                    "画面内嵌的字幕/贴片文字/招牌/包装文字若提及原商品的品类或名称,"
                    "必须同步改写为与新商品一致的表述,严禁保留原商品的品类词;"
                )
            elif key == "person":
                clauses.append(
                    "将参考视频中的原有【人物/出镜者】替换为新人物"
                    "(若本次提供了对应参考图,以其外观为基准:脸型、发型、服饰等保持一致"
                    f"{(';' + desc) if desc else ''});"
                )
                # 只换外观会退化成"静景翻拍":不显式锁定动作与情节,模型常把连续动作改成静止画面、
                # 甚至省略原片镜头(实测:原片"狗拉着婴儿车奔跑"在成片里整段消失)。
                clauses.append(
                    "新人物必须完整承接原片人物的动作、姿态与运动轨迹(原片在做什么,新人物就做什么),"
                    "严禁把连续动作改成静止站立或滑行、严禁消失出画、严禁省略或改写原有镜头与事件;"
                )
            elif key == "scene":
                clauses.append(
                    "将参考视频中的原有【场景/背景/环境】替换为新场景"
                    "(若本次提供了对应参考图,以其为场景基准"
                    f"{(';' + desc) if desc else ''});"
                )
        if not clauses and not fmt:
            return ""
        # 主角表现(创意增强):仅"换人物"时追加 —— 上游改写常把"跳舞/推广"的表演要求弱化,
        # 故与替换指令一样在末端确定性追加;正文单一来源是 backend 的 gen_lead_act_*.md。
        lead_key = str(getattr(self, "_lead_act", "") or "").strip().lower()
        person_requested = any(str(i).strip().lower() == "person" for i in replace_intent)
        if person_requested and lead_key in LEAD_ACT_ASSETS:
            asset_name, default_text = LEAD_ACT_ASSETS[lead_key]
            lead_text = safe_render(asset_name, default=default_text).strip()
            if lead_text:
                clauses.append(lead_text + ";")
        header = "【强制替换要求】以下替换必须发生,严禁保留原视频对应元素:"
        lines = [header] + [f"- {c}" for c in clauses]
        if fmt:
            # 形态存在时:动作/表演归模型自由发挥(按形态演),其余维度继续钉死原片。
            lines.append(
                "- 【出镜者表演】出镜者的动作、表情与叙事方式按上文【复刻形态】要求重新演绎,"
                "严禁照搬原片出镜者的原有动作。"
            )
            footer = (
                "场景、背景、画幅、镜头运动与节奏仍严格保持与原参考视频一致;"
                "仅出镜者的动作与表演按上述形态重塑;未提及的其他主体不得改动。"
            )
        else:
            footer = (
                "其余所有维度(构图、运镜、节奏、转场、未提及的主体)严格保持与原参考视频一致,"
                "不得因上述替换改变整体观感。"
            )
        return "\n" + "\n".join(lines) + "\n" + footer

    def _build_style_directive(
        self, creative_level: str, hook_boost: str, asset_override: str,
    ) -> str:
        """把创意档位/开头钩子/专家追加要求转成「确定性强、追加在 prompt 末尾」的编辑指令。

        与 _build_replace_directive 同一范式:在真正提交编辑模型前确定性地拼到 prompt 末尾,
        确保模型最后看到的一定是这些指令,不受上游 LLM 改写弱化影响。

        - creative_level:空/faithful=忠实复刻(编辑模型默认即跟随原片,不追加);
          creative=适度改造(保留原片结构做创意增强);viral=爆款改写(按爆款逻辑重塑表演与节奏)。
        - hook_boost:strong=前 3 秒用强钩子抓住注意力;其余不追加。
        - asset_override:专家模式追加的创作要求,原样挂在末尾(位置即优先级)。
        """
        cl = str(creative_level or "").strip().lower()
        hb = str(hook_boost or "").strip().lower()
        override = str(asset_override or "").strip()
        clauses: List[str] = []
        if cl == "viral":
            clauses.append(
                "按爆款逻辑重塑表演与节奏,强化记忆点与情绪起伏,用更有冲击力的方式重演原片内容;"
            )
        elif cl == "creative":
            clauses.append(
                "在保留原片风格与结构的基础上做创意增强,不要大改原片的镜头骨架与叙事;"
            )
        # faithful / 空 / 其它:不追加(编辑模型默认忠实跟随原片)
        if hb == "strong":
            clauses.append("前 3 秒必须用强钩子抓住注意力(抛出冲突/反差/悬念),提升完播率;")
        if override:
            clauses.append(f"(用户额外创作要求){override}")
        if not clauses:
            return ""
        header = "【创意与节奏要求】以下要求必须体现在成片中:"
        lines = [header] + [f"- {c}" for c in clauses]
        return "\n" + "\n".join(lines)

    async def _matte_product_images(
        self, images: List[str], replace_intent: Optional[List[str]]
    ) -> Tuple[List[str], str]:
        """换商品时,把含真人的上传图抠成纯商品前景,避免真人泄漏进成片。

        入参 images 为替换目标图 URL 列表;返回(处理后 URL 列表, 处理说明)。
        仅当「intent=product 且视觉识别到图含人物」才对图做抠像——干净的纯商品图不折腾,
        避免透明通道边缘损伤。抠像网关未配置/任一图抠失败 → 该图保持原样(整图直传),
        整体回退说明写入 note,由上层既有「真人拦截→拟态化/丢弃」兜底,保证不阻断生成。
        """
        # 只有换商品且图里真有人才需要抠:纯商品图抠了反而可能损边缘
        person_in_image = str((self._replace_subjects or {}).get("person") or "").strip()
        if not person_in_image:
            return images, ""
        # 抠像网关未配置 → 直接跳过(不下载、不联网),整图直传沿用既有真人拦截兜底
        if not gateway.resolve_all("matting"):
            return images, ""
        # 延迟导入:抠像工具与视频工具互不依赖,保持按需加载
        from app.tools.matting_tool import MattingTool
        tool = MattingTool()
        workdir = tempfile.mkdtemp(prefix="prod_matte_")
        out: List[str] = []
        matted = 0
        failed = 0
        try:
            for url in images:
                local = await asyncio.to_thread(download_to_local, url, ".png")
                if not local:
                    out.append(url)
                    failed += 1
                    continue
                res = await tool.matte_image(local, task_id=self.task_prefix, workdir=workdir)
                fg_path = res.content if (res.metadata or {}).get("success") else ""
                if fg_path and os.path.exists(fg_path):
                    new_url = await asyncio.to_thread(
                        upload_local_file, fg_path, f"generate/material/{uuid4().hex}.png"
                    )
                    if new_url:
                        out.append(new_url)
                        matted += 1
                    else:
                        out.append(url)
                        failed += 1
                else:
                    out.append(url)
                    failed += 1
                # 清理本地下载/抠像中间文件(抠像产物已上传,本地的可删)
                for p in (local, fg_path):
                    if p and os.path.exists(p):
                        try:
                            os.remove(p)
                        except OSError:
                            pass
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        note = ""
        if matted:
            note = f"已将 {matted} 张含真人的商品图抠出纯商品前景(去除人物),避免人物泄漏进成片"
        elif failed:
            note = "含真人的商品图抠像未生效(网关未配置或失败),已回退整图直传(沿用真人拦截兜底)"
        return out, note

    async def edit_video(
        self, prompt: str, reference_video: str, model: Optional[str] = None, duration: int = 5,
        ratio: str = "9:16", resolution: str = "1080P", images: Optional[List[str]] = None,
        generate_audio: bool = True, checkpoint: Optional[dict] = None, on_stage=None,
        replace_intent: Optional[List[str]] = None,
        fmt: str = "",
        real_person_strategy: Optional[str] = None,
        first_frame: Optional[str] = None,
        creative_level: Optional[str] = None,
        hook_boost: Optional[str] = None,
        asset_override: Optional[str] = None,
        source_window: Optional[Tuple[float, float]] = None,
    ) -> ToolResult:
        """视频编辑(Seedance 2.x):参考视频 + 商品图 + 新台词 → 同款新片

        与 r2v 的本质区别:
          r2v 传的是**参考视频的抽帧图片** —— 只保留构图/色调,丢掉原片的运镜、节奏与转场;
          视频编辑直接传**视频本身**,模型能学到镜头语言,且可生成与新台词同步的语音
          (lip-synced speech),字幕时间轴才对得上。

        字段名按 OpenAI 兼容网关常见约定(videos / generate_audio);不同中转站可能只认
        sound 或 duration,故失败时上层会降级回 r2v,不会因为字段不认就整个任务失败。
        """
        # 允许调用方显式覆盖(局部重跑需与首轮同源);未传则取本任务从建单参数下发的档位
        creative_level = creative_level if creative_level is not None else getattr(self, "_creative_level", "")
        hook_boost = hook_boost if hook_boost is not None else getattr(self, "_hook_boost", "")
        asset_override = asset_override if asset_override is not None else getattr(self, "_asset_override", "")
        if not reference_video:
            return self._fail("视频编辑失败:未提供参考视频", "invalid_request")
        # 编辑任务允许 4~30s(普通参考生视频仅 15s):按编辑上限裁剪,避免白丢后半段。
        # 同时把参考视频对齐到目标画幅:方舟编辑只认 ratio=adaptive,成片画幅跟随参考视频,
        # 不对齐的话请求里的 9:16 会被静默忽略(实测:请求 9:16、成片 16:9)。
        # O5:纯复刻(无替换意图)且开关开启 → 不强制裁切,成片画幅跟随参考视频(保留原片构图)。
        fit_ratio = ratio
        if config.REPLICATE_FOLLOW_REFERENCE_RATIO and not replace_intent:
            fit_ratio = ""
        reference_video = await media_prep.fit_reference_video(
            reference_video,
            max_seconds=media_prep.video_edit_max_seconds(),
            ratio=fit_ratio,
        )
        # 编辑成片时长必须**跟随参考视频**(用户要的是"原片多长就多长"),不能沿用图片链路的吸附档位:
        # 实测参考视频 6.97s、成片只有 5.06s —— 被砍掉的后半段正是原片的关键动作画面。
        # 方舟原生协议其后还会强制覆盖为 duration=-1;这里同时纠正非方舟/兼容协议下的提交时长。
        ref_seconds = await media_prep.probe_duration(reference_video)
        if ref_seconds:
            duration = max(1, int(round(ref_seconds)))
        # 替换意图必须**确定性**地写进提交给编辑模型的 prompt(追加在最末尾)。
        # 上游 LLM 改写常把 backend [补充要求] 里的替换语义弱化/丢弃,导致成片仍是原片元素
        # (用户反馈『换产品/换人物/换场景无效』的根因)。此处兜底,确保模型最后看到的
        # 一定是强制替换指令,不依赖改写模型是否保留。
        # 不再用 `if replace_intent` 把它挡在外面:只选了复刻形态(未选替换维度)的任务同样需要
        # 这条确定性指令 —— 上游 LLM 改写会弱化 [复刻形态],而"放开对动作的约束"正是它最容易丢的一句。
        # 替换意图(确定性)与创意档位/钩子/专家追加要求(确定性)都追加到 prompt 末尾,
        # 确保模型最后看到的一定是强制指令,不受上游 LLM 改写弱化影响。
        directive = self._build_replace_directive(replace_intent, images)
        style_directive = self._build_style_directive(creative_level, hook_boost, asset_override)
        try:
            binding_directive = build_binding_directive(
                images or [], getattr(self, "_image_slots", {}), getattr(self, "_reference_elements", []), source_window,
                material_groups=getattr(self, "_material_groups", []),
            )
        except ValueError as exc:
            return self._fail(f"原片元素绑定无效:{exc}", "invalid_request")
        extras = [d for d in (directive, style_directive, binding_directive) if d]
        if extras:
            prompt = (prompt or "").strip() + "\n".join(extras)
        payload = {
            "model": model or config.VIDEO_MODEL_EDIT,
            "prompt": prompt,
            "videos": [reference_video],
            "seconds": str(duration),
            "generate_audio": bool(generate_audio),
            "metadata": {"parameters": {"resolution": resolution, "ratio": ratio, "duration": duration}},
        }
        # 「换商品」且上传图含真人 → 先把商品从图中抠出,避免真人被一起带进成片。
        # 电商带货图常为「模特+商品」复合图:整图直传会让模型把人物也替换进去(成片多出无关人物、
        # 且姿态会从「上身穿」漂移成「手持」),参考 task 47。抠出纯商品后替换目标只剩商品本身,
        # 原片人物穿上新商品、不再触发真人隐私拦截、也不走拟态化保人。
        # 抠像网关未配置/失败 → 优雅回退为整图直传(沿用既有真人拦截→拟态化/丢弃兜底),不阻断主链路。
        matte_note = ""
        if images and "product" in (replace_intent or []):
            images, matte_note = await self._matte_product_images(images, replace_intent)
            if matte_note:
                logger.info(f"[VideoGenTool] 换商品抠图: {matte_note} task={self.task_prefix}")
        if images:
            payload["images"] = images
        # 尾帧续接(可选):上一段尾帧作为本段编辑的首帧约束,让多段成片接缝处主体连续。
        # 方舟编辑协议原生不含首帧参数,不支持的网关会在提交阶段 400,
        # 由下方降级逻辑去掉该字段重试(见 edit_video 末段)。
        if first_frame:
            payload["first_frame"] = first_frame
        # 提交并轮询;若"输入素材含真人"被平台拦下,做**有界本地修正**后重试:
        #   · 参考图含真人 → 丢弃该图(图转文)或拟态化后再提交;
        #   · 参考视频含真人 → 本地去身份化后重新提交。
        # 两类各最多修正一次;处理结果回写 image_note / deidentify_note,绝不静默。
        # 有替换意图时编辑失败仍走上层"不降级"策略(见 generate),这里的修正不改变该结论。
        # per-task 真人处理策略:未显式传则沿用 generate() 注入的 self._real_person_strategy
        # 替换素材图若被平台判定含真人而**全部丢弃**,编辑模型就失去"换成什么"的锚点、只能自由生成,
        # 表现就是"新主角根本没出现"(实测现象)。这种"看似成功、其实没做替换"的成片比失败更糟
        # (用户既拿不到效果、也拿不回额度),故在替换意图场景下明确失败并给出可执行修法。
        async def _no_replace_image_fail() -> ToolResult:
            return self._fail(
                f"替换{_intent_text(list(replace_intent or []))}失败:"
                "上传的替换素材图被平台判定含真人并已移除,没有可用的替换目标。"
                "请改用不含真人的素材图,或把真人处理策略调为「写实化保留」后重试",
                # 专用失败码:前端据此直接引导去「数字人」或换素材,而不是让用户自己读文案猜
                "real_person_blocked",
            )
        # per-task 真人处理策略:未显式传则沿用 generate() 注入的 self._real_person_strategy
        strategy = real_person_strategy or getattr(self, "_real_person_strategy", None)
        decision = self._new_decision("edit", payload["model"], duration, resolution, ratio)
        result = await self._submit_and_fix_real_person(
            payload, "视频编辑", duration, resolution, ratio, "edit",
            checkpoint=checkpoint, on_stage=on_stage, allow_video_fix=True, decision=decision,
            keep_person=True, real_person_strategy=strategy,
            # 有替换意图时才接管"图片被清空"的兜底(纯复刻无替换目标,保持既有重提交行为)
            no_image_fallback=_no_replace_image_fail if replace_intent else None,
        )
        # 尾帧续接降级:网关不支持编辑首帧(多为 400/参数错误)时,去掉首帧重试一次,
        # 退回"无首帧约束"的既有行为,保证多段成片仍能拼出(见 _generate_multi_segment)。
        if (not (result.metadata or {}).get("success", True)) and payload.get("first_frame"):
            logger.warning(
                f"[VideoGenTool] 编辑首帧续接不被网关接受,去掉首帧重试 task={self.task_prefix}"
            )
            payload.pop("first_frame", None)
            result = await self._submit_and_fix_real_person(
                payload, "视频编辑", duration, resolution, ratio, "edit",
                checkpoint=checkpoint, on_stage=on_stage, allow_video_fix=True, decision=decision,
                keep_person=True, real_person_strategy=strategy,
                no_image_fallback=_no_replace_image_fail if replace_intent else None,
            )
        # 换商品抠图说明回写 metadata:成功时标记已抠出纯商品,失败回退时标记未生效,
        # 便于后端/前端区分「成片是否可能因含真人而走了拟态化兜底」。
        if matte_note and (result.metadata or {}).get("success"):
            result.metadata["product_matting"] = matte_note
        self._record_decision(decision)
        return result

    async def regenerate_segment(
        self, params: dict, segment_index: int, new_text: str,
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """局部重跑(O7):只重生成某一分段的口播,烧录字幕后与原始成片拼接替换。

        用于"复刻后想改一句台词"——不必整条重跑,省额度与时延。依赖 script_anchors 的
        segments[].timing(已在 O6 时间轴导出)。

        入参 params 需额外携带:
          - original_video: 原始成片 URL(把新段替换回原片时间窗)
          - segment_index / new_text: 目标分段下标与新口播文案
        其余沿用原始生成参数(reference_video / materials / ratio / resolution 等)。
        """
        script = params.get("script") or {}
        segments = script.get("segments") or []
        if not (0 <= segment_index < len(segments)):
            return self._fail(
                f"局部重跑失败:分段下标越界({segment_index}/{len(segments)})", "invalid_request",
            )
        seg = segments[segment_index]
        timing = seg.get("timing") or {}
        start_ms = int(timing.get("start_ms") or 0)
        end_ms = int(timing.get("end_ms") or 0)
        if end_ms <= start_ms:
            return self._fail("局部重跑失败:目标分段缺少有效时间窗(timing)", "invalid_request")
        window_ms = end_ms - start_ms
        # 分段时长:方舟最短 4s,不足则补齐(避免传非法时长被 400)
        seg_duration = max(4, int(round(window_ms / 1000.0)))

        # 视觉生成提示词:优先采用用户编辑后的复刻描述(edited_prompt),否则沿用口播(new_text)/原台词。
        # 字幕文案独立于视觉提示词:用 new_text 或原台词,避免把"画面描述"烧进字幕里。
        edited_prompt = str(params.get("edited_prompt") or "").strip()
        subtitle_text = (new_text or "").strip() or str(seg.get("text") or "")
        gen_prompt = edited_prompt or subtitle_text
        reference_video = str(params.get("reference_video") or "").strip()
        materials = _replace_assets(params)
        self._image_slots = params.get("image_slots") or {}
        self._material_groups = params.get("material_groups") or []
        self._reference_elements = params.get("reference_elements") or []
        # 替换意图必须一并取回并传下去:首轮有意图时成片会**强制对齐目标画幅**,
        # 重跑若不传,方舟会改成"跟随参考视频画幅"(edit_video 的 fit_ratio 分支),
        # 重跑段画幅与首轮不一致 —— 拼回原片后画幅就对不上了。
        replace_intent = [str(i).strip() for i in (params.get("intent") or []) if str(i).strip()]
        # 复刻目标形态一并取回并传下去:与首轮同源,否则重跑段不会按该形态重塑结构,
        # 与原片其余分段形态不一致(同 P1-6 口径一致性问题)。
        replicate_format = str(params.get("format") or "").strip()
        # 主角表现同样取回:与首轮同源,否则"跳舞/推广"的重跑段会与原片其余分段表现不一致。
        self._lead_act = str(params.get("lead_act") or "").strip().lower()
        # 创意档位/开头钩子/专家追加要求同样取回:与首轮同源,否则重跑段风格/节奏与原片其余分段不一致。
        self._creative_level = str(params.get("creative_level") or "").strip().lower()
        self._hook_boost = str(params.get("hook_boost") or "").strip().lower()
        self._asset_override = str(params.get("asset_override") or "").strip()
        # 低分镜头自动重跑:默认沿用全局配置(关闭)。建单显式传 qc_auto_retry 时按任务覆盖 ——
        # 重跑会产生新的模型费用,因此只接受"显式开启",绝不在代码里静默改成默认开启。
        _qa = params.get("qc_auto_retry")
        self._qc_auto_retry = bool(config.VIDEO_QC_AUTO_RETRY) if _qa is None else bool(_qa)
        ratio = params.get("ratio") or config.VIDEO_RATIO
        resolution = params.get("resolution") or config.VIDEO_RESOLUTION

        # 1) 按原始生成模式重生成该分段:有参考视频则裁到该时间窗后视频编辑(保留原片运镜)
        if reference_video:
            window_url = await self._trim_video_window(reference_video, start_ms, end_ms)
            if not window_url and (self._image_slots or self._material_groups) and self._reference_elements:
                return self._fail("定向复刻重跑无法取得原片切片，不使用完整视频替代", "invalid_reference")
            seg_result = await self.edit_video(
                gen_prompt, reference_video=window_url or reference_video, duration=seg_duration,
                source_window=(start_ms / 1000, end_ms / 1000) if window_url else None,
                ratio=ratio, resolution=resolution, generate_audio=True,
                # 替换素材与首轮同源:不带 images 的话,重跑段会照抄原片该窗口的商品/人物,
                # 等于把首轮做好的替换又换回去了(实测口径一致性问题,P1-6)
                images=materials or None,
                checkpoint=checkpoint, on_stage=on_stage, replace_intent=replace_intent,
                fmt=replicate_format,
                creative_level=self._creative_level, hook_boost=self._hook_boost,
                asset_override=self._asset_override,
            )
        elif len(materials) == 1:
            seg_result = await self.image_to_video(
                gen_prompt, duration=seg_duration, ratio=ratio, resolution=resolution,
                input_image=materials[0], checkpoint=checkpoint, on_stage=on_stage,
            )
        elif len(materials) > 1:
            seg_result = await self.reference_to_video(
                gen_prompt, duration=seg_duration, ratio=ratio, resolution=resolution,
                reference_images=materials, checkpoint=checkpoint, on_stage=on_stage,
            )
        else:
            seg_result = await self.text_to_video(
                gen_prompt, duration=seg_duration, ratio=ratio, resolution=resolution,
                checkpoint=checkpoint, on_stage=on_stage,
            )
        if not (seg_result.metadata or {}).get("success", True):
            return seg_result

        # 2) 烧录该段字幕(仅本段时间窗,保证与原片时间轴对齐)
        seg_url = seg_result.content
        seg_script = {"segments": [{**seg, "text": subtitle_text, "timing": {"start_ms": 0, "end_ms": window_ms}}]}
        burned = await subtitle.burn_subtitle(seg_url, {"script": seg_script}, seg_duration, prefix=f"seg{segment_index}")
        if burned:
            seg_url = burned

        # 3) 拼回原片对应时间窗;无 original_video 则只返回新段
        original_video = str(params.get("original_video") or "").strip()
        final_url = seg_url
        spliced = False
        if original_video:
            spliced_url = await self._splice_segment(original_video, seg_url, start_ms, end_ms)
            if not spliced_url:
                return ToolResult(content="局部镜头已生成，但合成整片失败，请重试合成", metadata={
                    "success": False, "segment_url": seg_url,
                    "original_video": original_video, "spliced": False,
                })
            final_url = spliced_url
            spliced = True

        logger.info(
            f"[VideoGenTool] 局部重跑完成 segment={segment_index} window={start_ms}-{end_ms}ms "
            f"spliced={spliced} task={self.task_prefix}"
        )
        return ToolResult(content=final_url, metadata={
            "success": True,
            "segment_index": segment_index,
            "window_ms": [start_ms, end_ms],
            "segment_url": seg_url,
            "original_video": original_video or None,
            "spliced": spliced,
            "subtitle_burned": bool(burned),
        })

    async def _trim_video_window(self, url: str, start_ms: int, end_ms: int) -> Optional[str]:
        """用 ffmpeg 把视频裁到 [start_ms, end_ms] 时间窗(本地处理,失败返回 None)"""
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg or not url:
            return None
        local = await asyncio.to_thread(download_to_local, url, suffix=".mp4")
        if not local:
            return None
        out = os.path.join(tempfile.gettempdir(), f"seg_{uuid4().hex}.mp4")
        try:
            result = await compose.run([
                ffmpeg, "-y", "-ss", f"{start_ms / 1000:.2f}", "-to", f"{end_ms / 1000:.2f}",
                "-i", local, "-c:v", "libx264", "-c:a", "aac", out,
            ], timeout=300)
            if result.get("ok") and os.path.exists(out):
                return await asyncio.to_thread(
                    upload_local_file, out, f"reference/seg_{uuid4().hex}.mp4",
                )
            return None
        finally:
            for path in (local, out):
                try:
                    os.remove(path)
                except OSError:
                    pass

    async def _splice_segment(
        self, original_url: str, segment_url: str, start_ms: int, end_ms: int,
    ) -> Optional[str]:
        """把新段替换进原片 [start_ms, end_ms] 时间窗(ffmpeg 三分段拼接,失败返回 None)。

        依赖 ffmpeg,真实拼接效果需接模型/视频样本人工核验(见文档 O7)。
        """
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg or not original_url or not segment_url:
            return None
        orig = await asyncio.to_thread(download_to_local, original_url, suffix=".mp4")
        seg = await asyncio.to_thread(download_to_local, segment_url, suffix=".mp4")
        if not orig or not seg:
            for path in (orig, seg):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return None
        out = os.path.join(tempfile.gettempdir(), f"splice_{uuid4().hex}.mp4")
        try:
            result = await compose.run([
                ffmpeg, "-y", "-i", orig, "-i", seg,
                "-filter_complex",
                f"[0:v]trim=start=0:end={start_ms / 1000:.2f}[a];"
                f"[0:v]trim=start={end_ms / 1000:.2f}[b];"
                f"[a][1:v][b]concat=n=3:v=1[vout];"
                f"[0:a]atrim=start=0:end={start_ms / 1000:.2f}[a1];"
                f"[0:a]atrim=start={end_ms / 1000:.2f}[b1];"
                f"[a1][1:a][b1]concat=n=3:a=1[aout]",
                "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-c:a", "aac", out,
            ], timeout=300)
            if result.get("ok") and os.path.exists(out):
                return await asyncio.to_thread(
                    upload_local_file, out, f"reference/splice_{uuid4().hex}.mp4",
                )
            return None
        finally:
            for path in (orig, seg, out):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _is_ark(self) -> bool:
        """是否火山方舟原生网关(协议 proto=ark):视频走 /contents/generations/tasks,而非 OpenAI /videos"""
        return self.proto == "ark"

    def _body_variants(self, payload: Dict[str, Any]) -> List[str]:
        """非方舟网关的视频编辑请求体候选形态(上次成功的那种排最前,避免每单都白试)

        · native:方舟原生形态 —— content[] 内 video_url(reference_video)+ 顶层
          ratio=adaptive / duration=-1。只在 ark 协议网关上成立。
        · legacy:顶层 videos / images / seconds 字段 —— relay/openai 中转站(如 aitoken)
          只认这种写法。native 形态提交到这类网关会被静默/显式拒绝
          (aitoken 实测报 "prompt 不能为空"),故非 ark 网关直接只给 legacy,
          让正确形态一次命中,不再走"先错后改"的故障路径。
        非编辑请求(t2v/i2v/r2v)没有参考视频,不存在这个分叉。
        """
        if not payload.get("videos"):
            return ["legacy"]
        # 非方舟网关:只发 legacy。native 是方舟原生形态,relay 中转站不认,强行先试必然 400
        # 再回退 legacy(实测 task 23 一次任务连试两次 native,白打一次 400 又拖慢)。
        if not self._is_ark():
            return ["legacy"]
        order = ["native", "legacy"]
        preferred = _BODY_SHAPE_PREF.get(f"{self.capability}@{self.base_url}")
        if preferred in order:
            order.remove(preferred)
            order.insert(0, preferred)
        return order

    def _body_for(self, payload: Dict[str, Any], variant: str) -> Dict[str, Any]:
        """按形态返回实际提交的请求体(native 复用方舟转换,保证两条协议同一套语义)"""
        return self._ark_body(payload) if variant == "native" else payload

    def _ark_body(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """把内部统一 payload 转成方舟原生请求体:model + content + 顶层控制字段

        content 支持的 type(实测方舟 2.x 报错信息给出):text / image_url / audio_url / video_url / draft_task。

        控制字段下发方式(与模型版本强相关,踩过坑):
          · Seedance 2.0 早期:ratio/duration 只能写在 text 末尾的 --ratio/--duration 标记;
          · Seedance 2.5 等新版:ratio/duration/generate_audio/watermark 必须走**顶层字段**,
            写在 text 里会被整段忽略(表现是"时长/比例不对、且永远没声音")。
        这里统一走顶层字段(text 只留 prompt + --resolution),对新旧模型都兼容,
        并顺带修掉旧实现"视频编辑 generate_audio=True 被丢弃"的隐患(见下方 generate_audio)。

        ⚠️ 参考视频必须转成 **video_url**(此前只拼 image_url,videos 会被整个丢掉 ——
        表现是"视频编辑"请求退化成文生视频,且不报错)。
        """
        params = (payload.get("metadata") or {}).get("parameters") or {}
        parts = [str(payload.get("prompt") or "")]
        resolution = params.get("resolution") or payload.get("resolution")
        ratio = params.get("ratio") or payload.get("ratio")
        duration = params.get("duration") or payload.get("seconds")
        # 视频编辑(v2v):方舟按 prompt 判定为编辑任务后,输出比例与时长必须跟随被编辑视频,
        # 只接受 ratio=adaptive、duration=-1。传显式值会被 400
        # (InvalidParameter.TaskTypeConstraint)拒绝,再被上层静默降级为图片链路 ——
        # 表现就是"完全没有做元素替换"。带参考视频(videos)即编辑任务,故在此强制覆盖。
        if payload.get("videos"):
            ratio = "adaptive"
            duration = -1
        # 仅分辨率保留 text 内 --resolution 标记(新版接口对 resolution 仍兼容文本标记,
        # 且在 text 内便于与 prompt 同段提交,避免顶层字段冲突)。
        if resolution:
            parts.append(f"--resolution {str(resolution).lower()}")
        content: List[Dict[str, Any]] = [{"type": "text", "text": " ".join(parts)}]
        # 数字人口播(形象图 + 口播音频):此时形象图是"参考形象"而不是首帧 ——
        # 标成 first_frame 会让方舟按图生视频处理、丢掉音频驱动,成片与口播对不上。
        audio_url = str(payload.get("audio") or "").strip()
        single = payload.get("image")
        if single:
            # 单图:普通生成=首帧图;数字人=参考形象(role 缺省时方舟不再二次提示,显式声明更稳)
            content.append({
                "type": "image_url", "image_url": {"url": single},
                "role": "reference_image" if audio_url else "first_frame",
            })
        # role 是必填的:方舟按 role 区分素材用途,缺了会直接 400
        #   · 单图 first_frame(首帧,i2v)
        #   · 参考图 reference_image(多图参考/r2v/视频编辑的商品图/数字人形象)
        #   · 参考视频 reference_video(视频编辑)
        for url in (payload.get("images") or []):
            content.append({
                "type": "image_url", "image_url": {"url": url}, "role": "reference_image",
            })
        # 参考视频(视频编辑):缺此段会让"视频编辑"静默退化成文生视频
        for url in (payload.get("videos") or []):
            content.append({
                "type": "video_url", "video_url": {"url": url}, "role": "reference_video",
            })
        # 首帧续接(可选):把上一段尾帧作为生成起点首帧,让多段成片接缝处主体连续。
        # 方舟编辑协议原生不含首帧参数,不支持的网关会在提交阶段 400,
        # 由 edit_video 的降级逻辑去掉该字段重试(见 edit_video)。
        first_frame = str(payload.get("first_frame") or "").strip()
        if first_frame:
            content.append({
                "type": "image_url", "image_url": {"url": first_frame}, "role": "first_frame",
            })
        # 口播音频(数字人):缺此段则口型驱动无所依据,只能靠 prompt 自由发挥
        if audio_url:
            content.append({"type": "audio_url", "audio_url": {"url": audio_url}})
        # 顶层控制字段:seedance 2.5 等新模型要求 ratio/duration/generate_audio/watermark 走顶层
        body: Dict[str, Any] = {"model": payload.get("model"), "content": content}
        if ratio:
            body["ratio"] = ratio
        if duration is not None:
            body["duration"] = int(float(duration))
        # 生成音频:编辑链路显式传 True;其余场景默认开启(视频成片通常需要配音/配乐)。
        # 旧实现把 generate_audio 丢在 payload 里却没下发,导致视频编辑永远无声,这里补上。
        body["generate_audio"] = bool(payload.get("generate_audio", True))
        body["watermark"] = False
        return body

    async def _ark_request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """调用火山方舟原生接口(用 httpx,避免 OpenAI SDK 对非 OpenAI 端点的解析问题)

        非 2xx 时把响应体带上抛出:方舟 400 的具体原因(duration 不支持 / 图片下载失败等)
        只在响应体里,不带出来就只能看到 "400 Bad Request" 无法定位。
        429 限流 / 5xx 内部错误属瞬时故障,按 with_transient_retry 退避重试
        (seedance 视频生成实测会偶发 500,重试通常可恢复;提交与轮询共用此出口)。
        """
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        async def _do() -> Dict[str, Any]:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.request(method, f"{self.base_url}{path}", json=body, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"方舟返回 {resp.status_code}: {(resp.text or '')[:300]}")
            return resp.json()

        return await with_transient_retry(_do, label=f"方舟 {method} {path}")

    @staticmethod
    def _is_private_url(url: str) -> bool:
        """是否模型侧拉不到的内网/本机地址"""
        return bool(_PRIVATE_URL_RE.match((url or "").strip()))

    @staticmethod
    def _backend_static_hosts() -> set:
        """允许回源的私网 host 白名单:backend 自身域名 + 本机回环 + 容器服务名"""
        hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "backend"}
        backend_url = getattr(config, "BACKEND_PUBLIC_URL", "")
        if backend_url:
            from urllib.parse import urlparse
            host = urlparse(backend_url).hostname
            if host:
                hosts.add(host.lower())
        return hosts

    def _is_backend_static(self, url: str) -> bool:
        """仅允许 backend 自身静态地址回源,禁止抓取任意私网(SSRF 防护)"""
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        return host in self._backend_static_hosts()

    async def _accessible_url(self, url: str, kind: str = "image") -> str:
        """把内网素材转成模型可拉取的形式:启用 OSS 时转存公网 URL,否则转 base64 data URI。

        转换失败保留原地址 —— 网关会返回明确错误,配合 _ark_request 的响应体可直接定位。
        """
        url = str(url or "").strip()
        if not url or url.startswith("data:") or not self._is_private_url(url):
            return url
        # SSRF 收窄:仅允许回源 backend 自身静态域,禁止抓取任意私网(云元数据等)
        if not self._is_backend_static(url):
            logger.warning(f"[VideoGenTool] 拒绝回源非 backend 私网地址: {url}")
            return url
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").split(";")[0].strip()
            if not ctype:
                # 扩展名由此推导,视频素材必须落到 .mp4,否则上传到 OSS 后模型拉不到
                ctype = {"audio": "audio/mpeg", "video": "video/mp4"}.get(kind, "image/jpeg")
            data = resp.content
            if config.OSS_ENABLED:
                from app.utils.oss import upload_bytes
                public = upload_bytes(data, f"generate/material/{uuid4().hex}.{ctype.split('/')[-1]}")
                if public:
                    logger.info(f"[VideoGenTool] 内网素材转存 OSS: {url} -> {public}")
                    return public
            uri = f"data:{ctype};base64,{base64.b64encode(data).decode()}"
            logger.info(f"[VideoGenTool] 内网素材转 base64: {url} ({len(data)} bytes)")
            return uri
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[VideoGenTool] 素材下载失败(保留原地址交给网关报错): {url} {exc}")
            return url

    async def _prepare_media(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """提交前处理素材地址:内网地址(127.0.0.1 等)模型拉不到,统一先转成可访问形式"""
        if payload.get("image"):
            payload["image"] = await self._accessible_url(payload["image"])
        if payload.get("images"):
            payload["images"] = [await self._accessible_url(u) for u in payload["images"]]
        if payload.get("audio"):
            payload["audio"] = await self._accessible_url(payload["audio"], "audio")
        # 视频编辑的参考视频:内网地址同样要先转存,否则模型拉不到
        if payload.get("videos"):
            payload["videos"] = [await self._accessible_url(u, "video") for u in payload["videos"]]
        return payload

    async def _submit_and_poll(
        self, payload: Dict[str, Any], label: str, duration: int, resolution: Optional[str], ratio: Optional[str],
        route: str = "",
        checkpoint: Optional[dict] = None, on_stage=None,
        decision: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """提交视频任务并轮询直到完成(全链路异步)。支持断点续跑:
        - stage>=2 且已保存 external_task_id → 跳过提交,直接复用该任务 ID 继续轮询(避免重复扣费生成);
        - stage>=3 且已保存 raw_url → 跳过轮询,直接转存 OSS。

        route 为本次实际走的链路(t2v/i2v/r2v/edit),会随 external_task_id 一并写入 checkpoint:
        外部任务 ID 只对**提交它的那条链路**有效,续跑时链路一旦变化(例如素材含视频被提升为
        参考视频,从 r2v 改走视频编辑),复用旧 ID 只会去轮询另一个链路的外部任务 ——
        拿不到结果、白等一轮,还会连带把降级/重试全部拖进同一个死循环(实测踩过)。
        留空表示不记录链路(数字人等单一链路场景),此时沿用原有的"同链路直接复用"行为。
        """
        checkpoint = checkpoint or {}
        stage = int(checkpoint.get("stage", 0) or 0)
        # 链路一致性校验:旧 checkpoint 未记录链路时按"同链路"处理,保持原有"续跑不重复扣费"的契约
        recorded_route = checkpoint.get("external_route")
        if recorded_route and recorded_route != route:
            logger.warning(
                f"[VideoGenTool] 断点续跑链路已变化({recorded_route} → {route}),"
                f"旧外部任务状态已失效,重新提交(原 external_task_id="
                f"{checkpoint.get('external_task_id')})"
            )
            # 同时作废 raw_url:否则会提交新任务却跳过轮询,把**旧链路**的成片当成本次结果
            stage = 0
        # 先按模型上限压分辨率:实测方舟 Seedance 2.0 的 r2v/v2v 变体只认 720p,
        # 传 1080P 必然 400 —— 与其失败后再降档,不如提交前就压到位。
        capped = _cap_resolution(payload.get("model"), resolution)
        if capped != resolution:
            logger.info(
                f"[VideoGenTool] {label}分辨率按模型上限下调: {resolution} → {capped}"
                f"(model={payload.get('model')})"
            )
            resolution = capped
            payload = self._with_resolution(payload, capped)
        # 实际生效的分辨率:降档重试会改写它,用于回写用量(记真实的生成参数)
        used_resolution = resolution
        logger.info(f"[VideoGenTool] {label}请求参数: {payload}")

        # 阶段2:提交(或复用已提交任务 ID 续跑轮询)
        if stage >= 2 and checkpoint.get("external_task_id"):
            external_task_id = checkpoint["external_task_id"]
            logger.info(f"[VideoGenTool] 断点续跑:复用 external_task_id={external_task_id},跳过提交直接轮询")
        else:
            # 逐站记录真实错误:故障转移会依次尝试多个网关,最终抛出的是**最后一个**网关的错误
            # (常见是备选网关的鉴权/余额),会把第一站真正的原因(如分辨率不支持)整段盖掉 ——
            # 只看最终异常就会漏掉"其实换参数就能过"的问题。
            submit_errors: List[Exception] = []

            async def _submit(_gw: Dict[str, str]) -> Dict[str, Any]:
                """提交一次(当前网关):方舟原生 /contents/generations/tasks;OpenAI 兼容 /videos

                视频编辑额外带"请求体形态"兜底(见 _body_variants):顶层 videos 是内部约定,
                部分中转站会静默丢弃,把编辑退化成"按 prompt 重新生成"(成片画幅/内容都不像
                原片且不报错)。形态被网关拒(400/404/405/415/422)时换另一种再试 —— 此时任务
                尚未创建,不产生生成费;试出来的可用形态按网关记住,后续任务不再重复试错。
                """
                if self._is_ark():
                    try:
                        return await self._ark_request(
                            "POST", "/contents/generations/tasks", self._ark_body(payload),
                        )
                    except Exception as exc:  # noqa: BLE001
                        submit_errors.append(exc)
                        raise
                last: Optional[Exception] = None
                variants = self._body_variants(payload)
                for pos, variant in enumerate(variants):
                    body = self._body_for(payload, variant)
                    try:
                        if variant == "native":
                            # 上面的「请求参数」打的是内部 payload,而编辑任务真正发出去的是
                            # 形态转换后的 body —— 不单独打出来,线上就看不到参考视频到底有没有
                            # 以 video_url 下发(曾因此把"编辑退化成重新生成"漏了整整一轮排查)。
                            logger.info(f"[VideoGenTool] {label}按方舟原生形态提交: {body}")
                        resp = await self.client.post("/videos", cast_to=dict, body=body)
                        _BODY_SHAPE_PREF[f"{self.capability}@{self.base_url}"] = variant
                        # 故障转移可能先把请求打到备选网关,使上面的记录只挂在备选地址下;
                        # 修正素材后 _reset_gateway 会拨回首选网关(如 aitoken),若只按"当前地址"
                        # 记,拨回后就会再试一次 native(实测 task 23 一次任务连试两次 native,
                        # 白打一次 400 又拖慢)。故把可用形态同步记到该能力的首选网关地址下。
                        _primary_url = (gateway.resolve(self.capability) or {}).get("url")
                        if _primary_url:
                            _BODY_SHAPE_PREF[f"{self.capability}@{_primary_url.rstrip('/')}"] = variant
                        if variant != variants[0]:
                            logger.info(
                                f"[VideoGenTool] 网关 {self.base_url} 的视频编辑改用「{variant}」请求体形态"
                            )
                        return resp
                    except Exception as exc:  # noqa: BLE001
                        last = exc
                        if pos + 1 < len(variants) and _is_body_shape_error(exc):
                            logger.warning(
                                f"[VideoGenTool] 网关 {self.base_url} 不接受「{variant}」请求体形态,"
                                f"换形态重试: {exc}"
                            )
                            continue
                        submit_errors.append(exc)
                        raise
                raise last if last is not None else RuntimeError(f"{label}提交失败:无可用请求体形态")

            # 提交阶段允许故障转移:失败即切到备选网关重试,成功后不再切换,
            # 后续轮询自然复用"提交成功的那个网关"。
            logger.info(f"[VideoGenTool] {label}提交网关: {self.base_url}(协议 {self.proto})")
            try:
                # 提交前先把内网素材转成模型可达形式(断点续跑不重复转换)
                payload = await self._prepare_media(payload)
            except Exception as exc:  # noqa: BLE001
                return self._fail(f"{label}素材预处理异常: {exc}", "request_error")

            # 分辨率按模型自动降档:同一份分辨率配置要适配多种模型,而它们接受的档位不同 ——
            # 实测方舟 doubao-seedance-2-0-fast 的 r2v(参考视频/参考图)变体**只认 720p**,
            # 传 1080p 直接 400;而 1.0 pro 反而支持 1080P。提前预知不现实(各中转站差异更大),
            # 所以只在「明确是分辨率问题」时降档重试,其他错误立即放弃(不做无谓重试)。
            last_error: Optional[Exception] = None
            resp: Dict[str, Any] = {}
            for attempt in [resolution, *self._resolution_fallbacks(resolution)]:
                if attempt != resolution:
                    logger.warning(
                        f"[VideoGenTool] {label}分辨率 {resolution} 不被模型接受,降档为 {attempt} 重试"
                    )
                    assert attempt is not None  # 候选只在 resolution 非空时产生
                    payload = self._with_resolution(payload, attempt)
                    # 上一轮 failover 已把网关切到备选,不拨回首选的话这次会白打在备选上
                    self._reset_gateway()
                used_resolution = attempt
                try:
                    resp = await self._with_failover(
                        self.capability, _submit, label=f"{label}提交", decision=decision,
                    )
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    # 只要**任一**网关报过分辨率问题就降档:最终异常可能来自备选网关,不代表主因
                    if not any(_is_resolution_error(e) for e in submit_errors):
                        break
            if last_error is not None:
                # 报第一站的错误:那才是这次提交真正的问题(备选网关的 401 只会把人带偏)
                detail = submit_errors[0] if submit_errors else last_error
                return self._fail(f"{label}提交异常(候选网关已全部尝试): {detail}", "request_error")
            external_task_id = (resp or {}).get("id") or (resp or {}).get("task_id")
            if not external_task_id:
                return self._fail(f"{label}失败:接口未返回任务ID({resp})", "invalid_request")
            logger.info(f"[VideoGenTool] {label}任务已提交: external_task_id={external_task_id}, 网关={self.base_url}")
            if on_stage:
                await on_stage(2, {
                    "external_task_id": external_task_id,
                    # 记录提交链路:续跑时据此判断旧外部任务 ID 是否还能复用
                    "external_route": route,
                    "duration": duration, "resolution": used_resolution, "ratio": ratio,
                })

        # 阶段3:轮询(或复用已取回的 raw_url 跳过轮询)
        raw_url = checkpoint.get("raw_url") if stage >= 3 else None
        if raw_url:
            logger.info(f"[VideoGenTool] 断点续跑:复用 raw_url,跳过轮询")
        else:
            raw_url, terminal_failed = await self._poll(
                external_task_id, label, duration, resolution, ratio
            )
            if not raw_url:
                if terminal_failed:
                    # 外部任务已被上游明确判失败:清掉断点里的任务 ID。
                    # 不清的话,本次降级、ARQ 重试以及用户「断点续跑」都会反复复用这个死 ID ——
                    # 每轮必然失败、又永远不会重新提交,把整条链路拖成死循环(实测踩过)。
                    # 内存副本与 backend 都要清:降级/去身份化重试读的是**内存里这份** checkpoint,
                    # 只回写 backend 拦不住同一次 job 内的复用。
                    # 轮询超时**不在此列**:外部任务可能仍在跑、钱已经花了,ID 必须留给续跑取结果。
                    logger.warning(
                        f"[VideoGenTool] {label}外部任务已判失败,清除断点任务ID后交由上层重试: "
                        f"external_task_id={external_task_id}"
                    )
                    checkpoint["stage"] = 2
                    checkpoint["external_task_id"] = None
                    checkpoint["external_route"] = None
                    checkpoint.pop("raw_url", None)
                    if on_stage:
                        await on_stage(2, {"external_task_id": None, "external_route": None})
                return self._fail(f"{label}生成未完成(轮询结束仍无结果)", "timeout")
            if on_stage:
                await on_stage(3, {"raw_url": raw_url})

        # 终态:转存 OSS(未启用时原样返回),避免模型临时直链过期。
        # 必须加整体超时:转存跑在 to_thread 里,COS SDK 上传一旦挂起就会让任务永久停在
        # processing(实测 5m37s),而此时没有任何心跳,外部完全无法感知任务还活着。
        #
        # 就地重试**而不是直接判失败**:成片已经生成、费用已经发生,而转存只是"搬到自己桶里"
        # 这一步,偶发挂起重试一次通常几秒就成。此前只在 ARQ 层重试,但实测带替换意图的任务
        # 失败即终态(不做降级、直接退款)—— 缩短超时后就成了"多等几分钟能拿片"变成"退款"。
        persisted: List[str] = []
        persist_started = time.monotonic()   # 整轮转存起始时刻,用于统计累计耗时
        for attempt in range(1, PERSIST_ATTEMPTS + 1):
            attempt_started = time.monotonic()
            try:
                persisted = await asyncio.wait_for(
                    persist_url_list([raw_url], self.task_prefix), timeout=PERSIST_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"[VideoGenTool] {label}成片转存 OSS 第 {attempt}/{PERSIST_ATTEMPTS} 次超时"
                    f"(等待满 {PERSIST_TIMEOUT}s) task={self.task_prefix}"
                )
                persisted = []
            # 转存耗时监控:无论成败都记录本次实测耗时(含下载模型直链 + 上传自有 COS 两段),
            # 慢于阈值时额外告警并给出剩余余量,便于判断 PERSIST_TIMEOUT 是否够用。
            attempt_cost = time.monotonic() - attempt_started
            if persisted and persisted[0] != raw_url:
                if attempt_cost >= PERSIST_SLOW_THRESHOLD:
                    logger.warning(
                        f"[VideoGenTool] {label}成片转存偏慢:转存耗时 {attempt_cost:.1f}s"
                        f"(阈值 {PERSIST_SLOW_THRESHOLD}s,距超时仅剩 "
                        f"{max(PERSIST_TIMEOUT - attempt_cost, 0):.1f}s)"
                        f" 第 {attempt}/{PERSIST_ATTEMPTS} 次 task={self.task_prefix}"
                    )
                else:
                    logger.info(
                        f"[VideoGenTool] {label}成片转存完成:转存耗时 {attempt_cost:.1f}s"
                        f" 第 {attempt}/{PERSIST_ATTEMPTS} 次 task={self.task_prefix}"
                    )
                break     # 转存成功(拿到自有 COS 地址)
            if attempt < PERSIST_ATTEMPTS:
                logger.warning(
                    f"[VideoGenTool] {label}成片转存未成功(本次耗时 {attempt_cost:.1f}s),"
                    f"{PERSIST_RETRY_GAP}s 后重试({attempt}/{PERSIST_ATTEMPTS})"
                    f" task={self.task_prefix}"
                )
                await asyncio.sleep(PERSIST_RETRY_GAP)
        url = persisted[0] if persisted else raw_url
        # OSS 已启用却原样拿回模型临时直链,说明转存失败被 _persist_single 兜底保留了原链。
        # 此时绝不能当成功回写:临时直链通常 24 小时即过期,用户稍后点开就是死链
        # (任务 21 实测:跨境下载中断后落地了过期 TOS 链,只能人工补救)。
        # 返回失败交 service 层重试 —— checkpoint 已停在 stage=3(raw_url 已落库),
        # 重试时复用该直链只重新转存,不会重新提交外部任务、不重复扣生成费。
        if config.OSS_ENABLED and url == raw_url:
            logger.error(
                f"[VideoGenTool] {label}成片转存最终失败:共 {PERSIST_ATTEMPTS} 次,"
                f"转存耗时累计 {time.monotonic() - persist_started:.1f}s(超时 {PERSIST_TIMEOUT}s/次),"
                f"交 service 层重试 task={self.task_prefix}"
            )
            return self._fail(
                f"{label}成片转存 OSS 失败,稍后自动重试重新转存(不重新生成): "
                f"external_task_id={external_task_id}",
                "persist_error",
            )
        # 成片兜底校验:抽帧看画面是不是彩条/测试卡/纯色/黑屏这类「有声无画」的废片。
        # 上游那道卡只查**参考帧**(降级链路),参考视频本身是彩条而编辑直接成功时根本不走降级,
        # 只能靠这里兜住(实测 task 59 的成片就是这么交付出去的)。
        # 检出即判失败:交付废片还计全额费用,比失败退款更糟。检测失败一律放行(不误伤)。
        if self._output_degenerate_check_enabled():
            degenerate = await frame_quality.detect_degenerate_video(url)
            if degenerate:
                logger.error(
                    f"[VideoGenTool] {label}成片画面无实际内容(彩条/测试图/纯色),按失败处理 "
                    f"task={self.task_prefix}: {degenerate}"
                )
                # 计数:成片侧检出 = 有链路绕过了参考帧校验,是比参考侧更严重的信号
                metrics.incr("frame.degenerate_blocked", detail=f"成片:{degenerate}"[:160])
                return self._fail(
                    f"{label}成片画面无实际内容({degenerate}),未交付。"
                    f"已终止本次生成并原路返还额度/退款,请更换有真实画面的素材后重试",
                    "invalid_output",
                )
        usage = self._usage(payload.get("model"), duration, used_resolution, ratio)
        logger.info(f"[VideoGenTool] {label}完成: external_task_id={external_task_id}, url={url}")
        return ToolResult(content=url, metadata={"success": True, **usage})

    def _min_reference_pixels(self) -> int:
        """参考视频的最低像素要求(0 = 不校验)。

        方舟 r2v/v2v 明确要求参考视频像素数 >= 407696(实测 task 58/59 的 400 原文),
        门槛随模型而异、且各网关不同,故做成可配:后台 gen.video_min_reference_pixels
        填「模型名子串:像素数」分号分隔,未配时回退 _DEFAULT_MIN_REFERENCE_PIXELS。
        填 0 或留空即关闭本校验,行为与改造前一致(不因猜错门槛而误杀正常任务)。
        """
        raw = (getattr(config, "VIDEO_MIN_REFERENCE_PIXELS", "") or "").strip()
        if not raw:
            return _DEFAULT_MIN_REFERENCE_PIXELS
        for part in raw.split(";"):
            part = part.strip()
            if not part or ":" not in part:
                continue
            name, _, value = part.partition(":")
            name, value = name.strip().lower(), value.strip()
            if not name or not value.isdigit():
                continue
            # 模型名未命中就继续看下一条;全部未命中则不校验(拿不到确知门槛就不猜)
            if name in (config.VIDEO_MODEL_EDIT or "").lower():
                return int(value)
        return 0

    @staticmethod
    def _output_degenerate_check_enabled() -> bool:
        """成片兜底校验开关(gen.video_output_degenerate_check,默认启用)。

        与开关类配置一致用字符串承载("1"/"0"),避免后台下发字符串后 bool("0") 仍为真、
        导致"想关却关不掉"(CACHE_ENABLED 的既有写法)。
        """
        raw = str(getattr(config, "VIDEO_OUTPUT_DEGENERATE_CHECK", "1") or "1").strip()
        return raw not in ("0", "false", "False", "")

    @staticmethod
    def _resolution_fallbacks(resolution: Optional[str]) -> List[str]:
        """当前分辨率之后可尝试的降档候选(大小写不同视为同一档位,不算降档)"""
        if not resolution:
            return []
        current = resolution.strip().lower()
        if current in _RESOLUTION_LADDER:
            return list(_RESOLUTION_LADDER[_RESOLUTION_LADDER.index(current) + 1:])
        # 认不出的写法(部分网关用自定义档位名):直接退回最通用的 720p
        return ["720p"]

    @staticmethod
    def _with_resolution(payload: Dict[str, Any], resolution: str) -> Dict[str, Any]:
        """替换 payload 中的分辨率(方舟会把它拼成 text 里的 --resolution 参数)"""
        cloned = copy.deepcopy(payload)
        params = cloned.setdefault("metadata", {}).setdefault("parameters", {})
        params["resolution"] = resolution
        return cloned

    def _reset_gateway(self) -> None:
        """把网关拨回该能力的首选(降档重试前调用:上一轮故障转移可能已切到备选)"""
        gw = gateway.resolve(self.capability)
        url = (gw.get("url") or "").rstrip("/")
        if url and url != self.base_url.rstrip("/"):
            self._switch_gateway(gw)

    async def _poll(
        self, external_task_id: str, label: str, duration: int, resolution: Optional[str], ratio: Optional[str],
    ) -> Tuple[Optional[str], bool]:
        """轮询外部视频任务直到完成,返回 (原始视频直链, 是否已被上游明确判失败)。

        第二个返回值区分两种"没拿到结果",它们对断点的处理**完全相反**:
          - True  外部任务已被上游判为 failed/error/canceled —— 死 ID,再轮询多少次都不会变成功,
                  必须从断点里清掉;否则本次降级与后续重试/续跑会反复"复用"它,
                  既拿不到结果、也永远不会重新提交(实测踩过:同链路死循环);
          - False 只是轮询超时 —— 外部任务可能仍在跑,生成费已经花了,ID **必须保留**,
                  续跑才能接着把结果取回来;清掉等于白付一次生成费。
        """
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < self.poll_timeout:
            await asyncio.sleep(self.poll_interval)
            try:
                if self._is_ark():
                    # 方舟:GET /contents/generations/tasks/{id},结果取 content.video_url
                    task = await self._ark_request("GET", f"/contents/generations/tasks/{external_task_id}")
                    status = (task or {}).get("status")
                    if status in ("succeeded", "success", "completed"):
                        url = ((task or {}).get("content") or {}).get("video_url")
                        if url:
                            return url, False
                        # 终态却没给直链:状态不会再变,按终态失败处理(继续轮询只会死等到超时)
                        logger.error(
                            f"[VideoGenTool] {label}任务已完成但未返回视频直链: external_task_id={external_task_id}"
                        )
                        return None, True
                    if status in ("failed", "error", "canceled"):
                        logger.error(f"[VideoGenTool] {label}生成失败: {(task or {}).get('error') or status}")
                        return None, True
                else:
                    task = await self.client.videos.retrieve(external_task_id)
                    status = getattr(task, "status", None)
                    metadata = getattr(task, "metadata", None)
                    url = metadata.get("url") if isinstance(metadata, dict) else None
                    if status in ("completed", "succeeded", "success"):
                        if url:
                            return url, False
                        logger.error(
                            f"[VideoGenTool] {label}任务已完成但未返回视频直链: external_task_id={external_task_id}"
                        )
                        return None, True
                    if status in ("failed", "error", "canceled"):
                        reason = getattr(task, "error", None) or status
                        logger.error(f"[VideoGenTool] {label}生成失败: {reason}")
                        return None, True
            except Exception as exc:
                logger.warning(f"[VideoGenTool] {label}轮询异常(继续重试): external_task_id={external_task_id}, {exc}")
                continue
        logger.error(f"[VideoGenTool] {label}生成超时: external_task_id={external_task_id}")
        return None, False

    @staticmethod
    def _clamp_duration(value: Any) -> int:
        """时长兜底:转 int 并就近吸附到模型支持的档位(默认 5/10 秒)

        方舟 seedance 只支持 5/10,模板时长配成 15 会直接 400;
        这里统一吸附(取最接近的档位),避免出现"建单成功但必然失败"的任务。
        档位可由系统配置 gen.video_durations 放开(如 Seedance 2.x 配 "4-15")。

        用「绝对差最小」而非「首末档位取中值」:后者只在两档时碰巧正确,
        档位扩到 (5,10,15) 会把 12 秒算成 5 秒。算法与 backend gen_rules 同构。
        """
        gears = parse_duration_gears(getattr(config, "VIDEO_DURATIONS", "")) or SUPPORTED_DURATIONS
        try:
            d = int(value)
        except (TypeError, ValueError):
            return gears[0]
        return min(gears, key=lambda x: abs(x - d))

    @staticmethod
    def _usage(model: Optional[str], duration: int, resolution: Optional[str], ratio: Optional[str]) -> Dict[str, Any]:
        """组装用量信息(供 backend 计费/展示):模型名取本次实际使用的模型(t2v/i2v/r2v 各不相同)"""
        usage = Usage(model=model or config.VIDEO_MODEL, seconds=duration).to_dict()
        usage.update({"resolution": resolution, "ratio": ratio})
        return usage

    def _fail(self, msg: str, error_type: str = "unknown") -> ToolResult:
        """统一的失败返回,交由上层 service 转 failed 回调"""
        logger.error(f"[VideoGenTool] {msg}")
        return ToolResult(content=msg, metadata={"success": False, "error_type": error_type, "error": msg})

    # --- 决策日志 / 成本快照(P2-9) ---
    # 每次生成产生一条决策记录,描述"这次生成走了哪条链路、用什么模型/分辨率/时长、
    # 估了多少成本、最终落在哪个网关"。只记成功提交(网关名由 _with_failover 回填),
    # 失败的调用不计入。落库在 generate() 收尾时一次性写入 metadata。
    # 注意:不能用类级可变列表(会被所有实例共享),这里用 None 作默认,首次记录时惰性初始化。
    _decision_log: Optional[List[Dict[str, Any]]] = None
    # 复刻形态(口播/短剧/街采…):类级默认空串 —— 直接调 edit_video 的路径(测试/局部重跑)
    # 没经过 generate() 赋值时也要能安全读取。
    _replicate_format: str = ""

    def _new_decision(self, route: str, model: Optional[str], duration: int,
                      resolution: Optional[str], ratio: Optional[str]) -> Dict[str, Any]:
        """预建一条决策记录(网关字段先留空,_with_failover 提交成功后再回填)"""
        return {
            "route": route,
            "model": model or "",
            "resolution": resolution or "",
            "ratio": ratio or "",
            "duration": int(duration),
            "estimated_seconds": int(duration),
            "gateway_name": None,
            "gateway_url": None,
        }

    def _record_decision(self, decision: Optional[Dict[str, Any]]) -> None:
        """提交成功(gateway_name 被回填)才记入决策日志;失败/未提交的忽略"""
        if not isinstance(decision, dict):
            return
        if not decision.get("gateway_name"):
            return
        if self._decision_log is None:
            self._decision_log = []
        self._decision_log.append(decision)

    def _attach_decision_log(self, result: ToolResult) -> None:
        """把本次生成的决策日志与成本快照写入结果 metadata(P2-9)

        cost_snapshot 是成本治理的数据基础:汇总本任务所有生成动作的估算时长与按模型分类,
        事后可回溯"这个任务花了多少生成时长、花在哪些模型上"。
        """
        if not isinstance(result.metadata, dict):
            return
        if not self._decision_log:
            return
        total_seconds = sum(int(d.get("estimated_seconds", 0) or 0) for d in self._decision_log)
        by_model: Dict[str, int] = {}
        for d in self._decision_log:
            m = d.get("model") or "unknown"
            by_model[m] = by_model.get(m, 0) + int(d.get("estimated_seconds", 0) or 0)
        result.metadata["decision_log"] = [dict(d) for d in self._decision_log]
        result.metadata["cost_snapshot"] = {
            "total_seconds": total_seconds,
            "actions": len(self._decision_log),
            "by_model": by_model,
        }
