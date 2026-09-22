# -*- coding: utf-8 -*-
"""参考素材预处理:超长参考视频自动裁剪

背景:方舟 Seedance 2.x 对参考视频有时长硬上限(实测 15.2s),超限直接 400,
且错误信息只指向 `content[4]` 这种数组下标 —— 用户看到的就是「生成失败」。
预处理的原则是**尽力而为**:任何一步失败都返回原始 URL,绝不阻断任务。
"""
import asyncio

import pytest

from app.core import media_prep

URL = "https://oss.example.com/ref.mp4"


@pytest.fixture(autouse=True)
def _has_ffmpeg(monkeypatch):
    """默认假定 ffmpeg 可用;需要测「无 ffmpeg」的用例自行覆盖"""
    monkeypatch.setattr(media_prep, "ffmpeg_path", lambda: "ffmpeg")


def test_short_video_returned_as_is(monkeypatch):
    """时长在限内 → 原样返回,不下载不裁剪(零开销)"""
    monkeypatch.setattr(media_prep, "probe_duration", _async(9.5))
    called = {"download": False}
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: called.__setitem__("download", True))
    assert asyncio.run(media_prep.fit_reference_video(URL)) == URL
    assert called["download"] is False


def test_overlong_video_gets_trimmed_and_replaced(monkeypatch):
    """超长 → 下载 → 裁剪 → 上传,返回新地址(用户不必自己剪视频)"""
    monkeypatch.setattr(media_prep, "probe_duration", _async(23.46))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: _touch("src.mp4"))
    monkeypatch.setattr(media_prep, "upload_local_file", lambda *a, **k: "https://oss.example.com/trimmed.mp4")
    monkeypatch.setattr(media_prep, "run", _run_ok())
    result = asyncio.run(media_prep.fit_reference_video(URL))
    assert result == "https://oss.example.com/trimmed.mp4"


def test_trim_passes_time_limit_to_ffmpeg(monkeypatch):
    """裁剪必须真的带上 -t 上限,否则等于没裁"""
    captured = {}

    async def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        _write(cmd[-1])   # 模拟 ffmpeg 产出:输出路径是最后一个参数
        return {"ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(media_prep, "probe_duration", _async(30.0))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: _touch("src.mp4"))
    monkeypatch.setattr(media_prep, "upload_local_file", lambda *a, **k: "https://oss/x.mp4")
    monkeypatch.setattr(media_prep, "run", fake_run)
    asyncio.run(media_prep.fit_reference_video(URL))
    cmd = captured["cmd"]
    assert "-t" in cmd
    assert cmd[cmd.index("-t") + 1] == str(media_prep.MAX_REFERENCE_SECONDS)


def test_probe_failure_keeps_original(monkeypatch):
    """读不出时长(网络抖动/格式怪)不能瞎猜 —— 原样放行,交给模型侧判定"""
    monkeypatch.setattr(media_prep, "probe_duration", _async(None))
    assert asyncio.run(media_prep.fit_reference_video(URL)) == URL


def test_download_failure_keeps_original(monkeypatch):
    monkeypatch.setattr(media_prep, "probe_duration", _async(99.0))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: None)
    assert asyncio.run(media_prep.fit_reference_video(URL)) == URL


def test_upload_failure_keeps_original(monkeypatch):
    """裁剪成功但上传失败 → 必须回退原片(否则等于把参考视频弄丢了)"""
    monkeypatch.setattr(media_prep, "probe_duration", _async(99.0))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: _touch("src.mp4"))
    monkeypatch.setattr(media_prep, "upload_local_file", lambda *a, **k: None)
    monkeypatch.setattr(media_prep, "run", _run_ok())
    assert asyncio.run(media_prep.fit_reference_video(URL)) == URL


def test_no_ffmpeg_keeps_original(monkeypatch):
    monkeypatch.setattr(media_prep, "ffmpeg_path", lambda: None)
    assert asyncio.run(media_prep.fit_reference_video(URL)) == URL


def test_parse_duration_from_stdout(monkeypatch):
    """ffprobe 输出可能带换行;解析失败要返回 None 而不是抛异常"""
    monkeypatch.setattr(media_prep, "run", _run_stdout("23.456790\n"))
    assert asyncio.run(media_prep.probe_duration(URL)) == pytest.approx(23.45679)
    monkeypatch.setattr(media_prep, "run", _run_stdout(""))
    assert asyncio.run(media_prep.probe_duration(URL)) is None


# --- 画幅对齐(方舟编辑只认 ratio=adaptive,成片画幅跟随参考视频) ---

def _run_ratio_fit(monkeypatch, pct, captured):
    """16:9 参考视频 + 目标 9:16 的完整预处理,返回新 URL(captured 里带 ffmpeg 命令)"""
    async def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        _write(cmd[-1])
        return {"ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(media_prep, "probe_duration", _async(9.0))
    monkeypatch.setattr(media_prep, "probe_size", _async((1280, 720)))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: _touch("src.mp4"))
    monkeypatch.setattr(media_prep, "upload_local_file", lambda *a, **k: "https://oss/fixed.mp4")
    monkeypatch.setattr(media_prep, "run", fake_run)
    monkeypatch.setattr(media_prep, "_subject_position_pct", _async(pct))
    return asyncio.run(media_prep.fit_reference_video(URL, ratio="9:16"))


