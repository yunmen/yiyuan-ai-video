# -*- coding: utf-8 -*-
"""僵尸任务回收:worker 崩溃/被重启/任务被超时杀掉后,ARQ 不会自动重入队 → 任务永久停在"生成中"。

回收策略按"是否已提交外部生成任务"分两类:
  · 未提交(checkpoint 无 external_task_id)→ **安全重跑**:断点复用已改写好的 prompt,不重复生成;
  · 已提交(checkpoint 有 external_task_id)→ **续跑**(不是重跑):worker stage=2 复用
    external_task_id 继续轮询,不重复扣费(由 test_video_tool_resume.py 钉住该契约)。
    此前这类被直接跳过,只能干等 TASK_STUCK_TIMEOUT(4 小时),表现为进度永远停在 80%;
  · ARQ 里仍在队列/正在执行 → 跳过(避免重复入队);
  · 两类各有次数上限(_orphan_recovered / _resume_count),不无限重入队。
"""
import asyncio

import app.core.task_queue as tq
from app.services import generate_task as gt


class _Task:
    def __init__(self, task_id, checkpoint=None, params=None, progress=80, task_type="video"):
        self.id = task_id
        self.type = task_type
        self.checkpoint = checkpoint or {}
        self.params = params or {}
        self.progress = progress
        self.saved_fields = []

    async def save(self, update_fields=None):
        self.saved_fields.append(list(update_fields or []))


class _Filter:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        async def _inner():
            return self._rows
        return _inner()


def _install(monkeypatch, rows, alive_ids=()):
    enqueued = []

    monkeypatch.setattr(gt.GenerateTaskModel, "filter", lambda **kwargs: _Filter(rows))
    monkeypatch.setattr(gt, "_build_notify_url", lambda: "http://backend/callback")
    monkeypatch.setattr(tq, "arq_pool", object())

    async def fake_alive(task_id):
        return task_id in alive_ids

    # 真实实现返回 bool(是否真正入队),桩必须同步返回 True ——
    # 返回 None 会被调用方的 `if not await enqueue_generate_task(...)` 当成"入队失败"。
    async def fake_enqueue(job_name, task_id, notify_url, params):
        assert job_name == gt.JOB_BY_TYPE[next(row.type for row in rows if row.id == task_id)]
        enqueued.append(task_id)
        return True

    monkeypatch.setattr(tq, "job_alive", fake_alive)
    monkeypatch.setattr(tq, "enqueue_generate_task", fake_enqueue)
    return enqueued


def test_recover_requeues_unsubmitted_orphans(monkeypatch):
    rows = [
        _Task(1),                                                   # 未提交 → 回收
        _Task(3, params={"_orphan_recovered": True}),               # 已回收过 → 不反复重试
        _Task(4),                                                   # 仍在 ARQ 里 → 跳过
    ]
    enqueued = _install(monkeypatch, rows, alive_ids={4})

    recovered = asyncio.run(gt.service.recover_orphan_tasks(600))

    assert recovered == 1
    assert enqueued == [1]
    assert rows[0].params["_orphan_recovered"] is True   # 打标,避免无限回收
    assert rows[0].progress == 0                         # 进度归零,前端重新进进度态
    assert "params" in rows[0].saved_fields[0]
    assert rows[2].saved_fields == []


def test_recover_resumes_submitted_task_instead_of_waiting_hours(monkeypatch):
    """已提交外部任务的僵尸任务要**续跑**(只重新轮询),不能干等 4 小时超时

    这是实测踩过的坑:23s 长片编辑的收尾阶段被 ARQ 超时掐掉后,任务卡在 80% 一动不动,
    而唯一兜底的 reconcile_stuck 要 4 小时才判失败。
    """
    rows = [_Task(2, checkpoint={"external_task_id": "cgt-1"})]
    enqueued = _install(monkeypatch, rows)

    recovered = asyncio.run(gt.service.recover_orphan_tasks(600))

    assert recovered == 1 and enqueued == [2]
    assert rows[0].params["_resume_count"] == 1
    # 续跑不清零进度:前端应看到"还在生成",而不是被退回初始态
    assert rows[0].progress == 80


def test_recover_stops_resuming_after_limit(monkeypatch):
    """续跑次数用尽后不再重入队(交给超时对账兜底),避免无限循环"""
    rows = [_Task(2, checkpoint={"external_task_id": "cgt-1"}, params={"_resume_count": 3})]
    enqueued = _install(monkeypatch, rows)

    assert asyncio.run(gt.service.recover_orphan_tasks(600)) == 0
    assert enqueued == []


def test_recover_skips_submitted_task_whose_job_is_alive(monkeypatch):
    """外部任务已提交但 ARQ job 还在跑 → 不能重复入队"""
    rows = [_Task(5, checkpoint={"external_task_id": "cgt-1"})]
    enqueued = _install(monkeypatch, rows, alive_ids={5})

    assert asyncio.run(gt.service.recover_orphan_tasks(600)) == 0
    assert enqueued == []


def test_recover_routes_images_and_skips_unknown_types(monkeypatch):
    rows = [_Task(6, task_type="image"), _Task(7, task_type="unknown")]
    enqueued = _install(monkeypatch, rows)

    assert asyncio.run(gt.service.recover_orphan_tasks(600)) == 1
    assert enqueued == [6]
    assert rows[1].saved_fields == []


def test_recover_noop_without_arq_pool(monkeypatch):
    """ARQ 池没初始化时不动任何任务(否则会误判成孤儿)"""
    monkeypatch.setattr(tq, "arq_pool", None)
    assert asyncio.run(gt.service.recover_orphan_tasks(600)) == 0


def test_job_id_is_stable():
    assert tq.job_id(10) == "task-10"


def test_job_alive_conservative_when_pool_missing(monkeypatch):
    """判不出存活时保守返回 True:宁可不回收,也不能把在跑的任务重复入队"""
    monkeypatch.setattr(tq, "arq_pool", None)
    assert asyncio.run(tq.job_alive(1)) is True


class _Pool:
    def __init__(self, exists_value=0, raise_exc=False):
        self._exists_value = exists_value
        self._raise = raise_exc

    async def exists(self, jid):
        if self._raise:
            raise RuntimeError("redis down")
        return self._exists_value


def test_job_alive_false_when_job_gone(monkeypatch):
    """ARQ 里查不到该 job → 判定为死,允许回收(ARQ 0.28 用 exists,不是 job_status)"""
    monkeypatch.setattr(tq, "arq_pool", _Pool(exists_value=0))
    assert asyncio.run(tq.job_alive(3)) is False


def test_job_alive_true_when_job_present(monkeypatch):
    """job 仍在队列/执行中 → True,不回收"""
    monkeypatch.setattr(tq, "arq_pool", _Pool(exists_value=1))
    assert asyncio.run(tq.job_alive(3)) is True


def test_job_alive_conservative_on_query_error(monkeypatch):
    """查询报错时保守返回 True(宁可不回收)"""
    monkeypatch.setattr(tq, "arq_pool", _Pool(raise_exc=True))
    assert asyncio.run(tq.job_alive(3)) is True
