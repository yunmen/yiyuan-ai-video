# -*- coding: utf-8 -*-
'''
@文件    :prompt_builder.py
@说明    :生成参数「输入校验/归一化」(建单前同步执行,不调模型)。
         真正的「提示词组装」(build_gen_params / build_prompt_context)已迁至 worker/app/services,
         由 worker 在 process_video 里执行。backend 这里只保留必须在 enqueue 之前同步完成的
         输入校验:意图白名单、创意档位白名单、素材(图片/参考视频)拆分 —— 这些用于扣额度前的
         能力前置校验(例如有替换意图但无参考视频,要在此明确失败),无法委托 worker 异步执行。
@时间    :2026/09/21 16:30:00
@作者    :一源AI
@版本    :1.0
'''
import re
from typing import Any, Dict, List, Optional, Tuple

# 关键词→意图(备注/素材类型兜底用)
INTENT_KEYWORDS = {
    "person": ["人物", "人像", "脸", "头像", "模特", "换人", "换脸", "出镜"],
    "product": ["商品", "产品", "货", "物", "包装", "品牌", "换商品", "换货"],
    "scene": ["场景", "背景", "环境", "换场景", "外景", "室内", "户外", "换成场景"],
}
INTENT_ALIASES = {"人物": "person", "人物图": "person", "人像": "person", "商品": "product",
                  "产品": "product", "场景": "scene", "背景": "scene"}

# 合法意图白名单(单一来源,与 worker/app/skills/prompt_library.py 的 INTENT_LABELS 对齐)
VALID_INTENTS = ("person", "product", "scene")

# 公开配置接口(/gen-config)下发的选项:前端直接渲染,不再另存白名单副本(单一来源)
# 键名统一为 `key`(与 gen_rules.REPLICATE_FORMAT_OPTIONS、worker 侧选项表、以及
# 前端读取方式一致)。此前这里写的是 `value`,导致同一份 /gen-config 下发里
# 形态用 key、意图/档位/钩子/主角表现用 value 两套键名并存:
# 前端只能靠 `key ?? value` 兜底,Upload 页未走归一化的分支因此匹配不上(能渲染但点不选中)。
CREATIVE_LEVEL_OPTIONS = [
    {"key": "faithful", "label": "忠实复刻", "desc": "保持原片结构与动作"},
    {"key": "creative", "label": "适度改造", "desc": "在保留原片风格下做创意增强"},
    {"key": "viral", "label": "爆款改造", "desc": "按爆款逻辑重塑表演与节奏"},
]
VALID_CREATIVE_LEVELS = ("faithful", "creative", "viral")

HOOK_BOOST_OPTIONS = [
    {"key": "normal", "label": "正常", "desc": "正常开头即可"},
    {"key": "strong", "label": "强化开头", "desc": "用强钩子抓住前 3 秒"},
    {"key": "off", "label": "关闭", "desc": "不做特殊处理"},
]
VALID_HOOK_BOOSTS = ("normal", "strong", "off")

# 主角表现(单一来源):仅在替换意图含 person(换人物)时生效,决定新主角以什么方式表演。
# key 与 backend/skills/prompts/generation/replace/gen_lead_act_<key>.md 一一对应;
# 随 /gen-config 的 lead_acts 下发给前端渲染。
# ⚠️ 此前 /gen-config 已 import 本常量但这里从未定义 → 接口直接 ImportError 500,
# 前端拿不到任何高级选项(创意档位/钩子/主角表现全空)。补齐定义即修复该故障。
LEAD_ACT_OPTIONS = [
    {"key": "dance", "label": "跳舞律动", "desc": "让新主角跟着节奏跳起来,更有传播力"},
    {"key": "pitch", "label": "推广种草", "desc": "让新主角像主播一样介绍产品"},
]
VALID_LEAD_ACTS = ("dance", "pitch")

INTENT_OPTIONS = [
    {"key": "person", "label": "换人物", "desc": "替换出镜人物"},
    {"key": "product", "label": "换商品", "desc": "替换商品/产品"},
    {"key": "scene", "label": "换场景", "desc": "替换场景/背景"},
]


def normalize_intent(value) -> List[str]:
    """把任意来源(显式/视觉类型/备注)的意图统一成白名单列表;非法值过滤,空返回 []"""
    if isinstance(value, str):
        value = re.split(r"[,，、\s]+", value.strip())
    if not value:
        return []
    out, seen = [], set()
    for v in value:
        v = (INTENT_ALIASES.get(v) or str(v or "").strip().lower())
        if v in ("person", "product", "scene") and v not in seen:
            out.append(v)
            seen.add(v)
    return out


def intent_labels(intent: List[str]) -> List[str]:
    labels = {"person": "换人物", "product": "换商品", "scene": "换场景"}
    return [labels.get(i, i) for i in intent or []]


def normalize_creative_level(value: Any) -> str:
    """创意档位白名单;空/非法 → 空串(表示不指定,链路与改造前一致)"""
    v = str(value or "").strip().lower()
    return v if v in ("faithful", "creative", "viral") else ""


def normalize_hook_boost(value: Any) -> str:
    v = str(value or "").strip().lower()
    return v if v in ("normal", "strong", "off") else ""


def split_materials(materials: Optional[List[str]]) -> Tuple[List[str], str]:
    """把素材里的参考视频单独拎出来(视频编辑要的是视频本身,不是抽帧图)。

    返回 (images, video):images 是图片(商品图/人物图/场景图),video 是第一个视频(空串表示无)。
    """
    images, video = [], ""
    for url in materials or []:
        if str(url or "").strip().lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
            if not video:
                video = url
        else:
            images.append(url)
    return images, video


def resolve_intent(intent, material_type: str = "", remark: str = "") -> List[str]:
    """意图决策优先级:显式意图(A)> 视觉识别类型(B)> 备注关键词兜底(C)。

    B:material_type 来自视觉识别(person/product/scene),无则为空串。
    C:扫备注关键词(人物/商品/场景),命中即视为该维度替换意图。
    返回去重后的白名单意图列表。
    """
    explicit = normalize_intent(intent)
    if explicit:
        return explicit
    if material_type:
        t = material_type if material_type in ("person", "product", "scene") else ""
        if t:
            return [t]
    if remark:
        for intent_name, keywords in INTENT_KEYWORDS.items():
            if any(k in remark for k in keywords):
                return [intent_name]
    return []
