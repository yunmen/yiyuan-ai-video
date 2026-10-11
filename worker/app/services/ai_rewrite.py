# -*- coding: utf-8 -*-
'''
@文件    :ai_rewrite.py
@说明    :长文「去 AI 味」改写(从 backend 业务下沉到 worker,使 backend 不再直连模型)。
         按 level(1..4,对应 Mark I–IV 改写强度)与 tone(语气)调用 chat 网关改写长文,
         消除 AI 套话与机器腔,保留原意与核心信息。
         提示词散文统一取自 worker/skills/text-rewrite/assets/rewrite_prompt.md(单一来源)。
         网关未配置 / 调用失败 / 格式异常时走规则兜底改写(去常见套话连接词、压缩重复标点),
         保证流程不中断(fallback=True 并附中文 note)。
@时间    :2026/10/03
@作者    :一源AI
@版本    :1.0
'''
from typing import Dict, Optional

from openai import AsyncOpenAI

from app.core.plugin import logger
from app.core import gateway
from app.settings import config

# —— level → 改写强度说明(注入提示词,严禁外泄到 URL/响应) —— #
_LEVEL_DESC: Dict[int, str] = {
    1: "轻度(仅微调表达):保留原文句式与段落结构,只去掉明显的 AI 套话与重复连接词,改动尽量小。",
    2: "中度(重述句子):换用更自然的连接与词汇,适度拆分过长的句子,消除排比堆砌,但整体结构不变。",
    3: "重度(重构段落):调整段落节奏与顺序,增加口语化转折,让行文更像真人书写,允许较大幅度的语句重组。",
    4: "深度(大幅口语化):在保留核心观点与全部关键信息的前提下,大幅去除教科书腔与书面机器腔,注入个人化语气,允许结构重排。",
}

# —— tone → 语气说明(注入提示词) —— #
_TONE_DESC: Dict[str, str] = {
    "natural": "自然:像普通人随手写下的口语化表达,不刻意正式也不刻意俏皮。",
    "formal": "正式:保持书面得体的语气,但去掉 AI 味的模板化表达。",
    "friendly": "亲切:像朋友间聊天的温和语气,带一点轻松感。",
    "sharp": "犀利:观点鲜明、直截了当,去掉委婉铺垫与正确的废话。",
    "humorous": "幽默:在不动原意的前提下带一点俏皮与调侃,适当使用生活化比喻。",
}

# 规则兜底要剔除的 AI 套话连接词/短语(仅做轻量清理,不调模型)
_AI_CLICHE = [
    "首先", "其次", "最后", "综上所述", "总而言之", "值得注意的是",
    "在当今社会", "随着……的发展", "随着...的发展", "不难发现", "毋庸置疑",
    "显而易见", "众所周知", "在这个", "可以说", "事实上", "本质上",
]


def _level_desc(level: int) -> str:
    """level 越界时回退到中度(2),保证提示词总有合理强度。"""
    return _LEVEL_DESC.get(int(level) if isinstance(level, (int, float)) else 2, _LEVEL_DESC[2])


def _tone_desc(tone: str) -> str:
    """tone 未知时回退自然(natural)。"""
    return _TONE_DESC.get((tone or "").strip().lower() or "natural", _TONE_DESC["natural"])


def _rule_fallback(text: str) -> str:
    """未配网关/调用失败时的规则兜底改写:去 AI 套话连接词、压缩连续重复标点。

    仅做轻量清理,不改变语义;返回 (改写文本, 原因说明)。
    """
    out = text
    for w in _AI_CLICHE:
        # 套话后若紧跟逗号/顿号则连同标点一起去掉,避免残留空标点
        out = out.replace(w + "，", "").replace(w + ",", "").replace(w + "、", "")
        out = out.replace(w, "")
    # 压缩连续重复标点(如多个逗号/句号)
    import re
    out = re.sub(r"([，。、；；])\1+", r"\1", out)
    out = re.sub(r"([.!?！？])\1+", r"\1", out)
    out = out.strip()
    return out, "模型网关不可用,已做基础去套话清理(非智能改写)"


def _llm_gateway() -> Dict[str, str]:
    gw = gateway.resolve("chat")
    return gw if gw.get("url") and gw.get("key") else {}


async def _chat_model() -> str:
    return (config.CHAT_MODEL or "").strip()


async def _complete_rewrite(system_content: str, user_content: str,
                             model: str, base_url: str, api_key: str) -> str:
    """发起一次改写 LLM 调用,返回模型原始文本;异常向上抛,由调用方降级。"""
    # 改写是纯文本任务,禁用思考链以降低延迟与成本
    extra_body: Dict[str, object] = {"enable_thinking": False}
    client = AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"), timeout=45)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.85,
        extra_body=extra_body,
    )
    return (resp.choices[0].message.content or "").strip()


