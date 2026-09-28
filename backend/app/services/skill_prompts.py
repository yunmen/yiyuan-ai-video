# -*- coding: utf-8 -*-
'''
@文件    :skill_prompts.py
@说明    :后端提示词资产加载器 — 读取 backend 自有技能包 backend/skills/prompts(单一来源)。
          backend 的生成参数组装(prompt_builder)与文案生成(copy_writer)都从这里读散文,
          把真正喂给模型的提示词集中到 MD,后续维护只改 MD、不碰代码。

          backend/skills 是 backend 的自有顶层包(与 worker/skills 解耦,backend 运行时不依赖 worker);
          其加载器为 backend/skills/prompts/__init__.py(PromptAsset 的 get / render)。
          加载失败时回退调用方传入的内联兜底,保证生成链路不中断。
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
import importlib.util
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

# backend 自有技能包路径(与 worker/skills 解耦,backend 运行时不依赖 worker)。
# 关键:此处用「按文件路径加载」而非 `import skills`,避免与 worker 的顶层 `skills` 包同名冲突 ——
# backend 测试会加载 worker 模块(如 prompt_template),其内 `from skills.prompts import render`
# 必须指向 worker 的加载器,不能让 backend 先把顶层 `skills` 占成自己的。
_PROMPTS_LOADER = (
    Path(__file__).resolve().parents[2] / "skills" / "prompts" / "__init__.py"
)


def _prompts_module():
    """按文件路径加载 backend/skills/prompts 加载器,避免注册顶层 `skills` 包造成命名冲突。"""
    name = "_backend_skills_prompts"
    mod = sys.modules.get(name)
    if mod is None:
        spec = importlib.util.spec_from_file_location(name, _PROMPTS_LOADER)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return mod.get, mod.render


def load_skill_prompt(name: str, default: Optional[str] = None) -> str:
    """读取 skill 提示词散文(无占位符)。

    name 对应 backend/skills/prompts 下某 .md 的 frontmatter name(或文件名 stem,
    支持按子目录分类:copy/、generation/replace|context|material/)。
    加载失败(文件缺失/解析异常)时回退 default,并由调用方保证 default 与 MD 正文一致。
    """
    try:
        _get, _ = _prompts_module()
        asset = _get(name)
        if asset is None:
            logger.warning(f"skill 提示词[{name}]未注册,回退内联兜底")
            return default if default is not None else ""
        return asset.body
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"加载 skill 提示词[{name}]失败,回退内联兜底: {exc}")
        return default if default is not None else ""


def render_skill_prompt(name: str, default: Optional[str] = None, **vars) -> str:
    """读取并渲染 skill 提示词(支持 {占位符})。

    仅用 str.format 注入,绝不 eval;占位符缺失会抛错,由 default 兜底。
    """
    try:
        _get, _render = _prompts_module()
        return _render(name, **vars)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"渲染 skill 提示词[{name}]失败,回退内联兜底: {exc}")
        return default if default is not None else ""
