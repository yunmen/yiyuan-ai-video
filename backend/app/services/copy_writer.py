# -*- coding: utf-8 -*-
'''
@文件    :copy_writer.py
@说明    :AI 文案生成/润色 — 按模板风格生成短视频三段文案(大标题/副标题/口播),
          用户不会写 prompt 也能一键得到可用文案;
          网关未配置/调用失败/格式异常时返回行业兜底文案,保证流程不中断。
@时间    :2026/09/20 08:05:00
@作者    :一源AI
@版本    :1.1
'''
import json
from typing import Dict, List, Optional

import httpx
from loguru import logger

from app.cruds.system_config import crud as config_crud
from app.settings import config

SYSTEM_PROMPT = (
    "你是短视频营销文案专家,为本地商家生成抖音/快手风格的带货视频文案。"
    "严格输出 JSON(不要 markdown 代码块),字段:"
    '{"title": "视频大标题,≤20字,有钩子",'
    ' "subtitle": "副标题/卖点,≤30字,突出利益点",'
    ' "script": "口播文案,≤50字,口语化有行动号召"}。'
    "以「文案主题」为创作核心;用户提供的其他字段草稿可作为卖点参考融入,"
    "但不要照抄,要围绕主题重新组织出有钩子、有利益点的成稿。"
)

# 「画面要求」草稿:用户不会写提示词时,由模型按识别结果给出**可直接改**的画面指令。
# 只在 with_demand=True 时请求,避免污染原有三段文案调用方的输出契约。
DEMAND_HINT = (
    "\n另外请在 JSON 中追加两个字段:"
    ' "subject": "素材里的主体是什么,≤40字;若同时有人物与产品,写成『人物:xx;产品:yy』",'
    ' "demand": "画面要求,≤90字,必须写成可直接执行的画面指令,形如'
    '『把参考视频里的原人物换成上传图第1张的人物(外观/服饰保持一致),'
    '把原商品换成上传图第2张的商品(包装与文字一并替换),其余场景、运镜与节奏严格保持原样』。'
    '要求:同时有**人物与产品**时,两者都要分别写清替换对象与保持要求;'
    '只描述画面怎么改,不要写成口播台词或营销话术"。'
)

# 兜底的画面要求模板:模型不可用时也要让用户看到"可改的起点",而不是空框
FALLBACK_DEMAND = (
    "把参考视频中的主体替换为上传图中的主体,保持外观一致;"
    "其余场景、构图、运镜与节奏严格保持原样"
)
FALLBACK_DEMAND_MULTI = (
    "把参考视频中的原人物换成上传的人物形象图,把原商品换成上传的产品图"
    "(含包装文字与标识一并替换),其余场景、构图、运镜与节奏严格保持原样"
)


def _build_demand_fallback(roles: Optional[List[str]]) -> str:
    """模型没回 demand 时的兜底画面要求:按素材角色说明替换哪些元素。

    视觉模型在带图推理时经常漏掉系统提示里追加的 subject/demand 字段,
    与其让前端「画面要求」输入框空着、用户以为功能失效,不如按上传素材的
    角色(产品/人物/场景)给一条可改的起点;没有任何角色标注时回退通用兜底。
    """
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

# 视觉提示词:带参考画面时的补充说明,直接决定"文案是否与视频内容相符"
VISION_HINT_WITH_DRAFT = (
    "\n参考画面:消息里附上了用户参考视频的关键画面。请先看清画面里的主体、场景与风格,"
    "再与用户草稿结合润色 —— 文案必须与画面相符,不要写成与该画面无关的行业套话。"
)
VISION_HINT_NO_DRAFT = (
    "\n参考画面:消息里附上了用户参考视频的关键画面。用户未填文案,"
    "请完全依据画面内容(主体是什么、什么场景、什么风格)从零创作,不要套用行业模板。"
)
# 多图素材提示词:用户可能**同时上传人物形象图与产品图**(真人出镜 + 手上拿产品)。
# 只描述其中一方、或把多张图当成"一张画面"整体看,都会漏掉另一半信息。
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
# 角色标注:前端知道每张图是"产品图/人物图/场景图",直接告诉模型能少猜一次
ROLE_LABELS = {"person": "人物形象图", "product": "产品图", "scene": "场景图"}


