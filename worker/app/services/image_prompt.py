# -*- coding: utf-8 -*-
'''
@文件    :image_prompt.py
@说明    :AI 图片提示词生成(从口播/旁白生成英文图片提示词)。
         复用 worker 自有 image-generation 技能资产(build_image_generation_prompt /
         build_style_conversion_prompt / apply_image_prefix / parse_image_prompts),
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
    build_style_conversion_prompt,
    parse_image_prompts,
)


def _chat_model() -> str:
    """取文本生成模型名(图片提示词是文本 LLM 任务,走 chat 网关)"""
    return (config.CHAT_MODEL or "").strip()


def _llm_gateway() -> dict:
    """解析 chat 网关;未配置完整 url/key 时返回空字典,由调用方降级"""
    gw = gateway.resolve("chat")
    return gw if gw.get("url") and gw.get("key") else {}


async def generate(
    narrations: List[str],
    style: Optional[str] = None,
    min_words: int = 50,
    max_words: int = 100,
) -> List[str]:
    """从口播/旁白列表生成英文图片提示词(逐条对应),复用 image-generation 技能资产。

    风格描述(可选)经 build_style_conversion_prompt 转英文前缀,再用 apply_image_prefix 拼到每条前面。
    网关未配置 / 调用失败 / 格式异常时返回空列表(由调用方降级,不中断主流程)。
    """
    narrations = [str(n).strip() for n in (narrations or []) if str(n or "").strip()]
    if not narrations:
        return []

    gw = _llm_gateway()
    if not (gw.get("url") and gw.get("key")):
        logger.warning("LLM 网关未配置,图片提示词生成降级为空")
        return []
    base_url, api_key = gw["url"], gw["key"]
    model = await _chat_model()
    if not model:
        logger.warning("CHAT_MODEL 未配置,图片提示词生成降级为空")
        return []

    # 系统提示由 image-generation 技能资产装配(口播 → 英文图片提示词,要求 JSON image_prompts)
    system_prompt = build_image_generation_prompt(
        narrations, min_words=min_words, max_words=max_words
    )
    user_prompt = "请根据系统提示中的口播内容,严格按要求的 JSON 格式输出对应数量的英文图片提示词。"
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

    # 可选风格前缀:把任意语言风格描述转成英文图片提示词前缀,拼到每条前面
    style_prefix = ""
    if style and str(style).strip():
        style_prefix = build_style_conversion_prompt(str(style).strip())
    if style_prefix:
        prompts = [apply_image_prefix(p, style_prefix) for p in prompts]
    return prompts
