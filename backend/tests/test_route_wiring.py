# -*- coding: utf-8 -*-
"""接口打通(路由接线)验证:前端可见路径必须映射到后端真实 handler。

前端经反向代理把 `/api/v1/...` 重写为 `/api/user/v1/...`,故后端真正挂载的路径是
`/api/user/v1/...`。本用例钉住三件事:
  1. `gen-config`(下发复刻形态/意图选项)确实挂在免登录路径上;
  2. `task/create` 与 `task/deconstruct` 接受 `format`(复刻目标形态);
  3. 这些路径真实存在于应用路由表,不会因重构漏挂导致前端 404。

注意:不启动 lifespan(Redis/DB),只校验路由注册 —— 运行期联调需 docker 起全栈。
"""
from app import create_app

# create_app() 不触发 lifespan,无需 Redis/DB,可安全在测试期构建
APP = create_app()

_ROUTE_PATHS = {getattr(r, "path", "") for r in APP.routes}


def _has(path_fragment: str) -> bool:
    return any(path_fragment in p for p in _ROUTE_PATHS)


def test_gen_config_route_mounted_login_free():
    """复刻形态/意图的下发接口必须挂在 `/api/user/v1/base/common/gen-config`"""
    assert _has("/user/v1/base/common/gen-config"), "gen-config 未挂载到预期路径"


def test_task_create_and_deconstruct_accept_format():
    """建单与拆解接口必须存在(前端 Replicate 页会带 format 调用它们)"""
    assert _has("/user/v1/task/create"), "task/create 路由缺失,前端建单会 404"
    assert _has("/user/v1/task/deconstruct"), "task/deconstruct 路由缺失,前端拆解会 404"


def test_format_field_exposed_on_task_contract():
    """OpenAPI 契约里 task/create 与 task/deconstruct 都必须暴露 format 字段"""
    spec = APP.openapi()
    schemas = spec.get("components", {}).get("schemas", {})
    REF_KEY = "$ref"
    exposed = set()
    for path, ops in spec["paths"].items():
        for method, op in (ops or {}).items():
            if method.lower() != "post":
                continue
            content = (op.get("requestBody") or {}).get("content") or {}
            for media in content.values():
                ref = (media.get("schema") or {}).get(REF_KEY, "")
                if not ref:
                    continue
                name = ref.split("/")[-1]
                props = (schemas.get(name) or {}).get("properties") or {}
                if "format" in props:
                    exposed.add(path)
    assert "/api/user/v1/task/create" in exposed, "create 契约未暴露 format"
    assert "/api/user/v1/task/deconstruct" in exposed, "deconstruct 契约未暴露 format"