def _role_line(roles: Optional[List[str]]) -> str:
    """把前端标注的素材角色转成一行提示(顺序与图片顺序一致);没标注则返回空串"""
    names = [ROLE_LABELS.get(str(r or "").strip().lower()) for r in (roles or [])]
    names = [n for n in names if n]
    if not names:
        return ""
    return "素材图顺序与角色:" + "、".join(f"第{i + 1}张={n}" for i, n in enumerate(names)) + "\n"
# 最多喂几张画面:画面越多 token 越贵,3 张已足够判断主体与风格
MAX_VISION_IMAGES = 3

# 行业兜底文案模板:{template} 会被模板标题替换
# AI 网关未配置/超时/返回异常时按行业分类取用,保证用户始终拿到可用文案
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
# 未匹配到行业时的通用兜底
FALLBACK_DEFAULT: Dict[str, str] = {
    "title": "{template}值得一试",
    "subtitle": "品质之选,不负期待",
    "script": "好内容值得被看见,感兴趣的朋友点赞关注,我们下期见!",
}


def fallback_copy(template_title: str, category: str, with_demand: bool = False,
                  multi: bool = False) -> Dict[str, str]:
    """按行业分类返回兜底文案,返回结构带 fallback=True 供前端区分提示

    multi=True(用户传了多张素材,如人物图+产品图)时,给一条同时覆盖人物与产品的
    「画面要求」兜底 —— 模型不可用也不要让用户对着空白框发呆。
    """
    tpl = FALLBACK_COPY.get(category, FALLBACK_DEFAULT)
    theme = (template_title or "本期推荐").strip()
    result: Dict[str, str] = {
        "title": tpl["title"].format(template=theme)[:20],
        "subtitle": tpl["subtitle"].format(template=theme)[:30],
        "script": tpl["script"].format(template=theme)[:50],
        "fallback": True,
    }
    if with_demand:
        # 字段契约保持一致,避免前端按 with_demand 读取时拿到 undefined
        result["subject"] = ""
        result["demand"] = FALLBACK_DEMAND_MULTI if multi else FALLBACK_DEMAND
    return result


async def _chat_model() -> str:
    obj = await config_crud.get_by_key("gen.chat_model")
    return obj.value if obj and obj.value else "qwen3.7-max"


async def _vision_model() -> str:
    """视觉(多模态)模型名;未配置返回空 → 走纯文本,不阻断文案生成"""
    obj = await config_crud.get_by_key("gen.vision_model")
    return (obj.value or "").strip() if obj else ""


async def _named_gateway(capability: str) -> Optional[tuple]:
    """按 gen.route.<能力> 解析命名网关(gen.gw.<名>.url/.key);未配置/不完整返回 None"""
    route_obj = await config_crud.get_by_key(f"gen.route.{capability}")
    if not (route_obj and route_obj.value):
        return None
    name = route_obj.value.strip()
    url_obj = await config_crud.get_by_key(f"gen.gw.{name}.url")
    key_obj = await config_crud.get_by_key(f"gen.gw.{name}.key")
    if url_obj and url_obj.value and key_obj and key_obj.value:
        return url_obj.value, key_obj.value
    logger.warning(f"gen.route.{capability} 指向网关[{name}]但未配置完整,回退")
    return None


async def _llm_gateway() -> tuple:
    """LLM 网关地址/Key,优先级:gen.route.chat 指定的命名网关(gen.gw.<名>.url/.key)
    → 主网关 gen.llm_* → env(LLM_BASE_API_URL / LLM_BASE_API_KEY)"""
    named = await _named_gateway("chat")
    if named:
        return named
    url_obj = await config_crud.get_by_key("gen.llm_base_url")
    key_obj = await config_crud.get_by_key("gen.llm_api_key")
    url = url_obj.value if url_obj and url_obj.value else config.LLM_BASE_API_URL
    key = key_obj.value if key_obj and key_obj.value else config.LLM_BASE_API_KEY
    return url, key


async def _vision_gateway() -> tuple:
    """视觉网关:gen.route.vision 指定的命名网关 → 回退 chat 网关链路

    视觉模型往往与文本模型不在同一家(如文本走 deepseek、视觉走方舟),
    所以单独给一条路由,避免被迫把文本也切过去。
    """
    return await _named_gateway("vision") or await _llm_gateway()


