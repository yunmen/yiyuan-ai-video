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

from app.core.plugin import logger

from app.services.gen_rules import (
    DEFAULT_RATIO,
    clamp_duration,
    normalize_ratio,
    normalize_replicate_format,
    normalize_resolution,
    replicate_format_prompt,
)
from app.services.script_schema import build_script
# 提示词散文集中到 backend/skills/prompts(单一来源);worker 扫描复用,改 MD 即维护、不碰代码。
# 加载失败时回退下方 DEFAULT_* 内联兜底(与 MD 正文保持一致),保证生成链路不中断。
from skills.prompts import get as _get_prompt, safe_render as _safe_render


def load_skill_prompt(name: str, default: str = "") -> str:
    """从 worker 加载器读提示词散文;缺失回退 default"""
    asset = _get_prompt(name)
    return asset.body if asset else default


def render_skill_prompt(name: str, default: str = "", **vars) -> str:
    """渲染带变量的提示词;资产缺失时回退 default(不抛异常)"""
    return _safe_render(name, default, **vars)


def _tpl_get(template, key, default=None):
    """统一读取模板字段:兼容 SimpleNamespace(测试)与序列化 dict(运行时 backend 下发)"""
    if isinstance(template, dict):
        return template.get(key, default)
    return getattr(template, key, default)

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
    pp = _tpl_get(template, "prompt_parts") or {}
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


# v2v 商品替换的系统默认要求(= gen_replace_blanket.md):用户「选模板 + 上传商品图」的意图
# 就是把参考视频里的商品换成自己的。这条**由系统注入**,不依赖用户手写备注(实测用户通常不写,
# 结果是成片里还是参考视频原来的商品/人物 —— 等于白复刻)。
# 真正单一来源是 backend/skills/prompts/generation/ 下的 gen_replace_blanket.md(worker 经 skills.prompts 复用,本地已不再存副本),此处仅作加载失败兜底。
DEFAULT_SYSTEM_REPLACE_REQUIREMENT = (
    "视频中的商品与出镜主体必须替换为用户上传的商品图内容,"
    "不得保留参考视频中的原有商品、人物与品牌标识,"
    "原商品包装/标签上的文字与标识也必须一并替换,不得残留"
)

# 纯复刻的系统默认要求(= gen_reference_requirement.md):用户「上传参考视频生成新视频」却
# **未选任何替换意图**时,参考视频仅作为风格/构图/运镜参照,上传图也只是风格参考而非替换目标 ——
# 不得改动画面主体(否则会退化成"用参考图重画整片",原片场景与主体全丢,实测踩过)。
# 真正单一来源是 backend/skills/prompts/generation/ 下的 gen_reference_requirement.md(worker 复用,本地已不再存副本),此处仅作加载失败兜底。
DEFAULT_SYSTEM_REFERENCE_REQUIREMENT = (
    "参考视频仅作为风格、构图、运镜与节奏的参照,产出同款新片;"
    "用户上传的参考图亦仅作风格参考,不得作为替换元素;"
    "严格保留参考视频的画面主体、场景、品牌标识与商品,不得擅自替换或重画"
)

# 替换意图维度:用户多选,决定"生成时替换原视频里的哪些元素"
INTENT_PRODUCT = "product"
INTENT_PERSON = "person"
INTENT_SCENE = "scene"

# 替换意图维度白名单:决定"生成时替换原视频里的哪些元素"。
# 维度必须与 skills/prompt_library.INTENT_LABELS(worker 内部意图标签单一来源)完全一致,
# 由 backend 测试 test_intent_labels_consistent 双向锁定;新增维度时两端必须同步。
# 注意:带 label/desc 的完整选项表由 backend 通过 /gen-config 的 replicate_intents 下发前端渲染,
# worker 不重复维护选项表(历史上在此处保留了一份 INTENT_OPTIONS 的 label/desc 副本,既未被使用、
# 又与会下发的版本文案不一致,属冗余漂移,已删除)。
VALID_INTENTS = {INTENT_PRODUCT, INTENT_PERSON, INTENT_SCENE}

# 备注关键词 → 意图兜底(B 方案:用户没显式选时,从自由文本推断)
INTENT_KEYWORDS = {
    INTENT_PERSON: ["人物", "换脸", "真人", "头像", "出镜人", "主角", "模特"],
    INTENT_PRODUCT: ["商品", "产品", "货品", "物品", "品牌", "logo", "LOGO"],
    INTENT_SCENE: ["场景", "环境", "背景", "地点", "布景", "取景"],
}

