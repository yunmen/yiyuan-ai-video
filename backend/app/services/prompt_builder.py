# -*- coding: utf-8 -*-
'''
@文件    :prompt_builder.py
@说明    :生成参数组装(纯函数)— 把模板 + 用户备注整理成结构化上下文
@时间    :2026/09/21 10:00:00
@作者    :一源AI
@版本    :1.0
@说明    :此前 prompt = 模板 desc + "。补充要求:" + remark 扁平拼接,
          remark 里的"大标题/副标题/口播文案"角色语义全丢,LLM 改写只能靠猜。
          这里先解析出结构化字段,再按 [模板结构]/[商家信息]/[生成模式] 组装上下文,
          让 worker 的 prompt 改写真正有结构可用(对应前端进度里的"解析模板结构")。
'''
from typing import Any, Dict, List, Optional, Tuple

from app.services.gen_rules import (
    DEFAULT_RATIO,
    clamp_duration,
    normalize_ratio,
    normalize_resolution,
)
from app.services.script_schema import build_script

# 前端/管理端备注中的字段别名 → 结构化键(大标题/副标题/口播文案)
REMARK_FIELD_MAP = {
    "大标题": "title",
    "标题": "title",
    "主标题": "title",
    "副标题": "subtitle",
    "卖点": "subtitle",
    "口播文案": "script",
    "口播": "script",
    "文案": "script",
    # 画面构成三段式(person/shot/setting):用户可在备注里单独覆盖,未填时用模板默认
    "主体": "person",
    "人物": "person",
    "主角": "person",
    "画面主体": "person",
    "镜头": "shot",
    "运镜": "shot",
    "景别": "shot",
    "镜头语言": "shot",
    "场景": "setting",
    "环境": "setting",
    "背景": "setting",
    "场景环境": "setting",
}

# 画面构成三段式的键与展示名(顺序即提示词中的输出顺序)
PROMPT_PARTS = ("person", "shot", "setting")
PROMPT_PART_LABELS = {"person": "画面主体", "shot": "镜头语言", "setting": "场景环境"}

# 备注分段分隔符:前端以 ";" 拼接,兼容中文分号/竖线/换行
_REMARK_SEPARATORS = (";", "；", "|", "\n")

# 素材中的视频扩展名(参考视频/原片)
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv", ".flv")


def split_materials(materials: Optional[List[str]]) -> Tuple[List[str], str]:
    """把混合素材拆成 (图片列表, 参考视频)

    视频编辑(Seedance 2.x)需要**视频本身**作参考 —— 抽帧成图片会丢掉原片的运镜与节奏;
    图片则继续作为商品图/参考帧下发。多个视频只取第一个:参考过多会分散模型注意力。
    """
    images: List[str] = []
    video = ""
    for item in materials or []:
        url = str(item or "").strip()
        if not url:
            continue
        path = url.split("?")[0].lower()
        if not video and path.endswith(VIDEO_EXTENSIONS):
            video = url
        else:
            images.append(url)
    return images, video


# 素材数量 → 生成模式(与 worker 的 mode 选择保持一致)
# v2v=视频编辑(有参考视频);1 张图生;多张参考生;无素材文生
def resolve_gen_mode(material_count: int, has_video: bool = False) -> str:
    if has_video:
        return "v2v"
    if material_count <= 0:
        return "t2v"
    if material_count == 1:
        return "i2v"
    return "r2v"


def _split_remark(remark: str) -> List[str]:
    """按分隔符切分备注;单条时原样返回"""
    parts = [remark]
    for sep in _REMARK_SEPARATORS:
        nxt: List[str] = []
        for part in parts:
            nxt.extend(part.split(sep))
        parts = nxt
    return [p.strip() for p in parts if p.strip()]


