# -*- coding: utf-8 -*-
"""跨端契约测试辅助:在 backend 测试进程内临时加载 worker 的 app 包。

问题:backend 与 worker 顶层包都叫 `app`,独立容器各自独立、互不干扰,但单进程里
无法同时 import 两个。这里用「快照 / 恢复 sys.modules['app']」的方式,在需要时
临时把 app 换成 worker 的,用完再还原 backend 的,从而让跨端契约测试能在 backend
测试会话里运行,且不污染同会话里的其它 backend 测试。

用法:
    with worker_app_context():
        from app.services.prompt_builder import build_gen_params   # 此时 app = worker 的
        build_gen_params(...)
    # 退出后 app 自动恢复为 backend 的,后续 backend 测试照常
"""
import contextlib
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = BACKEND_ROOT.parent / "worker"
REPO_ROOT = BACKEND_ROOT.parent


@contextlib.contextmanager
def worker_app_context():
    """临时把 sys.modules['app'] 换成 worker 的 app(worker 根置于 sys.path 最前),退出时还原 backend 的。

    进入后可在本块内 `from app...` 拿到 worker 的模块;块结束后 backend 的 app 完全恢复,
    不影响同会话里的其它 backend 测试。
    """
    # worker 的顶层包名与 backend 冲突(app / plugin / skills / worker),且 backend 根下也可能存在
    # 同名目录被解析成 namespace 包并缓存到 sys.modules。进入前把这些前缀全部快照并清除,
    # 保证 worker 内部 `from app...` / `from plugin...` / `from skills...` 重新解析到 WORKER_ROOT,
    # 不会复用 backend 侧误缓存的版本。
    _worker_top = ("app", "plugin", "skills", "worker")
    saved = {
        k: v for k, v in sys.modules.items()
        if any(k == p or k.startswith(p + ".") for p in _worker_top)
    }
    for k in list(saved):
        sys.modules.pop(k, None)
    added_roots = []
    # WORKER_ROOT 必须最前:worker 内部 `from app...` / `from plugin...` / `from skills...`
    # 都依赖它解析到 worker 自己的包;REPO_ROOT 仅用于 `import worker` 包(本测试未用),
    # 放在其次,避免它意外遮蔽 worker 内的同名顶层包。
    for root in (str(REPO_ROOT), str(WORKER_ROOT)):
        if root not in sys.path:
            sys.path.insert(0, root)
            added_roots.append(root)
    try:
        yield
    finally:
        for k in [k for k in sys.modules if k == "app" or k.startswith("app.")]:
            sys.modules.pop(k, None)
        for root in added_roots:
            if root in sys.path:
                sys.path.remove(root)
        sys.modules.update(saved)


def load_worker_module(rel: str, name: str):
    """在 worker 上下文内按文件路径加载 worker 模块(避免 `from worker.app...` 顶层 import 与 backend 冲突)。

    调用方必须在 `with worker_app_context():` 块内调用,且加载后立即在同一块内使用——
    退出上下文后模块内部的 `app.*` 依赖会被回收,跨块访问会重新解析到 backend 的 app。
    """
    import importlib.util
    import pytest

    path = WORKER_ROOT / rel
    if not path.exists():
        pytest.skip(f"未找到 worker 源码({path}),跳过跨端契约校验")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
