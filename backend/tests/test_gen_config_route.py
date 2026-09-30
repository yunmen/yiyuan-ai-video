# -*- coding: utf-8 -*-
"""公开配置接口(/gen-config):复刻目标形态随配置下发

前端的形态标签直接渲染这份数据,不再另存一份白名单副本 —— 这组用例钉住
「后端选项 = 校验白名单 = 接口下发内容」三者的同源关系,防止再次漂移。
"""
import asyncio
import json

from app.routes.user.common import gen_config
from app.services.gen_rules import REPLICATE_FORMAT_OPTIONS, SUPPORTED_REPLICATE_FORMATS
from app.services.prompt_builder import (
    CREATIVE_LEVEL_OPTIONS,
    HOOK_BOOST_OPTIONS,
    INTENT_OPTIONS,
    LEAD_ACT_OPTIONS,
    VALID_CREATIVE_LEVELS,
    VALID_HOOK_BOOSTS,
    VALID_INTENTS,
)


def _payload(resp) -> dict:
    """Success 是 JSONResponse,取回反序列化后的响应体"""
    return json.loads(resp.body.decode("utf-8"))


def test_gen_config_includes_replicate_formats(monkeypatch):
    """形态选项必须随公开配置下发,且不污染原有配置项"""
    from app.services import system_config

    async def _fake_public_map():
        # 公开配置来自数据库,这里用桩替代;本用例只验证「形态选项被并入」
        return {"gen.video_price": "10"}

    monkeypatch.setattr(system_config.service, "get_public_map", _fake_public_map)

    body = _payload(asyncio.run(gen_config()))
    assert body["code"] == 1
    assert body["data"]["gen.video_price"] == "10"      # 原公开配置不受影响
    formats = body["data"]["replicate_formats"]
    assert [f["key"] for f in formats] == list(SUPPORTED_REPLICATE_FORMATS)
    for item in formats:
        assert item["label"] and item["desc"], f"形态[{item['key']}]缺少展示文案"


def test_gen_config_includes_replicate_intents(monkeypatch):
    """替换意图选项同样由后端下发给前端渲染,不再两端各存一份"""
    from app.services import system_config

    async def _fake_public_map():
        return {}

    monkeypatch.setattr(system_config.service, "get_public_map", _fake_public_map)

    body = _payload(asyncio.run(gen_config()))
    intents = body["data"]["replicate_intents"]
    assert [i["key"] for i in intents] == [o["key"] for o in INTENT_OPTIONS]
    # 每个可选项都必须是后端可校验的取值
    assert {i["key"] for i in intents} == set(VALID_INTENTS)
    for item in intents:
        assert item["label"] and item["desc"], f"意图[{item['key']}]缺少展示文案"


def test_intent_options_are_single_source():
    """意图选项与校验白名单必须同源(白名单由选项派生),杜绝"能选却校验不过\""""
    assert {o["key"] for o in INTENT_OPTIONS} == set(VALID_INTENTS)
    for opt in INTENT_OPTIONS:
        assert set(opt) == {"key", "label", "desc"}
        assert all(isinstance(v, str) and v for v in opt.values())


def test_gen_config_includes_creative_levels_and_hook_boosts(monkeypatch):
    """创意档位/开头钩子同样由后端单一来源下发,前端只渲染 label/desc"""
    from app.services import system_config

    async def _fake_public_map():
        return {}

    monkeypatch.setattr(system_config.service, "get_public_map", _fake_public_map)

    body = _payload(asyncio.run(gen_config()))
    levels = body["data"]["replicate_creative_levels"]
    boosts = body["data"]["replicate_hook_boosts"]
    assert [i["key"] for i in levels] == [o["key"] for o in CREATIVE_LEVEL_OPTIONS]
    # 下发的每个档位都必须是后端可校验的取值,否则用户选了却不生效
    assert {i["key"] for i in levels} == set(VALID_CREATIVE_LEVELS)
    assert {i["key"] for i in boosts} == set(VALID_HOOK_BOOSTS)
    for item in list(levels) + list(boosts):
        assert item["label"] and item["desc"], f"档位[{item['key']}]缺少展示文案"


def test_creative_options_are_single_source():
    """创意档位/钩子选项与白名单同源,且必须是可 JSON 序列化的纯字符串字典"""
    assert {o["key"] for o in CREATIVE_LEVEL_OPTIONS} == set(VALID_CREATIVE_LEVELS)
    assert {o["key"] for o in HOOK_BOOST_OPTIONS} == set(VALID_HOOK_BOOSTS)
    for opt in tuple(CREATIVE_LEVEL_OPTIONS) + tuple(HOOK_BOOST_OPTIONS):
        assert set(opt) == {"key", "label", "desc"}
        assert all(isinstance(v, str) and v for v in opt.values())


def test_gen_config_replicate_formats_json_serializable():
    """下发的形态选项必须是纯字符串字典:前端直接渲染,不能夹带不可序列化的对象"""
    for opt in REPLICATE_FORMAT_OPTIONS:
        assert set(opt) == {"key", "label", "desc"}
        assert all(isinstance(v, str) and v for v in opt.values())


def test_all_gen_config_option_tables_share_one_shape():
    """同批下发的选项表必须共用同一套键名({key,label,desc}),不能有的用 key 有的用 value。

    历史故障:形态表用 `key`,意图/档位/钩子/主角表现用 `value`,前端被迫写 `o.key ?? o.value`
    兜底;而 Upload 页未走归一化的分支读不到 key,表现为"选项能渲染但点了不选中"。
    这里把所有选项表一起钉死,任何一张表换键名都会被拦下。
    """
    tables = {
        "replicate_formats": REPLICATE_FORMAT_OPTIONS,
        "replicate_intents": INTENT_OPTIONS,
        "lead_acts": LEAD_ACT_OPTIONS,
        "replicate_creative_levels": CREATIVE_LEVEL_OPTIONS,
        "replicate_hook_boosts": HOOK_BOOST_OPTIONS,
    }
    for name, table in tables.items():
        for opt in table:
            assert set(opt) == {"key", "label", "desc"}, (
                f"{name} 的选项键名与其他表不一致(应为 key/label/desc): {sorted(opt)}"
            )
            assert all(isinstance(v, str) and v for v in opt.values()), f"{name} 存在空值选项: {opt}"