def parse_remark(remark: Optional[str]) -> Dict[str, Any]:
    """把备注串解析成结构化文案。

    输入形如 "大标题:xx;副标题:yy;口播文案:zz"(前端拼接),
    输出 {"title","subtitle","script","extra":[...]},未识别片段进 extra。
    """
    result: Dict[str, Any] = {
        "title": "", "subtitle": "", "script": "",
        "person": "", "shot": "", "setting": "", "extra": [],
    }
    if not remark or not str(remark).strip():
        return result
    for seg in _split_remark(str(remark)):
        # 中英文冒号都支持,只按第一个冒号切分(文案本身可能含冒号)
        idx = min([i for i in (seg.find(":"), seg.find("：")) if i >= 0], default=-1)
        if idx < 0:
            result["extra"].append(seg)
            continue
        key = seg[:idx].strip()
        value = seg[idx + 1:].strip()
        field = REMARK_FIELD_MAP.get(key)
        if field and value:
            # 同键重复出现时合并,避免后写覆盖先写
            result[field] = f"{result[field]} {value}".strip() if result[field] else value
        elif value:
            result["extra"].append(f"{key}:{value}")
        elif seg:
            result["extra"].append(seg)
    return result


def build_structured_text(parsed: Dict[str, Any]) -> Dict[str, str]:
    """结构化文案:**只取用户实际确认的内容**。

    模板文案(含 default_text / 模板标题)一律不参与 —— 模板文案往往绑定某个品类
    (如"洗发水"),用户换成别的品类时会把它直接串进口播与字幕(实测踩过)。
    文案统一来自「上传图识别 → 用户确认/修改」,生成时严格以用户确认的那份为准。
    """
    return {
        "title": (parsed.get("title") or "").strip(),
        "subtitle": (parsed.get("subtitle") or "").strip(),
        "script": (parsed.get("script") or "").strip(),
    }


def _template_default_parts(template: Any) -> Dict[str, str]:
    pp = getattr(template, "prompt_parts", None) or {}
    if not isinstance(pp, dict):
        return {}
    return {k: str(pp.get(k) or "").strip() for k in PROMPT_PARTS}


def build_prompt_parts(template: Any, parsed: Dict[str, Any]) -> Dict[str, str]:
    """画面构成三段式:用户备注覆盖模板默认,都没填的段落留空。

    拆成三段的意义:运营想换场景(如从门店换到厨房)只改 setting,
    不必重写整段 prompt —— 否则每次微调都要重新理解整段描述。
    """
    dt = _template_default_parts(template)
    return {k: (parsed.get(k) or dt.get(k) or "").strip() for k in PROMPT_PARTS}


def _render_prompt_parts(parts: Optional[Dict[str, str]]) -> str:
    """渲染 [画面构成] 段;三段全空时不输出,避免空段落稀释注意力"""
    if not parts:
        return ""
    lines = ["[画面构成]"]
    for key in PROMPT_PARTS:
        value = str(parts.get(key) or "").strip()
        if value:
            lines.append(f"{PROMPT_PART_LABELS[key]}:{value}")
    return "\n".join(lines) if len(lines) > 1 else ""


# v2v 商品替换的系统默认要求:用户「选模板 + 上传商品图」的意图就是把参考视频里的
# 商品换成自己的。这条**由系统注入**,不依赖用户手写备注(实测用户通常不写,
# 结果是成片里还是参考视频原来的商品/人物 —— 等于白复刻)。
SYSTEM_REPLACE_REQUIREMENT = (
    "视频中的商品与出镜主体必须替换为用户上传的商品图内容,"
    "不得保留参考视频中的原有商品、人物与品牌标识,"
    "原商品包装/标签上的文字与标识也必须一并替换,不得残留"
)

# 纯复刻的系统默认要求:用户「上传参考视频生成新视频」却**未选任何替换意图**时,
# 参考视频仅作为风格/构图/运镜参照,上传图也只是风格参考而非替换目标 ——
# 不得改动画面主体(否则会退化成"用参考图重画整片",原片场景与主体全丢,实测踩过)。
SYSTEM_REFERENCE_REQUIREMENT = (
    "参考视频仅作为风格、构图、运镜与节奏的参照,产出同款新片;"
    "用户上传的参考图亦仅作风格参考,不得作为替换元素;"
    "严格保留参考视频的画面主体、场景、品牌标识与商品,不得擅自替换或重画"
)


