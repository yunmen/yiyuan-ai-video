# -*- coding: utf-8 -*-
"""真人去身份化:拦截判定 + 自动处理链路(含缓存/失败回退)。

背景:方舟对**输入视频含真人**直接拒绝(平台隐私策略,与提示词无关)。
素材已获授权、只是需要过检测时,worker 会自动本地去身份化后重试一次 ——
这里把"什么错误才重试""处理不出来怎么办"钉死,避免退化成"每次失败都白跑一遍去真人"。
"""
import asyncio
import os
import shutil
import tempfile

import pytest

from app.core import deidentify, media_prep

BLOCKED_VIDEO = (
    '视频编辑提交异常(候选网关已全部尝试): 方舟返回 400: {"error":{"code":'
    '"InputVideoSensitiveContentDetected.PrivacyInformation","message":"The request failed '
    "because the input video 'content[1]' may contain real person.\"}}"
)
BLOCKED_IMAGE = (
    '图生视频提交异常(候选网关已全部尝试): 方舟返回 400: {"error":{"code":'
    '"InputImageSensitiveContentDetected.PrivacyInformation","message":"The request failed '
    "because the input image 'content[1]' may contain real person.\"}}"
)
OTHER_ERROR = '视频编辑提交异常(候选网关已全部尝试): 方舟返回 401: {"error":{"code":"AuthenticationError"}}'


def test_video_block_is_detected():
    assert deidentify.is_input_video_blocked(BLOCKED_VIDEO) is True


def test_image_block_is_not_treated_as_video():
    """图片被判定含真人时**不能**走"去真人"重试:图片就是要被替换的主体,打码等于糊掉目标"""
    assert deidentify.is_input_image_blocked(BLOCKED_IMAGE) is True
    assert deidentify.is_input_video_blocked(BLOCKED_IMAGE) is False


def test_other_errors_are_not_blocks():
    assert deidentify.is_input_video_blocked(OTHER_ERROR) is False
    assert deidentify.is_input_image_blocked(OTHER_ERROR) is False
    assert deidentify.is_input_video_blocked("") is False


def test_message_only_form_is_detected():
    """异步失败时只有 message 形态(没有 code),也要能认出来"""
    text = "the input video 'content[1]' may contain real person"
    assert deidentify.is_input_video_blocked(text) is True


def _stub_media(monkeypatch, detect_result, new_url="https://oss/deid.mp4"):
    """打桩下载/检测/上传,只验证编排与缓存"""
    calls = {"download": 0, "detect": 0, "upload": 0}

    def fake_download(url, suffix=".mp4"):
        calls["download"] += 1
        import tempfile
        fd, path = tempfile.mkstemp(suffix=suffix)
        import os
        os.close(fd)
        return path

    def fake_detect(src, out, *a, **k):
        calls["detect"] += 1
        if detect_result.get("detected"):
            open(out, "wb").write(b"x")
        return detect_result

    monkeypatch.setattr(media_prep, "download_to_local", fake_download)
    monkeypatch.setattr(media_prep.deidentify, "deidentify_video", fake_detect)
    monkeypatch.setattr(media_prep, "upload_local_file",
                        lambda path, key: (calls.__setitem__("upload", calls["upload"] + 1), new_url)[1])
    monkeypatch.setattr(media_prep, "ffmpeg_path", lambda: "ffmpeg")
    media_prep._DEID_CACHE.clear()
    return calls


def test_deidentify_returns_new_url_when_person_found(monkeypatch):
    calls = _stub_media(monkeypatch, {"detected": True, "hits": 3, "box": (0, 0, 10, 10)})

    url = asyncio.run(media_prep.deidentify_reference_video("https://oss/ref.mp4"))

    assert url == "https://oss/deid.mp4"
    assert calls["detect"] == 1 and calls["upload"] == 1


