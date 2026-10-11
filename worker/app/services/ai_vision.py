# -*- coding: utf-8 -*-
'''
@文件    :ai_vision.py
@说明    :商品/参考图视觉识别(从 backend/app/services/product_vision.py 迁至 worker,
         使 backend 不再直连模型)。纯 LLM 识别 + 解析 + 降级,任何失败返回空字典/空串,不阻断建单。
         网关走 worker 既有命名网关路由(gateway.resolve("vision"/"chat")),
         模型名取自 worker 配置(config.VISION_MODEL / config.CHAT_MODEL,由 backend 热更新同步)。
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from typing import Any, Dict, List, Optional

from openai import APIStatusError, AsyncOpenAI

from app.core.plugin import logger
from app.core import gateway
from app.settings import config


# 识别提示词:只要商品本身的信息,不要营销话术(那是 ai_copy 的职责)
PRODUCT_VISION_PROMPT = (
    "这是用户要植入短视频的商品图。请用一句话客观描述画面里的**商品主体**:"
    "是什么品类、外观特征(颜色/形状/包装/上面的图文)。"
    "只输出这一句描述,不超过 40 字,不要营销话术、不要加引号或额外说明。"
)

# 与复刻八张参考图上限对齐，不能静默遗漏后续产品或角度。
MAX_PRODUCT_IMAGES = 8


async def _vision_model() -> str:
    """视觉(多模态)模型名;未配置返回空 → 走纯文本,不阻断识别"""
    return (config.VISION_MODEL or "").strip()


def _vision_gateway() -> Dict[str, str]:
    """视觉网关:gen.route.vision 指定的命名网关;未命中回退空(由调用方决定回退 chat)"""
    gw = gateway.resolve("vision")
    return gw if gw.get("url") and gw.get("key") else {}


def _llm_gateway() -> Dict[str, str]:
    """文本/视觉回退网关:gen.route.chat 指定的命名网关"""
    gw = gateway.resolve("chat")
    return gw if gw.get("url") and gw.get("key") else {}


async def _chat_model() -> str:
    return (config.CHAT_MODEL or "").strip()


def _is_model_not_found(exc: BaseException) -> bool:
    """判定是否为「模型不存在/无权限」类错误(应回退 chat 模型而非重试)。"""
    if isinstance(exc, APIStatusError) and getattr(exc, "status_code", None) == 404:
        return True
    msg = str(exc)
    return (
        "InvalidEndpointOrModel.NotFound" in msg
        or "does not exist or you do not have access" in msg
        or "model_not_found" in msg.lower()
    )


async def _post_vision(base_url: str, api_key: str, model: str, payload: Dict[str, Any]) -> str:
    """以指定网关/模型发起一次多模态识别,返回 message content 文本(不解析)

    方舟 doubao-seed 系视觉模型默认开思考链,识别短输出任务也会被上千 reasoning token
    拖到 30s 以上;用方舟的 thinking 参数(非 OpenAI 标准字段)经 extra_body 关闭,
    仅对 doubao 系模型携带,避免非方舟网关因未知参数报 400。
    """
    messages = payload.get("messages") or []
    temperature = payload.get("temperature", 0.9)
    response_format = payload.get("response_format")
    extra_body: Dict[str, Any] = {}
    if "doubao" in str(model).lower():
        extra_body["thinking"] = {"type": "disabled"}
    create_kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "extra_body": extra_body,
    }
    if response_format:
        create_kwargs["response_format"] = response_format
    client = AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"), timeout=30)
    resp = await client.chat.completions.create(**create_kwargs)
    return (resp.choices[0].message.content or "").strip()


async def _vision_chat(payload: Dict[str, Any]) -> str:
    """调用视觉模型识别,返回 message content 文本。

    若配置的视觉模型(gen.vision_model)返回 404/无权限,自动回退用 chat 模型(同为多模态)重试一次,
    保证「管理端把视觉模型配成不可达模型」时识别仍不中断。完全失败抛异常 —— 由调用方降级。
    """
    last_exc: Optional[BaseException] = None
    model = await _vision_model()
    vision_gw = _vision_gateway()
    if model and vision_gw:
        try:
            return await _post_vision(vision_gw["url"], vision_gw["key"], model, payload)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_model_not_found(exc):
                logger.warning(f"[ai_vision] 视觉模型[{model}]不可达(404/无权限),回退 chat 模型: {exc}")
            else:
                logger.warning(f"[ai_vision] 视觉模型调用失败,回退 chat 模型: {exc}")
    # 回退 chat 模型(多模态,如 deepseek-v4-1-flash)
    chat_gw = _llm_gateway()
    chat_model = await _chat_model()
    if chat_gw.get("url") and chat_gw.get("key") and chat_model:
        try:
            return await _post_vision(chat_gw["url"], chat_gw["key"], chat_model, payload)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(f"[ai_vision] chat 模型回退识别也失败: {exc}")
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("[ai_vision] 视觉与 chat 网关均未配置,无法识别")


async def vision_chat(payload: Dict[str, Any]) -> str:
    """公开的多模态识别入口:element_detect 等增强能力复用同一命名网关与回退逻辑。

    入参 payload 即 {\"messages\":[...], \"temperature\":...} 形式的 chat 请求体,
    返回模型 message content 文本(不解析)。完全失败抛异常,由调用方降级。
    """
    return await _vision_chat(payload)


async def _describe(urls: List[str]) -> str:
    """实际执行识别;失败返回空串"""
    model = await _vision_model()
    if not model:
        logger.info("[ai_vision] 未配置 gen.vision_model,跳过商品识别(商品图仍照常提交)")
        return ""
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": PRODUCT_VISION_PROMPT}]
            + [{"type": "image_url", "image_url": {"url": u}} for u in urls],
        }],
        "temperature": 0.2,
    }
    try:
        text = await _vision_chat(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_vision] 商品识别失败(不影响生成): {exc}")
        return ""

    cleaned = text.strip().strip("\"'").replace("\n", " ").strip()
    if not cleaned:
        return ""
    logger.info(f"[ai_vision] 商品识别结果: {cleaned[:60]}")
    return cleaned[:80]


async def describe_product(images: List[str]) -> str:
    """识别商品图内容并返回一句描述;任何异常都返回空串(绝不阻断建单)"""
    urls = [u for u in (images or []) if u][:MAX_PRODUCT_IMAGES]
    if not urls:
        return ""
    try:
        return await _describe(urls)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_vision] 商品识别异常(不影响生成): {exc}")
        return ""


# 类型识别提示词:判定主体类型,驱动「换人/换产品/换场景」意图路由
CLASSIFY_PROMPT = (
    "这是用户要植入或替换进短视频的参考图。请判断画面主体类型并客观描述它。\n"
    "只输出一个 JSON 对象,格式:{\"type\":\"person|product|scene|other\",\"desc\":\"一句话描述主体,不超过40字\"}。\n"
    "type 取值:person=人物/真人/头像/模特;product=商品/产品/物品/logo;scene=场景/背景/环境;other=其它或无法判断。\n"
    "不要营销话术,desc 不要加引号。"
)


async def classify_material(images: List[str]) -> Dict[str, str]:
    """识别参考图的内容与类型,返回 {desc, type}。任何异常都返回空字典(绝不阻断建单)"""
    urls = [u for u in (images or []) if u][:MAX_PRODUCT_IMAGES]
    if not urls:
        return {"desc": "", "type": ""}
    try:
        return await _classify(urls)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_vision] 参考图识别异常(不影响生成): {exc}")
        return {"desc": "", "type": ""}


async def _classify(urls: List[str]) -> Dict[str, str]:
    """实际执行类型+描述识别;失败返回空字典"""
    model = await _vision_model()
    if not model:
        return {"desc": "", "type": ""}
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": CLASSIFY_PROMPT}]
            + [{"type": "image_url", "image_url": {"url": u}} for u in urls],
        }],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    try:
        text = await _vision_chat(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_vision] 参考图识别失败(不影响生成): {exc}")
        return {"desc": "", "type": ""}
    return _parse_classify(text)


def _parse_classify(text: str) -> Dict[str, str]:
    """解析识别返回的 JSON;解析失败或返回非对象时退回按商品图处理"""
    import json as _json

    try:
        obj = _json.loads(text)
    except Exception:  # noqa: BLE001
        cleaned = text.strip().strip("\"'").replace("\n", " ").strip()[:80]
        return {"desc": cleaned, "type": "product"}
    if not isinstance(obj, dict):
        cleaned = str(obj).strip().strip("\"'").replace("\n", " ").strip()[:80]
        return {"desc": cleaned, "type": "product"}
    desc = str(obj.get("desc") or "").strip().strip("\"'").replace("\n", " ").strip()[:80]
    t = str(obj.get("type") or "").strip().lower()
    if t not in ("person", "product", "scene", "other"):
        t = "product"
    return {"desc": desc, "type": t}


# ---- 多图分组识别:人物形象图 / 产品图 / 场景图 分别出描述 ----
SUBJECT_PROMPT = (
    "这是用户要植入或替换进短视频的参考图,可能同时包含多张(人物形象图 / 产品图 / 场景图)。\n"
    "请逐张看清后**按角色归纳**,只输出一个 JSON 对象:\n"
    '{"person": "人物主体的外观描述(没有人物则空串)",'
    ' "product": "产品主体的外观描述(没有产品则空串)",'
    ' "scene": "场景/环境描述(没有场景则空串)",'
    ' "primary": "person|product|scene|other(最主要的那个)"}\n'
    "描述要客观具体:品类、颜色、形状、材质、服饰/发型、包装上的图文等。"
    "**只描述主体自身的特征,不要描述主体所在的背景/环境/道具/摆设**"
    "(实测:狗照里露出的庭院、红漆木门、铜门环被写进人物描述后,会被下游当成成片场景,污染画面);"
    "没有对应主体就留空串,不要为了凑字段硬编。"
    "**人物描述必须写出面部特征**:脸型与轮廓线条、眉形/眼型/眼色/鼻型/唇形、发型与发色、肤色、"
    "妆造、年龄段与性别、体态 —— 这是下游「换人物」时锁定脸部一致性的**唯一依据**;"
    "只写发型服饰而略过五官时,模型会拿不到任何脸部约束并自由发挥,成片主角的脸必然与参考图对不上"
    "(脸型/五官是辨识同一人的关键,发型服饰不足以锁定)。"
    "产品与场景每条不超过40字,人物可到60字(五官细节需要更多字),不要营销话术,不要加引号。"
)

VALID_ROLES = ("person", "product", "scene")
ALLOWED_TYPES = ("person", "product", "scene", "other")
ROLE_LABELS = {"person": "人物形象图", "product": "产品图", "scene": "场景图"}


def _empty_subjects() -> Dict[str, str]:
    """字段契约保持一致:任何失败都返回空串而不是缺键,调用方无需做 None 判断"""
    return {"person": "", "product": "", "scene": "", "type": "", "desc": ""}


async def classify_material_types(images: List[str], roles: Optional[List[str]] = None) -> Dict[str, str]:
    """逐图中立识别真实主体类型,返回 {role: type}(role∈person/product/scene)。

    不带角色提示,只问"这张图到底是什么",才能戳穿"用户把狗标成人物的误标"。
    供调用方在「换人物/换产品/换场景」前校验参考图名副其实。逐张识别,任何异常/未知角色跳过。
    """
    urls = [u for u in (images or []) if u][:MAX_PRODUCT_IMAGES]
    role_list = [str(r or "").strip().lower() for r in (roles or [])][:len(urls)]
    result: Dict[str, str] = {}
    for url, role in zip(urls, role_list):
        if role not in ("person", "product", "scene"):
            continue
        try:
            info = await classify_material([url])
            t = (info or {}).get("type") or ""
            if t:
                result[role] = t
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[ai_vision] 逐图类型识别异常(不影响生成): {exc}")
    return result


async def classify_subjects(images: List[str], roles: Optional[List[str]] = None) -> Dict[str, str]:
    """多图分组识别:返回 {person, product, scene, type, desc}

    一次调用即可拿到"人物长什么样 + 产品长什么样",供提示词分段注入与文案生成使用。
    任何异常都返回空字典,绝不阻断建单。
    """
    urls = [u for u in (images or []) if u][:MAX_PRODUCT_IMAGES]
    if not urls:
        return _empty_subjects()
    role_list = [str(r or "").strip().lower() for r in (roles or [])][:len(urls)]
    try:
        return await _classify_subjects(urls, role_list)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_vision] 多图识别异常(不影响生成): {exc}")
        return _empty_subjects()


def _role_hint(roles: List[str]) -> str:
    """把前端标注的角色转成一行提示(顺序与图片顺序一致);没标注则返回空串"""
    names = [ROLE_LABELS.get(r) for r in roles]
    names = [n for n in names if n]
    if not names:
        return ""
    return "已知素材图角色:" + "、".join(
        f"第{i + 1}张={n}" for i, n in enumerate(names)
    ) + "。请据此归类,不要改判角色。\n"


async def _classify_subjects(urls: List[str], roles: List[str]) -> Dict[str, str]:
    """实际执行多图分组识别;失败返回空字典"""
    model = await _vision_model()
    if not model:
        return _empty_subjects()
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": _role_hint(roles) + SUBJECT_PROMPT}]
            + [{"type": "image_url", "image_url": {"url": u}} for u in urls],
        }],
        "temperature": 0.2,
    }
    try:
        text = await _vision_chat(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[ai_vision] 多图识别失败(不影响生成): {exc}")
        return _empty_subjects()
    result = _parse_subjects(text)
    logger.info(
        f"[ai_vision] 多图识别结果: person={result['person'][:20]} "
        f"product={result['product'][:20]} scene={result['scene'][:20]}"
    )
    return result


def _clean_field(value) -> str:
    return str(value or "").strip().strip("\"'").replace("\n", " ").strip()[:80]


def _parse_subjects(text: str) -> Dict[str, str]:
    """解析多图分组识别结果;JSON 不合规时退回单主体解析,保证仍能注入一段描述"""
    import json as _json

    try:
        obj = _json.loads(text)
    except Exception:  # noqa: BLE001
        obj = None
    if not isinstance(obj, dict):
        single = _parse_classify(text)
        result = _empty_subjects()
        role = single["type"] if single["type"] in VALID_ROLES else "product"
        result[role] = single["desc"]
        result["type"] = single["type"]
        result["desc"] = single["desc"]
        return result

    result = _empty_subjects()
    for role in VALID_ROLES:
        result[role] = _clean_field(obj.get(role))
    primary = str(obj.get("primary") or "").strip().lower()
    if primary not in ALLOWED_TYPES:
        primary = next((r for r in VALID_ROLES if result[r]), "other")
    result["type"] = primary
    result["desc"] = result.get(primary) or next(
        (result[r] for r in VALID_ROLES if result[r]), ""
    )
    return result
