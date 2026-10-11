# -*- coding: utf-8 -*-
"""编排服务:成功回调、失败重试(未到最后一次抛 Retry)、最后一次回写 failed"""
import asyncio

import pytest
from arq.worker import Retry

from app.services import base as base_mod
from app.services.base import BaseGenService
from app.schemas.base import ToolResult
from app.settings import config


class _OkTool:
    async def generate(self, params, checkpoint=None, on_stage=None):
        return ToolResult(content="https://x/result.mp4", metadata={"success": True, "seconds": 5})


class _FailTool:
    async def generate(self, params, checkpoint=None, on_stage=None):
        return ToolResult(content="模型报错", metadata={"success": False, "error": "模型报错"})


def _capture_notify(monkeypatch):
    sent = []

    async def fake_notify(url, payload, token=None):
        sent.append(payload)

    monkeypatch.setattr(base_mod, "notify", fake_notify)
    return sent


def test_success_sends_success_callback(monkeypatch):
    sent = _capture_notify(monkeypatch)

    class Svc(BaseGenService):
        tool_class = _OkTool

    asyncio.run(Svc().run(1, "http://cb", {"prompt": "p"}, ctx={"job_try": 1}))
    assert sent[-1]["status"] == "success"
    assert sent[-1]["result_video"] == "https://x/result.mp4"


def test_element_qc_checks_final_postprocessed_delivery(monkeypatch):
    """验收必须发生在后处理之后，回调的报告URL与实际交付URL相同。"""
    from app.services import element_binding_qc
    sent = _capture_notify(monkeypatch)
    checked = []

    class Svc(BaseGenService):
        tool_class = _OkTool

        def _should_burn_subtitle(self):
            """隔离字幕外部依赖。"""
            return False

        async def _apply_sound_effects(self, content, params, task_id, metadata):
            """模拟最后一道后处理改变交付URL。"""
            return "https://x/final.mp4"

    async def review(url, params):
        """捕获最终成片并返回未知报告。"""
        checked.append(url)
        return {"status": "unknown", "checked_output_url": url}

    monkeypatch.setattr(element_binding_qc, "review_final_output", review)
    asyncio.run(Svc().run(5, "http://cb", {"prompt": "p", "image_slots": {"a": "p1"},
                                          "reference_elements": [{"id": "p1"}]}, ctx={"job_try": 1}))
    assert checked == ["https://x/final.mp4"]
    assert sent[-1]["result_video"] == checked[0]
    assert sent[-1]["usage"]["element_binding_qc"]["checked_output_url"] == checked[0]


def test_failure_retries_when_attempts_remain(monkeypatch):
    _capture_notify(monkeypatch)

    class Svc(BaseGenService):
        tool_class = _FailTool

    # 第 1 次失败、还有重试次数 → 抛 Retry 交由 ARQ 重试
    with pytest.raises(Retry):
        asyncio.run(Svc().run(2, "http://cb", {"prompt": "p"}, ctx={"job_try": 1}))


def test_failure_sends_failed_on_last_attempt(monkeypatch):
    sent = _capture_notify(monkeypatch)

    class Svc(BaseGenService):
        tool_class = _FailTool

    # 最后一次尝试 → 回写 failed,不再抛 Retry
    asyncio.run(Svc().run(3, "http://cb", {"prompt": "p"}, ctx={"job_try": int(config.ARQ_MAX_RETRIES)}))
    assert sent[-1]["status"] == "failed"
    assert sent[-1]["fail_reason"] == "模型报错"


def test_tool_exception_is_treated_as_failure(monkeypatch):
    _capture_notify(monkeypatch)

    class _BoomTool:
        async def generate(self, params, checkpoint=None, on_stage=None):
            raise RuntimeError("连接超时")

    class Svc(BaseGenService):
        tool_class = _BoomTool

    with pytest.raises(Retry):
        asyncio.run(Svc().run(4, "http://cb", {"prompt": "p"}, ctx={"job_try": 1}))


# —— P3-4:动效按词锚点回填时间(消费 P3-1 回灌的 anchor_timing)——