def _vf(captured):
    cmd = captured["cmd"]
    return cmd[cmd.index("-vf") + 1]


def test_ratio_mismatch_triggers_crop(monkeypatch):
    """参考视频 16:9 + 目标 9:16 → 必须裁成目标画幅,否则请求里的 9:16 被静默忽略"""
    captured = {}
    result = _run_ratio_fit(monkeypatch, None, captured)   # 主体位置不可用 → 居中
    assert result == "https://oss/fixed.mp4"
    assert _vf(captured) == "crop=404:720:438:0,scale=720:1280"
    assert "-t" not in captured["cmd"]   # 时长没超,不该顺手裁时长


def test_subject_aware_crop_shifts_window_right(monkeypatch):
    """主体偏右(80%)→ 裁切窗口右移,避免把主体切掉"""
    captured = {}
    _run_ratio_fit(monkeypatch, 80.0, captured)
    assert _vf(captured) == "crop=404:720:822:0,scale=720:1280"


def test_subject_aware_crop_shifts_window_left(monkeypatch):
    """主体偏左(20%)→ 裁切窗口左移"""
    captured = {}
    _run_ratio_fit(monkeypatch, 20.0, captured)
    assert _vf(captured) == "crop=404:720:54:0,scale=720:1280"


def test_parse_pct_variants():
    """模型回复格式不受控:纯数字/带百分号/夹在句子里的都要能取到,不可信的返回 None"""
    assert media_prep._parse_pct("50") == 50.0
    assert media_prep._parse_pct(" 80% ") == 80.0
    assert media_prep._parse_pct("主体大约在75左右") == 75.0
    assert media_prep._parse_pct("") is None
    assert media_prep._parse_pct("居中") is None
    assert media_prep._parse_pct("200") is None                       # 越界视为不可信
    assert media_prep._parse_pct("1") == media_prep.SUBJECT_MIN_PCT   # 结果夹紧


def test_ratio_already_matching_is_noop(monkeypatch):
    """参考视频本来就是目标画幅 → 不下载不转码(零开销)"""
    monkeypatch.setattr(media_prep, "probe_duration", _async(9.0))
    monkeypatch.setattr(media_prep, "probe_size", _async((720, 1280)))
    called = {"download": False}
    monkeypatch.setattr(
        media_prep, "download_to_local", lambda *a, **k: called.__setitem__("download", True)
    )
    assert asyncio.run(media_prep.fit_reference_video(URL, ratio="9:16")) == URL
    assert called["download"] is False


def test_no_ratio_skips_size_probe(monkeypatch):
    """不传 ratio(老调用)不该多一次 ffprobe —— 保持原有零额外开销"""
    called = {"size": False}

    async def fake_size(*a, **k):
        called["size"] = True
        return (1280, 720)

    monkeypatch.setattr(media_prep, "probe_duration", _async(9.0))
    monkeypatch.setattr(media_prep, "probe_size", fake_size)
    assert asyncio.run(media_prep.fit_reference_video(URL)) == URL
    assert called["size"] is False


def test_trim_and_ratio_share_one_ffmpeg_pass(monkeypatch):
    """既超长又画幅不符 → 一次 ffmpeg 同时处理,避免来回下载/上传两遍"""
    captured = {}

    async def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        _write(cmd[-1])
        return {"ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(media_prep, "probe_duration", _async(40.0))
    monkeypatch.setattr(media_prep, "probe_size", _async((1280, 720)))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: _touch("src.mp4"))
    monkeypatch.setattr(media_prep, "upload_local_file", lambda *a, **k: "https://oss/both.mp4")
    monkeypatch.setattr(media_prep, "run", fake_run)
    monkeypatch.setattr(media_prep, "_subject_position_pct", _async(None))

    assert asyncio.run(media_prep.fit_reference_video(URL, ratio="9:16")) == "https://oss/both.mp4"
    cmd = captured["cmd"]
    assert cmd.count("-i") == 1
    assert "-vf" in cmd and "-t" in cmd


# --- 测试替身 ---

def _async(value):
    async def _inner(*a, **k):
        return value
    return _inner


def _touch(name):
    import os
    import tempfile
    path = os.path.join(tempfile.gettempdir(), name)
    with open(path, "wb") as f:
        f.write(b"x")
    return path


def _write(path):
    """模拟 ffmpeg 写出产物文件(实现会校验产物存在,缺了这个判断必然落空)"""
    try:
        with open(path, "wb") as f:
            f.write(b"x")
    except OSError:
        pass


def _run_ok():
    async def _inner(cmd, **k):
        if cmd:
            _write(cmd[-1])
        return {"ok": True, "stdout": "", "stderr": ""}
    return _inner


def _run_stdout(text):
    async def _inner(*a, **k):
        return {"ok": True, "stdout": text, "stderr": ""}
    return _inner