def test_deidentify_keeps_original_when_no_person(monkeypatch):
    """不含真人 → 原样返回(只多一次检测,不产出新文件、不额外上传)"""
    calls = _stub_media(monkeypatch, {"detected": False, "hits": 0})

    url = asyncio.run(media_prep.deidentify_reference_video("https://oss/ref.mp4"))

    assert url == "https://oss/ref.mp4"
    assert calls["upload"] == 0


def test_deidentify_is_cached(monkeypatch):
    """同一参考视频重复处理必须命中缓存:否则每次提交都白跑一次检测+上传"""
    calls = _stub_media(monkeypatch, {"detected": True, "hits": 1, "box": (0, 0, 4, 4)})
    src = "https://oss/ref-same.mp4"

    first = asyncio.run(media_prep.deidentify_reference_video(src))
    second = asyncio.run(media_prep.deidentify_reference_video(src))

    assert first == second == "https://oss/deid.mp4"
    assert calls["detect"] == 1 and calls["upload"] == 1


def test_deidentify_falls_back_to_original_on_error(monkeypatch):
    """处理失败 → 保留原片(不能因为"增强项"失败把原失败结果也搅乱)"""
    def boom(*a, **k):
        raise RuntimeError("ffmpeg 挂了")
    _stub_media(monkeypatch, {"detected": True})
    monkeypatch.setattr(media_prep.deidentify, "deidentify_video", boom)

    url = asyncio.run(media_prep.deidentify_reference_video("https://oss/ref-err.mp4"))

    assert url == "https://oss/ref-err.mp4"


# --- 检测召回:漏检 = 去身份化产不出新视频 = 编辑不重试 = 整单失败 ---

class _FakeClf:
    """假级联:只在宽松参数(minNeighbors=3)下命中,模拟"远景小脸/侧脸严格轮漏检\""""

    def __init__(self, box=(10, 10, 40, 40)):
        self._box = box
        self.calls = []

    def empty(self):
        return False

    def detectMultiScale(self, gray, scaleFactor=1.1, minNeighbors=5, minSize=None):
        self.calls.append((scaleFactor, minNeighbors, minSize))
        return [self._box] if minNeighbors == 3 else []


def _workdir_with_frame():
    """造一个含一帧抽样的临时目录(检测只读这里的 jpg)"""
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    workdir = tempfile.mkdtemp(prefix="deid_union_")
    cv2.imwrite(os.path.join(workdir, "s_001.jpg"), np.zeros((60, 80, 3), dtype="uint8"))
    return workdir


def test_detect_union_falls_back_to_loose_pass(monkeypatch):
    """严格轮漏检时必须还有宽松轮兜底

    调用方只在"平台已判定含真人"时才走到这里,漏检就直接导致换产品/换人物整单失败,
    所以宁可多检(框略大)也不能漏。
    """
    pytest.importorskip("cv2")
    clf = _FakeClf()
    monkeypatch.setattr(deidentify, "_load_cascades", lambda: ([clf], [], []))
    workdir = _workdir_with_frame()
    try:
        box, hits = deidentify._detect_union(workdir, 480, 640)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    assert box is not None and hits == 1
    assert any(n == 3 for (_, n, _) in clf.calls), "必须走过宽松轮"


def test_detect_union_clamps_oversized_box(monkeypatch):
    """宽松轮可能检出占满画面的框 —— 必须夹紧,否则原片场景被全糊、编辑模型没有锚点"""
    pytest.importorskip("cv2")
    clf = _FakeClf(box=(0, 0, 80, 60))          # 整帧都被判成真人
    monkeypatch.setattr(deidentify, "_load_cascades", lambda: ([clf], [], []))
    workdir = _workdir_with_frame()
    try:
        box, _ = deidentify._detect_union(workdir, 480, 640)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    _, _, w, h = box
    assert w <= 480 * deidentify.BOX_MAX_W_RATIO + 2
    assert h <= 640 * deidentify.BOX_MAX_H_RATIO + 2