def _qc_rewrite(rewritten: str, src: str) -> tuple:
    """轻量规则质检:非空、非远短于原文(防模型偷工)、非原文完全照搬。

    返回 (是否通过, 原因)。
    """
    r = (rewritten or "").strip()
    if not r:
        return False, "改写为空"
    # 允许深度口语化后长度浮动,但不得低于原文 40%(防模型只回一句)
    if len(src) >= 50 and len(r) < len(src) * 0.4:
        return False, "改写后过短,疑似未完整输出"
    return True, ""


async def rewrite_text(text: str, level: int = 2, tone: str = "natural",
                       max_chars: int = 0) -> Dict[str, object]:
    """长文去 AI 味改写。

    参数:
      text      : 待改写原文(必填)。
      level     : 1..4 改写强度(Mark I–IV)。
      tone      : 语气 natural/formal/friendly/sharp/humorous。
      max_chars : 0=不限;>0 约束输出字数上限(注入提示词)。
    返回结构含 rewritten/fallback/note/src_chars/dst_chars/level/tone。
    """
    src = (text or "").strip()
    src_chars = len(src)

    gw = _llm_gateway()
    if not (gw.get("url") and gw.get("key")):
        logger.warning("chat 网关未配置,去 AI 味改写降级为规则兜底")
        rewritten, note = _rule_fallback(src)
        return {
            "rewritten": rewritten, "level": int(level), "tone": (tone or "natural"),
            "src_chars": src_chars, "dst_chars": len(rewritten),
            "fallback": True, "note": note,
        }

    from skills.prompts import get as _get_prompt, safe_render as _safe_render

    system_content = _get_prompt("rewrite_prompt")
    if system_content is None:
        system_content_body = (
            "你是中文文本去 AI 味改写专家,在不改变原意的前提下改写为更自然的中文,"
            "去掉 AI 套话与机器腔,保留事实与核心观点。"
        )
    else:
        system_content_body = safe_render(
            "rewrite_prompt",
            "你是中文文本去 AI 味改写专家,在不改变原意的前提下改写为更自然的中文。",
            level_desc=_level_desc(level), tone_desc=_tone_desc(tone),
        )

    limit_hint = ""
    if int(max_chars or 0) > 0:
        limit_hint = f"\n输出请控制在 {int(max_chars)} 字以内(含标点)。"
    user_content = (
        f"请把下面这段原文改写成去 AI 味的中文。\n改写强度:{_level_desc(level)}\n"
        f"语气:{_tone_desc(tone)}{limit_hint}\n\n原文:\n{src}"
    )

    model = await _chat_model()
    base_url, api_key = gw["url"], gw["key"]

    # 反思环:生成 → 规则质检 → 不通过则回填意见重生成(默认 1 次重试)
    _max_retries = int(getattr(config, "REWRITE_REFLECT_MAX_RETRIES", 1) or 0)
    last_text = ""
    data = None
    for _i in range(_max_retries + 1):
        try:
            last_text = await _complete_rewrite(system_content_body, user_content, model, base_url, api_key)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"去 AI 味改写调用失败,降级为规则兜底: {exc}")
            rewritten, note = _rule_fallback(src)
            return {
                "rewritten": rewritten, "level": int(level), "tone": (tone or "natural"),
                "src_chars": src_chars, "dst_chars": len(rewritten),
                "fallback": True, "note": "模型调用失败,已做基础去套话清理",
            }
        passed, issues = _qc_rewrite(last_text, src)
        if passed:
            data = last_text
            break
        logger.warning(f"[ai_rewrite] 质检未通过(第{_i + 1}次): {issues}")
        if _i < _max_retries:
            user_content += f"\n\n[质检反馈]{issues}。请完整重写,直接输出改写文本。"

    if data is None:
        # 重试耗尽仍不达标 → 拿最后一次原始输出(尽可能不空),fallback 标记兜底
        logger.error("去 AI 味改写经重试仍不达标,返回最后产出并标记 fallback")
        data = last_text or src
        return {
            "rewritten": data, "level": int(level), "tone": (tone or "natural"),
            "src_chars": src_chars, "dst_chars": len(data),
            "fallback": True, "note": "模型产出质检未达标,已尽量返回",
        }

    return {
        "rewritten": data, "level": int(level), "tone": (tone or "natural"),
        "src_chars": src_chars, "dst_chars": len(data),
        "fallback": False, "note": "",
    }