# 以下常量与通用/品类护栏一样,正文已外置到 skill md(单一来源),此处仅作加载失败兜底。
# 修改提示词请直接改对应 MD,不要改这里,否则会出现"MD 与兜底不一致"的漂移。
DEFAULT_REPLACE_TEXTS = {
    INTENT_PRODUCT: (
        "视频中的商品与品牌标识必须替换为用户上传的商品图内容,不得沿用原商品;"
        "原商品包装、瓶身、标签上的文字、品牌名与 logo 也必须一并替换,不得残留任何原商品字样或标识"
    ),
    INTENT_PERSON: (
        "视频中的出镜人物必须替换为用户上传的人物参考图,保持该人物外观一致,不得沿用原人物"
    ),
    INTENT_SCENE: (
        "视频中的场景与背景必须替换为用户上传/指定的场景,保留主体与运镜节奏"
    ),
}
# 换人物时追加的「脸部特征保真」强约束(= gen_face_identity_guard.md):
# 「替换为参考图人物」只是**方向**,不含"脸要像"的具体约束时,模型没有任何依据锁定五官,
# 会把脸重画成另一张(实测:只锁发型服饰时,成片五官与参考图对不上,用户观感就是"换了个陌生人")。
# 依赖识别人物描述里已写出面部特征(ai_vision.SUBJECT_PROMPT),两者配套生效。
DEFAULT_FACE_IDENTITY_GUARD = (
    "成片主角的面部特征必须与用户上传的人物参考图严格一致:"
    "脸型与轮廓线条、眉形、眼型与眼色、鼻型、唇形、发型与发色、肤色、妆造须逐项对应,"
    "不得改变、不得美化成另一张脸、不得替换成五官相近但明显不是本人的脸;"
    "人物在整片中必须始终是同一张面孔,不同镜头与角度下五官比例与面部结构保持稳定,"
    "不得出现五官漂移、脸型忽变或中途换脸;表情与口型可贴合原片,但情绪变化不得改变五官结构;"
    "若因平台隐私策略需规避真人身份特征,应保留该人的五官结构与面部比例、仅转为非写实风格,不得替换成另一张脸"
)
# 通用护栏(= gen_replace_keep_guard.md):上传图只是替换素材而非首帧,其余跟随原片
DEFAULT_KEEP_GUARD = (
    "用户上传的图片仅作为被替换元素的参考,不是视频首帧;"
    "除被替换的元素外,严格保持参考视频的场景、背景、运镜、节奏与镜头语言"
)
# 品类串扰护栏(= gen_replace_category_guard.md):以用户素材文案为准,清理原品类话术
DEFAULT_CATEGORY_GUARD = (
    "以用户上传的素材与文案为准;模板或参考视频中与被替换元素相关的原有品类、"
    "原商品名称及行业话术不得残留"
)
# 来源水印护栏(= gen_watermark_guard.md):去除参考视频里的品牌台标/水印/频道标识。
# 只在「替换元素」链路注入 —— 纯复刻(照搬原片)的语义是"严格保留原片主体与品牌",
# 对该链路去水印属于擅自改变用户要求,故不在那里注入。
DEFAULT_WATERMARK_GUARD = (
    "不得保留或重绘参考视频中的品牌水印、频道台标、平台标识、账号名称、logo 与贴片广告;"
    "这些区域须还原为该处的自然背景,不得出现任何文字、标识或半透明色块"
)


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
    # 各维度的「替换」表述与对应元素名(用于反向生成"保持"条款)。
    # 替换正文(散文)已外置到 backend/skills/prompts/generation/ 下的 gen_replace_<dim>.md(唯一来源,worker 复用),
    # 此处 label 仅作结构化的"保持"条款锚点,text 从 skill md 读取、失败回退内联兜底。
    replace_texts = {
        # 换产品最容易翻车的点:原商品没了、但包装/瓶身上的文字与 logo 还留着(实测)。
        # 故显式要求连包装文字一起替换,而不是只说"换成上传的商品图"。
        INTENT_PRODUCT: ("商品与品牌标识", "gen_replace_product", DEFAULT_REPLACE_TEXTS[INTENT_PRODUCT]),
        INTENT_PERSON: ("出镜人物", "gen_replace_person", DEFAULT_REPLACE_TEXTS[INTENT_PERSON]),
        INTENT_SCENE: ("场景与背景", "gen_replace_scene", DEFAULT_REPLACE_TEXTS[INTENT_SCENE]),
    }
    rules: List[str] = []
    keeps: List[str] = []
    for dim, (label, prompt_name, default_text) in replace_texts.items():
        if dim in intent:
            rules.append(load_skill_prompt(prompt_name, default=default_text))
            # 换人物时紧接着追加脸部保真锚点(必须紧跟 gen_replace_person:先说"换成谁"、
            # 再说"脸要怎么像",顺序颠倒时后一句会被前一句的方向带偏)。
            if dim == INTENT_PERSON:
                rules.append(load_skill_prompt(
                    "gen_face_identity_guard", default=DEFAULT_FACE_IDENTITY_GUARD))
        else:
            keeps.append(label)
    if not rules:
        return load_skill_prompt("gen_replace_blanket", default=DEFAULT_SYSTEM_REPLACE_REQUIREMENT)
    # 未被替换的元素显式锁死:与替换条款同等强度,防止模型自由发挥
    if keeps:
        rules.append(f"参考视频中的{'、'.join(keeps)}必须保持原样,不得改动或重新生成")
    # 通用护栏:上传图只是替换素材,不是首帧;运镜/节奏/镜头语言始终跟随原片
    # （= backend/skills/prompts/generation/ 下的 gen_replace_keep_guard.md,worker 复用）
    rules.append(load_skill_prompt("gen_replace_keep_guard", default=DEFAULT_KEEP_GUARD))
    # 品类串扰护栏:模板与原片里的原品类描述(原商品名、行业话术)属于"要被换掉的东西",
    # 不显式声明时会被 LLM 当创作素材保留(实测:换了产品品类,成片仍带原品类文案)。
    # （= backend/skills/prompts/generation/ 下的 gen_replace_category_guard.md,worker 复用）
    rules.append(load_skill_prompt("gen_replace_category_guard", default=DEFAULT_CATEGORY_GUARD))
    # 来源水印护栏:复刻出的成片不得携带原片的品牌台标/水印(实测原片"麻花实采"这类频道标识
    # 会被视频编辑模型一起重绘出来),显式要求把该区域还原为自然背景,避免成片带他人品牌标识。
    # （= backend/skills/prompts/generation/replace/gen_watermark_guard.md,worker 复用）
    rules.append(load_skill_prompt("gen_watermark_guard", default=DEFAULT_WATERMARK_GUARD))
    return "；".join(rules)


