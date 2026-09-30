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
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from skills.prompts import render

logger = logging.getLogger("skills.prompt_library")

# —— 关于本模块中「生产链路尚未接线」的构建器 ——
# build_image_generation_prompt / build_title_generation_prompt / build_style_conversion_prompt /
# build_content_narration_prompt / build_topic_narration_prompt 目前只被 worker/tests 与
# skills/__init__.py 的重导出引用,生产链路没有调用点(文案/标题/图片提示词当前由 backend 的
# copy_writer / prompt_builder 承担)。保留它们是预留的原子能力,不是死代码 ——
# 改动这些函数与对应 md 不会影响线上出片,但也别把它们当成已接线的入口去找调用方。
# 当前真正被生产链路消费的是:build_video_generation_prompt、build_asset_script_prompt、
# build_shot_reverse_prompt、build_shot_qc_prompt、build_image_direction_prompt。

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
    base = render(
        "asset_script_generation",
        duration=duration,
        title_section=title_section,
        intent=intent,
        assets_text=assets_text,
        title_instruction=title_instruction,
    )
    return _append_replicate_methodology(base, SCRIPT_METHODOLOGY)


def parse_asset_script(text: str) -> str:
    """从脚本生成的 LLM 输出里取出逐场景 narration,拼成一段口播文案。

    容错(与 parse_shot_prompts 同思路):```json 围栏、{"scenes": [...]} /
    {"script": [...]} / 顶层数组;narrations 可能是字符串或字符串数组。
    解析不出返回空串 —— 调用方据此回退"无文案"的历史行为,不因一次解析失败影响主链路。
    """
    data = _loads_json(text)
    scenes: Optional[List[Any]] = None
    if isinstance(data, dict):
        for key in ("scenes", "script", "segments"):
            value = data.get(key)
            if isinstance(value, list):
                scenes = value
                break
    elif isinstance(data, list):
        scenes = data
    if not scenes:
        return ""
    lines: List[str] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        narrations = scene.get("narrations")
        if isinstance(narrations, str):
            lines.append(narrations.strip())
        elif isinstance(narrations, list):
            lines += [str(x).strip() for x in narrations if str(x).strip()]
    return "\n".join(line for line in lines if line)


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


# 逆推的**基础**方法论:理解参考视频所必需(先把原片看懂),任何档位都要注入。
# 视频方向资产决定每个镜头该用哪种控制语义(参考条件/关键帧约束/纯文本),
# 这样逆推产出的是"有约束力的生成依据",而不只是一句"中景推近"的静态构图描述。
REVERSE_BASE: Tuple[str, ...] = (
    "replicate_reference_understanding",
    "replicate_video_direction",
)

# **改造透镜**类资产:描述"怎样把参考改造成新版本"(换角色/重塑形态/浅依赖)。
# 只在用户选择改造档位时注入 —— 忠实复刻档位注入它,会让模型主动重写原片结构,
# 与"尽量保留原片"的目标直接冲突,还白耗 token 稀释真正的约束。
REVERSE_TRANSFORM: Tuple[str, ...] = (
    "replicate_transformation_lenses",
    "replicate_generated_dependencies",
)

# 「不指定创意档位」时的资产集合 = 改造前的行为(全量注入)。
# 保留它,是为了让老任务重跑与老客户端下发的请求结果与改造前完全一致。
REVERSE_METHODOLOGY: Tuple[str, ...] = REVERSE_BASE + REVERSE_TRANSFORM

# 创意档位 key(与 backend prompt_builder.CREATIVE_LEVEL_OPTIONS 的 key 对齐;
# 选项表的单一来源在 backend,/gen-config 下发前端渲染,worker 只按 key 选资产)。
CREATIVE_FAITHFUL = "faithful"
CREATIVE_REWRITE = "rewrite"
CREATIVE_VIRAL = "viral"

# 档位 → 该档位额外追加的资产(改造透镜之外,讲"这一档要做到什么"的资产)
CREATIVE_ASSET_NAMES = {
    CREATIVE_REWRITE: "replicate_creative_rewrite",
    CREATIVE_VIRAL: "replicate_creative_viral",
}

# 开头钩子强化 key(与 backend prompt_builder.HOOK_BOOST_OPTIONS 对齐)
HOOK_BOOST_STRONG = "strong"
HOOK_BOOST_ASSET = "replicate_hook_boost"

# 质检:只需「改造透镜」。质检只回答"差异是不是本次改造的预期结果",
# 参考理解/生成依赖与打分无关,注入只会白白增加 token。
QC_METHODOLOGY: Tuple[str, ...] = ("replicate_transformation_lenses",)

