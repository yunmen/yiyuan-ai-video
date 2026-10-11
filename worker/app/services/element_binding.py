"""原片元素与参考图的确定性约束，不把代表帧时间伪装为完整出现区间。"""
import json
from typing import Any, Dict, List


def normalize_groups(slots, material_groups=None):
    """新素材组优先，旧单图映射转为同一结构供编辑和质检共同消费。"""
    if material_groups:
        return material_groups
    grouped = {}
    for url, slot in (slots or {}).items():
        grouped.setdefault(slot, []).append(url)
    return [{"element_id": slot, "images": urls, "primary_image": urls[0]} for slot, urls in grouped.items()]


def build_binding_directive(images: List[str], slots: Dict[str, str], elements: List[Dict[str, Any]], window=None, material_groups=None) -> str:
    """以最终图片顺序生成分组指令，主图优先，缺图或悬空绑定明确失败。"""
    bindings = normalize_groups(slots, material_groups)
    if not bindings or not elements:
        return ""
    element_map = {element["id"]: element for element in elements}
    groups = {}
    for group in bindings:
        slot = group["element_id"]
        urls = group["images"]
        if slot not in element_map or any(url not in images for url in urls):
            raise ValueError("替换图片已丢失或绑定的原片元素不存在，不能继续定向编辑")
        primary = group.get("primary_image") or urls[0]
        ordered = [primary] + [url for url in urls if url != primary]
        groups[slot] = [images.index(url) + 1 for url in ordered]
    lines = ["【原片元素定向替换约束】以下绑定优先于笼统的按类别替换要求。"]
    if window is not None:
        lines.append(f"本次切片对应原片 {window[0]:.3f}-{window[1]:.3f} 秒；切片内时间从0开始。范围为估计包络，不代表元素持续出现；仅在当前画面实际出现对应元素时替换，不得为匹配参考图添加主体。")
    for slot, indices in groups.items():
        element = element_map[slot]
        detail = {"元素": slot, "类型": element.get("kind"), "原片描述": element.get("label"), "使用参考图序号": indices, "主参考图序号": indices[0]}
        if element.get("bbox"):
            detail["代表帧归一化位置"] = element["bbox"]
        observations = element.get("observations") or []
        if observations:
            visible = []
            for point in observations:
                if window is not None and not window[0] <= point["time"] < window[1]:
                    continue
                visible.append({**point, "切片内观测秒": round(point["time"] - window[0], 3)} if window else point)
            detail["当前窗口可见帧定位"] = visible
            detail["观测语义"] = "同一元素的多次出现共用目标身份；观测点之间及未采样镜头可见性未知，不补主体、不把离场空档合并为连续出现"
        if element.get("start") is not None and element.get("end") is not None:
            detail["原片估计出现范围秒"] = [element["start"], element["end"]]
            if window is not None:
                start = max(element["start"], window[0])
                end = min(element["end"], window[1])
                detail["切片内估计重叠范围秒"] = [round(start - window[0], 3), round(end - window[0], 3)] if end > start else []
                if end <= start:
                    detail["定位提示"] = "估计范围未覆盖当前切片，不主动添加该元素；以实际画面核对为准"
        elif element.get("time") is not None:
            detail["原片代表帧秒（非完整范围）"] = element["time"]
        lines.append(json.dumps(detail, ensure_ascii=False))
    lines.append("序号按本次 images 从1开始。同一元素的多张图是同一主体的多角度，不得生成额外商品。不同元素不得串位；同一元素跨镜头保持身份一致。未绑定元素保持原片，不得按类别全部替换。时间仅供定位，须结合原片画面核对，不能据此虚构新镜头。保留原片顺序、节奏、动作与运镜。")
    return "\n".join(lines)