def build_material_hint(gen_mode: str, material_count: int, material_type: str = "") -> str:
    """素材语义说明:复刻场景(多张)与产品图场景(单张)必须区分,否则 LLM 改写方向跑偏

    material_type 用于把 i2v 首帧准确标注为「人物参考图」或「产品图」,
    避免把用户上传的人像误叫作商品(此前视觉识别只认商品)。

    散文正文已外置到 backend/skills/prompts/generation/ 下的 gen_material_hint_*.md(唯一来源,worker 复用);
    render 失败时回退下方内联兜底(变量已先按本函数语义替换好)。
    """
    if gen_mode == "t2v":
        return load_skill_prompt(
            "gen_material_hint_t2v",
            default="无素材(纯文案生成,画面由模型自由创作)",
        )
    if gen_mode == "i2v":
        if material_type == INTENT_PERSON:
            return render_skill_prompt(
                "gen_material_hint_i2v",
                default="1 张人物参考图(作为视频首帧,需保持该人物外观一致)",
                ref="人物参考图", obj="该人物",
            )
        return render_skill_prompt(
            "gen_material_hint_i2v",
            default="1 张产品图(作为视频首帧,需保持产品外观一致)",
            ref="产品图", obj="产品",
        )
    if gen_mode == "v2v":
        base = load_skill_prompt(
            "gen_material_hint_v2v_base",
            default="1 段参考视频(复刻其场景、构图、运镜、节奏与转场,产出同款新片)",
        )
        if material_count:
            # 必须点明"不是首帧":否则模型会把上传图当首帧重画整片,原片场景全丢
            base += render_skill_prompt(
                "gen_material_hint_v2v_extra",
                default=(
                    f";{material_count} 张替换参考图(商品图/人物图/场景图,"
                    f"仅用于按所选意图替换参考视频中的对应元素,"
                    f"不是视频首帧,不得以它们为起点重新生成场景)"
                ),
                count=material_count,
            )
        return base
    return render_skill_prompt(
        "gen_material_hint_r2v",
        default=(
            f"{material_count} 张参考画面(来自用户上传的参考视频/多张素材,"
            f"请保持参考画面的场景、构图、色调与质感,复刻同款镜头语言)"
        ),
        count=material_count,
    )