# 复刻口播脚本:声音方向(选角/递送)+ 字幕(语义短语断句/阅读节奏)。
# 二者都作用在**文案本身**上:字幕内容本就来自新脚本(断句决定字幕怎么切),
# 声音方向决定这句词由谁、以什么节奏递送 —— 所以它们属于脚本生成环节,
# 而不是 TTS(会把方法论念出来)或烧字幕(纯文本,无 LLM)环节。
SCRIPT_METHODOLOGY: Tuple[str, ...] = (
    "replicate_voice_direction",
    "replicate_captions",
)

# 图像方向:复刻换商品/人物/场景时,把参考图里观察到的外观转成生成指令。
IMAGE_METHODOLOGY: Tuple[str, ...] = ("replicate_image_direction",)


def build_image_direction_prompt() -> str:
    """复刻换图时,给「写图片提示词的 LLM」的指引。

    注意它**不是**可以直接拼进图片模型 prompt 的片段:那是给模型的元指引
    (保留构图/光线/位置,只把具体外观交给参考图),直接塞进图片模型会干扰出图、
    甚至产生文字伪影。所以调用方应拿它作 system prompt 让 chat 改写提示词。
    资产缺失时返回空串,调用方据此跳过改写。
    """
    parts: List[str] = []
    for name in IMAGE_METHODOLOGY:
        try:
            parts.append(render(name))
        except Exception:  # noqa: BLE001
            continue
    if not parts:
        return ""
    return "# 图像方向(改写图片提示词时必须遵循)\n" + "\n\n".join(parts)


# 方法论附录的默认标题:说明这些散文的来源与优先级,避免模型把它当成新的任务描述
DEFAULT_METHODOLOGY_HEADER = "\n\n# 视频复刻方法论参考(改编自 Hypit 技能,优先于上方通用规则)\n"


def _append_replicate_methodology(
    base: str, names: Tuple[str, ...], header: str = DEFAULT_METHODOLOGY_HEADER
) -> str:
    """把复刻方法论/增强资产追加到提示词尾部。

    这些资产来自 backend/skills/prompts/replicate/(worker 通过引用复用,不复制),
    缺失或渲染失败时静默跳过 —— 它们都是"增强"而非"必需",绝不能因为一份资产
    没加载到就让整条逆推链路失败。

    header 可覆盖默认标题,让不同用途的附录(方法论 / 钩子要求)各自有准确的说明。
    """
    appendix_parts: List[str] = []
    for name in names:
        try:
            appendix_parts.append(render(name))
        except Exception:  # noqa: BLE001  资产缺失/渲染失败均不影响主链路
            continue
    if not appendix_parts:
        return base
    return base + header + "\n\n".join(appendix_parts)


def resolve_reverse_assets(creative_level: Optional[str]) -> Tuple[str, ...]:
    """按创意档位解析「逐镜头逆推」要注入的方法论资产集合。

    空值/非法值 → 返回 REVERSE_METHODOLOGY(改造前的全量集合),保证老任务重跑行为不变;
    faithful    → 只注入基础集合(不塞改造透镜,避免模型主动重写原片结构);
    rewrite     → 基础 + 改造透镜 + 轻度改写资产;
    viral       → 基础 + 改造透镜 + 爆款改造资产。
    """
    key = str(creative_level or "").strip().lower()
    if key == CREATIVE_FAITHFUL:
        return REVERSE_BASE
    prompt_name = CREATIVE_ASSET_NAMES.get(key)
    if prompt_name:
        return REVERSE_BASE + REVERSE_TRANSFORM + (prompt_name,)
    return REVERSE_METHODOLOGY


# 复刻目标形态资产名前缀(与 backend/skills/prompts/replicate/formats/*.md 的 frontmatter name 对齐)。
# 形态资产由 backend 持有(单一来源),worker 通过 loader 引用复用,不复制。
REPLICATE_FORMAT_PREFIX = "replicate_format_"


def _append_replicate_format(base: str, fmt: Optional[str]) -> str:
    """把「复刻目标形态」资产追加到逆推提示词尾部。

    形态决定成片的内容结构(短剧/口播/街采/…):让逐镜头逆推按目标形态组织画面与运镜,
    而不是照抄原片结构 —— 否则"选了短剧形态"仍会拿到与原片同构的镜头描述。
    未指定形态 / 形态资产缺失时原样返回(静默跳过),不影响既有逆推链路。
    """
    key = str(fmt or "").strip().lower()
    if not key:
        return base
    try:
        # 前缀固定,故即使传入非法形态也只会命中"不存在的形态资产"而跳过,不会误渲染其它资产
        body = render(f"{REPLICATE_FORMAT_PREFIX}{key}")
    except Exception:  # noqa: BLE001  形态不存在/渲染失败均不影响主链路
        return base
    if not body.strip():
        return base
    return f"{base}\n\n# 复刻目标形态(必须按此形态重塑结构,而非照抄原片)\n{body.strip()}"


