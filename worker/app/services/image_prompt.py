# -*- coding: utf-8 -*-
'''
@文件    :image_prompt.py
@说明    :AI 图片提示词生成(从口播/旁白生成中文图片提示词)。
         复用 worker 自有 image-generation 技能资产(build_image_generation_prompt /
         apply_image_prefix / parse_image_prompts),
         去除对 backend 的依赖;大模型调用经 worker 网关,backend 不再直连模型。
         结果经 ARQ 任务回传并写入 Redis(键 ai_image_prompt:{job_id}),供 backend 轮询。
@时间    :2026/09/30
@作者    :一源AI
@版本    :1.0
'''
from typing import List, Optional

from openai import AsyncOpenAI

from app.core.plugin import logger
from app.core import gateway
from app.settings import config
from skills.prompt_library import (
    apply_image_prefix,
    build_image_generation_prompt,
    parse_image_prompts,
)


async def _chat_model() -> str:
    """取文本生成模型名(图片提示词是文本 LLM 任务,走 chat 网关)

    必须声明为 async:与 ai_copy._chat_model / ai_vision._chat_model 保持同一约定,
    generate() 内部以 `await _chat_model()` 取值。若改回同步 def,await 会抛
    `TypeError: object str can't be used in 'await' expression`,
    技能在进入模型调用之前就失败(图片提示词直接空掉)。
    """
    return (config.CHAT_MODEL or "").strip()


def _llm_gateway() -> dict:
    """解析 chat 网关;未配置完整 url/key 时返回空字典,由调用方降级"""
    gw = gateway.resolve("chat")
    return gw if gw.get("url") and gw.get("key") else {}


def _vision_gateway() -> dict:
    """解析 vision 网关;未配置完整 url/key 时返回空字典(参考条件化不可用,退回纯文本)"""
    gw = gateway.resolve("vision")
    return gw if gw.get("url") and gw.get("key") else {}


# 参考条件化提示词:要求模型把参考帧的"商品形态/人物样貌/配色/镜头关系"带进每条图提示词,
# 让复刻出的画面在视觉上与原片一致(Hypit 的 reference-conditioned generation 思想)。
_REFERENCE_PROMPT = (
    "下面是同一段带货参考视频抽出的几帧画面。请结合这些画面生成图片提示词:"
    "保留参考画面里真实的商品形态、人物样貌、配色与镜头关系(景别/角度/构图),"
    "只把口播对应的内容替换成新文案要表达的主体,不要凭空改变原片的视觉风格。"
    "严格按要求的 JSON 格式输出与口播条数一致的中文图片提示词。"
)


async def _generate_reference_conditioned(
    narrations: List[str],
    reference_images: List[str],
    min_words: int,
    max_words: int,
) -> List[str]:
    """参考条件化生成:把参考帧作为视觉上下文喂给多模态模型,产出"长得像原片"的图片提示词。

    仅当 vision 网关可用时调用;任何失败返回空列表,由 generate 退回纯文本路径(不阻断主流程)。
    """
    gw = _vision_gateway()
    if not gw:
        return []
    vision_model = str(getattr(config, "VISION_MODEL", "") or "").strip()
    if not vision_model:
        return []
    # 系统提示仍由 image-generation 技能资产装配(口播 → 中文图片提示词, JSON image_prompts)
    system_prompt = build_image_generation_prompt(
        narrations, min_words=min_words, max_words=max_words
    )
    content: List[dict] = [{"type": "text", "text": _REFERENCE_PROMPT}]
    for url in reference_images[:4]:  # 最多 4 帧,避免 prompt 过长拖慢/超 token
        content.append({"type": "image_url", "image_url": {"url": url, "detail": "low"}})
    content.append({"type": "text", "text": system_prompt})
    try:
        client = AsyncOpenAI(
            api_key=gw["key"], base_url=str(gw["url"]).rstrip("/"), timeout=60
        )
        resp = await client.chat.completions.create(
            model=vision_model,
            messages=[{"role": "user", "content": content}],
            temperature=0.6,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"参考条件化图提示词生成失败,退回纯文本路径: {exc}")
        return []
    return parse_image_prompts(text)