# 主体角色 → (段落名, 称谓);顺序即注入顺序(人物→商品→场景→其它)
SUBJECT_SECTIONS = {
    INTENT_PERSON: ("[人物信息]", "人物主体"),
    INTENT_PRODUCT: ("[商品信息]", "商品主体"),
    INTENT_SCENE: ("[场景信息]", "场景"),
    "other": ("[主体信息]", "主体"),
}
SUBJECT_ORDER = (INTENT_PERSON, INTENT_PRODUCT, INTENT_SCENE, "other")

# 复刻目标形态资产名前缀:与 backend/skills/prompts/replicate/formats/*.md 的 frontmatter name 对齐
REPLICATE_FORMAT_PREFIX = "replicate_format_"


def _render_replicate_format(replicate_format: Optional[str]) -> str:
    """渲染 [复刻目标形态] 段落;未指定/非法/资产缺失时返回空串(静默跳过,不阻断链路)。

    形态决定成片的内容结构(短剧/口播/街采/…),是「复刻提示词」的单一来源
    (backend/skills/prompts/replicate/formats/),worker 通过引用复用同一份,不复制。
    """
    fmt = normalize_replicate_format(replicate_format)
    if not fmt:
        return ""
    body = load_skill_prompt(f"{REPLICATE_FORMAT_PREFIX}{fmt}", default="")
    if not body.strip():
        logger.warning(f"复刻目标形态[{fmt}]提示词资产缺失,本次不注入形态段落")
        return ""
    return f"[复刻目标形态]\n{body.strip()}"


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
    replicate_format: str = "",
) -> str:
    """组装下发 worker 的结构化上下文(供 LLM 改写成最终 prompt)。

    结构为 [模板结构] / [复刻目标形态] / [画面构成] / [商家信息] / [生成模式],缺失段落不输出,
    避免把空行喂给模型稀释注意力。

    replicate_format 为复刻目标形态(短剧/口播/街采/…),非空时把对应形态资产
    (backend/skills/prompts/replicate/formats/*.md)作为 [复刻目标形态] 段落注入,
    让改写按目标形态重塑结构,而不是照抄原片。资产缺失时静默跳过,不阻断链路。
    """
    # 模板只提供**结构与画幅**:模板自身的品类文字(标题/分类/标签/描述)一律不再喂给模型 ——
    # 画面内容以「用户上传素材 + 用户确认的文案」为准(模板品类文字会被当素材保留,实测踩过)。
    head = ["[模板结构]"]
    # 首段规则散文已外置到 backend/skills/prompts/generation/ 下的 gen_context_template_rule.md(唯一来源,worker 复用)
    head.append(load_skill_prompt(
        "gen_context_template_rule",
        default="模板仅提供画面结构与画幅,画面内容一律以用户上传素材与下方文案为准",
    ))
    if gen_mode == "v2v":
        # 视频编辑不能写死时长/画幅:方舟按编辑任务判定时强制 ratio=adaptive、duration=-1,
        # 成片**跟随参考视频**。提示词里再写"9:16 / 10 秒"会与真实参数互斥,
        # 模型两头都可能听,是"成片画幅/时长与预期不符"的独立来源(实测:请求 9:16、成片 16:9)。
        # 该说明散文已外置到 backend/skills/prompts/generation/ 下的 gen_context_v2v_note.md(worker 复用)
        head.append(load_skill_prompt(
            "gen_context_v2v_note",
            default="画幅与时长跟随参考视频(视频编辑由模型自适应,不要另行指定画幅或时长)",
        ))
    else:
        head.append(f"时长:{duration} 秒 | 画幅:{ratio}")

    # 明确标注「逐字照念」:这些是用户提供的台词,不是可自由改写的素材描述。
    # 不标注时 LLM 会把它当作改写素材,成片念出来的话与用户填写的内容对不上
    # (字幕用的是原文,于是出现"字幕与语音不一致"的观感问题)。
    # 段首说明散文已外置到 backend/skills/prompts/generation/ 下的 gen_context_merchant_intro.md(worker 复用)
    merchant = [load_skill_prompt(
        "gen_context_merchant_intro",
        default="[商家信息](以下为必须逐字照念的台词,不得改写或替换措辞)",
    )]
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
    composition = _render_prompt_parts(parts)
    if composition:
        sections.insert(1, composition)
    # 形态资源提供具体创作指引,规则补充场景与商品保持不变的约束。
    fmt_text = _render_replicate_format(replicate_format)
    format_prompt = replicate_format_prompt(replicate_format)
    if fmt_text or format_prompt:
        format_text = "\n".join(part for part in (fmt_text, format_prompt) if part)
        sections.insert(2 if composition else 1, format_text)
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
    replicate_format: Optional[str] = None,
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
    raw_duration = duration or _tpl_get(template, "duration") or 5
    gen_duration = clamp_duration(raw_duration)

    parsed = parse_remark(remark)
    structured = build_structured_text(parsed)
    gen_mode = resolve_gen_mode(len(materials), bool(reference_video))
    # 解析替换意图:显式(A)优先,视觉识别类型 + 备注关键词兜底(B)
    intent = resolve_intent(intent, material_type, remark or "")
    # 复刻目标形态:白名单收口,非法值归为「不指定形态」(与历史行为一致)
    fmt = normalize_replicate_format(replicate_format)
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
    # 复刻形态:白名单校验后注入(非法/未传 → 空串 = 沿用原片结构)
    fmt = normalize_replicate_format(replicate_format)
    context = build_prompt_context(
        structured, gen_mode, len(materials), ratio=ratio, duration=gen_duration,
        parts=parts, product_desc=product_desc, material_type=material_type, intent=intent,
        subjects=subjects, replicate_format=fmt,
    )
    # 用户补充要求必须进提示词。
    # 此前它只随扁平 prompt 下发,而 worker 有 prompt_context 时**不再读扁平 prompt**,
    # 于是"把视频里的人换成商品图主体"这类指令被静默丢弃 —— 用户以为写了会生效,实际没有。
    extra = [str(e).strip() for e in (parsed.get("extra") or []) if str(e or "").strip()]
    # 系统默认要求:**视频编辑(v2v,即带参考视频)** → 注入「保留原片结构」指令。
    # 放在最前面,即使用户没写备注也一定有 —— 否则成片里还是原视频的元素,复刻失去意义。
    # 关键修复:此前只在「有可替换素材」时才注入,导致**纯复刻(只传对标视频、不上传替换图、
    # 无替换意图)完全拿不到保留原片指令**,v2v 编辑自由发挥,成片像"另一个 AI 视频"。
    # 现放宽为「只要走 v2v 就注入」:
    #   · 有替换意图 → 按意图替换对应元素,未选中维度显式锁死"保持原样";
    #   · 无意图但有图(v2v)→ 默认按商品替换(不再静默忽略素材,D4 修复);
    #   · 纯复刻(无图无意图)→ 注入 gen_reference_requirement:严格保留原片主体/场景/品牌,
    #     仅以原片作风格/构图/运镜/节奏参照,不得擅自重画(正是"复刻出来要像原片"的护栏)。
    if gen_mode == "v2v":
        # 有替换意图 → 按意图替换对应元素;无意图 → 保留原片结构(纯复刻也走这里)
        extra.insert(0, build_replace_requirement(intent) if intent else load_skill_prompt(
            "gen_reference_requirement", default=DEFAULT_SYSTEM_REFERENCE_REQUIREMENT))
    if extra:
        context = f"{context}\n\n[补充要求]\n" + "\n".join(extra)
    # 词锚点脚本(P0):分段 + 选区/瞬时点,一律用词序号锚定
    script = build_script(structured, parsed.get("extra") or [])

    return {
        "template_id": _tpl_get(template, "id"),
        "template_title": _tpl_get(template, "title", ""),
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
        # 复刻目标形态(可选):worker 据此给逐镜头逆推注入对应形态资产;
        # 不指定时为空串,键仍必须存在(契约测试按"是否下发"校验),worker 读到空串即跳过注入。
        "format": fmt,
        # 复刻形态(可选):worker 据此放宽 v2v 对"动作严格保持一致"的约束,让出镜者按形态演绎。
        # 键必须存在(空串=未指定形态),worker 读到空串即保持原有"严格照搬原片"的行为。
        "replicate_format": fmt,
    }


