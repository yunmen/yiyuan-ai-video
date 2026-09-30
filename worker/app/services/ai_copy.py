# -*- coding: utf-8 -*-
'''
@文件    :ai_copy.py
@说明    :AI 文案生成/润色(从 backend/app/services/copy_writer.py 迁至 worker,使 backend 不再直连模型)。
         按模板风格生成短视频三段文案(大标题/副标题/口播),用户不会写 prompt 也能一键得到可用文案;
         网关未配置/调用失败/格式异常时返回行业兜底文案,保证流程不中断。
         提示词散文统一取自 backend/skills/prompts/merchant_copy.md(worker 扫描复用,单一来源)。
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
import asyncio
import json
from typing import Dict, List, Optional

from openai import AsyncOpenAI

from app.core.plugin import logger
from app.core import gateway
from app.settings import config
from app.services.ai_vision import classify_subjects, classify_material_types
from skills.prompts import get as _get_prompt, safe_render as _safe_render


def load_skill_prompt(name: str, default: str = "") -> str:
    """从 worker 加载器读提示词散文(扫描 backend/skills/prompts,单一来源);缺失回退 default"""
    asset = _get_prompt(name)
    return asset.body if asset else default


def render_skill_prompt(name: str, default: str = "", **vars) -> str:
    """渲染带变量的提示词;资产缺失时回退 default(不抛异常)"""
    return _safe_render(name, default, **vars)


# 降级兜底:仅在 merchant_copy.md 加载失败时使用(真正的单源是 backend/skills/prompts/merchant_copy.md)
_MERCHANT_COPY_FALLBACK = (
    "你是短视频营销文案助手。严格输出 JSON(不要 markdown 代码块),字段:"
    '{"title":"视频大标题,≤20字","subtitle":"副标题/卖点,≤30字","script":"口播文案,≤50字"}。'
    "以「文案主题」为创作核心,围绕主题组织有钩子、有利益点的成稿。"
)

# 兜底的画面要求模板:模型不可用时也要让用户看到"可改的起点"
FALLBACK_DEMAND = (
    "把参考视频中的主体替换为上传图中的主体,保持外观一致;"
    "其余场景、构图、运镜与节奏严格保持原样"
)
FALLBACK_DEMAND_MULTI = (
    "把参考视频中的原人物换成上传的人物形象图,把原商品换成上传的产品图"
    "(含包装文字与标识一并替换),其余场景、构图、运镜与节奏严格保持原样"
)


def _build_demand_fallback(roles: Optional[List[str]]) -> str:
    """模型没回 demand 时的兜底画面要求:按素材角色说明替换哪些元素"""
    clauses = []
    for r in (roles or []):
        key = str(r or "").strip().lower()
        if key == "product":
            clauses.append("把原商品换成上传的产品图(包装与文字一并替换)")
        elif key == "person":
            clauses.append("把原出镜人物换成上传的人物图(外观保持一致)")
        elif key == "scene":
            clauses.append("把原场景与背景换成上传的场景图")
    if clauses:
        return "；".join(clauses) + "，其余场景、构图、运镜与节奏严格保持原样"
    return FALLBACK_DEMAND


# 视觉提示词:带参考画面时的补充说明
VISION_HINT_WITH_DRAFT = (
    "\n参考画面:消息里附上了用户参考视频的关键画面。请先看清画面里的主体、场景与风格,"
    "再与用户草稿结合润色 —— 文案必须与画面相符,不要写成与该画面无关的行业套话。"
)
VISION_HINT_NO_DRAFT = (
    "\n参考画面:消息里附上了用户参考视频的关键画面。用户未填文案,"
    "请完全依据画面内容(主体是什么、什么场景、什么风格)从零创作,不要套用行业模板。"
)
VISION_HINT_MULTI = (
    "\n参考素材:消息里附上了用户上传的**多张素材图**,可能同时包含人物形象图与产品图。"
    "请先分别看清:(a) 有没有出镜人物、长什么样;(b) 有没有产品、是什么品类与外观。"
    "文案必须**把两者结合起来** —— 人物负责出镜口播的语气与人设,产品负责卖点与利益点;"
    "不要只写其中一方,也不要写成与素材无关的行业套话。"
)
VISION_HINT_MULTI_DRAFT = (
    "\n参考素材:消息里附上了用户上传的**多张素材图**(可能同时含人物形象图与产品图)。"
    "请先分别看清人物与产品,再把用户草稿与素材**结合润色**:人物定口播语气与人设,"
    "产品定卖点与利益点;不要只写其中一方。"
)
# 主体命名硬规则:配合"先识别后生成"的素材锚点一起生效
VISION_GROUND_RULES = (
    "\n主体命名硬规则:标题/副标题/口播/subject/画面要求中,同一素材主体必须使用**同一个名称**,"
    "以「素材识别结果」为准,不得一处叫汉堡另一处叫三明治;"
    "只描述图片中**实际可见**的特征,禁止臆造看不见的馅料/配料/口味/品牌"
    "(图中是炸鸡汉堡,就不能写成芝士火腿烤鸡);"
    "卖点可基于品类常识,但不得写成图中不存在的细节。"
)
ROLE_LABELS = {"person": "人物形象图", "product": "产品图", "scene": "场景图"}

# 最多喂几张画面:3 张已足够判断主体与风格
MAX_VISION_IMAGES = 3

# 行业兜底文案模板:{template} 会被模板标题替换
FALLBACK_COPY: Dict[str, Dict[str, str]] = {
    "美食探店": {
        "title": "这家{template}藏不住了",
        "subtitle": "本地人都在排队,味道真的绝",
        "script": "今天带你们打卡这家宝藏店,招牌必点,看完记得收藏,周末约起来!",
    },
    "零售带货": {
        "title": "{template}限时开抢",
        "subtitle": "好价不等人,错过再等一年",
        "script": "今天这个价格真的打下来了,品质放心,点击下方链接,手慢无!",
    },
    "美妆个护": {
        "title": "{template}实测分享",
        "subtitle": "亲测好用,无限回购款",
        "script": "用了两周来给大家交作业,效果看得到的,姐妹们放心冲!",
    },
    "健身运动": {
        "title": "来{template}练出好状态",
        "subtitle": "专业指导,新手也能轻松上手",
        "script": "坚持打卡遇见更好的自己,现在预约还有新人体验价,快来试试!",
    },
    "教育培训": {
        "title": "{template}开课啦",
        "subtitle": "干货满满,学完就能用",
        "script": "名额有限,想提升自己的朋友抓紧时间报名,点击了解课程详情!",
    },
    "家居生活": {
        "title": "{template}提升幸福感",
        "subtitle": "实用又好看,居家必备",
        "script": "家里添了它生活品质直线上升,喜欢的朋友赶紧入手,链接放下面了!",
    },
    "门店宣传": {
        "title": "{template}邀您到店",
        "subtitle": "活动进行中,到店有惊喜",
        "script": "新店活动火热进行中,地址就在屏幕下方,欢迎大家到店体验!",
    },
}
FALLBACK_DEFAULT: Dict[str, str] = {
    "title": "{template}值得一试",
    "subtitle": "品质之选,不负期待",
    "script": "好内容值得被看见,感兴趣的朋友点赞关注,我们下期见!",
}


def fallback_copy(template_title: str, category: str, with_demand: bool = False,
                  multi: bool = False) -> Dict[str, str]:
    """按行业分类返回兜底文案,返回结构带 fallback=True 供前端区分提示"""
    tpl = FALLBACK_COPY.get(category, FALLBACK_DEFAULT)
    theme = (template_title or "本期推荐").strip()
    result: Dict[str, str] = {
        "title": tpl["title"].format(template=theme)[:20],
        "subtitle": tpl["subtitle"].format(template=theme)[:30],
        "script": tpl["script"].format(template=theme)[:50],
        "fallback": True,
    }
    if with_demand:
        result["subject"] = ""
        result["demand"] = FALLBACK_DEMAND_MULTI if multi else FALLBACK_DEMAND
    return result


def _merchant_copy_system(with_demand: bool = False) -> str:
    """三段带货文案的系统提示:统一取自 backend/skills/prompts/merchant_copy.md(单一来源)"""
    prompt = load_skill_prompt("merchant_copy", default=_MERCHANT_COPY_FALLBACK)
    if with_demand:
        prompt += load_skill_prompt("merchant_copy_demand", default="")
    return prompt


def _role_line(roles: Optional[List[str]]) -> str:
    """把前端标注的素材角色转成一行提示(顺序与图片顺序一致);没标注则返回空串"""
    names = [ROLE_LABELS.get(str(r or "").strip().lower()) for r in (roles or [])]
    names = [n for n in names if n]
    if not names:
        return ""
    return "素材图顺序与角色:" + "、".join(f"第{i + 1}张={n}" for i, n in enumerate(names)) + "\n"


def _grounding_line(subjects: Dict[str, str], roles: Optional[List[str]]) -> str:
    """把多图分组识别结果转成提示词里的**事实锚点**;识别结果为空返回空串"""
    parts: List[str] = []
    for i, role in enumerate(roles or []):
        desc = str((subjects or {}).get(role) or "").strip()
        if desc:
            label = ROLE_LABELS.get(role, role)
            parts.append(f"第{i + 1}张({label}):{desc}")
    if not parts:
        for role in ("person", "product", "scene"):
            desc = str((subjects or {}).get(role) or "").strip()
            if desc:
                parts.append(f"{ROLE_LABELS.get(role, role)}:{desc}")
    if not parts:
        return ""
    return ("素材识别结果(创作时必须以此为准,不要自行猜测图里是什么):"
            + ";".join(parts) + "\n")


async def _vision_model() -> str:
    return (config.VISION_MODEL or "").strip()


async def _chat_model() -> str:
    """聊天/文本生成模型名;未配置返回空。

    必须与 `ai_vision._chat_model` 一样声明为 async:`generate()` 内部用
    `await _chat_model()` 取值,若改回同步 def,await 会直接抛
    `TypeError: object str can't be used in 'await' expression`,文案任务在
    进入模型调用之前就失败。
    """
    return (config.CHAT_MODEL or "").strip()


def _vision_gateway() -> Dict[str, str]:
    gw = gateway.resolve("vision")
    return gw if gw.get("url") and gw.get("key") else {}


def _llm_gateway() -> Dict[str, str]:
    gw = gateway.resolve("chat")
    return gw if gw.get("url") and gw.get("key") else {}


async def generate(template_title: str, category: str,
                   title: Optional[str] = None, subtitle: Optional[str] = None,
                   script: Optional[str] = None,
                   images: Optional[List[str]] = None,
                   with_demand: bool = False,
                   roles: Optional[List[str]] = None) -> Dict[str, str]:
    """生成/润色三段文案。

    带参考画面(images)且已配置视觉模型时走**图文结合**:
      · 用户没填草稿 → 完全依据画面内容从零创作;
      · 用户填了草稿   → 画面与草稿结合润色。
    未配视觉模型 / 网关未配置 / 调用失败 / 格式异常 → 逐级降级(纯文本 → 行业兜底),不中断流程。
    """
    theme = (title or "").strip() or (subtitle or "").strip() or (template_title or "").strip()

    img_urls = [u for u in (images or []) if u][:MAX_VISION_IMAGES]
    vision_model = await _vision_model() if img_urls else ""
    use_vision = bool(img_urls and vision_model)
    if use_vision:
        vision_gw = _vision_gateway()
        if not (vision_gw.get("url") and vision_gw.get("key")):
            use_vision = False
    if use_vision:
        base_url, api_key = vision_gw["url"], vision_gw["key"]
        model = vision_model
    else:
        llm_gw = _llm_gateway()
        if not (llm_gw.get("url") and llm_gw.get("key")):
            logger.warning("LLM 网关未配置,AI 文案降级为兜底模板")
            return fallback_copy(theme, category, with_demand, multi=len(img_urls) > 1)
        base_url, api_key = llm_gw["url"], llm_gw["key"]
        model = await _chat_model()
    if img_urls and not vision_model:
        logger.info("未配置 gen.vision_model,参考画面被忽略,按纯文本生成文案")

    draft_lines = []
    if subtitle and (subtitle or "").strip() != theme:
        draft_lines.append(f"副标题草稿:{subtitle}")
    if script:
        draft_lines.append(f"口播草稿:{script}")
    user_content = (
        f"文案主题:{theme}\n行业分类:{category}\n"
        + _role_line(roles)
        + ("\n".join(draft_lines) if draft_lines else "用户未提供更多参考,请围绕主题从零创作")
    )
    if use_vision:
        subjects: Dict[str, str] = {}
        try:
            subjects = await classify_subjects(img_urls, roles) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[ai_copy] 素材识别失败(不影响文案生成): {exc}")
        user_content += _grounding_line(subjects, roles)
        if len(img_urls) > 1:
            user_content += VISION_HINT_MULTI_DRAFT if draft_lines else VISION_HINT_MULTI
        else:
            user_content += VISION_HINT_WITH_DRAFT if draft_lines else VISION_HINT_NO_DRAFT
        user_content += VISION_GROUND_RULES
        content: List[Dict] = [{"type": "text", "text": user_content}]
        content += [{"type": "image_url", "image_url": {"url": u}} for u in img_urls]
        user_message: Dict = {"role": "user", "content": content}
    else:
        user_message = {"role": "user", "content": user_content}

    system_content = _merchant_copy_system(with_demand)
    payload: Dict[str, object] = {
        "model": model,
        "messages": [{"role": "system", "content": system_content}, user_message],
        "temperature": 0.9,
    }

    types_task = None
    if use_vision and with_demand:
        try:
            types_task = asyncio.create_task(classify_material_types(img_urls, roles))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[ai_copy] 类型识别并行任务创建失败(不影响文案): {exc}")
            types_task = None
    if not use_vision:
        payload["enable_thinking"] = False
    elif "doubao" in str(model).lower():
        payload["thinking"] = {"type": "disabled"}

    extra_body: Dict[str, object] = {}
    if use_vision:
        if "doubao" in str(model).lower():
            extra_body["thinking"] = {"type": "disabled"}
    else:
        extra_body["enable_thinking"] = False
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"), timeout=45 if use_vision else 30)
        resp = await client.chat.completions.create(
            model=model,
            messages=payload["messages"],
            temperature=payload.get("temperature", 0.9),
            extra_body=extra_body,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"AI 文案生成失败({'图文' if use_vision else '纯文本'}),降级为兜底模板: {exc}")
        return fallback_copy(theme, category, with_demand, multi=len(img_urls) > 1)

    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"AI 文案返回格式异常,降级为兜底模板: {text[:200]}")
        return fallback_copy(theme, category, with_demand, multi=len(img_urls) > 1)

    result: Dict[str, str] = {
        "title": str(data.get("title", ""))[:20],
        "subtitle": str(data.get("subtitle", ""))[:30],
        "script": str(data.get("script", ""))[:50],
        "fallback": False,
        "vision": use_vision,
    }
    if with_demand:
        if use_vision:
            result["subject"] = str(data.get("subject", ""))[:40]
            demand = str(data.get("demand", "")).strip()[:90]
            if not demand:
                demand = _build_demand_fallback(roles)
        else:
            result["subject"] = ""
            demand = _build_demand_fallback(roles)
        result["demand"] = demand
    if types_task is not None:
        try:
            result["material_types"] = await types_task
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[ai_copy] 逐图类型识别失败(不影响文案与生成): {exc}")
            result["material_types"] = {}
    else:
        result["material_types"] = {}
    return result
