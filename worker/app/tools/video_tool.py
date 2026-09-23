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
import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

from app.schemas.base import ToolResult, Usage
from app.tools.base import BaseGenTool
from app.tools.prompt_template import build_prompt_optimize_system
from app.tools.script_anchor import (
    estimate_timing,
    render_anchor_hint,
    resolve_tracks,
)
from app.settings import config
from app.core import compose
from app.core import gateway
from app.core import media_prep
from app.core import multiseg
from app.core.asset_cache import ASSET_OPTIMIZED_PROMPT, build_cache_key
from app.core import asset_cache
from app.core.plugin import logger
from app.utils.oss import download_to_local, persist_url_list, upload_local_file

# 视频模型支持的时长档位(秒):方舟 seedance 只认 5/10,传 15 会直接 400(InvalidParameter)
# 与 backend app/services/gen_rules.py 的 SUPPORTED_DURATIONS 保持一致(有契约测试兜底)
# 换到支持连续时长的模型(Seedance 2.x 支持 4~15s)后,由系统配置 gen.video_durations 放开。
SUPPORTED_DURATIONS = (5, 10)

# 分辨率档位(由高到低):模型不接受当前档位时按此顺序降档重试
_RESOLUTION_LADDER = ("1080p", "720p", "480p")


def _is_resolution_error(exc: Exception) -> bool:
    """异常是否为「该分辨率不被模型支持」

    方舟的报错形如:
      The parameter `contents[0].text.resolution` specified in the request is not valid:
      the specified resolution is not supported for model doubao-seedance-2-0-fast-r2v
    这类错误换参数就能过,值得降档重试;其他错误(余额/鉴权/素材)重试也没意义。
    """
    return "resolution" in str(exc).lower()


# 已知的模型分辨率上限(键为模型名子串):方舟 Seedance 2.0 的 r2v/v2v 变体**只支持 720p**,
# 传 1080p/1080P 会被 400 拒绝。提前压档,既省掉一次注定失败的提交,也避免白跑一轮网关故障转移。
_MODEL_RESOLUTION_CAP = {
    "seedance-2": "720p",
}

# prompt 改写(chat)单次请求超时(秒)。实测方舟上的 GLM 端点偶发抖动:
# 30s 会直接 timeout 并静默回退原始 prompt(丢掉改写收益),放宽到 90s。
# 注意:openai SDK 默认还会重试 2 次,所以最坏耗时 ≈ 90s × 3。
CHAT_REWRITE_TIMEOUT = 90


def _cap_resolution(model: Optional[str], resolution: Optional[str]) -> Optional[str]:
    """把分辨率压到该模型实际支持的上限内(不改变认不出的档位,交给降档逻辑兜底)"""
    if not model or not resolution:
        return resolution
    current = resolution.strip().lower()
    if current not in _RESOLUTION_LADDER:
        return resolution
    name = model.lower()
    for key, cap in _MODEL_RESOLUTION_CAP.items():
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


# 替换意图(与 backend prompt_builder.VALID_INTENTS 一致)→ 中文名。
# 失败原因里必须用用户看得懂的说法,不能只回一串英文错误码。
_INTENT_LABELS = {
    "product": "商品",
    "person": "人物",
    "scene": "场景",
}