# 替换意图维度:用户多选,决定"生成时替换原视频里的哪些元素"
INTENT_PRODUCT = "product"
INTENT_PERSON = "person"
INTENT_SCENE = "scene"
VALID_INTENTS = {INTENT_PRODUCT, INTENT_PERSON, INTENT_SCENE}

# 备注关键词 → 意图兜底(B 方案:用户没显式选时,从自由文本推断)
INTENT_KEYWORDS = {
    INTENT_PERSON: ["人物", "换脸", "真人", "头像", "出镜人", "主角", "模特"],
    INTENT_PRODUCT: ["商品", "产品", "货品", "物品", "品牌", "logo", "LOGO"],
    INTENT_SCENE: ["场景", "环境", "背景", "地点", "布景", "取景"],
}


def normalize_intent(intent) -> List[str]:
    """把任意来源的意图收口为合法维度列表(去重、保序、过滤非法值)"""
    seen: set[str] = set()
    out: List[str] = []
    for it in (intent or []):
        key = str(it).strip().lower()
        if key in VALID_INTENTS and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def resolve_intent(intent, material_type: str, remark: str) -> List[str]:
    """解析替换意图:显式选择(A)优先,否则视觉识别类型 + 备注关键词兜底(B)

    - 显式 intent 非空 → 直接采用(用户多选即多选,三者都选=三者都替换)
    - 否则用视觉识别类型(人物/商品/场景)作默认意图
    - 再否则扫备注关键词,命中的维度并入意图
    """
    explicit = normalize_intent(intent)
    if explicit:
        return explicit
    mt = str(material_type or "").strip().lower()
    if mt in VALID_INTENTS:
        return [mt]
    text = str(remark or "")
    fallback: List[str] = []
    for dim, kws in INTENT_KEYWORDS.items():
        if any(k in text for k in kws):
            fallback.append(dim)
    return fallback


def build_replace_requirement(intent: List[str]) -> str:
    """按意图维度组装「替换原视频元素」的系统指令(v2v 视频编辑用)

    维度可多选:三者都选=把商品、人物、场景全部换成用户上传/指定的内容,产出全新一片。
    意图为空时回退原 blanket 指令,保证改造前后 v2v 默认行为一致。

    除被替换维度外必须显式声明「保持原样」:只说"把 X 换成 Y"时,模型会把上传图
    当作首帧重画整片,参考视频的场景/运镜全丢(实测:只换人物,成片变成上传图的
    图生视频,原片背景完全消失)。所以未选中的维度也要点名"不得改动"。
    """
    # 各维度的「替换」表述与对应元素名(用于反向生成"保持"条款)
    replace_texts = {
        # 换产品最容易翻车的点:原商品没了、但包装/瓶身上的文字与 logo 还留着(实测)。
        # 故显式要求连包装文字一起替换,而不是只说"换成上传的商品图"。
        INTENT_PRODUCT: ("商品与品牌标识", "视频中的商品与品牌标识必须替换为用户上传的商品图内容,不得沿用原商品;原商品包装、瓶身、标签上的文字、品牌名与 logo 也必须一并替换,不得残留任何原商品字样或标识"),
        INTENT_PERSON: ("出镜人物", "视频中的出镜人物必须替换为用户上传的人物参考图,保持该人物外观一致,不得沿用原人物"),
        INTENT_SCENE: ("场景与背景", "视频中的场景与背景必须替换为用户上传/指定的场景,保留主体与运镜节奏"),
    }
    rules: List[str] = []
    keeps: List[str] = []
    for dim, (label, text) in replace_texts.items():
        if dim in intent:
            rules.append(text)
        else:
            keeps.append(label)
    if not rules:
        return SYSTEM_REPLACE_REQUIREMENT
    # 未被替换的元素显式锁死:与替换条款同等强度,防止模型自由发挥
    if keeps:
        rules.append(f"参考视频中的{'、'.join(keeps)}必须保持原样,不得改动或重新生成")
    # 通用护栏:上传图只是替换素材,不是首帧;运镜/节奏/镜头语言始终跟随原片
    rules.append(
        "用户上传的图片仅作为被替换元素的参考,不是视频首帧;"
        "除被替换的元素外,严格保持参考视频的场景、背景、运镜、节奏与镜头语言"
    )
    # 品类串扰护栏:模板与原片里的原品类描述(原商品名、行业话术)属于"要被换掉的东西",
    # 不显式声明时会被 LLM 当创作素材保留(实测:换了产品品类,成片仍带原品类文案)。
    rules.append(
        "以用户上传的素材与文案为准;模板或参考视频中与被替换元素相关的原有品类、"
        "原商品名称及行业话术不得残留"
    )
    return "；".join(rules)