async def generate(template_title: str, category: str,
                   title: Optional[str] = None, subtitle: Optional[str] = None,
                   script: Optional[str] = None,
                   images: Optional[List[str]] = None,
                   with_demand: bool = False,
                   roles: Optional[List[str]] = None) -> Dict[str, str]:
    """生成/润色三段文案。

    带参考画面(images)且已配置视觉模型时走**图文结合**:
      · 用户没填草稿 → 完全依据画面内容从零创作(否则会写出与视频无关的行业套话);
      · 用户填了草稿   → 画面与草稿结合润色。
    未配视觉模型 / 网关未配置 / 调用失败 / 格式异常 → 逐级降级(纯文本 → 行业兜底),不中断流程。
    """
    # 文案主题以用户填写内容为准:大标题 > 副标题 > 模板标题
    # (template_title 是管理端配置的模板名,仅供用户未填任何内容时兜底)
    theme = (title or "").strip() or (subtitle or "").strip() or (template_title or "").strip()

    img_urls = [u for u in (images or []) if u][:MAX_VISION_IMAGES]
    vision_model = await _vision_model() if img_urls else ""
    use_vision = bool(img_urls and vision_model)
    if use_vision:
        base_url, api_key = await _vision_gateway()
        model = vision_model
    else:
        base_url, api_key = await _llm_gateway()
        model = await _chat_model()
    if not base_url or not api_key:
        logger.warning("LLM 网关未配置,AI 文案降级为兜底模板")
        return fallback_copy(theme, category, with_demand, multi=len(img_urls) > 1)
    if img_urls and not vision_model:
        # 有画面但没有可用视觉模型:明确记一笔,便于排查"文案为何没参考画面"
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
        if len(img_urls) > 1:
            # 多张素材图 → 明确要求"人物与产品结合",避免只写其中一方
            user_content += VISION_HINT_MULTI_DRAFT if draft_lines else VISION_HINT_MULTI
        else:
            user_content += VISION_HINT_WITH_DRAFT if draft_lines else VISION_HINT_NO_DRAFT
        content: List[Dict] = [{"type": "text", "text": user_content}]
        content += [{"type": "image_url", "image_url": {"url": u}} for u in img_urls]
        user_message: Dict = {"role": "user", "content": content}
    else:
        user_message = {"role": "user", "content": user_content}

    system_content = SYSTEM_PROMPT + (DEMAND_HINT if with_demand else "")
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_content}, user_message],
        "temperature": 0.9,
    }
    if not use_vision:
        # 短文案不需要推理:开启思考会生成上千 token 的思考链,耗时飙到 10~30s
        # (实测关闭后 14.7s → 2.6s,且 JSON 合规率 9/9)。
        # 视觉模型多为方舟系,不认这个参数,故仅在纯文本链路携带。
        payload["enable_thinking"] = False

    try:
        async with httpx.AsyncClient(timeout=45 if use_vision else 30) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"AI 文案生成失败({'图文' if use_vision else '纯文本'}),降级为兜底模板: {exc}")
        return fallback_copy(theme, category, with_demand, multi=len(img_urls) > 1)

    # 兼容模型偶发输出 markdown 代码块
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
        # 是否用了参考画面:前端可据此提示"文案已结合画面",也便于排查
        "vision": use_vision,
    }
    if with_demand:
        # 识别到的主体 + 可直接改的画面要求草稿(前端预填「画面要求」输入框)
        # subject 放宽到 40 字:同时含人物与产品时(『人物:xx;产品:yy』)20 字装不下;
        # demand 放宽到 90 字:人物与产品都要写清"替换对象 + 保持要求",60 字经常被截断
        result["subject"] = str(data.get("subject", ""))[:40]
        demand = str(data.get("demand", "")).strip()[:90]
        if not demand:
            # 视觉模型带图推理时常漏掉追加的 demand 字段(系统提示要求了也没回),
            # 若直接留空,前端「画面要求」预填为空、用户以为功能失效。
            # 这里按素材角色补一条兜底画面要求,保证前端始终有可改起点。
            demand = _build_demand_fallback(roles)
        result["demand"] = demand
    return result
