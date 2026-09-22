# -*- coding: utf-8 -*-
"""生成任务:参数组装与工具函数(纯函数,无需数据库/Redis)"""
import asyncio
import inspect
from types import SimpleNamespace

from app.services.generate_task import (
    JOB_BY_TYPE,
    _abs_url,
    _build_gen_params,
    _gen_task_no,
    calc_stage,
)
from app.services.gen_rules import resolve_gen_defaults
from app.settings import config


def test_gen_defaults_keys_fit_into_build_gen_params():
    """resolve_gen_defaults 的返回键会被 ** 展开传给 _build_gen_params —— 多一个键建单就 500

    这个坑真实踩过:给 resolve_gen_defaults 加了 durations(时长档位展示用)之后,
    建单接口直接报 "unexpected keyword argument 'durations'"。
    """
    defaults = resolve_gen_defaults({
        "gen.video_ratio": "9:16",
        "gen.video_resolution": "1080P",
        "gen.video_durations": "4-15",
    })
    sig = inspect.signature(_build_gen_params)
    accepts_var_kwargs = any(
        p.kind == p.VAR_KEYWORD for p in sig.parameters.values()
    )
    if not accepts_var_kwargs:
        extra = sorted(set(defaults) - set(sig.parameters))
        assert not extra, f"**gen_defaults 会多传键 {extra},建单接口将报 500"


def test_refund_precharge_calls_refund(monkeypatch):
    """建单失败要退回预扣额度 —— 否则用户扣了额度却没拿到任务"""
    from app.services import credit as credit_mod
    from app.services.generate_task import Service

    called = {}

    async def fake_refund(log_id, remark=""):
        called["log_id"] = log_id
        return 1

    monkeypatch.setattr(credit_mod.service, "refund_consume_log", fake_refund)
    asyncio.run(Service._refund_precharge(99))
    assert called["log_id"] == 99


def test_refund_precharge_swallows_refund_failure(monkeypatch):
    """退款自身失败不能掩盖原始异常(原始异常才是排查入口),也不能再抛出去"""
    from app.services import credit as credit_mod
    from app.services.generate_task import Service

    async def boom(log_id, remark=""):
        raise RuntimeError("db down")

    monkeypatch.setattr(credit_mod.service, "refund_consume_log", boom)
    asyncio.run(Service._refund_precharge(99))  # 不抛异常即通过


def test_refund_precharge_noop_without_log():
    """没扣过额度(付费订单任务)时不做任何事"""
    from app.services.generate_task import Service
    asyncio.run(Service._refund_precharge(None))


def test_abs_url_prefixes_relative_only():
    assert _abs_url("/static/a.jpg") == f"{config.BACKEND_PUBLIC_URL}/static/a.jpg"
    assert _abs_url("https://cdn.example.com/a.jpg") == "https://cdn.example.com/a.jpg"
    assert _abs_url("") == ""


def test_build_gen_params_merges_desc_and_remark():
    tpl = SimpleNamespace(id=9, title="探店模板", desc="适合餐饮门店", duration=12)
    params = _build_gen_params(tpl, ["/static/a.jpg"], "突出招牌菜")
    assert params["template_id"] == 9
    assert params["duration"] == 12
    # 模板品类文字不再进扁平 prompt;只保留用户确认的内容
    assert "适合餐饮门店" not in params["prompt"]
    assert "突出招牌菜" in params["prompt"]
    assert params["materials"][0] == f"{config.BACKEND_PUBLIC_URL}/static/a.jpg"


def test_calc_stage_thresholds():
    assert calc_stage(0) == "解析模板结构"
    assert calc_stage(100) == "回传成片"


def test_calc_stage_by_task_type():
    """数字人任务有独立的阶段划分,不复用视频阶段"""
    assert calc_stage(0, "digital") == "解析口播文案"
    assert calc_stage(20, "digital") == "合成口播音频"
    assert calc_stage(100, "digital") == "回传成片"


def test_job_by_type_covers_all_capabilities():
    assert JOB_BY_TYPE == {
        "video": "process_video",
        "image": "process_image",
        "audio": "process_audio",
        "text": "process_text",
        "digital": "process_digital",
    }


def test_gen_task_no_prefix_and_unique():
    a, b = _gen_task_no(), _gen_task_no()
    assert a.startswith("GY")
    assert a != b


def test_build_gen_params_carries_structured_context():
    """除兼容用的扁平 prompt 外,还需下发结构化上下文与模型实际档位"""
    tpl = SimpleNamespace(
        id=9, title="探店模板", desc="适合餐饮门店", category="餐饮", tags=["探店"],
        duration=12, default_text={"title": "默认标题"},
    )
    params = _build_gen_params(tpl, ["/static/a.jpg", "/static/b.jpg"], "大标题:招牌菜", ratio="9:16", resolution="1080P")
    assert params["gen_mode"] == "r2v"
    assert params["gen_duration"] == 10      # 模板 12 秒 → 吸附到 10
    assert params["ratio"] == "9:16"
    assert params["resolution"] == "1080P"
    assert params["structured"]["title"] == "招牌菜"
    assert "[模板结构]" in params["prompt_context"]
    assert len(params["materials"]) == 2
