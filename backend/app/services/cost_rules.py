# -*- coding: utf-8 -*-
'''
@文件    :cost_rules.py
@说明    :成本规则(纯函数)— 各任务类型额度消耗的唯一定义处
@时间    :2026/09/21 17:00:00
@作者    :一源AI
@版本    :1.0
@说明    :此前扣费额度写死在 generate_task.TASK_COST(每种类型固定 1 次),
          与「预算前置」要求的「下单前可见花费」矛盾:用户看到的和扣的对不上。
          这里收敛成唯一实现,并让**预估与实扣调用同一个函数**
          (estimate_cost),保证所见即所扣。
          附加项默认 0(关闭):默认行为与现状完全一致,运营在后台调配置才生效。
'''
from typing import Any, Dict, Optional

# 各任务类型的基础消耗(次);配置未设置时的兜底值
BASE_COST = {
    "video": 1,
    "image": 1,
    "audio": 1,
    "text": 1,
    "digital": 1,
    "render": 1,
}
DEFAULT_BASE_COST = 1

TASK_LABELS = {
    "video": "视频生成",
    "image": "图片生成",
    "audio": "音频生成",
    "text": "文本生成",
    "digital": "数字人口播",
    "render": "视频换口播",
}

# 系统配置键(与 app/services/system_config.py 的 DEFAULT_CONFIGS 一致)
CFG_KEY_BY_TYPE = {
    "video": "gen.cost.video",
    "image": "gen.cost.image",
    "audio": "gen.cost.audio",
    "text": "gen.cost.text",
    "digital": "gen.cost.digital",
    "render": "gen.cost.render",
}
# 附加项(默认 0 = 不加价,保持现状)
CFG_KEY_DURATION_EXTRA = "gen.cost.duration_10"          # 10 秒档额外消耗
CFG_KEY_RESOLUTION_EXTRA = "gen.cost.resolution_1080p"   # 1080P 额外消耗
CFG_KEY_IMAGE_EXTRA = "gen.cost.image_extra"             # 每多生成 1 张图的额外消耗
CFG_KEY_SHOT_EXTRA = "gen.cost.video_shot_extra"         # 逐镜出片:每多 1 段(第 2 段起)的额外消耗

MIN_COST = 0


def _as_int(value: Any, default: int) -> int:
    """配置值转非负整数;空值/非法值回退默认(配置坏了不能让建单失败)"""
    if value is None or str(value).strip() == "":
        return default
    try:
        return max(MIN_COST, int(value))
    except (TypeError, ValueError):
        return default


def resolve_costs(cfg: Optional[Dict[str, str]] = None) -> Dict[str, int]:
    """从系统配置映射中解析各任务类型的基础消耗。"""
    cfg = cfg or {}
    return {
        task_type: _as_int(cfg.get(key), BASE_COST.get(task_type, DEFAULT_BASE_COST))
        for task_type, key in CFG_KEY_BY_TYPE.items()
    }


def estimate_cost(
    task_type: str,
    *,
    duration: Optional[int] = None,
    resolution: Optional[str] = None,
    num_images: Optional[int] = None,
    shot_count: Optional[int] = None,
    cfg: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """预估本次生成的额度消耗(次)。

    **预估与实扣必须调用同一个函数**:否则前端展示的价与实扣的价会漂移。
    返回明细供前端展示「为什么是这个价」(detail 为空单项时前端可只显示总价)。
    """
    cfg = cfg or {}
    base = _as_int(
        cfg.get(CFG_KEY_BY_TYPE.get(task_type, "")),
        BASE_COST.get(task_type, DEFAULT_BASE_COST),
    )
    detail: list = [{
        "key": "base",
        "label": TASK_LABELS.get(task_type, "生成"),
        "cost": base,
    }]

    # 附加项:只在配置大于 0 时累加(默认关闭,行为与现状一致)
    duration_extra = _as_int(cfg.get(CFG_KEY_DURATION_EXTRA), 0)
    if duration_extra and (duration or 0) >= 10:
        detail.append({"key": "duration_10", "label": "10 秒时长", "cost": duration_extra})

    resolution_extra = _as_int(cfg.get(CFG_KEY_RESOLUTION_EXTRA), 0)
    if resolution_extra and str(resolution or "").upper() == "1080P":
        detail.append({"key": "resolution_1080p", "label": "1080P 清晰度", "cost": resolution_extra})

    image_extra = _as_int(cfg.get(CFG_KEY_IMAGE_EXTRA), 0)
    extra_images = max(0, int(num_images or 1) - 1)
    if image_extra and extra_images:
        detail.append({
            "key": "image_extra", "label": f"额外 {extra_images} 张",
            "cost": image_extra * extra_images,
        })

    # 逐镜出片:每段都要独立调用一次视频模型,成本随段数线性增长。
    # 默认 0(关闭)—— 与现有「按次计费」一致;运营开启后才按段加收,避免默默改变价格。
    shot_extra = _as_int(cfg.get(CFG_KEY_SHOT_EXTRA), 0)
    extra_shots = max(0, int(shot_count or 1) - 1)
    if shot_extra and extra_shots:
        detail.append({
            "key": "shot_extra",
            "label": f"逐镜额外 {extra_shots} 段",
            "cost": shot_extra * extra_shots,
        })

    return {
        "type": task_type,
        "cost": sum(item["cost"] for item in detail),
        "detail": detail,
    }


def settle_refund(consumed: int, refunded: int, actual_cost: int) -> int:
    """结算应退额度 = 剩余未退(消耗 - 已退) - 实际用量。

    预算前置的最后一步:预扣按预估,成功后按实际用量结算。
    结果永不为负(实际用量大于预扣时**不倒扣**,宁可少收也不产生意外扣费)。
    """
    remaining = max(0, int(consumed or 0) - int(refunded or 0))
    return max(0, remaining - max(0, int(actual_cost or 0)))


def describe(detail: list) -> str:
    """把明细渲染成一句话(写入流水备注,便于事后核对扣了多少、为什么)"""
    if not detail:
        return ""
    return " + ".join(f"{item['label']}({item['cost']})" for item in detail)
