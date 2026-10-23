# -*- coding: utf-8 -*-
"""复刻结构提取与确定性迁移：只编译可验证结构，不从原片散文猜测产品事实。"""
import math
from typing import Any, Dict, List


# 封闭词表防止结构字段夹带原品牌、动作或任意提示词；未知值保持未知。
STRUCTURE_VALUES = {
    "shot_size": {"特写", "近景", "中景", "全景", "远景"},
    "camera_move": {"固定", "推近", "拉远", "横移", "环绕", "上摇", "下摇"},
    "transition": {"硬切", "叠化", "淡入", "淡出", "动作匹配"},
}
INTENT_LABELS = {"product": "产品", "person": "人物", "scene": "场景"}


def build_reference_dna(rows: list, duration: float = 0) -> Dict[str, Any]:
    """从内部镜头表提取时间轴及白名单结构；无镜头时只记录整片窗口，不假造切镜。"""
    candidates = rows or ([{"index": 0, "start": 0, "end": duration}] if duration else [])
    structure: List[dict] = []
    previous_end = 0.0
    for row in candidates[:300]:
        try:
            start, end = float(row["start"]), float(row["end"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(start) or not math.isfinite(end) or start < previous_end or end <= start:
            continue
        item = {"index": row.get("index", len(structure)), "start": start, "end": end}
        for field, values in STRUCTURE_VALUES.items():
            value = row.get(field)
            item[field] = value if isinstance(value, str) and value in values else "未知"
        structure.append(item)
        previous_end = end
    return {
        "version": 1,
        "status": "partial" if structure else "unavailable",
        "source": "shot_table" if rows else "whole_video_window",
        "shots": structure,
        "limitations": ["不从散文推断结构", "未分析产品功效及动作适用性"],
    }


def adapt_reference_plan(dna: dict, intent: list) -> Dict[str, Any]:
    """按已确认替换维度生成保守目标规则；不携带原描述、原旁白或臆测产品卖点。"""
    dimensions = [key for key in INTENT_LABELS if key in intent]
    rules = []
    if dimensions:
        rules.append("仅替换指定的" + "、".join(INTENT_LABELS[key] for key in dimensions)
                     + "，其他维度保持原片；目标外观与绑定关系以本任务素材及替换要求为准")
        rules.append("来源描述与旁白不作为目标事实，不恢复被替换主体的品牌、标识或话术")
    if "product" in dimensions:
        rules.append("保留展示节奏和构图；原品类操作不能直接迁移到新产品，"
                     "食用、涂抹、喷洒等动作仅在任务明确确认适用时采用，否则使用中性外观展示")
        rules.append("不得推断或编造新产品的功效、规格、认证、价格；未确认的包装文字不补造")
    return {"version": 1, "status": dna["status"], "intent": dimensions,
            "shots": [dict(row) for row in dna["shots"]], "rules": rules,
            "action_policy": "confirmed_or_neutral" if "product" in dimensions else "preserve_source"}


def compile_adapted_shot(plan: dict, index: int) -> str:
    """编译单镜结构及目标护栏；只读取迁移层，不读取来源散文。"""
    row = next((item for item in plan["shots"] if item["index"] == index), None)
    if row is None:
        return ""
    parts = [f"镜头{index}（{row['start']:g}–{row['end']:g}秒）保留原片时间节奏"]
    labels = {"shot_size": "景别", "camera_move": "运镜", "transition": "转场"}
    parts.extend(f"{labels[field]}：{row[field]}" for field in STRUCTURE_VALUES if row[field] != "未知")
    parts.extend(plan["rules"])
    return "；".join(parts)


def prepare_replica_plan(rows: list, intent: list, duration: float = 0) -> Dict[str, Any]:
    """统一生成可检查点固化的分析与迁移产物；本阶段不新增模型调用或跨任务缓存。"""
    dna = build_reference_dna(rows, duration)
    return {"version": 1, "reference_dna": dna, "adapted_plan": adapt_reference_plan(dna, intent)}