def build_material_hint(gen_mode: str, material_count: int, material_type: str = "") -> str:
    """素材语义说明:复刻场景(多张)与产品图场景(单张)必须区分,否则 LLM 改写方向跑偏

    material_type 用于把 i2v 首帧准确标注为「人物参考图」或「产品图」,
    避免把用户上传的人像误叫作商品(此前视觉识别只认商品)。
    """
    if gen_mode == "t2v":
        return "无素材(纯文案生成,画面由模型自由创作)"
    if gen_mode == "i2v":
        if material_type == INTENT_PERSON:
            return "1 张人物参考图(作为视频首帧,需保持该人物外观一致)"
        return "1 张产品图(作为视频首帧,需保持产品外观一致)"
    if gen_mode == "v2v":
        base = "1 段参考视频(复刻其场景、构图、运镜、节奏与转场,产出同款新片)"
        if material_count:
            # 必须点明"不是首帧":否则模型会把上传图当首帧重画整片,原片场景全丢
            base += (
                f";{material_count} 张替换参考图(商品图/人物图/场景图,"
                f"仅用于按所选意图替换参考视频中的对应元素,"
                f"不是视频首帧,不得以它们为起点重新生成场景)"
            )
        return base
    return (
        f"{material_count} 张参考画面(来自用户上传的参考视频/多张素材,"
        f"请保持参考画面的场景、构图、色调与质感,复刻同款镜头语言)"
    )


# 主体角色 → (段落名, 称谓);顺序即注入顺序(人物→商品→场景→其它)
SUBJECT_SECTIONS = {
    INTENT_PERSON: ("[人物信息]", "人物主体"),
    INTENT_PRODUCT: ("[商品信息]", "商品主体"),
    INTENT_SCENE: ("[场景信息]", "场景"),
    "other": ("[主体信息]", "主体"),
}
SUBJECT_ORDER = (INTENT_PERSON, INTENT_PRODUCT, INTENT_SCENE, "other")


def _subject_sections(
    subjects: Optional[Dict[str, str]], product_desc: str,
    material_type: str, intent,
) -> List[tuple]:
    """把「多图分组识别结果」整理成待注入的主体段落 [(段名, 称谓, 描述)]

    - 多主体(人物图+产品图):**各角色独立成段**,替换指令分别下发,不会互相覆盖;
    - 单主体 + 单意图:称谓以**用户选择的意图**为准(实测:狗图配"换人物"就该按人物处理,
      识别结果只负责提供"这个主体长什么样");
    - 只有老的单主体入参(product_desc)时,行为与改造前完全一致。
    """
    chosen = normalize_intent(intent)
    roles: Dict[str, str] = {}
    for role in SUBJECT_ORDER:
        desc = str((subjects or {}).get(role) or "").strip()
        if desc:
            roles[role] = desc
    if not roles and str(product_desc or "").strip():
        # 回退优先级:单意图 > 视觉识别类型(含 other) > 默认商品主体。
        # 默认商品主体是改造前的既有行为(没识别类型时一律按商品处理),不能改成"主体",
        # 否则老调用方拿到的段名会变(有单测钉着)。
        known = tuple(VALID_INTENTS) + ("other",)
        single_role = (chosen[0] if len(chosen) == 1 else "") or (
            material_type if material_type in known else ""
        ) or INTENT_PRODUCT
        roles = {single_role: str(product_desc).strip()}
    # 单主体 + 单意图 → 称谓以用户意图为准(与改造前一致)
    if len(roles) == 1 and len(chosen) == 1:
        roles = {chosen[0]: next(iter(roles.values()))}
    # 有显式意图时,**只注入用户要替换的维度**。
    # 否则视觉识别把"照片背景"也归纳成 scene 时,会凭空多出一条
    # 「场景必须替换为…」的指令,把用户没要求换的场景也换掉(实测踩过)。
    # 过滤后若一段不剩,则退回未过滤结果 —— 宁可多描述一句,也不能丢失唯一的描述。
    if chosen:
        filtered = {r: d for r, d in roles.items() if r in chosen}
        if filtered:
            roles = filtered
    out: List[tuple] = []
    for role in SUBJECT_ORDER:
        desc = roles.get(role)
        if not desc:
            continue
        section_name, label = SUBJECT_SECTIONS[role]
        out.append((section_name, label, desc))
    return out


