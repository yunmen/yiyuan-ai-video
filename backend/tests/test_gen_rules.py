# -*- coding: utf-8 -*-
"""生成规则:时长吸附 / 画幅 / 清晰度 / 复刻形态(纯函数)"""
from app.services import gen_rules
from app.services.gen_rules import (
    DEFAULT_RATIO,
    DEFAULT_RESOLUTION,
    REPLICATE_FORMATS,
    SUPPORTED_DURATIONS,
    clamp_duration,
    normalize_ratio,
    normalize_replicate_format,
    normalize_resolution,
    parse_duration_gears,
    replicate_format_prompt,
    resolve_gen_defaults,
    set_duration_gears,
)


def test_clamp_duration_hits_supported_gears():
    """时长必须落在模型支持的档位上,避免建单成功但必然 400"""
    for value in (-1, 0, 1, 4, 5, 6, 7, None, "abc", "6"):
        assert clamp_duration(value) in SUPPORTED_DURATIONS
    assert clamp_duration(8) == 10
    assert clamp_duration(15) == 10
    assert clamp_duration(3) == 5


def test_clamp_duration_uses_nearest_gear():
    """就近吸附:与 worker 的 _clamp_duration 同一算法"""
    assert clamp_duration(5) == 5
    assert clamp_duration(7) == 5
    assert clamp_duration(8) == 10


def test_clamp_duration_survives_new_gears(monkeypatch):
    """档位扩展后仍取最近档:旧实现用首末档取中值,档位变 (5,10,15) 会把 12 秒算成 5 秒"""
    monkeypatch.setattr(gen_rules, "SUPPORTED_DURATIONS", (5, 10, 15))
    assert gen_rules.clamp_duration(12) == 10
    assert gen_rules.clamp_duration(14) == 15
    assert gen_rules.clamp_duration(6) == 5


def test_normalize_ratio_falls_back_to_vertical():
    assert normalize_ratio("9:16") == "9:16"
    assert normalize_ratio("16:9") == "16:9"
    assert normalize_ratio("21:9") == DEFAULT_RATIO
    assert normalize_ratio("") == DEFAULT_RATIO
    assert normalize_ratio(None) == DEFAULT_RATIO


def test_normalize_resolution_case_insensitive():
    assert normalize_resolution("1080p") == "1080P"
    assert normalize_resolution("720P") == "720P"
    assert normalize_resolution("4K") == DEFAULT_RESOLUTION


def test_resolve_gen_defaults_reads_config_map():
    cfg = {"gen.video_ratio": "16:9", "gen.video_resolution": "720P"}
    result = resolve_gen_defaults(cfg)
    assert result["ratio"] == "16:9"
    assert result["resolution"] == "720P"
    assert result["durations"] == gen_rules.SUPPORTED_DURATIONS  # 未配时长则取当前档位
    # 配置缺失/非法时回退内置默认值
    assert resolve_gen_defaults({})["ratio"] == DEFAULT_RATIO
    assert resolve_gen_defaults(None)["resolution"] == DEFAULT_RESOLUTION


# --- 时长档位可配置(换支持连续时长的模型后可放开) ---

def test_parse_duration_gears_discrete():
    """离散档位:"5,10" → (5, 10)"""
    assert parse_duration_gears("5,10") == (5, 10)
    assert parse_duration_gears(" 10 , 5 ") == (5, 10)


def test_parse_duration_gears_range():
    """连续区间:"4-15" → 4..15,Seedance 2.x 这类支持任意秒数的模型用这个"""
    assert parse_duration_gears("4-15") == tuple(range(4, 16))
    assert parse_duration_gears("4~15") == tuple(range(4, 16))


def test_parse_duration_gears_invalid_keeps_default():
    """配置写错必须"不覆盖",否则会提交模型不支持的时长(建单成功但必然失败)"""
    for bad in ("", "   ", "abc", "5,x", "15-4", "0-10", "4-150", None):
        assert parse_duration_gears(bad) == (), f"{bad!r} 应视为非法"


def test_set_duration_gears_only_applies_valid(monkeypatch):
    monkeypatch.setattr(gen_rules, "SUPPORTED_DURATIONS", (5, 10))
    assert gen_rules.set_duration_gears("4-15") == tuple(range(4, 16))
    assert gen_rules.clamp_duration(12) == 12      # 放开后 12 秒原样保留
    assert gen_rules.set_duration_gears("乱写") == tuple(range(4, 16))  # 非法不覆盖
    assert gen_rules.clamp_duration(12) == 12


# --- 复刻形态(成片的"内容结构":口播/短剧/街采…) ---

def test_replicate_format_whitelist():
    """形态必须走白名单:前端传什么都得收口成合法值,非法一律空串=沿用原片结构"""
    assert normalize_replicate_format("talking_head") == "talking_head"
    # 大小写/空白差异应被归一化(不能因此误判成非法)
    assert normalize_replicate_format("  SHORT_DRAMA  ") == "short_drama"
    for bad in ("", "   ", None, "unknown", "短剧", 123):
        assert normalize_replicate_format(bad) == "", f"{bad!r} 应视为未指定形态"


def test_replicate_format_prompt_only_when_valid():
    """未指定/非法形态不产生提示词片段 —— 否则存量任务的提示词会被平白改动"""
    assert replicate_format_prompt("") == ""
    assert replicate_format_prompt("乱写") == ""
    prompt = replicate_format_prompt("talking_head")
    assert "口播" in prompt
    # 形态只重塑表演,场景/画幅/运镜仍跟随原片 —— 这句必须在,否则模型会连场景一起重画
    assert "严格跟随参考视频" in prompt


def test_replicate_formats_all_have_label_and_act():
    """每种形态都要有 label 与 act:缺 act 模型就不知道该让出镜者怎么演"""
    assert REPLICATE_FORMATS, "形态白名单不能为空"
    for key, item in REPLICATE_FORMATS.items():
        assert item.get("label"), f"{key} 缺 label"
        assert item.get("act"), f"{key} 缺 act"
        assert replicate_format_prompt(key), f"{key} 未生成提示词片段"
