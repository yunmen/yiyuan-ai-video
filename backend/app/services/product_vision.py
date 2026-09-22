# -*- coding: utf-8 -*-
'''
@文件    :product_vision.py
@说明    :商品图识别 — 让提示词拿到商品的**文字语义**
@时间    :2026/09/22 08:30:00
@作者    :一源AI
@版本    :1.0
@说明    :为什么要这一步——
          商品图此前只作为 reference_image 原样提交,系统对"这是什么商品"一无所知,
          prompt 只能写"把主体换成商品图里的东西"这种泛指指令,替换准不准全靠模型自己认图
          (实测成片里原商品长期没被换掉)。
          这里先识别一次,把描述写进 prompt 的 [商品信息] 段,形成「图片 + 文字」双通道。

          任何失败(未配视觉模型 / 网关异常 / 返回异常)一律返回空串:
          识别是增强项,不能成为建单的关键路径。
'''
from typing import Dict, List, Optional

import httpx

from app.core.plugin import logger
from app.services.copy_writer import _vision_gateway, _vision_model

# 识别提示词:只要商品本身的信息,不要营销话术(那是 copy_writer 的职责)
PRODUCT_VISION_PROMPT = (
    "这是用户要植入短视频的商品图。请用一句话客观描述画面里的**商品主体**:"
    "是什么品类、外观特征(颜色/形状/包装/上面的图文)。"
    "只输出这一句描述,不超过 40 字,不要营销话术、不要加引号或额外说明。"
)

# 最多识别几张:商品图一般 1~3 张,再多 token 涨而信息增量很小
MAX_PRODUCT_IMAGES = 3


async def describe_product(images: List[str]) -> str:
    """识别商品图内容并返回一句描述;任何异常都返回空串(绝不阻断建单)

    连"读配置/解析网关"这类前置动作抛的异常也一并吞掉 —— 识别是增强项,
    绝不能因为它的配置问题让一次正常的建单失败。
    """
    urls = [u for u in (images or []) if u][:MAX_PRODUCT_IMAGES]
    if not urls:
        return ""
    try:
        return await _describe(urls)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[product_vision] 商品识别异常(不影响生成): {exc}")
        return ""


async def _describe(urls: List[str]) -> str:
    """实际执行识别;失败返回空串"""
    model = await _vision_model()
    if not model:
        logger.info("[product_vision] 未配置 gen.vision_model,跳过商品识别(商品图仍照常提交)")
        return ""
    base_url, api_key = await _vision_gateway()
    if not base_url or not api_key:
        logger.warning("[product_vision] 视觉网关未配置,跳过商品识别")
        return ""

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": PRODUCT_VISION_PROMPT}]
            + [{"type": "image_url", "image_url": {"url": u}} for u in urls],
        }],
        # 识别要的是稳定复现,不要发散
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[product_vision] 商品识别失败(不影响生成): {exc}")
        return ""

    # 模型偶发加引号或换行:清理成单行短句再入库
    cleaned = text.strip().strip("\"'").replace("\n", " ").strip()
    if not cleaned:
        return ""
    logger.info(f"[product_vision] 商品识别结果: {cleaned[:60]}")
    return cleaned[:80]


# 类型识别提示词:在"描述主体"之外,先判定它是人物/商品/场景/其它,
# 才能驱动后端「换人还是换产品」的意图路由(此前视觉识别只认商品,人像会被错叫商品)。
CLASSIFY_PROMPT = (
    "这是用户要植入或替换进短视频的参考图。请判断画面主体类型并客观描述它。\n"
    "只输出一个 JSON 对象,格式:{\"type\":\"person|product|scene|other\",\"desc\":\"一句话描述主体,不超过40字\"}。\n"
    "type 取值:person=人物/真人/头像/模特;product=商品/产品/物品/logo;scene=场景/背景/环境;other=其它或无法判断。\n"
    "不要营销话术,desc 不要加引号。"
)


async def classify_material(images: List[str]) -> Dict[str, str]:
    """识别参考图的内容与类型,返回 {desc, type}。任何异常都返回空字典(绝不阻断建单)

    与 describe_product 的区别:额外给出主体类型(type),供后端「换人/换产品/换场景」
    意图路由使用。识别是增强项,失败一律静默降级。
    """
    urls = [u for u in (images or []) if u][:MAX_PRODUCT_IMAGES]
    if not urls:
        return {"desc": "", "type": ""}
    try:
        return await _classify(urls)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[product_vision] 参考图识别异常(不影响生成): {exc}")
        return {"desc": "", "type": ""}


async def _classify(urls: List[str]) -> Dict[str, str]:
    """实际执行类型+描述识别;失败返回空字典"""
    model = await _vision_model()
    if not model:
        return {"desc": "", "type": ""}
    base_url, api_key = await _vision_gateway()
    if not base_url or not api_key:
        return {"desc": "", "type": ""}

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": CLASSIFY_PROMPT}]
            + [{"type": "image_url", "image_url": {"url": u}} for u in urls],
        }],
        # 识别要的是稳定复现,不要发散
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[product_vision] 参考图识别失败(不影响生成): {exc}")
        return {"desc": "", "type": ""}
    return _parse_classify(text)


