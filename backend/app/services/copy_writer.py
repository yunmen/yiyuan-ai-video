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
from typing import Dict, Optional

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
    "若用户给了草稿则在其基础上润色;没给则根据模板主题从零创作。"
)

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


def fallback_copy(template_title: str, category: str) -> Dict[str, str]:
    """按行业分类返回兜底文案,返回结构带 fallback=True 供前端区分提示"""
    tpl = FALLBACK_COPY.get(category, FALLBACK_DEFAULT)
    theme = (template_title or "本期推荐").strip()
    return {
        "title": tpl["title"].format(template=theme)[:20],
        "subtitle": tpl["subtitle"].format(template=theme)[:30],
        "script": tpl["script"].format(template=theme)[:50],
        "fallback": True,
    }


async def _chat_model() -> str:
    obj = await config_crud.get_by_key("gen.chat_model")
    return obj.value if obj and obj.value else "qwen3.7-max"


async def _llm_gateway() -> tuple:
    """LLM 网关地址/Key:DB 配置优先,为空回退 env(LLM_BASE_API_URL / LLM_BASE_API_KEY)"""
    url_obj = await config_crud.get_by_key("gen.llm_base_url")
    key_obj = await config_crud.get_by_key("gen.llm_api_key")
    url = url_obj.value if url_obj and url_obj.value else config.LLM_BASE_API_URL
    key = key_obj.value if key_obj and key_obj.value else config.LLM_BASE_API_KEY
    return url, key


async def generate(template_title: str, category: str,
                   title: Optional[str] = None, subtitle: Optional[str] = None,
                   script: Optional[str] = None) -> Dict[str, str]:
    """生成/润色三段文案。网关未配置、调用失败或返回格式异常时降级为行业兜底文案"""
    base_url, api_key = await _llm_gateway()
    if not base_url or not api_key:
        logger.warning("LLM 网关未配置,AI 文案降级为兜底模板")
        return fallback_copy(template_title, category)

    draft_lines = []
    if title:
        draft_lines.append(f"大标题草稿:{title}")
    if subtitle:
        draft_lines.append(f"副标题草稿:{subtitle}")
    if script:
        draft_lines.append(f"口播草稿:{script}")
    user_content = (
        f"模板主题:{template_title}\n行业分类:{category}\n"
        + ("\n".join(draft_lines) if draft_lines else "用户未提供草稿,请从零创作")
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": await _chat_model(),
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.9,
                },
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        logger.error(f"AI 文案生成失败,降级为兜底模板: {exc}")
        return fallback_copy(template_title, category)

    # 兼容模型偶发输出 markdown 代码块
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"AI 文案返回格式异常,降级为兜底模板: {text[:200]}")
        return fallback_copy(template_title, category)

    return {
        "title": str(data.get("title", ""))[:20],
        "subtitle": str(data.get("subtitle", ""))[:30],
        "script": str(data.get("script", ""))[:50],
        "fallback": False,
    }
