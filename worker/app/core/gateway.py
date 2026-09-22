# -*- coding: utf-8 -*-
'''
@文件    :gateway.py
@说明    :命名网关注册表 + 能力路由(灵活网关)。
        后台配置:
          gen.gw.<name>.url / .key / .proto    proto ∈ openai|ark
          gen.route.<cap> = <name>             cap ∈ chat|text|image|video|audio|music|digital
        未配置路由时回退到旧的固定槽位(CHAT_LLM_*/LLM_BASE_*/AUDIO_LLM_*),保证向后兼容。
        这样"火山/阿里/DeepSeek/中转站混着用"只需改几行路由,无需改代码。
        resolve() 取主用网关;resolve_all() 返回完整候选列表,供调用方做故障转移。
'''
from typing import Dict, List, Set

from app.settings import config

PREFIX_GW = "gen.gw."
PREFIX_ROUTE = "gen.route."

# 能力 → 旧槽位回退(按优先级);一个槽位 = (base_url 属性,api_key 属性)
_FALLBACK = {
    "chat": [("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY"), ("LLM_BASE_API_URL", "LLM_BASE_API_KEY")],
    "text": [("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY"), ("LLM_BASE_API_URL", "LLM_BASE_API_KEY")],
    "image": [("LLM_BASE_API_URL", "LLM_BASE_API_KEY"), ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY")],
    "video": [("LLM_BASE_API_URL", "LLM_BASE_API_KEY"), ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY")],
    # 数字人口播与视频同协议(提交+轮询),默认与视频同网关;可经 gen.route.digital 单独指向别的网关
    "digital": [("LLM_BASE_API_URL", "LLM_BASE_API_KEY"), ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY")],
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
    # 视频编辑:默认跟随视频网关(同一回退链)
    "video_edit": [("LLM_BASE_API_URL", "LLM_BASE_API_KEY"), ("CHAT_LLM_BASE_URL", "CHAT_LLM_API_KEY")],
}

# 能力别名:未单独配置 gen.route.<能力> 时复用目标能力的候选列表。
# 视频编辑默认跟随 video;要让它走别处(如中转站)时配 gen.route.video_edit 即可,
# 不影响普通视频(t2v/i2v/r2v)的网关选择。
_CAPABILITY_ALIAS = {"video_edit": "video"}

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


def resolve_all(capability: str) -> List[Dict[str, str]]:
    """按能力解析网关候选列表(有序、已去重):第 1 个为主用,其余作为故障转移备选。

    候选顺序:gen.route.<cap> 命中的命名网关 → 固定槽位回退链(_FALLBACK,按优先级)。
    仅纳入 url 非空的项;**同一地址只保留一次**(最先命中的槽位优先):
    故障转移的意义是换一个地址重试,主备恰好同址时把同一地址重试两遍没有意义。
    """
    # 能力别名:未单独配置路由时直接复用目标能力的候选。
    # 视频编辑(参考视频→新片)默认跟随 video 网关;若要让它走别处(如中转站),
    # 单独配 gen.route.video_edit 即可,无需改动普通视频(t2v/i2v/r2v)的网关。
    if capability in _CAPABILITY_ALIAS and not ROUTES.get(capability):
        return resolve_all(_CAPABILITY_ALIAS[capability])

    candidates: List[Dict[str, str]] = []
    seen: Set[str] = set()

    def _append(name: str, url: str, key: str, proto: str = "") -> None:
        url = (url or "").strip().rstrip("/")
        if not url or url in seen:
            return
        seen.add(url)
        candidates.append({
            "name": name,
            "url": url,
            "key": key,
            "proto": (proto or "").strip() or auto_proto(url),
        })

    route_name = ROUTES.get(capability)
    if route_name and route_name in GATEWAYS:
        g = GATEWAYS[route_name]
        if (g.get("url") or "").strip() and (g.get("key") or "").strip():
            _append(route_name, g["url"], g["key"], g.get("proto") or "")

    for url_attr, key_attr in _FALLBACK.get(capability, [("LLM_BASE_API_URL", "LLM_BASE_API_KEY")]):
        _append(
            f"fallback:{url_attr}",
            getattr(config, url_attr, "") or "",
            getattr(config, key_attr, "") or "",
        )

    return candidates


def resolve(capability: str) -> Dict[str, str]:
    """按能力解析主用网关(候选列表首个);无可用网关时返回 none。"""
    candidates = resolve_all(capability)
    if candidates:
        return candidates[0]
    return {"name": "none", "url": "", "key": "", "proto": "openai"}
