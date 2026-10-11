# -*- coding: utf-8 -*-
"""用户端接口打通(前后端覆盖一致性)验证。

本用例把 desktop 前端 API 层与后端真实路由表做**双向比对**,防止两类问题:

  1. 前端调了后端没有的路径 → 线上直接 404(重构改路径时最易漏改某一端);
  2. 后端开放了用户端接口但前端从未接入 → 能力"存在却没人用",例如本次发现
     `/copy/generate` 已改为异步下发(返回 task_id),配套轮询接口 `/copy/result`
     前端根本没有接,导致页面把 task_id 当文案读,一个字段都填不上。

同时钉死"同一路径只允许一份前端定义",杜绝同一接口在多个模块各写一份 URL 副本。

注意:不启动 lifespan(Redis/DB),只校验静态接线 —— 运行期联调需 docker 起全栈。
"""
import re
from collections import defaultdict
from pathlib import Path

from app import create_app

ROOT = Path(__file__).resolve().parent.parent  # backend/
DESKTOP_API_DIR = ROOT.parent / "desktop" / "src" / "api" / "model"

APP = create_app()

# 前端 `${config.API_URL}/v1/xxx` 中 config.API_URL 为 `/api`,
# 经 vite/网关 rewrite 落到后端真实挂载前缀 `/api/user`,故拼接后才是后端路径
BACKEND_PREFIX = "/api/user"

_FRONTEND_URL_PATTERN = re.compile(r"\$\{config\.API_URL\}(/[^`\s'\"]+)")


def _frontend_endpoints():
    """扫描前端 API 模块,返回 {后端路径: 定义该路径的前端文件名列表}"""
    endpoints = defaultdict(list)
    for js in sorted(DESKTOP_API_DIR.glob("*.js")):
        content = js.read_text(encoding="utf-8")
        for path in _FRONTEND_URL_PATTERN.findall(content):
            endpoints[BACKEND_PREFIX + path].append(js.name)
    return endpoints


FE_ENDPOINTS = _frontend_endpoints()

_ROUTES = {(r.path, m) for r in APP.routes for m in getattr(r, "methods", set())}
_USER_ROUTES = {p for (p, _m) in _ROUTES if p.startswith("/api/user/v1/")}

# Worker / 回调专用通道:由后端或 worker 内部调用,前端不应也不需要接
WORKER_ONLY = {
    "/api/user/v1/task/callback",
    "/api/user/v1/task/checkpoint",
    "/api/user/v1/task/cache",
    "/api/user/v1/base/common/worker-config",
}


def test_frontend_endpoints_all_mounted():
    """前端用到的每个接口都必须真实挂在后端路由表上,否则必然 404"""
    missing = {
        path: files
        for path, files in FE_ENDPOINTS.items()
        if (path, "POST") not in _ROUTES
    }
    assert not missing, f"前端调用了后端不存在的接口(会 404): {missing}"


def test_backend_user_endpoints_covered_by_frontend():
    """后端开放的用户端 POST 接口都必须被前端接入,避免能力"实现了没人用"。

    Worker 回调/内部通道(见 WORKER_ONLY)不在前端职责内,显式豁免。
    """
    uncovered = sorted(
        p for p in _USER_ROUTES
        if p not in WORKER_ONLY and (p, "POST") in _ROUTES and p not in FE_ENDPOINTS
    )
    assert not uncovered, (
        "以下后端用户端接口未被前端接入(能力悬空),请补齐 "
        f"desktop/src/api/model/*.js:{uncovered}"
    )


def test_worker_only_endpoints_not_exposed_to_frontend():
    """Worker 专用通道不该被前端引用:它们靠 X-Worker-Token 鉴权,浏览器调用必被拒"""
    leaked = sorted(p for p in WORKER_ONLY if p in FE_ENDPOINTS)
    assert not leaked, f"Worker 内部接口被前端直接引用了: {leaked}"


def test_async_copy_contract_paired():
    """`/content/copy` 已异步化(返回 task_id),轮询接口 /content/result 必须成对存在,不能只改一半。

    注:`/base/common/copy/*` 老接口已在 /skill→/content 迁移中废弃删除(前端改用 /content/*),
    此处钉死新契约,防止有人只加下单接口漏了轮询。
    """
    assert "/api/user/v1/content/copy" in _USER_ROUTES, "文案生成下单接口缺失"
    assert "/api/user/v1/content/result" in _USER_ROUTES, (
        "文案已改为异步生成,但轮询接口 /content/result 未挂载,前端拿不到文案结果"
    )


def test_frontend_consumes_copy_result_after_fix():
    """前端必须真正订阅异步文案结果:content 模块要定义 /content/copy 与 /content/result。

    老接口 /base/common/copy/* 已废弃(见 test_async_copy_contract_paired 注释),
    前端统一经 content.js 的 /content/* 下单+轮询,这里钉死,避免再次漂移回老路径。
    """
    content = (DESKTOP_API_DIR / "content.js").read_text(encoding="utf-8")
    assert "/v1/content/copy" in content, "前端未接入 /content/copy 下单接口"
    assert "/v1/content/result" in content, "前端未接入 /content/result 轮询接口"


def test_no_duplicate_frontend_definitions():
    """同一后端路径在前端只允许一处定义,杜绝多模块各持一份 URL 副本造成漂移"""
    duplicates = {p: files for p, files in FE_ENDPOINTS.items() if len(files) > 1}
    assert not duplicates, f"同一接口在多个前端模块重复定义(易漂移): {duplicates}"