def _intent_text(intent: List[str]) -> str:
    """替换意图 → 「商品」/「商品、人物」这类中文短语;识别不出时回退「元素」"""
    labels = [_INTENT_LABELS.get(str(i).strip()) for i in intent or []]
    labels = [l for l in labels if l]
    return "、".join(labels) or "元素"


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

        logger.info(
            f"[VideoGenTool] 生成模式选择 gen_mode={gen_mode} materials={len(materials)} duration={duration} "
            f"ratio={ratio} resolution={resolution} hint={material_hint} prompt={prompt[:60]}"
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
            system_prompt = build_prompt_optimize_system(
                ratio=None if len(materials) == 1 else ratio, resolution=resolution,
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
            edit_first = not ref_len or ref_len <= media_prep.VIDEO_EDIT_MAX_REFERENCE_SECONDS
        # 时长超出模型单段上限(Seedance 2.x ≈15s)→ 分段生成再拼接。
        # 独立路径:只在「有参考视频 + 超上限」时触发,原有单段链路行为完全不变。
        if reference_video and not edit_first and requested_duration > multiseg.MAX_SEGMENT_SECONDS:
            result = await self._generate_multi_segment(
                prompt, reference_video, materials, requested_duration, ratio, resolution,
                script_text=self._script_text(params, script_anchors),
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
            result = await self.edit_video(
                prompt, reference_video=reference_video, duration=duration, ratio=ratio,
                resolution=resolution, images=materials or None, generate_audio=True,
                checkpoint=checkpoint, on_stage=on_stage,
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
                result = await self._generate_by_materials(
                    prompt, materials, duration, ratio, resolution, checkpoint, on_stage,
                )
                # 降级不静默:把降级原因并入 metadata 随 usage 回写 backend 落库。
                # 否则编辑失败(如参数不被模型接受)会退化成"看似成功、其实没做元素替换"的成片,
                # 用户与排查者都无从察觉 —— 正是踩过的坑。
                if (result.metadata or {}).get("success", True):
                    result.metadata["degraded"] = True
                    result.metadata["degrade_from"] = "video_edit"
                    result.metadata["degrade_reason"] = edit_error[:255]
            else:
                # 编辑成功:成片时长跟随参考视频,字幕时间轴与烧录都要按它来。
                # 统一取整一次,保证 metadata.seconds 与脚本时间轴用的是同一个值。
                script_duration = int(requested_duration)
                self._set_output_seconds(result, script_duration)
                await self._check_output_against_reference(result, ratio, script_duration)
        else:
            # 有原片也选了替换意图,却没配编辑模型 → 只能走图片链路,
            # 那等于"用上传图重画整片",原片完全用不上。明确失败并说清怎么修,
            # 而不是交出一段"看似成功、其实没替换"的成片。
            if reference_video and replace_intent and not config.VIDEO_MODEL_EDIT:
                return self._fail(
                    f"替换{_intent_text(replace_intent)}失败:系统未配置视频编辑模型"
                    "(gen.video_model_edit),无法在参考视频上做替换,请配置后重试",
                    "config_error",
                )
            result = await self._generate_by_materials(
                prompt, materials, duration, ratio, resolution, checkpoint, on_stage,
            )
            # 未配编辑模型时,参考视频**根本没进生成**(纯复刻场景不阻断:用户拿一段
            # 成片好过整单失败)。但这是"静默丢弃原片",必须打标记透出到前端 ——
            # 否则用户以为成片复刻了自己的原片,实际只是用上传图重画。
            if reference_video and not config.VIDEO_MODEL_EDIT and (result.metadata or {}).get("success", True):
                result.metadata["degraded"] = True
                result.metadata["degrade_from"] = "video_edit"
                result.metadata["degrade_reason"] = (
                    "未配置视频编辑模型(gen.video_model_edit),参考视频未参与生成"
                )
        self._attach_script_meta(result, script_anchors, script_duration)
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
    ) -> None:
        """成片自检:视频编辑的成片必须"像"参考视频(画幅/时长),不像就打标

        为什么需要这道自检:换产品那次的成片是 960×960 / 10s,原片是 1440×2560 / 23.5s,
        差得极其明显却没有任何环节发现,最后靠人工 ffprobe 才定性。有了它,
        "产出错片"会在发生的那一刻被打标,而不是等用户投诉后再抽帧比对。

        只标记、**不阻断**:成片已经付费,残缺的成片也比没有强。
        探测失败(网络/格式)一律跳过 —— 自检不能反过来把任务搞失败。
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
        expected_aspect = self._aspect_of_ratio(ratio)
        if size and expected_aspect:
            actual_aspect = size[0] / float(size[1]) if size[1] else 0
            if actual_aspect and abs(actual_aspect - expected_aspect) / expected_aspect > 0.05:
                problems.append(f"画幅 {size[0]}x{size[1]} ≠ 目标 {ratio}")
        if seconds and abs(seconds - expected_seconds) / float(expected_seconds) > 0.3:
            problems.append(f"时长 {seconds:.1f}s ≠ 参考视频 {expected_seconds}s")
        if not problems:
            return

        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        metadata["output_mismatch"] = {
            "expected": {"ratio": ratio, "seconds": expected_seconds},
            "actual": {"size": f"{size[0]}x{size[1]}" if size else "", "seconds": round(seconds or 0, 1)},
            "reason": "；".join(problems),
        }
        result.metadata = metadata
        logger.warning(
            f"[VideoGenTool] 成片与参考视频不一致 task={self.task_prefix}: {'；'.join(problems)}"
        )

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

    @staticmethod
    def _script_text(params: dict, script_anchors: dict) -> str:
        """取原始口播文案:分段生成时用来给每段分配各自的台词"""
        for key in ("script_text", "copywriting", "text"):
            value = params.get(key)
            if value:
                return str(value).strip()
        # 旧任务只有词锚点脚本,退回从分段文本拼
        return "".join(str(s.get("text") or "") for s in (script_anchors or {}).get("segments") or [])

    @staticmethod
    def _segment_prompt(prompt: str, script_parts: List[str], idx: int) -> str:
        """给某一段的 prompt 加上「本段台词」边界

        不加的话每段都会把整篇文案念一遍,成片里同一句话重复两次。
        """
        part = script_parts[idx] if idx < len(script_parts) else ""
        if not part:
            return prompt
        return f"{prompt}\n[本段台词] {part}\n请只表现本段台词的内容,不要念其他段落的台词。"

    async def _generate_multi_segment(
        self, prompt: str, reference_video: str, materials: List[str], duration: int,
        ratio: str, resolution: str, script_text: str = "",
    ) -> ToolResult:
        """超出模型单段上限时:切分参考视频 → 逐段生成(尾帧续接)→ 拼接成整片

        三个为什么:
          · 为什么分段 —— Seedance 2.x 单次上限约 15s(实测 15.2s),30s 一次生成不出来;
          · 为什么续接 —— 两段独立生成会出现人物/光线/场景突变,直接拼像两条片子;
            改用上一段的**尾帧**作下一段首帧,视觉上能接上;
          · 为什么能流复制拼接 —— 各段同模型同参数,concat 直接 copy,秒级完成、不重编码。

        任何一步失败都**明确失败并带原因**,不做"凑一段交差"的降级:残缺的成片
        比失败更糟(用户会以为成功了)。
        """
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            return self._fail("多段生成需要 ffmpeg,当前环境不可用(容器需安装 ffmpeg)", "config_error")

        durations = multiseg.plan_segments(duration)
        script_parts = multiseg.split_script_for_segments(script_text, len(durations))
        logger.info(f"[VideoGenTool] 时长 {duration}s 超单段上限,拆为 {len(durations)} 段: {durations}")

        workdir = tempfile.mkdtemp(prefix="multiseg_")
        cleanup: List[str] = []
        try:
            # 参考视频落本地:切片与时长探测都需要本地文件
            local_ref = await asyncio.to_thread(download_to_local, reference_video, ".mp4")
            if not local_ref:
                return self._fail("多段生成失败:参考视频下载失败", "request_error")
            cleanup.append(local_ref)
            ref_duration = await media_prep.probe_duration(local_ref) or 0.0

            seg_files: List[str] = []
            next_frame = ""
            cursor = 0
            for idx, seg_duration in enumerate(durations):
                seg_prompt = self._segment_prompt(prompt, script_parts, idx)
                # 每段都尽量按**原片对应切片**走视频编辑。
                # 旧实现只有首段用原片、后续段拿尾帧续接 —— 那样后半段与原片毫无关系,
                # 换产品时商品/场景会一路漂移,拼出来像"前半段复刻 + 后半段自由发挥"。
                seg_ref = ""
                if ref_duration >= cursor + seg_duration:
                    seg_ref = await self._trim_reference(ffmpeg, local_ref, workdir, cursor, seg_duration)
                if seg_ref:
                    result = await self.edit_video(
                        seg_prompt, reference_video=seg_ref, duration=seg_duration,
                        ratio=ratio, resolution=resolution, images=materials or None, generate_audio=True,
                    )
                elif idx == 0:
                    # 首段必须走编辑(它是整片的起点);切片失败就退回完整参考视频
                    result = await self.edit_video(
                        seg_prompt, reference_video=reference_video, duration=seg_duration,
                        ratio=ratio, resolution=resolution, images=materials or None, generate_audio=True,
                    )
                else:
                    # 原片不够长,裁不出本段切片 → 退回尾帧续接,至少保住总时长不缺口
                    result = await self.image_to_video(
                        seg_prompt, duration=seg_duration, ratio=ratio, resolution=resolution,
                        input_image=next_frame,
                    )
                if not (result.metadata or {}).get("success", True):
                    meta = result.metadata or {}
                    return self._fail(
                        f"多段生成第 {idx + 1}/{len(durations)} 段失败: {meta.get('error') or result.content}",
                        meta.get("error_type") or "unknown",
                    )

                local_seg = await asyncio.to_thread(download_to_local, result.content, ".mp4")
                if not local_seg:
                    return self._fail(f"多段生成失败:第 {idx + 1} 段成片下载失败", "request_error")
                cleanup.append(local_seg)
                seg_files.append(local_seg)

                if idx < len(durations) - 1:
                    next_frame = await self._extract_and_upload_frame(ffmpeg, local_seg, workdir, idx, cleanup)
                    if not next_frame:
                        return self._fail("多段生成失败:抽取续接首帧失败(画面会断裂)", "compose_error")
                cursor += seg_duration

            final_url = await self._concat_segments(ffmpeg, seg_files, workdir)
            if not final_url:
                return self._fail("多段生成失败:分段拼接失败", "compose_error")
            logger.info(f"[VideoGenTool] 多段生成完成 {len(durations)} 段 {durations} → {final_url}")
            usage = self._usage(config.VIDEO_MODEL_EDIT, duration, resolution, ratio)
            return ToolResult(content=final_url, metadata={"success": True, **usage})
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

    async def _concat_segments(self, ffmpeg: str, seg_files: List[str], workdir: str) -> str:
        """拼接各段:同源同参数,流复制(秒级);清单用相对文件名 + cwd,规避 Windows 盘符冒号"""
        names: List[str] = []
        for i, path in enumerate(seg_files):
            name = f"seg_{i}.mp4"
            shutil.copy(path, os.path.join(workdir, name))
            names.append(name)
        with open(os.path.join(workdir, "list.txt"), "w", encoding="utf-8") as fh:
            fh.write(compose.build_concat_list(names))
        result = await compose.run(compose.build_concat_cmd("list.txt", "merged.mp4"), cwd=workdir, timeout=300)
        merged = os.path.join(workdir, "merged.mp4")
        if not result.get("ok") or not os.path.exists(merged):
            logger.error(f"[VideoGenTool] 分段拼接失败: {result.get('stderr')}")
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
        return await self._submit_and_poll(
            payload, "文生视频", duration, resolution, ratio, "t2v",
            checkpoint=checkpoint, on_stage=on_stage,
        )

    async def image_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "9:16",
        resolution: str = "1080P", input_image: Optional[str] = None,
        checkpoint: Optional[dict] = None, on_stage=None,
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
        return await self._submit_and_poll(
            payload, "图生视频", duration, resolution, ratio, "i2v",
            checkpoint=checkpoint, on_stage=on_stage,
        )

    async def reference_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "9:16",
        resolution: str = "1080P", reference_images: Optional[List[str]] = None,
        checkpoint: Optional[dict] = None, on_stage=None,
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
        return await self._submit_and_poll(
            payload, "参考生视频", duration, resolution, ratio, "r2v",
            checkpoint=checkpoint, on_stage=on_stage,
        )

    async def edit_video(
        self, prompt: str, reference_video: str, model: Optional[str] = None, duration: int = 5,
        ratio: str = "9:16", resolution: str = "1080P", images: Optional[List[str]] = None,
        generate_audio: bool = True, checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """视频编辑(Seedance 2.x):参考视频 + 商品图 + 新台词 → 同款新片

        与 r2v 的本质区别:
          r2v 传的是**参考视频的抽帧图片** —— 只保留构图/色调,丢掉原片的运镜、节奏与转场;
          视频编辑直接传**视频本身**,模型能学到镜头语言,且可生成与新台词同步的语音
          (lip-synced speech),字幕时间轴才对得上。

        字段名按 OpenAI 兼容网关常见约定(videos / generate_audio);不同中转站可能只认
        sound 或 duration,故失败时上层会降级回 r2v,不会因为字段不认就整个任务失败。
        """
        if not reference_video:
            return self._fail("视频编辑失败:未提供参考视频", "invalid_request")
        # 模型对参考视频时长有硬上限(方舟实测 15.2s),超限直接 400 且只报 content 下标,
        # 用户完全看不懂 —— 这里先自动裁到上限内(裁不动则原样放行,不阻断)
        from app.core import deidentify, media_prep
        # 编辑任务允许 4~30s(普通参考生视频仅 15s):按编辑上限裁剪,避免白丢后半段。
        # 同时把参考视频对齐到目标画幅:方舟编辑只认 ratio=adaptive,成片画幅跟随参考视频,
        # 不对齐的话请求里的 9:16 会被静默忽略(实测:请求 9:16、成片 16:9)。
        reference_video = await media_prep.fit_reference_video(
            reference_video,
            max_seconds=media_prep.VIDEO_EDIT_MAX_REFERENCE_SECONDS,
            ratio=ratio,
        )
        payload = {
            "model": model or config.VIDEO_MODEL_EDIT,
            "prompt": prompt,
            "videos": [reference_video],
            "seconds": str(duration),
            "generate_audio": bool(generate_audio),
            "metadata": {"parameters": {"resolution": resolution, "ratio": ratio, "duration": duration}},
        }
        if images:
            payload["images"] = images
        result = await self._submit_and_poll(
            payload, "视频编辑", duration, resolution, ratio, "edit",
            checkpoint=checkpoint, on_stage=on_stage,
        )
        # 提交被"输入视频含真人"拦下 → 本地去身份化后**重试一次**。
        # 方舟对含真人的输入视频直接拒绝(平台隐私策略,与提示词无关,实测连"仅提升画质"也被拦);
        # 素材已获授权、只是需要过检测时,这是唯一能继续跑下去的路径。
        # 两条硬约束:① 只重试一次(去身份化有画面代价,不能反复试);
        #            ② 必须把"已打码"回写出去 —— 打码区正是要被替换的主体,成片观感有代价,不能静默。
        if not (result.metadata or {}).get("success"):
            error = str((result.metadata or {}).get("error") or "")
            if deidentify.is_input_image_blocked(error):
                # 参考图含真人:本地处理帮不上忙(图片正是要被替换的主体,打码等于把"要换成的东西"糊掉),
                # 直接把可执行结论写进日志,供排查/前端提示使用。
                logger.warning(
                    "[VideoGenTool] 参考图被判定含真人,本地无法绕过"
                    f"(需换非真人形象图,或走方舟官方可信素材库+真人认证): {error[:200]}"
                )
            elif (deidentify.is_input_video_blocked(error)
                  and not (checkpoint or {}).get("external_task_id")):
                logger.warning(f"[VideoGenTool] 输入视频被判定含真人,本地去身份化后重试: {error[:200]}")
                new_url = await media_prep.deidentify_reference_video(reference_video)
                if new_url and new_url != reference_video:
                    payload["videos"] = [new_url]
                    retry = await self._submit_and_poll(
                        payload, "视频编辑", duration, resolution, ratio, "edit",
                        checkpoint=checkpoint, on_stage=on_stage,
                    )
                    if (retry.metadata or {}).get("success"):
                        retry.metadata["deidentified"] = True
                        retry.metadata["deidentify_note"] = "输入视频含真人,已本地去身份化后重新提交"
                    result = retry
                else:
                    logger.warning("[VideoGenTool] 去身份化未产出可用视频,保持原失败结果")
        return result

    def _is_ark(self) -> bool:
        """是否火山方舟原生网关(协议 proto=ark):视频走 /contents/generations/tasks,而非 OpenAI /videos"""
        return self.proto == "ark"

    def _ark_body(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """把内部统一 payload 转成方舟原生请求体:model + content

        content 支持的 type(实测方舟 2.x 报错信息给出):text / image_url / audio_url / video_url / draft_task。
        分辨率/比例/时长按方舟约定附加在 text 末尾(--resolution/--ratio/--duration)。

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
        if resolution:
            parts.append(f"--resolution {str(resolution).lower()}")
        if ratio:
            parts.append(f"--ratio {ratio}")
        if duration:
            parts.append(f"--duration {int(float(duration))}")
        content: List[Dict[str, Any]] = [{"type": "text", "text": " ".join(parts)}]
        single = payload.get("image")
        if single:
            # 单图 = 首帧图(role 缺省时方舟不再二次提示,显式声明更稳)
            content.append({"type": "image_url", "image_url": {"url": single}, "role": "first_frame"})
        # role 是必填的:方舟按 role 区分素材用途,缺了会直接 400
        #   · 单图 first_frame(首帧,i2v)
        #   · 参考图 reference_image(多图参考/r2v/视频编辑的商品图)
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
        return {"model": payload.get("model"), "content": content}

    async def _ark_request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """调用火山方舟原生接口(用 httpx,避免 OpenAI SDK 对非 OpenAI 端点的解析问题)

        非 2xx 时把响应体带上抛出:方舟 400 的具体原因(duration 不支持 / 图片下载失败等)
        只在响应体里,不带出来就只能看到 "400 Bad Request" 无法定位。
        """
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.request(method, f"{self.base_url}{path}", json=body, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f"方舟返回 {resp.status_code}: {(resp.text or '')[:300]}")
        return resp.json()

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
                """提交一次(当前网关):方舟原生 /contents/generations/tasks;OpenAI 兼容 /videos"""
                try:
                    if self._is_ark():
                        return await self._ark_request("POST", "/contents/generations/tasks", self._ark_body(payload))
                    return await self.client.post("/videos", cast_to=dict, body=payload)
                except Exception as exc:  # noqa: BLE001
                    submit_errors.append(exc)
                    raise

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
                    resp = await self._with_failover(self.capability, _submit, label=f"{label}提交")
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

        # 终态:转存 OSS(未启用时原样返回),避免模型临时直链过期
        persisted = await persist_url_list([raw_url], self.task_prefix)
        url = persisted[0] if persisted else raw_url
        usage = self._usage(payload.get("model"), duration, used_resolution, ratio)
        logger.info(f"[VideoGenTool] {label}完成: external_task_id={external_task_id}, url={url}")
        return ToolResult(content=url, metadata={"success": True, **usage})

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