def build_gen_params_from_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """从 backend 下发的「原始参数 + 序列化模板」组装成完整生成参数(prompt_context 等)。

    backend 不再做组装,只下发业务输入(已 abs_url 的素材、备注、归一化画幅/时长、识别结果、
    序列化模板);worker 在 process_video 里调用本函数完成组装,与旧链路产出完全一致。
    非组装字段(creative_level/hook_boost/lead_act/asset_override/cost 等)原样透传,
    避免破坏下游字段读取。
    """
    # 动作复刻不继承模板中的营销提示词或口播，用户备注仍由公共组装解析。
    tpl = {} if raw.get("replicate_mode") == "action" else (raw.get("_template") or {})
    # 原始 build_gen_params 的签名不含 creative_level/hook_boost/lead_act/asset_override,
    # 这些字段由 backend 单独下发,组装后回填到结果上供下游消费。
    assembled = build_gen_params(
        template=tpl,
        materials=raw.get("materials") or [],
        remark=raw.get("remark"),
        ratio=raw.get("ratio"),
        resolution=raw.get("resolution"),
        duration=raw.get("duration"),
        product_desc=raw.get("product_desc", ""),
        material_type=raw.get("material_type", ""),
        intent=raw.get("intent"),
        subjects=raw.get("subjects") or {},
        real_person_strategy=raw.get("real_person_strategy", "auto"),
        replicate_format=raw.get("replicate_format"),
    )
    # 透传 per-task 覆盖字段(原始组装函数不产出,需保留)
    assembled["creative_level"] = raw.get("creative_level", "")
    assembled["hook_boost"] = raw.get("hook_boost", "")
    assembled["lead_act"] = raw.get("lead_act", "")
    assembled["asset_override"] = raw.get("asset_override", "")
    assembled["remark"] = raw.get("remark") or ""
    # 兼容字段:下游可能按 gen_ratio/gen_resolution 读取
    assembled.setdefault("gen_ratio", assembled.get("ratio"))
    assembled.setdefault("gen_resolution", assembled.get("resolution"))
    # 其余业务透传字段(避免破坏下游字段读取)。
    # 注意透传用 `if k in raw` 才赋值:backend 未下发时不写入 assembled,从而保证下游
    # 「未传则回退全局配置」的语义(例如 qc_auto_retry 未下发时退回 worker 的
    # VIDEO_QC_AUTO_RETRY,绝不能因为组装函数塞了个空串就把全局开启也关掉)。
    passthrough = (
        "cost", "webui", "subtitle", "voice", "tts", "type", "device",
        "original_video", "segment_index", "new_text", "edited_prompt",
        "_regenerate_segment", "result_video",
        "qc_auto_retry", "goal", "replicate_mode",
        # 服务端可信复刻快照独立于九宫格字符串提示词，保持结构原样传递。
        "shot_plan", "deconstruct_id", "_analysis_owner",
        # 原片元素表与多角度图片映射必须一起保留，编辑请求按最终图片顺序消费。
        "image_slots", "reference_elements", "material_groups", "analysis_id", "analysis_version",
        # 逐镜出片(九宫格):每张分镜图独立成段再拼接;不透传会被静默丢弃,
        # 退化成「多图 → r2v」(整批图一起生成一段),逐镜语义全丢。
        "shot_mode", "shot_prompts", "per_shot_seconds",
        # P3 合成层增强(代码渲染层):自动 B-roll / 信息卡·角标·动效 / 音效卡点。
        # 这些字段由 backend 下发、base.run 在成片收尾阶段消费;而组装函数只产出提示词相关
        # 字段,若不在此显式透传,就会被组装结果整体覆盖而静默丢弃 —— 主视频链路(process_video)
        # 会退化成「P3 能力全不生效」(render/digital 直传原始 params,不受影响)。
        # 透传键在 backend 未下发时为 None,消费侧一律按「未声明即跳过」处理,行为与改造前一致。
        "auto_broll", "sound_effects",
        "overlay_card", "overlay_badge", "overlay_ranking",
        "overlay_reveal", "overlay_flash", "overlay_sticker",
    )
    for k in passthrough:
        if k in raw:
            assembled.setdefault(k, raw[k])
    if raw.get("reference_video"):
        assembled.setdefault("reference_video", raw["reference_video"])
    return assembled
