# -*- coding: utf-8 -*-
'''
@文件    :prompts/__init__.py
@说明    :backend 提示词资产层 — 把运行时提示词从 .py 常量搬到 MD(frontmatter + 正文),
         集中管理、可热更新。本加载器为 backend 自包含副本(不依赖 worker),
         扫描 backend/skills/prompts 下所有子目录的 .md。
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
@说明    :设计原则(详见 backend/skills/docs/prompt-assets.md):
          · 这里只放「散文 + 占位变量」;变量注入、条件分支、调用编排仍在各 service。
          · 仅用 str.format 注入,绝不 eval;占位符白名单由 frontmatter 的 variables 声明。
          · 改 MD 即生效:runtime 刷新调用 reload();亦按文件 mtime 惰性重载。
          · 改编自 Pixelle-Video(prompts/*.md 中标注 source)。
'''
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_DIR = Path(__file__).parent
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
    """递归扫描本目录及子目录,按文件 mtime 增量重载所有 .md 提示词。"""
    with _LOCK:
        for p in _DIR.rglob("*.md"):
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


# 导入即扫描一次,避免首次请求才懒加载
reload()
