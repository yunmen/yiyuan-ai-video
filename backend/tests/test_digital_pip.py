# -*- coding: utf-8 -*-
"""画中画参数归一化(_normalize_pip 纯函数)

关键约束:bg_volume=0 必须被保留 —— 它表示「背景静音」,若用 `or` 兜底会被当成未填
而回退默认音量,用户选静音后背景原声依旧可闻(此前 worker 侧就是这个坑)。
"""
from app.services.generate_task import DEFAULT_PIP_BG_VOLUME, _normalize_pip


def test_normalize_pip_keeps_zero_bg_volume():
    """静音背景(bg_volume=0)必须原样下发,不能回退默认音量"""
    out = _normalize_pip({"position": "bl", "scale": 0.4, "bg_volume": 0})
    assert out == {"position": "bl", "scale": 0.4, "bg_volume": 0.0}


def test_normalize_pip_defaults_and_clamps():
    """缺省 bg_volume 用统一默认值;scale / bg_volume 越界或非法值收敛到合法区间"""
    # 缺省背景音量(未传键)
    assert _normalize_pip({"position": "br", "scale": 0.3})["bg_volume"] == DEFAULT_PIP_BG_VOLUME
    # 传 None 同样按缺省处理
    assert _normalize_pip({"bg_volume": None})["bg_volume"] == DEFAULT_PIP_BG_VOLUME
    # 越界收敛
    assert _normalize_pip({"scale": 5, "bg_volume": 9}) == {
        "position": "br", "scale": 1.0, "bg_volume": 1.0,
    }
    # 非法值回退默认(不抛异常,绝不因脏数据阻断用户建单)
    bad = _normalize_pip({"scale": "abc", "bg_volume": "abc"})
    assert bad["scale"] == 0.3 and bad["bg_volume"] == DEFAULT_PIP_BG_VOLUME
    # 非法位置回退右下角(与 worker compose._PIP_POSITIONS 的键一致)
    assert _normalize_pip({"position": "中间"})["position"] == "br"


def test_normalize_pip_drops_unknown_keys_and_empty():
    """只保留白名单键;空/非字典输入返回 None(不下发 pip)"""
    assert _normalize_pip(None) is None
    assert _normalize_pip({}) is None
    assert _normalize_pip("脏数据") is None
    assert set(_normalize_pip({"position": "tl", "evil": "x"})) == {"position", "scale", "bg_volume"}
