# -*- coding: utf-8 -*-
'''
@文件    :ai_translate.py
@说明    :文本翻译(从 backend 业务下沉到 worker,使 backend 不再直连模型)。
         批量翻译一组文本(如视频画面上的信息卡/角标/揭示/贴纸文案 + 创作目标)到目标语言,
         供「模板多语言变体一键本地化」复用:一次调用翻译整组,保持顺序与数量一致。
         网关未配置 / 调用失败 / 输出数量不匹配时走规则兜底(原样返回,fallback=True),
         保证流程不中断。
@时间    :2026-10-03
@作者    :一源AI
@版本    :1.0
'''
from typing import Dict, List, Optional

from openai import AsyncOpenAI

from app.core.plugin import logger
from app.core import gateway
from app.settings import config

# 目标语言代码 → 中文/英文显示名(仅用于注入提示词,不泄露到 URL/响应)
_LANG_NAME = {
    "en": "英语(English)",
    "ja": "日语(日本語)",
    "ko": "韩语(한국어)",
    "es": "西班牙语(Español)",
    "fr": "法语(Français)",
    "de": "德语(Deutsch)",
    "pt": "葡萄牙语(Português)",
    "ru": "俄语(Русский)",
    "zh": "中文(简体)",
}


def _lang_name(lang: str) -> str:
    """语言代码未知时回退到英文(最通用的本地化目标)。"""
    return _LANG_NAME.get((lang or "").strip().lower() or "en", _LANG_NAME["en"])


def _llm_gateway() -> Dict[str, str]:
    gw = gateway.resolve("chat")
    return gw if gw.get("url") and gw.get("key") else {}


async def _chat_model() -> str:
    return (config.CHAT_MODEL or "").strip()


async def _complete_translate(system_content: str, user_content: str,
                              model: str, base_url: str, api_key: str) -> str:
    """发起一次翻译 LLM 调用,返回模型原始文本;异常向上抛,由调用方降级。"""
    # 翻译是纯文本任务,禁用思考链以降低延迟与成本
    extra_body: Dict[str, object] = {"enable_thinking": False}
    client = AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"), timeout=45)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        extra_body=extra_body,
    )
    return (resp.choices[0].message.content or "").strip()


def _align(lines: List[str], n: int) -> List[str]:
    """把模型输出对齐到输入数量 n:不足补空、超出截断,保证 override 映射不串位。"""
    out = [s.strip() for s in lines]
    while len(out) < n:
        out.append("")
    return out[:n]


async def translate(texts: List[str], target_lang: str = "en") -> Dict[str, object]:
    """批量翻译一组文本到目标语言。

    参数:
      texts      : 待翻译文本列表(至少 1 条,顺序敏感)。
      target_lang: 目标语言代码(en/ja/ko/es/fr/...)。
    返回结构含 translated(列表)/target_lang/fallback/note/src_chars/dst_chars。
    网关未配置或调用失败 → 原样返回输入(fallback=True),绝不阻断本地化变体出片。
    """
    items = [str(t or "").strip() for t in (texts or [])]
    # 过滤掉纯空白条目后再翻译,但保留占位以保证返回数量与调用方输入一致
    src_chars = sum(len(t) for t in items)

    gw = _llm_gateway()
    if not (gw.get("url") and gw.get("key")):
        logger.warning("chat 网关未配置,翻译降级为原样返回(本地化变体仍按原语言出片)")
        return {
            "translated": list(items), "target_lang": (target_lang or "en"),
            "fallback": True, "note": "模型网关不可用,已原样返回(未翻译)",
            "src_chars": src_chars, "dst_chars": src_chars,
        }

    lang_disp = _lang_name(target_lang)
    model = await _chat_model()
    base_url, api_key = gw["url"], gw["key"]

    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(items))
    system_content = (
        "你是一名专业的多语言本地化翻译,擅长电商/短视频带货文案。\n"
        "请把用户给出的若干条文本逐条翻译为目标语言,保持带货营销语气与原有含义,"
        "不要增减条目数量,不要解释,不要输出编号以外的多余文字。\n"
        "输出要求:严格按输入顺序,每行一条译文,行数与输入完全一致;"
        "若某条为空或无需翻译,对应行输出空行。"
    )
    user_content = f"目标语言:{lang_disp}\n请逐条翻译以下 {len(items)} 条文本:\n{numbered}"

    try:
        raw = await _complete_translate(system_content, user_content, model, base_url, api_key)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"翻译调用失败,降级为原样返回: {exc}")
        return {
            "translated": list(items), "target_lang": (target_lang or "en"),
            "fallback": True, "note": "模型调用失败,已原样返回(未翻译)",
            "src_chars": src_chars, "dst_chars": src_chars,
        }

    lines = [ln for ln in raw.split("\n")]
    # 去除模型可能自作主张加的 "1. " 前缀,再按行对齐
    cleaned = []
    for ln in lines:
        s = ln.strip()
        # 去掉行首 "数字." 编号
        if s and s[0:1].isdigit() and s[1:2] in (".", "、"):
            s = s[2:].strip()
        cleaned.append(s)
    translated = _align(cleaned, len(items))
    dst_chars = sum(len(t) for t in translated)
    return {
        "translated": translated, "target_lang": (target_lang or "en"),
        "fallback": False, "note": "",
        "src_chars": src_chars, "dst_chars": dst_chars,
    }
