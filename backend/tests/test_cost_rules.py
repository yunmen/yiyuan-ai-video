# -*- coding: utf-8 -*-
"""成本规则(纯函数):预算前置的唯一计价入口。

关键约束:预估与实扣必须是同一个函数,否则前端展示的价与实扣的价会漂移。
"""
from app.services import generate_task
from app.services.cost_rules import describe, estimate_cost, resolve_costs, settle_refund


def test_default_cost_matches_history():
    """无配置时各类型均为 1 次 —— 与改造前 TASK_COST 写死的默认值一致"""
    assert resolve_costs({})["video"] == 1
    assert estimate_cost("video", cfg={})["cost"] == 1
    assert estimate_cost("digital", cfg={})["cost"] == 1


def test_base_cost_follows_config():
    cfg = {"gen.cost.video": "3"}
    assert estimate_cost("video", cfg=cfg)["cost"] == 3
    assert estimate_cost("image", cfg=cfg)["cost"] == 1     # 未配置的取默认值


def test_extras_are_off_by_default():
    """附加项默认关闭:10 秒 + 1080P 仍只收基础价(行为与现状一致)"""
    est = estimate_cost("video", duration=10, resolution="1080P", cfg={})
    assert est["cost"] == 1
    assert len(est["detail"]) == 1


def test_extras_accumulate_when_enabled():
    cfg = {"gen.cost.duration_10": "1", "gen.cost.resolution_1080p": "2"}
    est = estimate_cost("video", duration=10, resolution="1080P", cfg=cfg)
    assert est["cost"] == 1 + 1 + 2
    assert [d["key"] for d in est["detail"]] == ["base", "duration_10", "resolution_1080p"]

    # 5 秒 + 720P:两个附加项都不触发
    assert estimate_cost("video", duration=5, resolution="720P", cfg=cfg)["cost"] == 1


def test_image_extra_per_additional_image():
    cfg = {"gen.cost.image_extra": "1"}
    assert estimate_cost("image", num_images=1, cfg=cfg)["cost"] == 1
    assert estimate_cost("image", num_images=3, cfg=cfg)["cost"] == 3


def test_invalid_config_falls_back_to_default():
    cfg = {"gen.cost.video": "abc", "gen.cost.duration_10": "-5"}
    assert estimate_cost("video", duration=10, cfg=cfg)["cost"] == 1


def test_settle_refund_never_over_refunds():
    """结算返还的核心是「不超退、不倒扣」——超退等于资损"""
    assert settle_refund(2, 0, 1) == 1        # 预扣 2、实际 1 → 退 1
    assert settle_refund(1, 0, 1) == 0        # 实扣相符 → 不退
    assert settle_refund(1, 1, 0) == 0        # 已退过 → 不再退
    assert settle_refund(1, 0, 3) == 0        # 实际超出预扣 → 不倒扣
    assert settle_refund(2, 1, 5) == 0


def test_describe_renders_breakdown():
    est = estimate_cost("video", duration=10, cfg={"gen.cost.duration_10": "1"})
    assert "10 秒时长(1)" in describe(est["detail"])


def test_no_hardcoded_cost_table_in_generate_task():
    """额度不能写死在 generate_task(会让前端预估与实扣漂移),必须走 cost_rules"""
    assert not hasattr(generate_task, "TASK_COST")