def _parse_classify(text: str) -> Dict[str, str]:
    """解析识别返回的 JSON;解析失败或返回非对象时退回按商品图处理,desc 取清理后的文本"""
    import json as _json

    try:
        obj = _json.loads(text)
    except Exception:  # noqa: BLE001
        cleaned = text.strip().strip("\"'").replace("\n", " ").strip()[:80]
        return {"desc": cleaned, "type": "product"}
    # 模型偶发只返回纯字符串而非 JSON 对象:当作商品图描述兜底
    if not isinstance(obj, dict):
        cleaned = str(obj).strip().strip("\"'").replace("\n", " ").strip()[:80]
        return {"desc": cleaned, "type": "product"}
    desc = str(obj.get("desc") or "").strip().strip("\"'").replace("\n", " ").strip()[:80]
    t = str(obj.get("type") or "").strip().lower()
    if t not in ("person", "product", "scene", "other"):
        t = "product"
    return {"desc": desc, "type": t}


# ---- 多图分组识别:人物形象图 / 产品图 / 场景图 分别出描述 ----
# 为什么要分组:用户可能**同时上传人物形象图和产品图**(例如"真人出镜口播 + 手上拿着产品")。
# 只识别第一张、只给一个主体的旧实现会丢掉另一半信息,文案与提示词都只能写一半。
SUBJECT_PROMPT = (
    "这是用户要植入或替换进短视频的参考图,可能同时包含多张(人物形象图 / 产品图 / 场景图)。\n"
    "请逐张看清后**按角色归纳**,只输出一个 JSON 对象:\n"
    '{"person": "人物主体的外观描述(没有人物则空串)",'
    ' "product": "产品主体的外观描述(没有产品则空串)",'
    ' "scene": "场景/环境描述(没有场景则空串)",'
    ' "primary": "person|product|scene|other(最主要的那个)"}\n'
    "描述要客观具体:品类、颜色、形状、材质、服饰/发型、包装上的图文等。"
    "每条不超过40字,不要营销话术,不要加引号。"
)

# 角色维度与合法类型:角色用于分段注入,类型用于「换人/换产品/换场景」意图兜底
VALID_ROLES = ("person", "product", "scene")
ALLOWED_TYPES = ("person", "product", "scene", "other")
# 角色 → 中文名:用于给视觉模型标注"第N张是什么",避免它靠自己猜(实测会猜错)
ROLE_LABELS = {"person": "人物形象图", "product": "产品图", "scene": "场景图"}


def _empty_subjects() -> Dict[str, str]:
    """字段契约保持一致:任何失败都返回空串而不是缺键,调用方无需做 None 判断"""
    return {"person": "", "product": "", "scene": "", "type": "", "desc": ""}


async def classify_subjects(images: List[str], roles: Optional[List[str]] = None) -> Dict[str, str]:
    """多图分组识别:返回 {person, product, scene, type, desc}

    一次调用即可拿到"人物长什么样 + 产品长什么样",供提示词分段注入([人物信息]/[商品信息])
    与文案生成(结合人物与产品)使用。任何异常都返回空字典,绝不阻断建单。

    roles:与 images 一一对应的角色(product/person/scene,由前端标注)。
    **强烈建议传**:实测只让模型"看图判断"时,穿在庭院里的产品图会被判成 scene
    (狗照→庭院场景),角色标注能把准确率显著拉高。
    """
    urls = [u for u in (images or []) if u][:MAX_PRODUCT_IMAGES]
    if not urls:
        return _empty_subjects()
    role_list = [str(r or "").strip().lower() for r in (roles or [])][:len(urls)]
    try:
        return await _classify_subjects(urls, role_list)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[product_vision] 多图识别异常(不影响生成): {exc}")
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
    base_url, api_key = await _vision_gateway()
    if not base_url or not api_key:
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
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[product_vision] 多图识别失败(不影响生成): {exc}")
        return _empty_subjects()
    result = _parse_subjects(text)
    # loguru 用 {} 占位,不支持 stdlib 的惰性 %s 参数(否则日志会原样打印 %s)
    logger.info(
        "[product_vision] 多图识别结果: person={} product={} scene={}",
        result["person"][:20], result["product"][:20], result["scene"][:20],
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
        # 模型没给 primary:按"谁有描述就取谁"兜底(人物优先,便于驱动换人意图)
        primary = next((r for r in VALID_ROLES if result[r]), "other")
    result["type"] = primary
    result["desc"] = result.get(primary) or next(
        (result[r] for r in VALID_ROLES if result[r]), ""
    )
    return result
