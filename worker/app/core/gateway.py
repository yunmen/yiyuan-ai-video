# -*- coding: utf-8 -*-
'''
@文件    :gateway.py
@说明    :命名网关注册表 + 能力路由(灵活网关)。
        后台配置:
          gen.gw.<name>.url / .key / .proto    proto ∈ openai|ark
          gen.route.<cap> = <name>             cap ∈ chat|text|image|video|audio|music
        未配置路由时回退到旧的固定槽位(CHAT_LLM_*/LLM_BASE_*/AUDIO_LLM_*),保证向后兼容。
        这样"火山/阿里/DeepSeek/中转站混着用"只需改几行路由,无需改代码。
'''
from typing import Dict, List

from app.settings import config

PREFIX_GW = "gen.gw."
PREFIX_ROUTE = "gen.route."

# 能力 → 旧槽位回退(按优先级);一个槽位 = (base_url 属性,api_key 属性)
_FALLBACK = {
    "chat": [("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY"), ("LLM_BASE_API_URL", "LLM_BASE_API_KEY")],
    "text": [("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY"), ("LLM_BASE_API_URL", "LLM_BASE_API_KEY")],
    "image": [("LLM_BASE_API_URL", "LLM_BASE_API_KEY"), ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY")],
    "video": [("LLM_BASE_API_URL", "LLM_BASE_API_KEY"), ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY")],
    "audio": [
        ("AUDIO_LLM_BASE_URL", "AUDIO_LLM_API_KEY"),
        ("LLM_BASE_API_URL", "LLM_BASE_API_KEY"),
        ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY"),
    ],
    "music": [
        ("AUDIO_LLM_BASE_URL", "AUDIO_LLM_API_KEY"),
        ("LLM_BASE_API_URL", "LLM_BASE_API_KEY"),
        ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY"),
    ],
}

GATEWAYS: Dict[str, Dict[str, str]] = {}
ROUTES: Dict[str, str] = {}


def auto_proto(url: str) -> str:
    """URL 嗅探协议(仅作缺省/回退;显式 proto 优先)"""
    return "ark" if "volces.com" in (url or "").lower() else "openai"


def load(data: Dict[str, str]) -> List[str]:
    """从全量配置解析 gen.gw.* / gen.route.*,返回变更项(供日志)。"""
    global GATEWAYS, ROUTES
    gw: Dict[str, Dict[str, str]] = {}
    routes: Dict[str, str] = {}
    for k, v in (data or {}).items():
        if k.startswith(PREFIX_GW):
            name, _, field = k[len(PREFIX_GW):].rpartition(".")
            if name and field in ("url", "key", "proto"):
                gw.setdefault(name, {})[field] = (v or "").strip()
        elif k.startswith(PREFIX_ROUTE):
            cap = k[len(PREFIX_ROUTE):]
            if cap:
                routes[cap] = (v or "").strip()

    changed = []
    if gw != GATEWAYS:
        GATEWAYS = gw
        changed.append(f"gateways={sorted(gw.keys())}")
    if routes != ROUTES:
        ROUTES = routes
        changed.append(f"routes={routes}")
    return changed


def resolve(capability: str) -> Dict[str, str]:
    """按能力解析网关:优先 gen.route.<cap>,否则回退旧槽位。返回 {name,url,key,proto}。"""
    name = ROUTES.get(capability)
    if name and name in GATEWAYS:
        g = GATEWAYS[name]
        url, key = g.get("url") or "", g.get("key") or ""
        if url and key:
            return {"name": name, "url": url, "key": key, "proto": g.get("proto") or auto_proto(url)}
    for url_attr, key_attr in _FALLBACK.get(capability, [("LLM_BASE_API_URL", "LLM_BASE_API_KEY")]):
        url = (getattr(config, url_attr, "") or "").strip()
        if url:
            key = (getattr(config, key_attr, "") or "").strip()
            return {"name": f"fallback:{url_attr}", "url": url, "key": key, "proto": auto_proto(url)}
    return {"name": "none", "url": "", "key": "", "proto": "openai"}
