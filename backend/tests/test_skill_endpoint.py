# -*- coding: utf-8 -*-
"""内容生成路由接线验证:对外只暴露产品功能接口(/content/*),不暴露内部技能名。

仅校验路由注册(不启动 lifespan/Redis/DB),运行期联调需 docker 起全栈。
"""
from app import create_app

APP = create_app()
_ROUTE_PATHS = {getattr(r, "path", "") for r in APP.routes}


def _has(path_fragment: str) -> bool:
    return any(path_fragment in p for p in _ROUTE_PATHS)


def test_content_copy_route_mounted():
    """文案生成入口必须挂在 /api/user/v1/content/copy"""
    assert _has("/user/v1/content/copy"), "文案生成路由缺失,前端生成文案会 404"


def test_content_result_route_mounted():
    """结果轮询必须挂在 /api/user/v1/content/result"""
    assert _has("/user/v1/content/result"), "内容结果轮询路由缺失,前端取产物会 404"


def test_skill_route_not_exposed():
    """对外不得再暴露 /skill 前缀(内部技能名属于服务端实现,不应出现在 URL)"""
    assert not _has("/user/v1/skill"), "仍存在 /skill 路由,内部技能名会被暴露给终端"
