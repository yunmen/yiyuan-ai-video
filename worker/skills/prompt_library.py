# -*- coding: utf-8 -*-
'''
@文件    :prompt_library.py
@说明    :从 Pixelle-Video 引入并适配的提示词构建器(散文正文见 worker/prompts/*.md)。
@时间    :2026/09/27
@作者    :一源AI
@版本    :1.0
@说明    :逻辑(变量装配)在此,散文在 MD 资产里 —— 改提示词无需动代码。
         适配自 https://github.com/ATH-MaaS/Pixelle-Video (Apache-2.0)。
         这些能力面向「视频复刻」:由口播/旁白生成英文视频/图片 prompt、标题生成、
         风格转换、基于素材生成脚本。
'''
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from skills.prompts import render

# 替换意图 → 中文标签(与 backend prompt_builder.VALID_INTENTS 一致)。
# 这里是**单一来源**:用户可见的失败原因(worker video_tool)与逐镜头逆推的
# 「要替换/要保留」维度的措辞都取自它,避免两处各写一份标签表而漂移。
INTENT_LABELS = {
    "product": "商品",
    "person": "人物",
    "scene": "场景",
}

# 意图识别不出时的兜底措辞(用户可见,不能用英文错误码)
INTENT_FALLBACK_LABEL = "元素"

# 图片风格预设(改编自 Pixelle-Video prompts/image_generation.py 的 IMAGE_STYLE_PRESETS)
IMAGE_STYLE_PRESETS = {
    "stick_figure": {
        "name": "Stick Figure Sketch",
        "description": "stick figure style sketch, black and white lines, pure white background, minimalist hand-drawn feel",
        "use_case": "General scenes, simple and intuitive",
    },
    "minimal": {
        "name": "Minimalist Abstract",
        "description": "minimalist abstract art, geometric shapes, clean composition, modern design, soft pastel colors",
        "use_case": "Modern, artistic feel",
    },
    "concept": {
        "name": "Conceptual Visual",
        "description": "conceptual visual metaphors, symbolic elements, thought-provoking imagery, artistic interpretation",
        "use_case": "Deep content, philosophical thinking",
    },
}
DEFAULT_IMAGE_STYLE = "stick_figure"


def build_video_generation_prompt(narrations: List[str]) -> str:
    """由口播/旁白列表生成英文视频生成 prompt(JSON 输出 {"video_prompts":[...]},逐条对应)。"""
    narrations_json = json.dumps({"narrations": narrations}, ensure_ascii=False, indent=2)
    return render(
        "video_generation",
        narrations_json=narrations_json,
        narrations_count=len(narrations),
    )


def parse_video_prompts(text: str) -> Optional[List[str]]:
    """从 Pixelle video_generation 的 LLM 输出里解析出英文分镜提示词列表。

    兼容两种输出键:{"video_prompts": [...]} 或 {"narrations": [...]} 包裹,
    并容忍 ```json 代码块围栏与前后多余文本。解析失败(含条数为 0)返回 None,
    由调用方回退到既有中文逐段提示词链路。
    """
    if not text:
        return None
    data = _loads_json(text)
    if not isinstance(data, dict):
        return None
    items = data.get("video_prompts") or data.get("narrations")
    if not isinstance(items, list) or not items:
        return None
    prompts = [
        str(it).strip() if not isinstance(it, dict)
        else str(it.get("content") or it.get("prompt") or "").strip()
        for it in items
    ]
    prompts = [p for p in prompts if p]
    return prompts or None


def build_image_generation_prompt(
    narrations: List[str], min_words: int = 50, max_words: int = 100,
) -> str:
    """由口播/旁白列表生成英文图片生成 prompt(JSON 输出,逐条对应)。"""
    narrations_json = json.dumps({"narrations": narrations}, ensure_ascii=False, indent=2)
    return render(
        "image_generation",
        narrations_json=narrations_json,
        narrations_count=len(narrations),
        min_words=min_words,
        max_words=max_words,
    )


def build_title_generation_prompt(content: str, max_length: int = 15) -> str:
    """为给定内容生成短视频标题(限长,语言与输入一致)。"""
    return render("title_generation", content=content[:500], max_length=max_length)


def build_style_conversion_prompt(description: str) -> str:
    """把任意语言的风格描述转成英文图片生成 prompt(适配 Stable Diffusion/FLUX)。"""
    return render("style_conversion", description=description)


def build_asset_script_prompt(
    intent: str, duration: int, assets_text: str, title: str = "",
) -> str:
    """基于用户素材(视频复刻场景:用户提供参考素材)生成视频脚本。"""
    title_section = f"- Video Title: {title}\n" if title else ""
    title_instruction = (
        f"6. Narration content should be consistent with the video title: {title}\n"
        if title else ""
    )
    return render(
        "asset_script_generation",
        duration=duration,
        title_section=title_section,
        intent=intent,
        assets_text=assets_text,
        title_instruction=title_instruction,
    )


def apply_image_prefix(prompt: str, prefix: str = "") -> str:
    """把可选风格前缀拼到图片 prompt 前(改编自 Pixelle-Video utils/prompt_helper.py)。"""
    prefix = prefix.strip() if prefix else ""
    prompt = prompt.strip() if prompt else ""
    if prefix and prompt:
        return f"{prefix}, {prompt}"
    return prefix or prompt


def build_content_narration_prompt(
    content: str, n_storyboard: int, min_words: int, max_words: int,
) -> str:
    """从用户给定内容提炼/润色为短视频口播文案(逐段 narration,供 TTS 生成音频)。"""
    return render(
        "content_narration",
        content=content,
        n_storyboard=n_storyboard,
        min_words=min_words,
        max_words=max_words,
    )


