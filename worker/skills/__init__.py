# -*- coding: utf-8 -*-
'''
@文件    :skills/__init__.py
@说明    :技能层入口 — 汇聚「视频复刻」相关的提示词资产与构建器(改编自 Pixelle-Video)。
          散文资产见 skills/prompts/*.md;变量装配见 skills/prompt_library.py。
          本包为独立顶层包(worker/skills),worker 直接 `import skills` 即可使用。
@时间    :2026/09/27
@作者    :一源AI
@版本    :1.0
'''
from .prompts import render, reload, get
from .prompt_library import (
    build_video_generation_prompt,
    build_image_generation_prompt,
    build_title_generation_prompt,
    build_style_conversion_prompt,
    build_asset_script_prompt,
    build_content_narration_prompt,
    build_topic_narration_prompt,
    apply_image_prefix,
    parse_video_prompts,
    IMAGE_STYLE_PRESETS,
    DEFAULT_IMAGE_STYLE,
)

__all__ = [
    "render", "reload", "get",
    "build_video_generation_prompt",
    "build_image_generation_prompt",
    "build_title_generation_prompt",
    "build_style_conversion_prompt",
    "build_asset_script_prompt",
    "build_content_narration_prompt",
    "build_topic_narration_prompt",
    "apply_image_prefix",
    "parse_video_prompts",
    "IMAGE_STYLE_PRESETS",
    "DEFAULT_IMAGE_STYLE",
]