async def generate(
    narrations: List[str],
    style: Optional[str] = None,
    min_words: int = 50,
    max_words: int = 100,
    reference_images: Optional[List[str]] = None,
) -> List[str]:
    """从口播/旁白列表生成中文图片提示词(逐条对应),复用 image-generation 技能资产。

    参考条件化(成片效果最佳):传入 reference_images(参考视频抽帧 URL)时,优先用多模态视觉模型
    把原片的商品形态/人物样貌/配色/镜头关系带进提示词,使复刻画面视觉上与原片一致
    (对齐 Hypit 的 reference-conditioned generation)。vision 网关不可用 / 无参考帧 / 调用失败
    时自动退回纯文本路径,行为与改造前一致。

    风格描述(可选,用户输入本身是中文)直接作为前缀拼到每条前面,不再额外转英文
    (此前转英文既多一次 LLM 调用,转换结果还经常偏离输入的风格)。
    网关未配置 / 调用失败 / 格式异常时返回空列表(由调用方降级,不中断主流程)。
    """
    narrations = [str(n).strip() for n in (narrations or []) if str(n or "").strip()]
    if not narrations:
        return []

    # 参考条件化优先:有参考帧且视觉网关可用时,让提示词"长得像原片"
    if reference_images:
        conditioned = await _generate_reference_conditioned(
            narrations, list(reference_images), min_words, max_words
        )
        if conditioned:
            logger.info(
                f"[image_prompt] 参考条件化生成 {len(conditioned)} 条图提示词"
            )
            prompts = conditioned
            style_prefix = _build_style_prefix(style)
            return [apply_image_prefix(p, style_prefix) for p in prompts] if style_prefix else prompts

    gw = _llm_gateway()
    if not (gw.get("url") and gw.get("key")):
        logger.warning("LLM 网关未配置,图片提示词生成降级为空")
        return []
    base_url, api_key = gw["url"], gw["key"]
    model = await _chat_model()
    if not model:
        logger.warning("CHAT_MODEL 未配置,图片提示词生成降级为空")
        return []

    # 系统提示由 image-generation 技能资产装配(口播 → 中文图片提示词,要求 JSON image_prompts)
    system_prompt = build_image_generation_prompt(
        narrations, min_words=min_words, max_words=max_words
    )
    user_prompt = "请根据系统提示中的口播内容,严格按要求的 JSON 格式输出对应数量的中文图片提示词,每条提示词必须使用中文。"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
    }
    # 纯文本任务禁用思考链,与 ai_copy 的非视觉分支保持一致
    extra_body: dict = {"enable_thinking": False}
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"), timeout=30)
        resp = await client.chat.completions.create(
            model=model,
            messages=payload["messages"],
            temperature=payload.get("temperature", 0.8),
            extra_body=extra_body,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"AI 图片提示词生成失败,降级为空: {exc}")
        return []

    # 解析模型输出的 JSON image_prompts;解析不出则降级为空,不中断主流程
    prompts = parse_image_prompts(text)
    if not prompts:
        logger.warning(f"AI 图片提示词返回格式异常,降级为空: {text[:200]}")
        return []

    # 可选风格前缀:用户输入的风格描述(中文)直接拼到每条提示词前面
    style_prefix = _build_style_prefix(style)
    if style_prefix:
        prompts = [apply_image_prefix(p, style_prefix) for p in prompts]
    return prompts


def _build_style_prefix(style: Optional[str]) -> str:
    """把用户输入的风格描述(中文)作为图片提示词前缀(空则返回空串)

    提示词产物已是中文,风格描述同样是中文,直接拼接即可:
    此前"经 LLM 转英文前缀"既多一次模型调用(更慢更贵),转换结果还经常
    偏离输入风格(如"清新日系"被转成"Enigmatic surrealism"),故移除。
    """
    if not style or not str(style).strip():
        return ""
    return str(style).strip()
