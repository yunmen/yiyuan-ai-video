# -*- coding: utf-8 -*-
"""进程内计数指标:坏素材/降级类事件必须能被累计观测

过去这些事件只有一行日志,批量出现时无人知晓(用户只会一个个来投诉)。
这里钉死的是**可观测性**:计数要累加、要能取快照、汇总日志要打出重点指标。
"""
from app.core import metrics


def test_incr_accumulates_and_returns_total():
    metrics._counters.clear()
    metrics._last_detail.clear()
    assert metrics.incr("test.counter") == 1
    assert metrics.incr("test.counter") == 2
    assert metrics.incr("test.counter", n=3) == 5
    assert metrics.snapshot()["test.counter"] == 5


def test_snapshot_is_a_copy():
    """快照必须是副本:调用方改它不能污染计数器"""
    metrics._counters.clear()
    metrics.incr("test.copy")
    snap = metrics.snapshot()
    snap["test.copy"] = 999
    assert metrics.snapshot()["test.copy"] == 1


def test_flush_logs_key_metrics(monkeypatch):
    """汇总日志要带上重点指标,便于运维一眼看出是否出现批量问题"""
    metrics._counters.clear()
    metrics._last_detail.clear()
    logs = []
    monkeypatch.setattr(metrics.logger, "info", lambda msg="", *a, **k: logs.append(str(msg)))
    monkeypatch.setattr(metrics.logger, "warning", lambda msg="", *a, **k: logs.append(str(msg)))

    metrics.incr("frame.degenerate_blocked", detail="成片:画面 85% 高饱和")
    metrics.flush(force=True)

    joined = " ".join(logs)
    assert "frame.degenerate_blocked" in joined
    assert "画面 85% 高饱和" in joined, "汇总要带最近一次的原因,否则只知道次数不知道为什么"
    assert any("批量" in line for line in logs), "重点指标非零时必须提示排查方向"


def test_flush_respects_interval_unless_forced(monkeypatch):
    """非强制刷新在间隔内不打日志:指标不该淹没业务日志"""
    metrics._counters.clear()
    metrics._last_detail.clear()
    metrics.incr("test.quiet")
    logs = []
    monkeypatch.setattr(metrics.logger, "info", lambda msg="", *a, **k: logs.append(str(msg)))
    monkeypatch.setattr(metrics.logger, "warning", lambda msg="", *a, **k: logs.append(str(msg)))
    metrics.flush()                      # 距上次刷新不足间隔 → 静默
    assert not any("指标汇总" in line for line in logs)
    metrics.flush(force=True)            # 强制 → 打
    assert any("指标汇总" in line for line in logs)
