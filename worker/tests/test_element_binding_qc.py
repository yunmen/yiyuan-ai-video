"""元素级最终采样验收回归，所有外部模型与媒体依赖均打桩。"""
import asyncio
import json

import pytest

from app.services import element_binding_qc as qc


def _params():
    """同一元素两张角度图，离场后再出现，不包含空档观测。"""
    return {"reference_video": "source.mp4", "materials": ["a.jpg", "b.jpg"],
            "image_slots": {"a.jpg": "p1", "b.jpg": "p1"},
            "reference_elements": [{"id": "p1", "label": "红罐", "kind": "product",
                                    "observations": [{"time": 1}, {"time": 9}]}]}


def _response(count=2, **changes):
    """生成具备完整证据字段的模型响应，允许覆盖字段测试保守解析。"""
    return json.dumps({"samples": [{"sample_index": index, "status": "pass", "aligned": True,
                                   "source_located": True, "target_match": True,
                                   "unbound_preserved": True, "reason": "指定位置与目标一致", **changes}
                                  for index in range(count)],
                       "consistency": "pass", "consistency_reason": "两次出现主体外观一致"})


def _infra(monkeypatch, raw=None):
    """替换下载、探测、抽帧与视觉请求并捕获消息顺序。"""
    captured = []
    monkeypatch.setattr(qc.compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(qc, "download_to_local", lambda url, suffix: url)

    async def duration(path):
        """两段等时长，允许核对相同原片秒数。"""
        return 12.0

    async def frame(video, at, workdir, ffmpeg):
        """直接返回可区分原片和成片的假帧URL。"""
        return f"{video}/{at}.jpg"

    async def vision(payload):
        """记录完整视觉请求，不触发真实模型成本。"""
        captured.append(payload)
        return raw if raw is not None else _response()

    monkeypatch.setattr(qc.compose, "probe_duration", duration)
    monkeypatch.setattr(qc, "_frame_url", frame)
    monkeypatch.setattr(qc, "vision_chat", vision)
    return captured


def test_target_angles_and_reappearance_pairs(monkeypatch):
    """目标多角度在前，每次出现按原片/最终片配对，并标记非全片验收。"""
    captured = _infra(monkeypatch)
    report = asyncio.run(qc.review_final_output("final.mp4", _params()))
    assert report["status"] == "pass"
    assert report["checked_output_url"] == "final.mp4"
    assert report["full_video_verified"] is False
    assert [sample["source_time"] for sample in report["elements"][0]["samples"]] == [1, 9]
    images = [part["image_url"]["url"] for part in captured[0]["messages"][0]["content"] if part["type"] == "image_url"]
    assert images == ["a.jpg", "b.jpg", "source.mp4/1.jpg", "final.mp4/1.jpg", "source.mp4/9.jpg", "final.mp4/9.jpg"]


@pytest.mark.parametrize("raw", ["不是JSON", "{}", _response(target_match=False), _response(aligned=False), _response(reason="")])
def test_insufficient_evidence_is_unknown(monkeypatch, raw):
    """模型自称通过但缺定位或目标匹配证据时必须降为未知。"""
    _infra(monkeypatch, raw)
    assert asyncio.run(qc.review_final_output("final.mp4", _params()))["status"] == "unknown"


def test_clear_failure_is_not_generation_failure(monkeypatch):
    """明确替错标为fail，报告仍关联已出片URL而不丢弃成片。"""
    _infra(monkeypatch, _response(status="fail", target_match=False, reason="替换成另一产品"))
    report = asyncio.run(qc.review_final_output("final.mp4", _params()))
    assert report["status"] == "fail"
    assert report["checked_output_url"] == "final.mp4"


def test_duration_mismatch_skips_paid_vision(monkeypatch):
    """不同长度不能强行拉伸时间点比较，也不产生视觉费用。"""
    captured = _infra(monkeypatch)

    async def duration(path):
        """模拟输出被截短。"""
        return 12.0 if path == "source.mp4" else 8.0

    monkeypatch.setattr(qc.compose, "probe_duration", duration)
    report = asyncio.run(qc.review_final_output("final.mp4", _params()))
    assert report["status"] == "unknown"
    assert not captured


def test_missing_or_unsampled_observations_do_not_pass(monkeypatch):
    """超过采样上限的观测和缺观测任务均不能被默认为全通过。"""
    _infra(monkeypatch, _response(3))
    params = _params()
    params["reference_elements"][0]["observations"] = [{"time": at} for at in range(5)]
    report = asyncio.run(qc.review_final_output("final.mp4", params))
    assert report["status"] == "unknown"
    assert report["elements"][0]["sampled_count"] == 3
    params["reference_elements"][0]["observations"] = []
    assert asyncio.run(qc.review_final_output("final.mp4", params))["status"] == "unknown"


def test_legacy_without_bindings_is_noop(monkeypatch):
    """旧任务不新增下载或视觉调用。"""
    captured = _infra(monkeypatch)
    assert asyncio.run(qc.review_final_output("final.mp4", {})) is None
    assert not captured


def test_infrastructure_failure_is_unknown(monkeypatch):
    """抽帧异常必须留痕为未知。"""
    _infra(monkeypatch)

    async def frame(*args):
        """模拟ffmpeg失败。"""
        raise RuntimeError("抽帧失败")

    monkeypatch.setattr(qc, "_frame_url", frame)
    assert asyncio.run(qc.review_final_output("final.mp4", _params()))["status"] == "unknown"
