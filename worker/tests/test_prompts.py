# -*- coding: utf-8 -*-
"""提示词资产层 + Pixelle 适配构建器测试。

覆盖:
- video_optimize 迁移后仍能按画幅/清晰度注入标签(i2v 走首帧);
- render 缺变量时抛 ValueError;
- 从 Pixelle-Video 引入的全部 7 个构建器可正常渲染;
- image_tool 可选风格预设接线(无 style 时不改变行为)。
"""
from skills.prompts import render
from app.tools.prompt_template import (
    RATIO_BY_FIRST_FRAME,
    build_prompt_optimize_system,
)
from skills import prompt_library as pl


def test_video_optimize_renders_labels():
    vertical = build_prompt_optimize_system(ratio="9:16", resolution="1080P")
    assert "竖版 9:16" in vertical and "1080P 高清" in vertical
    horizontal = build_prompt_optimize_system(ratio="16:9", resolution="720P")
    assert "横版 16:9" in horizontal and "720P 标清" in horizontal
    assert "9:16" not in horizontal


def test_i2v_ratio_from_first_frame():
    sys_p = build_prompt_optimize_system(ratio=None, resolution="1080P")
    assert RATIO_BY_FIRST_FRAME in sys_p


def test_render_missing_variable_raises():
    raised = False
    try:
        render("video_optimize", ratio="x")  # 缺 resolution
    except ValueError:
        raised = True
    assert raised, "缺少必填变量应抛 ValueError"


def test_pixelle_assets_render():
    vp = pl.build_video_generation_prompt(["你好世界", "第二句"])
    assert "2" in vp and "narration" in vp.lower()

    ip = pl.build_image_generation_prompt(["场景一"], min_words=50, max_words=100)
    assert "1" in ip

    tp = pl.build_title_generation_prompt("这是一段很长的测试内容用于生成标题", max_length=15)
    assert "max_length" not in tp

    sp = pl.build_style_conversion_prompt("赛博朋克风格")
    assert "赛博朋克" in sp

    ap = pl.build_asset_script_prompt(intent="复刻一个咖啡店", duration=10, assets_text="asset1.jpg")
    assert "复刻一个咖啡店" in ap and "10" in ap

    # 补全全部 7 个 Pixelle 技能:内容 / 主题口播文案生成
    cn = pl.build_content_narration_prompt("用户原始长文内容……", n_storyboard=3, min_words=20, max_words=60)
    assert "3" in cn and "narration" in cn.lower()
    tn = pl.build_topic_narration_prompt("咖啡文化与生活方式", n_storyboard=3, min_words=20, max_words=60)
    assert "咖啡" in tn and "3" in tn

    # 前缀拼接 + 风格预设
    assert pl.apply_image_prefix("a cat", "anime") == "anime, a cat"
    assert pl.DEFAULT_IMAGE_STYLE in pl.IMAGE_STYLE_PRESETS
    assert pl.IMAGE_STYLE_PRESETS["minimal"]["name"] == "Minimalist Abstract"


def test_image_style_prefix_preset():
    # 风格预设可直接用于 image_tool 的提示词增强(仅当传 style 时生效)
    base = "一家咖啡店的温暖午后"
    prefixed = pl.apply_image_prefix(base, pl.IMAGE_STYLE_PRESETS["stick_figure"]["description"])
    assert prefixed.startswith(pl.IMAGE_STYLE_PRESETS["stick_figure"]["description"])


def test_video_prompt_engine_default_native():
    # 默认 native:既有 video_tool 多段链路零变化,仅显式配置 pixelle 时才切换
    try:
        from app.settings import config
    except Exception:
        return  # worker 依赖(pydantic_settings)未安装时跳过,真实环境会执行断言
    assert config.VIDEO_PROMPT_ENGINE == "native"


def test_parse_video_prompts():
    # 标准输出键 video_prompts
    ok = '{"video_prompts": ["A cat runs.", "A dog jumps."]}'
    assert pl.parse_video_prompts(ok) == ["A cat runs.", "A dog jumps."]

    # 兼容 narrations 键 + ```json 围栏 + 前后多余文本
    fenced = '补充说明\n```json\n{"narrations": ["scene one", "scene two"]}\n```\n结束'
    assert pl.parse_video_prompts(fenced) == ["scene one", "scene two"]

    # 字典元素取 content 字段
    dicted = '{"video_prompts": [{"content": "x"}, {"content": "y"}]}'
    assert pl.parse_video_prompts(dicted) == ["x", "y"]

    # 非法 / 空 / 条数为 0 → None(触发回退)
    assert pl.parse_video_prompts("不是 json") is None
    assert pl.parse_video_prompts("") is None
    assert pl.parse_video_prompts('{"video_prompts": []}') is None
    assert pl.parse_video_prompts('{"foo": 1}') is None


def test_asset_script_prompt_injects_voice_and_captions():
    """复刻脚本必须带上「声音方向 + 字幕」方法论。

    二者作用在**文案本身**上(这句词由谁、以什么节奏递送;按语义短语断句决定字幕怎么切),
    所以属于脚本生成环节 —— 不是 TTS(会被念出来),也不是烧字幕(纯文本,无 LLM)。
    """
    text = pl.build_asset_script_prompt(intent="商品", duration=15, assets_text="对标视频: x.mp4")
    assert "视频复刻方法论参考" in text
    assert "声音方向" in text and "字幕" in text


def test_parse_asset_script():
    # 标准形态:scenes → narrations 数组
    ok = '{"scenes": [{"narrations": ["第一款。", "限时秒杀。"]}, {"narrations": ["快下单。"]}]}'
    assert pl.parse_asset_script(ok) == "第一款。\n限时秒杀。\n快下单。"

    # 兼容 script 键 + ```json 围栏 + narration 为单字符串
    fenced = '说明\n```json\n{"script": [{"narrations": "只有一句。"}]}\n```'
    assert pl.parse_asset_script(fenced) == "只有一句。"

    # 非 JSON / 空 / 结构不符 → 空串(调用方回退"无文案",不阻断主链路)
    assert pl.parse_asset_script("不是 json") == ""
    assert pl.parse_asset_script("") == ""
    assert pl.parse_asset_script('{"foo": 1}') == ""
