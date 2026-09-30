# -*- coding: utf-8 -*-
'''
@文件    :prompts/__init__.py
@说明    :提示词资产层 — 把运行时提示词从 .py 常量搬到 MD(frontmatter + 正文),集中管理、可热更新。
         PromptAsset/_parse/reload/get/render 与 backend/skills/prompts/__init__.py 逐行同源,
         **刻意不合并**(两侧可独立部署,共享文件需要额外打包方案);改动公共部分必须同步两侧,
         worker 特有的 safe_render 与 backend 目录扫描只留在这里。
@时间    :2026/09/27
@作者    :一源AI
@版本    :1.0
@说明    :设计原则(详见 worker/skills/docs/prompt/prompt-assets.md):
          · 这里只放「散文 + 占位变量」;变量注入、条件分支、调用编排仍在各 tool / prompt_library.py。
          · 仅用 str.format 注入,绝不 eval;占位符白名单由 frontmatter 的 variables 声明。
          · 改 MD 即生效:runtime_config 周期刷新调用 reload();亦按文件 mtime 惰性重载。
          · 改编自 Pixelle-Video(prompts/*.md 中标注 source)。
          · 视频复刻相关的「标准资产」统一收归 backend/skills/prompts(单一来源),
            worker 通过引用复用:reload() 同时扫描本目录与 backend 目录,不复制、避免两份漂移。
          · backend 目录定位:默认按 monorepo 布局(本文件向上 3 级)自动发现;独立部署 worker 时
            由 BACKEND_SKILLS_PROMPTS_DIR 显式指定,解耦对 backend 源码树的硬依赖。
            该目录缺失时复刻增强链路优雅降级(告警一次,不崩溃)。
'''
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.settings import config

logger = logging.getLogger("skills.prompts")

# 本目录(worker 自有提示词)与 backend 权威资产目录(复刻方法论等标准资产)。
# 默认按 monorepo 布局定位:worker/skills/prompts/__init__.py -> parents[3] 即仓库根;
# 独立部署时由 config.BACKEND_SKILLS_PROMPTS_DIR 显式指定,解耦对 backend 源码树的硬依赖。
_DIR = Path(__file__).parent


def _resolve_backend_prompts_dir() -> Path:
    """解析 backend 权威提示词资产目录。

    优先用 BACKEND_SKILLS_PROMPTS_DIR(独立部署挂载/拷贝路径);未配置则按 monorepo
    布局向上 3 级定位到 仓库根/backend/skills/prompts。
    """
    if config.BACKEND_SKILLS_PROMPTS_DIR:
        return Path(config.BACKEND_SKILLS_PROMPTS_DIR)
    return Path(__file__).resolve().parents[3] / "backend" / "skills" / "prompts"


_BACKEND_PROMPTS = _resolve_backend_prompts_dir()
# 扫描顺序:先 worker 自有,再 backend;同名时 backend 权威(后扫覆盖)。
_SCAN_DIRS: List[Path] = [_DIR, _BACKEND_PROMPTS]
_BACKEND_WARNED = False  # backend 目录缺失告警只打一次,避免周期刷新刷屏
_LOCK = threading.Lock()
_MTIME: Dict[str, float] = {}
_REGISTRY: Dict[str, "PromptAsset"] = {}


@dataclass
class PromptAsset:
    name: str
    capability: str = ""
    version: int = 1
    description: str = ""
    variables: List[str] = field(default_factory=list)
    body: str = ""


def _parse(text: str):
    """解析 '---\\n yaml \\n---\\n body' 形式的 frontmatter。无第三方依赖。"""
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        return {"name": None}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {"name": None}, text.strip()
    fm_raw, body = parts[1], parts[2]
    meta: Dict[str, object] = {}
    for line in fm_raw.strip().splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k == "variables":
                inner = v.strip("[]").strip()
                v = [x.strip() for x in inner.split(",") if x.strip()] if inner else []
            elif v.isdigit():
                v = int(v)
            meta[k] = v
    return meta, body.strip()


def reload() -> None:
    """扫描本目录与 backend 权威资产目录,按文件 mtime 增量重载所有 .md 提示词。

    worker 不复刻复刻方法论资产,仅通过扫描 backend/skills/prompts 引用复用,
    保证单一来源、避免两份漂移。key 用完整路径,跨目录也不冲突。
    """
    with _LOCK:
        for base in _SCAN_DIRS:
            if not base.exists():
                # backend 目录缺失只告警一次:独立部署且未配置 BACKEND_SKILLS_PROMPTS_DIR 时,
                #复刻方法论/逆推/质检等可选资产加载不到,相关增强链路优雅降级而非崩溃。
                if base is _BACKEND_PROMPTS:
                    global _BACKEND_WARNED
                    if not _BACKEND_WARNED:
                        _BACKEND_WARNED = True
                        logger.warning(
                            "backend 提示词资产目录不存在(%s):复刻方法论/逆推/质检等资产将无法加载,"
                            "相关增强链路会降级。独立部署时请配置 BACKEND_SKILLS_PROMPTS_DIR 指向 "
                            "backend/skills/prompts。", base
                        )
                continue
            for p in base.rglob("*.md"):
                key = str(p)
                try:
                    mtime = p.stat().st_mtime
                except FileNotFoundError:
                    continue
                if _MTIME.get(key) == mtime and p.stem in _REGISTRY:
                    continue
                _MTIME[key] = mtime
                meta, body = _parse(p.read_text(encoding="utf-8"))
                name = meta.get("name") or p.stem
                vars_ = meta.get("variables") or []
                if not isinstance(vars_, list):
                    vars_ = [vars_]
                _REGISTRY[name] = PromptAsset(
                    name=name,
                    capability=str(meta.get("capability", "")),
                    version=int(meta.get("version", 1) or 1),
                    description=str(meta.get("description", "")),
                    variables=list(vars_),
                    body=body,
                )


def get(name: str) -> Optional[PromptAsset]:
    if name not in _REGISTRY:
        reload()
    return _REGISTRY.get(name)


def render(name: str, **vars) -> str:
    """渲染提示词:校验必填变量后用 str.format 注入(仅简单占位,绝不 eval)。"""
    asset = get(name)
    if asset is None:
        raise KeyError(f"提示词不存在: {name}")
    missing = [v for v in asset.variables if v not in vars]
    if missing:
        raise ValueError(f"提示词[{name}]缺少必填变量: {missing}")
    try:
        return asset.body.format(**vars)
    except (KeyError, IndexError) as exc:
        raise ValueError(f"提示词[{name}]占位符渲染失败(检查模板与变量是否匹配): {exc}")


def safe_render(name: str, default: str = "", **vars) -> str:
    """渲染提示词,资产缺失或渲染失败时返回 default(不抛异常)。

    用于 backend 来源的「可选增强资产」(如复刻逆推/质检):worker 独立部署且未配置
    BACKEND_SKILLS_PROMPTS_DIR 时这些资产可能缺失,主链路应降级而非崩溃。
    worker 自有必需资产仍用 render()(缺失即明确报错,属部署错误)。
    """
    try:
        return render(name, **vars)
    except (KeyError, ValueError):
        return default


# 导入即扫描一次,避免首次请求才懒加载
reload()
