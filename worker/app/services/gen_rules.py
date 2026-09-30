# -*- coding: utf-8 -*-
'''
@文件    :gen_rules.py
@说明    :生成规则(纯函数)— 时长档位 / 画幅 / 清晰度的唯一定义处
@时间    :2026/09/21 10:00:00
@作者    :一源AI
@版本    :1.0
@说明    :此前 backend(_to_detail)与 worker(_clamp_duration)各写一份时长吸附规则,
          任一侧修改都会静默漂移;这里收敛成唯一实现,两侧共同引用/对齐。
          本文件从 backend 迁至 worker(backend 不再保留副本),由 worker runtime_config 同步 gen.video_durations。
'''
import re
from typing import Any, Dict, Optional, Tuple

# 视频模型支持的时长档位(秒)。
# 默认 (5, 10):部分模型(如方舟 seedance 1.x)只认固定档,传 15 会直接 400(InvalidParameter)。
# 换到支持连续时长的模型(Seedance 2.x 支持 4~15s)后,在系统配置 gen.video_durations 里
# 配成 "4-15" 即可放开;不配置或配置非法则**保持默认档位**,不会因为配错而提交必然失败的任务。
SUPPORTED_DURATIONS = (5, 10)

# 允许下发的画幅与清晰度(短视频场景默认竖版 1080P)
SUPPORTED_RATIOS = ("9:16", "16:9", "1:1", "4:3", "3:4")
SUPPORTED_RESOLUTIONS = ("720P", "1080P")
DEFAULT_RATIO = "9:16"
DEFAULT_RESOLUTION = "1080P"

# 复刻目标形态(单一来源):key 与 backend/skills/prompts/replicate/formats/*.md 一一对应
# (资产 name = replicate_format_<key>)。label/desc 由后端随公开配置下发、前端直接渲染 ——
# 前端不再另存一份白名单副本,新增形态只需在此补一条 + 加对应 .md,消除前后端两份漂移。
# 改编自 hypit 的 7 种复刻目标形态;不指定(空串)时复刻沿用原片结构,行为与改造前一致。
# 元组顺序即前端展示顺序(把最常用的「口播」排在最前)。
REPLICATE_FORMAT_OPTIONS: Tuple[Dict[str, str], ...] = (
    {"key": "talking_head", "label": "口播",
     "desc": "单人面对镜头讲解,适合知识分享与种草"},
    {"key": "short_drama", "label": "短剧",
     "desc": "情绪/冲突驱动的表演结构,适合剧情带货"},
    {"key": "presenter_led_explainer", "label": "主讲人讲解",
     "desc": "边演示边讲解,适合功能展示类产品"},
    {"key": "street_interview", "label": "街采",
     "desc": "随机路人问答,真实感强、适合口碑类内容"},
    {"key": "two_person_podcast", "label": "双人播客",
     "desc": "两人对谈,适合观点碰撞与访谈"},
    {"key": "ranking_listicle", "label": "榜单/盘点",
     "desc": "逐条揭示,适合 TopN 排行与合集"},
    {"key": "narration_led_demo", "label": "旁白演示",
     "desc": "画外音带演示,适合教程与操作演示"},
)

# 校验白名单由上述选项派生:保证「前端可选项」与「后端可校验项」永远同源,不会各改各的
SUPPORTED_REPLICATE_FORMATS: Tuple[str, ...] = tuple(o["key"] for o in REPLICATE_FORMAT_OPTIONS)

# 系统配置键(与 app/services/system_config.py 的 DEFAULT_CONFIGS 一致)
CFG_KEY_RATIO = "gen.video_ratio"
CFG_KEY_RESOLUTION = "gen.video_resolution"
CFG_KEY_DURATIONS = "gen.video_durations"

# 连续区间的上限保护:超过这个秒数多半是配置写错(如 4-150)
MAX_DURATION = 60


