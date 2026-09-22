# -*- coding: utf-8 -*-
"""P2 资产缓存:键控与过期判定(纯函数)

缓存键一旦漂移,表现是「明明缓存过却永远 miss」——不报错、只是钱照花,
所以这里把键的稳定性钉死。
"""
from datetime import timedelta

from tortoise.timezone import now as tz_now

from app.services.asset_cache import build_cache_key, compute_hit_stats, is_expired

PAYLOAD = {"text": "招牌小龙虾现在特惠", "voice": "alloy", "model": "qwen-audio", "format": "mp3"}


def test_cache_key_stable_for_same_payload():
    assert build_cache_key("tts_audio", PAYLOAD) == build_cache_key("tts_audio", dict(PAYLOAD))


def test_cache_key_ignores_dict_order():
    """worker 与 backend 组装 payload 的顺序可能不同,键不能因此漂移"""
    reversed_payload = {k: PAYLOAD[k] for k in reversed(list(PAYLOAD))}
    assert build_cache_key("tts_audio", PAYLOAD) == build_cache_key("tts_audio", reversed_payload)


def test_cache_key_changes_with_content():
    """换文案/换音色必须是不同的键,否则会复用错误的产物"""
    assert build_cache_key("tts_audio", PAYLOAD) != build_cache_key("tts_audio", {**PAYLOAD, "text": "欢迎光临"})
    assert build_cache_key("tts_audio", PAYLOAD) != build_cache_key("tts_audio", {**PAYLOAD, "voice": "nova"})


def test_cache_key_differs_by_asset_type():
    """同一入参的不同产物类型不能互相命中"""
    assert build_cache_key("tts_audio", PAYLOAD) != build_cache_key("optimized_prompt", PAYLOAD)


def test_is_expired():
    now = tz_now()
    assert is_expired(now - timedelta(seconds=1), now), "过期时间已过应判定为过期"
    assert not is_expired(now + timedelta(days=1), now)
    assert not is_expired(None, now), "无过期时间视为不过期"


def test_hit_rate_counts_first_generation_as_miss():
    """命中率语义:一条缓存 = 一次未命中,之后每次复用 +1"""
    stats = compute_hit_stats([
        {"asset_type": "tts_audio", "count": 10, "hits": 5},
        {"asset_type": "optimized_prompt", "count": 2, "hits": 0},
    ])
    assert (stats["total"], stats["hits"], stats["requests"]) == (12, 5, 17)
    assert stats["hit_rate"] == round(5 / 17, 4)


def test_hit_rate_zero_when_empty():
    """空表不能除零"""
    assert compute_hit_stats([])["hit_rate"] == 0.0
    assert compute_hit_stats([{"count": 0, "hits": 0}])["requests"] == 0