def test_apply_anchor_effects_backfills_missing_at_ms():
    """带 ref/anchor 且未显式给 at_ms 时按锚点真实秒回填;显式 at_ms 不被夺权"""
    params = {
        "overlay_reveal": {"text": "揭秘", "ref": "moment:reveal"},                     # 无 at_ms → 回填
        "overlay_flash": {"color": "#FF0000", "at_ms": 300, "ref": "moment:reveal"},    # 显式 → 不动
        "overlay_sticker": {"text": "好评", "anchor": "selection:product"},             # 别名 → 回填窗口起点
    }
    anchor = {
        "moment:reveal": {"start_ms": 1200, "end_ms": 1500, "at_ms": 1200},
        "selection:product": {"start_ms": 800, "end_ms": 2000},
    }
    BaseGenService._apply_anchor_effects(params, anchor)
    assert params["overlay_reveal"]["at_ms"] == 1200
    assert params["overlay_flash"]["at_ms"] == 300
    assert params["overlay_sticker"]["at_ms"] == 800


def test_apply_anchor_effects_noop_without_anchor():
    """无锚点窗口(未命中/未回灌)时原样不动,行为与改造前一致"""
    params = {"overlay_reveal": {"text": "揭秘", "ref": "moment:reveal"}}
    BaseGenService._apply_anchor_effects(params, {})
    assert "at_ms" not in params["overlay_reveal"]


# —— P3-5:音效卡点(消费 anchor_timing / 显式毫秒;失败一律保留原片)——

def test_apply_sound_effects_noop_without_spec():
    """未声明 sound_effects 时原样返回,不触碰 ffmpeg(行为与改造前逐字节一致)"""
    url = "https://x/v.mp4"
    out = asyncio.run(BaseGenService()._apply_sound_effects(url, {}, 1, {}))
    assert out == url


def test_apply_sound_effects_skips_when_no_usable_timecode(monkeypatch):
    """声明了音效但条项缺时间码(无 at_ms 且 ref 未命中)→ 不叠加、留痕,不臆造时间也不阻断出片"""
    monkeypatch.setattr(base_mod.compose, "available", lambda: True)
    meta = {}
    url = "https://x/v.mp4"
    out = asyncio.run(BaseGenService()._apply_sound_effects(
        url, {"sound_effects": [{"url": "https://x/ding.mp3"}]}, 9, meta,
    ))
    assert out == url
    assert meta["sfx_applied"] is False
    assert meta["sfx_skip_reason"]


def test_apply_sound_effects_uses_anchor_timing_when_at_ms_missing(monkeypatch):
    """未给 at_ms 时用 ref 指向的锚点真实秒回填;叠加成功后回传新片并按条数留痕"""
    monkeypatch.setattr(base_mod.compose, "available", lambda: True)

    async def _has_audio(_path):
        return True

    monkeypatch.setattr(base_mod.compose, "probe_has_audio", _has_audio)

    captured = {}

    def _build(video, items, out, duration=0.0, has_base_audio=True, ffmpeg="ffmpeg"):
        # 模拟 ffmpeg 落盘:使 os.path.exists(out) 成立
        captured["items"] = items
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("x")
        return ["ffmpeg", "-y"]

    async def _run(_cmd, timeout=0):
        return {"ok": True}

    monkeypatch.setattr(base_mod.compose, "build_sfx_cmd", _build)
    monkeypatch.setattr(base_mod.compose, "run", _run)

    import app.utils.oss as oss
    monkeypatch.setattr(oss, "download_to_local", lambda url, suffix="": "/tmp/local" + suffix)
    monkeypatch.setattr(oss, "upload_local_file", lambda path, key: "https://cdn/out_sfx.mp4")

    meta = {"anchor_timing": {"moment:hook": {"start_ms": 1500, "end_ms": 2000, "at_ms": 1500}}}
    out = asyncio.run(BaseGenService()._apply_sound_effects(
        "https://x/v.mp4",
        {"sound_effects": [{"url": "https://x/ding.mp3", "ref": "moment:hook"}]},
        11, meta,
    ))
    assert out == "https://cdn/out_sfx.mp4"
    assert meta["sfx_applied"] is True and meta["sfx_count"] == 1
    assert captured["items"][0]["at_ms"] == 1500
    assert captured["items"][0]["path"].endswith(".mp3")  # 本地音效路径来自下载