def build_shot_reverse_prompt(
    shot_count: int, intent: Optional[List[str]], frames_per_shot: int = 2,
    fmt: Optional[str] = None, creative_level: Optional[str] = None,
    hook_boost: Optional[str] = None, asset_override: Optional[str] = None,
) -> str:
    """逐镜头逆推提示词(P0-3):读原片镜头画面与原片台词,产出该镜头的画面与运镜描述

    散文正文在 backend/skills/prompts/replicate/shot_reverse.md(权威资产),
    此处只做变量装配 —— 改提示词不需要动代码。
    替换意图按维度注入「要替换 / 要保留」两段,避免逆推把原片元素写回画面;
    尾部按**创意档位**追加对应的方法论资产(见 resolve_reverse_assets)。

    fmt 为复刻目标形态(短剧/口播/街采/…):非空时再追加对应形态资产,
    使逆推按目标形态组织画面与运镜,而不是照抄原片结构。

    creative_level 为空时沿用改造前的全量方法论注入 —— 老任务与老客户端行为不变;
    显式选「忠实复刻」时不注入改造透镜,逆推只描述原片事实而不主动重写结构。
    hook_boost 为「强化开头3秒」时追加钩子资产:首镜逆推直接产出钩子式画面描述,
    而不是等生成阶段再改(拆解与生成同源,用户看到的描述就是将要出片的依据)。
    """
    replace_text, keep_text = intent_scope(intent)
    try:
        base = render(
            "shot_reverse",
            shot_count=shot_count,
            frames_per_shot=frames_per_shot,
            intent_replace=replace_text,
            intent_keep=keep_text,
        )
    except (KeyError, ValueError):
        # backend 复刻资产缺失(独立部署未配置 BACKEND_SKILLS_PROMPTS_DIR):
        # 逆推降级为基础指令,主视频任务不因此中断。
        logger.warning(
            "复刻逆推资产 shot_reverse 缺失,逆推提示词降级为基础指令"
            "(请配置 BACKEND_SKILLS_PROMPTS_DIR 指向 backend/skills/prompts)"
        )
        base = (
            f"你是短视频同款复刻的分镜分析师。原片被切成 {shot_count} 个镜头,"
            f"请对每个镜头产出画面与运镜描述。需要替换的维度:{replace_text};"
            f"需要保留的维度:{keep_text}。"
        )
    base = _append_replicate_methodology(base, resolve_reverse_assets(creative_level))
    # 钩子强化独立成附录:它只作用于第一镜,与通篇生效的创意档位用不同标题区分,
    # 避免模型把"改开头"的要求推广到所有镜头。
    if str(hook_boost or "").strip().lower() == HOOK_BOOST_STRONG:
        base = _append_replicate_methodology(
            base,
            (HOOK_BOOST_ASSET,),
            header="\n\n# 开头钩子强化要求(仅作用于第一镜)\n",
        )
    base = _append_replicate_format(base, fmt)
    override = str(asset_override or "").strip()
    if override:
        # 用户专家模式追加的创作要求:挂在提示词末尾,逆推时一并作为约束,
        # 使拆解分镜描述也能体现该要求(与生成路径同源,用户看到的拆解描述即出片依据)。
        base = base + f"\n\n# 额外创作要求(用户专家模式追加)\n{override}\n"
    return base


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

    再注入 Hypit「改造透镜」:它定义了复刻要"保留角色语义、重塑形态",
    即形态层面的差异(构图/表演/包装)是**达成复刻**而非失败 ——
    少了这层,质检会把按透镜正确改造的镜头也判成低分,误导用户去重试本已正确的成片。
    """
    replace_text, _ = intent_scope(intent)
    try:
        base = render("shot_qc", shot_count=shot_count, intent_replace=replace_text)
    except (KeyError, ValueError):
        # backend 复刻资产缺失(独立部署未配置 BACKEND_SKILLS_PROMPTS_DIR):
        # 质检降级为无方法论的基础比对指令,主视频任务不因此中断。
        logger.warning(
            "复刻质检资产 shot_qc 缺失,质检提示词降级为基础指令"
            "(请配置 BACKEND_SKILLS_PROMPTS_DIR 指向 backend/skills/prompts)"
        )
        base = (
            f"请比对原片与成片的 {shot_count} 个同位置镜头,评估复刻质量。"
            f"本次预期差异(应判为成功而非失败):{replace_text}。"
        )
    return _append_replicate_methodology(base, QC_METHODOLOGY)


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