def build_topic_narration_prompt(
    topic: str, n_storyboard: int, min_words: int, max_words: int,
) -> str:
    """从主题/话题发散为短视频口播文案(逐段 narration,强调开头多样性与口语化)。"""
    return render(
        "topic_narration",
        topic=topic,
        n_storyboard=n_storyboard,
        min_words=min_words,
        max_words=max_words,
    )


def intent_labels(intent: Optional[List[str]]) -> List[str]:
    """替换意图 → 中文标签列表(保持入参顺序,识别不出的整条丢弃)"""
    picked: List[str] = []
    for raw in intent or []:
        label = INTENT_LABELS.get(str(raw).strip().lower())
        if label and label not in picked:
            picked.append(label)
    return picked


def intent_scope(intent: Optional[List[str]]) -> Tuple[str, str]:
    """替换意图 → (需要替换的维度文案, 需要保留的维度文案)

    逐镜头逆推必须按维度区分这两类:
    把**被替换维度**如实描述出来(如原片商品的颜色/材质),模型会把原片元素又写回画面,
    与用户的替换意图直接打架 —— 那正是「复刻白做」(成片还是原片的商品)的成因。
    反之,没被选中的维度就是要复刻下来的部分,必须如实描述。

    未选任何意图(纯复刻)时:替换文案为「无」,保留文案列出全部维度 ——
    此时原片里的每一个元素都要复刻下来,逆推应如实描述,不应留空。
    """
    chosen = intent_labels(intent)
    kept = [label for key, label in INTENT_LABELS.items() if label not in chosen]
    replace_text = "、".join(chosen) or "无(本次为纯复刻,不替换任何元素)"
    keep_text = "、".join(kept) or "全部元素"
    return replace_text, keep_text


def build_shot_reverse_prompt(
    shot_count: int, intent: Optional[List[str]], frames_per_shot: int = 2,
) -> str:
    """逐镜头逆推提示词(P0-3):读原片镜头画面与原片台词,产出该镜头的画面与运镜描述

    散文正文在 prompts/shot_reverse.md,此处只做变量装配 —— 改提示词不需要动代码。
    替换意图按维度注入「要替换 / 要保留」两段,避免逆推把原片元素写回画面。
    """
    replace_text, keep_text = intent_scope(intent)
    return render(
        "shot_reverse",
        shot_count=shot_count,
        frames_per_shot=frames_per_shot,
        intent_replace=replace_text,
        intent_keep=keep_text,
    )


def parse_shot_prompts(text: str, indexes: List[int]) -> Dict[int, str]:
    """从逆推结果里解析出「镜头序号 → 画面描述」;解析不出返回空字典

    三种容错(都是实测常见形态):
      · ```json 代码块围栏与前后多余说明文字;
      · `{"shots": [{"index": 0, "shot": "..."}]}` 标准形态;
      · `{"shots": ["...", "..."]}` 只给了字符串数组 —— 按 indexes 顺序对应。

    **允许部分成功**:某个镜头没解析出内容就跳过它(调用方对缺失的镜头沿用原提示词),
    这比整批丢弃更有价值 —— 逆推是逐镜头增强,不该因为模型漏了一个镜头而全废。
    """
    if not text or not indexes:
        return {}
    data = _loads_json(text)
    if not isinstance(data, dict):
        return {}
    items = data.get("shots")
    if not isinstance(items, list) or not items:
        return {}
    out: Dict[int, str] = {}
    for pos, item in enumerate(items):
        if isinstance(item, dict):
            raw_index = item.get("index")
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                # 没给 index 时按位置对应(模型偶尔会漏字段)
                index = indexes[pos] if pos < len(indexes) else None
                if index is None:
                    continue
            body = str(item.get("shot") or item.get("prompt") or item.get("content") or "").strip()
        else:
            index = indexes[pos] if pos < len(indexes) else None
            body = str(item).strip() if item is not None else ""
        if index is None or index not in indexes or not body:
            continue
        out[index] = body
    return out


def build_shot_qc_prompt(shot_count: int, intent: Optional[List[str]]) -> str:
    """逐镜头质检提示词(P1-7):把原片与成片的同位置画面配对比对

    替换意图必须一起注入:成片里"商品/人物换了"是本次复刻**要求的结果**,
    若不告诉模型,它会把预期差异判成"没复刻上",给出无意义的低分与误导性建议。
    """
    replace_text, _ = intent_scope(intent)
    return render("shot_qc", shot_count=shot_count, intent_replace=replace_text)


def parse_shot_qc(text: str, indexes: List[int]) -> Dict[int, Dict[str, Any]]:
    """解析逐镜头质检结果 → {镜头序号: {"score": int, "issue": str}};解析不出返回空字典

    容错与 parse_shot_prompts 一致(围栏/多余文字/字符串数组),另外:
      · score 夹到 0-100,取不到分数的条目直接跳过(没有分数的质检没有意义);
      · issue 允许缺失(高分本来就不需要填)。
    **允许部分成功**:漏判的镜头不参与汇总,而不是让整批质检作废。
    """
    if not text or not indexes:
        return {}
    data = _loads_json(text)
    if not isinstance(data, dict):
        return {}
    items = data.get("shots")
    if not isinstance(items, list) or not items:
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for pos, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        raw_index = item.get("index")
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            index = indexes[pos] if pos < len(indexes) else None
        if index is None or index not in indexes or index in out:
            continue
        try:
            score = int(round(float(item.get("score"))))
        except (TypeError, ValueError):
            continue
        score = min(max(score, 0), 100)
        out[index] = {"score": score, "issue": str(item.get("issue") or "").strip()}
    return out


def _loads_json(text: str) -> Optional[object]:
    """宽松 JSON 解析:剥掉代码块围栏,再退化到"截取最外层花括号"重试"""
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None