def build_prompt_context(
    structured: Dict[str, str],
    gen_mode: str,
    material_count: int,
    ratio: str = DEFAULT_RATIO,
    duration: int = 5,
    parts: Optional[Dict[str, str]] = None,
    product_desc: str = "",
    material_type: str = "",
    intent=None,
    subjects: Optional[Dict[str, str]] = None,
) -> str:
    """组装下发 worker 的结构化上下文(供 LLM 改写成最终 prompt)。

    结构为 [模板结构] / [画面构成] / [商家信息] / [生成模式],缺失段落不输出,
    避免把空行喂给模型稀释注意力。
    """
    # 模板只提供**结构与画幅**:模板自身的品类文字(标题/分类/标签/描述)一律不再喂给模型 ——
    # 画面内容以「用户上传素材 + 用户确认的文案」为准(模板品类文字会被当素材保留,实测踩过)。
    head = ["[模板结构]"]
    head.append("模板仅提供画面结构与画幅,画面内容一律以用户上传素材与下方文案为准")
    if gen_mode == "v2v":
        # 视频编辑不能写死时长/画幅:方舟按编辑任务判定时强制 ratio=adaptive、duration=-1,
        # 成片**跟随参考视频**。提示词里再写"9:16 / 10 秒"会与真实参数互斥,
        # 模型两头都可能听,是"成片画幅/时长与预期不符"的独立来源(实测:请求 9:16、成片 16:9)。
        head.append("画幅与时长跟随参考视频(视频编辑由模型自适应,不要另行指定画幅或时长)")
    else:
        head.append(f"时长:{duration} 秒 | 画幅:{ratio}")

    # 明确标注「逐字照念」:这些是用户提供的台词,不是可自由改写的素材描述。
    # 不标注时 LLM 会把它当作改写素材,成片念出来的话与用户填写的内容对不上
    # (字幕用的是原文,于是出现"字幕与语音不一致"的观感问题)。
    merchant = ["[商家信息](以下为必须逐字照念的台词,不得改写或替换措辞)"]
    if structured.get("title"):
        merchant.append(f"大标题:{structured['title']}")
    if structured.get("subtitle"):
        merchant.append(f"副标题:{structured['subtitle']}")
    if structured.get("script"):
        merchant.append(f"口播文案:{structured['script']}")

    mode = [
        "[生成模式]",
        {"t2v": "文生视频", "i2v": "图生视频", "r2v": "参考生视频", "v2v": "视频编辑"}.get(gen_mode, gen_mode),
        build_material_hint(gen_mode, material_count),
    ]

    # 被替换的维度不注入模板自带的画面构成描述:该维度要由**用户上传的素材**决定,
    # 保留模板描述会与用户意图打架(实测:模板写"画面主体:手持产品特写",用户却选了换人物)。
    # 未替换的维度(如镜头语言)仍保留模板值作结构参考。
    replaced_parts = {"person"} & set(intent or [])
    if INTENT_SCENE in (intent or []):
        replaced_parts.add("setting")
    parts = {k: v for k, v in (parts or {}).items() if k not in replaced_parts}

    sections = ["\n".join(head), "\n".join(mode)]
    if composition := _render_prompt_parts(parts):
        sections.insert(1, composition)
    if len(merchant) > 1:
        sections.insert(-1, "\n".join(merchant))
    # 商品/人物识别结果独立成段:它描述的是「画面主体长什么样」,与台词([商家信息])职责不同。
    # 视觉识别类型决定称谓:人像不准叫"商品",否则替换指令错位(换人变换货)。
    # 只有识别成功(配了视觉模型且调用正常)才会出现,识别失败时链路与之前完全一致。
    for section_name, subject_label, subject_desc in _subject_sections(
        subjects, product_desc, material_type, intent
    ):
        # v2v 视频编辑场景下,该主体需替换参考视频中的原有同名主体
        replace_tail = "并替换参考视频中的原有" + subject_label if gen_mode == "v2v" else ""
        sections.insert(-1, "\n".join([
            section_name,
            f"{subject_label}(视觉识别):{subject_desc}",
            f"画面中的{subject_label}必须与上述描述一致{replace_tail}",
        ]))
    return "\n\n".join(sections)