def parse_duration_gears(text: Any) -> Tuple[int, ...]:
    """解析时长档位配置,支持两种写法

      "5,10"  → (5, 10)       离散档位(只认固定档的模型)
      "4-15"  → (4,5,...,15)  连续区间(支持任意秒数的模型)

    空 / 非法 → 返回空元组,表示"不覆盖",沿用默认档位(配置写错不会让任务必然失败)。
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


def set_duration_gears(text: Any) -> Tuple[int, ...]:
    """按系统配置更新档位(未配置/非法则保持原值),返回当前生效档位"""
    global SUPPORTED_DURATIONS
    gears = parse_duration_gears(text)
    if gears:
        SUPPORTED_DURATIONS = gears
    return SUPPORTED_DURATIONS


def clamp_duration(value: Any) -> int:
    """时长兜底:转 int 并就近吸附到模型支持的档位(5/10 秒)。

    与 worker 的 VideoGenTool._clamp_duration 保持同一算法:
    取绝对差最小的档位(不是首末档取中值 —— 后者只在两档时碰巧正确,
    档位扩到 (5,10,15) 会把 12 秒算成 5 秒),避免出现"建单成功但必然失败"的任务。
    """
    try:
        d = int(value)
    except (TypeError, ValueError):
        return SUPPORTED_DURATIONS[0]
    return min(SUPPORTED_DURATIONS, key=lambda x: abs(x - d))


def normalize_ratio(value: Any, default: str = DEFAULT_RATIO) -> str:
    """画幅白名单校验,非法值(含空)回退默认竖版。"""
    v = str(value or "").strip()
    return v if v in SUPPORTED_RATIOS else default


def normalize_resolution(value: Any, default: str = DEFAULT_RESOLUTION) -> str:
    """清晰度白名单校验(大小写不敏感),非法值回退默认。"""
    v = str(value or "").strip()
    for item in SUPPORTED_RESOLUTIONS:
        if v.upper() == item.upper():
            return item
    return default


def normalize_replicate_format(value: Any) -> str:
    """复刻目标形态白名单校验(大小写不敏感);非法值/空值回退空串。

    返回空串表示「不指定形态」——此时不注入任何形态提示词,复刻沿用原片结构,
    与改造前行为完全一致(老客户端与老任务重跑都不受影响)。
    """
    v = str(value or "").strip().lower()
    return v if v in SUPPORTED_REPLICATE_FORMATS else ""


def resolve_gen_defaults(cfg: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """从系统配置映射中解析画幅/清晰度/时长档位(读不到时用内置默认值)。

    cfg 为 {key: value} 形式(来自 SystemConfigModel),避免 service 层依赖具体查询实现。
    durations 供展示用;真正生效的档位由调用方通过 set_duration_gears 写入。
    """
    cfg = cfg or {}
    return {
        "ratio": normalize_ratio(cfg.get(CFG_KEY_RATIO)),
        "resolution": normalize_resolution(cfg.get(CFG_KEY_RESOLUTION)),
        "durations": parse_duration_gears(cfg.get(CFG_KEY_DURATIONS)) or SUPPORTED_DURATIONS,
    }


# ==================== 复刻目标形态(成片的"内容结构") ====================
# 与前端 desktop/src/views/create/Replicate.vue 的 FORMATS 一一对应 —— 这里是唯一事实源,
# 前端新增形态必须同步到这里,否则会被白名单挡掉(与时长档位/画幅同一套治理方式)。
#
# 为什么需要它:用户选了「替换主角」,期望的是"主角换人 + 有创意的表演(跳舞/讲解/带货反应)",
# 但 v2v 编辑的默认指令是「除被替换元素外严格保持与原片一致」—— 动作也被要求不变,
# 于是只能产出"原片的动作 + 换了张脸",观感上就是"一点创意也没有"。
# 形态字段把「允许改什么」显式打开:场景/画幅/运镜仍跟随原片,而出镜者的表演结构按形态重塑。
#
#   act  —— 出镜者该怎么"演"(注入提示词,并放开 v2v 对动作的"严格保持一致")
#   不选 / 非法值 → 空串,链路与改造前完全一致(沿用原片结构),不影响存量任务。
REPLICATE_FORMATS: Dict[str, Dict[str, str]] = {
    "talking_head": {
        "label": "口播",
        "act": "出镜者面对镜头讲解,以口播表达为主,有自然的手势与表情变化",
    },
    "short_drama": {
        "label": "短剧",
        "act": "以情绪冲突与小剧情推进:出镜者有明确的情绪变化、对话反应与肢体表演",
    },
    "presenter_led_explainer": {
        "label": "主讲人讲解",
        "act": "主讲人边演示边讲解,动作与解说同步推进",
    },
    "street_interview": {
        "label": "街采",
        "act": "以随机路人问答呈现:被访者面对镜头作答,有自然的反应与肢体语言",
    },
    "two_person_podcast": {
        "label": "双人播客",
        "act": "两人对谈,交替发言并有倾听、点头等互动反应",
    },
    "ranking_listicle": {
        "label": "榜单/盘点",
        "act": "逐条揭示与介绍,配合指出、展示、对比等动作逐项推进",
    },
    "narration_led_demo": {
        "label": "旁白演示",
        "act": "以画外旁白串联,画面主体持续做演示动作",
    },
}


def normalize_replicate_format(value: Any) -> str:
    """形态白名单校验(大小写不敏感);非法值/空 → 空串 = 沿用原片结构"""
    v = str(value or "").strip().lower()
    return v if v in REPLICATE_FORMATS else ""


def replicate_format_prompt(value: Any) -> str:
    """把形态转成注入提示词的片段;未指定/非法返回空串(调用方据此跳过该段落)"""
    key = normalize_replicate_format(value)
    if not key:
        return ""
    item = REPLICATE_FORMATS[key]
    return (
        f"目标形态:{item['label']}。{item['act']}。"
        "场景、背景、画幅与镜头运动仍严格跟随参考视频;"
        "只重塑出镜者的表演结构与动作,不得改动场景与商品"
    )