def build_gen_params(
    template: Any,
    materials: Optional[List[str]],
    remark: Optional[str],
    ratio: Optional[str] = None,
    resolution: Optional[str] = None,
    abs_url=None,
    # duration 放在 abs_url 之后:保持现有位置参数顺序不变(旧调用方按位置传 abs_url 不受影响)
    duration: Optional[int] = None,
    product_desc: str = "",
    material_type: str = "",
    intent=None,
    subjects: Optional[Dict[str, str]] = None,
    real_person_strategy: Optional[str] = None,
) -> Dict[str, Any]:
    """组装下发给 worker 的生成参数(结构化版,兼容旧的扁平 prompt 字段)。

    新增字段均为"只读增强":worker 缺失时自动回退 prompt,旧任务重跑不受影响。
    duration 为用户在页面显式选择的时长(秒):不传则回退模板时长 ——
    "规格由模板写死、用户无法选择"是此前与成熟产品差距最大的一项。
    intent / material_type 为「替换意图」增强:显式选择(A)优先,视觉识别类型 + 备注关键词兜底(B)。
    subjects 为**多图分组识别**结果(person/product/scene → 各自描述),用于多主体分段注入。
    """
    materials = [m for m in (materials or []) if m]
    # 视频素材单独提出来作「参考视频」(视频编辑用),图片仍走 materials
    materials, reference_video = split_materials(materials)
    ratio = normalize_ratio(ratio)
    resolution = normalize_resolution(resolution)
    raw_duration = duration or getattr(template, "duration", None) or 5
    gen_duration = clamp_duration(raw_duration)

    parsed = parse_remark(remark)
    structured = build_structured_text(parsed)
    gen_mode = resolve_gen_mode(len(materials), bool(reference_video))
    # 解析替换意图:显式(A)优先,视觉识别类型 + 备注关键词兜底(B)
    intent = resolve_intent(intent, material_type, remark or "")
    # D4 修复:视频编辑(v2v)且上传了图片素材、但用户没显式选替换意图时,不应静默忽略素材。
    # 但维度不能一刀切成 product —— 用户上传人物图/场景图做"人物/场景复刻"时,
    # 强行当商品替换会把人/场景错当商品换掉(复刻不都是产品复刻)。
    # 改为按视觉识别分组结果推断维度:上传什么就替换什么(人物图→person、场景图→scene、产品图→product);
    # 识别不到类型(未配视觉模型/失败)时,回退商品替换以保证上传图仍被使用、不白复刻。
    if gen_mode == "v2v" and len(materials) > 0 and not intent:
        # 只认「值非空」的维度:视觉识别失败/未配时 classify_subjects 返回
        # _empty_subjects()(person/product/scene 键都在,但值都是空串),
        # 只判断键存在会把三个维度全误收成替换意图。必须按值非空推断。
        _detected = [d for d in SUBJECT_ORDER if d in VALID_INTENTS and (subjects or {}).get(d)]
        if _detected:
            intent = _detected
        elif material_type in VALID_INTENTS:
            intent = [material_type]
        else:
            intent = [INTENT_PRODUCT]
    material_hint = build_material_hint(gen_mode, len(materials), material_type)

    # 扁平 prompt 仅作**旧任务 / 旧 worker 的兼容兜底**(prompt_context 存在时 worker 不读它)。
    # 不再拼接模板 desc/title:模板品类文字无实际用处,还会串进提示词,彻底清除,
    # 只保留用户确认过的内容。
    prompt = str(remark or "").strip()

    parts = build_prompt_parts(template, parsed)
    context = build_prompt_context(
        structured, gen_mode, len(materials), ratio=ratio, duration=gen_duration,
        parts=parts, product_desc=product_desc, material_type=material_type, intent=intent,
        subjects=subjects,
    )
    # 用户补充要求必须进提示词。
    # 此前它只随扁平 prompt 下发,而 worker 有 prompt_context 时**不再读扁平 prompt**,
    # 于是"把视频里的人换成商品图主体"这类指令被静默丢弃 —— 用户以为写了会生效,实际没有。
    extra = [str(e).strip() for e in (parsed.get("extra") or []) if str(e or "").strip()]
    # 系统默认要求:**选模板 + 有可替换素材** → 按意图注入「替换原视频对应元素」指令。
    # 放在最前面,即使用户没写备注也一定有 —— 否则成片里还是原视频的元素,复刻失去意义。
    # 三者都选意图=商品/人物/场景全替换;无显式意图但上传了图(v2v)→ 默认按商品替换(D4 修复)。
    if gen_mode == "v2v" and len(materials) > 0:
        # 有替换意图 → 按意图替换对应元素;无意图但有图 → 默认商品替换(不再静默忽略素材)
        extra.insert(0, build_replace_requirement(intent) if intent else SYSTEM_REFERENCE_REQUIREMENT)
    if extra:
        context = f"{context}\n\n[补充要求]\n" + "\n".join(extra)
    # 词锚点脚本(P0):分段 + 选区/瞬时点,一律用词序号锚定
    script = build_script(structured, parsed.get("extra") or [])

    return {
        "template_id": getattr(template, "id", None),
        "template_title": getattr(template, "title", ""),
        "prompt": prompt or "生成一段高质量短视频",
        # 结构化上下文(worker 优先使用,缺失时回退 prompt)
        "prompt_context": context,
        "structured": structured,
        # 画面构成三段式:worker 可直接用 prompt_context,该结构化字段供局部重跑时单段替换
        "prompt_parts": parts,
        # 词锚点脚本(P0):worker 消费后按分段/锚点组织提示词,并导出编排 cue
        "script": script,
        "materials": [abs_url(u) for u in materials] if abs_url else list(materials),
        # 参考视频(视频编辑用):无视频时为空串但**键必须存在** —— 跨端契约测试按"是否下发"校验,
        # 缺键会让 worker 静默回退到普通 r2v。
        "reference_video": (abs_url(reference_video) if abs_url else reference_video) if reference_video else "",
        "material_hint": material_hint,
        "gen_mode": gen_mode,
        # 替换意图(可选):product/person/scene 多选。worker 据此区分「换产品/换人物/换场景」,
        # 三者全选=原视频商品、人物、场景都换成用户的内容
        "intent": intent,
        # 多图分组识别结果(person/product/scene → 各自描述):worker 的强制替换指令用它提供
        # 「新主体长什么样」的文字语义 —— 只给参考图不给文字时,模型对『换成什么』没有锚点,
        # 容易把替换做成"保留原商品"(实测 task=43:意面沙拉图 + 汉堡原片,成片仍是汉堡)。
        # 键必须存在(即便为空对象),旧 worker 读不到该键时回退纯参考图指令,行为不变。
        "subjects": subjects or {},
        # 视觉识别出的参考图类型(person/product/scene/other),与 intent 互补(B 方案兜底)
        "material_type": material_type,
        # duration 保留原值(历史兼容),gen_duration 为模型实际档位(与前端展示同源)
        "duration": raw_duration,
        "gen_duration": gen_duration,
        "ratio": ratio,
        "resolution": resolution,
        # 真人处理策略(per-task 覆盖):auto=沿用系统配置;stylize=写实化保留;drop=直接丢弃。
        # 键必须存在(即便为空串),跨端契约测试按"是否下发"校验;worker 读到空串即回退系统默认。
        "real_person_strategy": real_person_strategy or "",
    }
