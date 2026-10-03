# -*- coding: utf-8 -*-
"""退化画面检测(彩条/测试卡/纯色/黑屏)与参考视频像素门槛

判据的实测依据与「宁可漏放、不可误杀」的取舍见 app/core/frame_quality.py 模块文档。
这里钉死的是**方向性**:废片必须被拦下、正常画面必须放行 ——
误杀的代价是「正常成片被判失败 + 白扣用户额度」,远大于漏放一个坏片。
"""
import asyncio
import os
import shutil
import tempfile

import pytest

from app.core import frame_quality as fq
from app.core import media_prep
from app.core.compose import run
from app.settings import config

# 彩条/测试卡的典型像素:几种高饱和纯色块(min 通道为 0 → 饱和度 S=1.0)
_COLOR_BARS = (
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (0, 255, 255), (255, 0, 255), (255, 128, 0), (128, 255, 0),
    (0, 128, 255), (255, 0, 128), (128, 0, 255), (0, 255, 128),
)
# 真实画面的典型像素:亮度接近、通道差值小(低饱和),且因渐变/噪点产生大量颜色
_NORMAL_PIXELS = (
    (100, 110, 105), (104, 112, 108), (108, 115, 111), (112, 118, 114),
    (116, 121, 117), (120, 124, 120), (124, 127, 123), (128, 130, 126),
    (132, 133, 129), (136, 136, 132), (140, 139, 135), (144, 142, 138),
)


def _bytes(spec, count=240):
    """按 (颜色列表, 是否逐像素轮转) 生成 rgb24 像素流

    spec 为颜色元组时轮转取色(模拟多色画面);为单色时整段同色(模拟纯色/黑屏)。
    """
    out = bytearray()
    for i in range(count):
        out += bytes(spec[i % len(spec)])
    return bytes(out)


def _temp_frame():
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    return path


def _patch_pixels(monkeypatch, data):
    """替换底层取像素:单测只验证统计与判定,不真跑 ffmpeg"""

    async def fake(path, timeout=60):
        return data

    monkeypatch.setattr(fq, "_read_pixels", fake)


# --- 像素统计 ---

def test_analyze_pixels_counts_colors_and_high_saturation():
    colors, high_sat, total = fq.analyze_pixels(_bytes(_COLOR_BARS))
    assert colors == len(_COLOR_BARS)
    assert total == 240
    assert high_sat == total, "彩条每个像素都应是高饱和(min 通道为 0)"


def test_analyze_pixels_low_saturation_for_real_scene():
    colors, high_sat, total = fq.analyze_pixels(_bytes(_NORMAL_PIXELS))
    assert colors > fq._PURE_COLOR_MAX, "真实画面颜色数必须多于纯色画面(否则会被判黑屏)"
    assert high_sat / total < fq._MAX_HIGH_SAT_RATIO


def test_analyze_pixels_pure_black():
    colors, high_sat, total = fq.analyze_pixels(_bytes(((0, 0, 0),)))
    assert colors == 1, "纯黑只有一种颜色(由判据 B 兜住)"
    assert high_sat == 0, "纯黑 max=0,不参与饱和度统计(不能除零)"


# --- 单帧判定 ---

def test_color_bars_are_blocked(monkeypatch):
    path = _temp_frame()
    try:
        _patch_pixels(monkeypatch, _bytes(_COLOR_BARS))
        reason = asyncio.run(fq.detect_degenerate_frame(path))
        assert reason and "彩条" in reason, "彩条测试卡必须被拦下"
    finally:
        os.remove(path)


def test_pure_color_frame_is_blocked(monkeypatch):
    """低饱和的纯色/黑屏由判据 B(唯一颜色数)兜住 —— 判据 A 对它们无效"""
    path = _temp_frame()
    try:
        _patch_pixels(monkeypatch, _bytes(((240, 240, 240),)))
        reason = asyncio.run(fq.detect_degenerate_frame(path))
        assert reason and "纯色" in reason
    finally:
        os.remove(path)


def test_normal_frame_passes(monkeypatch):
    path = _temp_frame()
    try:
        _patch_pixels(monkeypatch, _bytes(_NORMAL_PIXELS))
        assert asyncio.run(fq.detect_degenerate_frame(path)) is None, "正常画面不得误杀"
    finally:
        os.remove(path)


def test_missing_file_and_empty_pixels_pass(monkeypatch):
    """测不出来一律放行:兜底校验绝不能反过来把任务搞失败"""
    assert asyncio.run(fq.detect_degenerate_frame("/not/exists.jpg")) is None
    _patch_pixels(monkeypatch, b"")
    assert asyncio.run(fq.detect_degenerate_frame(_temp_frame())) is None


def test_probe_exception_passes(monkeypatch):
    async def boom(path, timeout=60):
        raise RuntimeError("ffmpeg 挂了")

    monkeypatch.setattr(fq, "_read_pixels", boom)
    assert asyncio.run(fq.detect_degenerate_frame(_temp_frame())) is None


def test_any_degenerate_frame_blocks(monkeypatch):
    """多帧中只要有一帧是彩条就判失败:一帧彩条足以让整条成片变成彩条片"""
    first, second = _temp_frame(), _temp_frame()
    try:
        async def fake(path, timeout=60):
            return _bytes(_NORMAL_PIXELS) if path == first else _bytes(_COLOR_BARS)

        monkeypatch.setattr(fq, "_read_pixels", fake)
        assert asyncio.run(fq.detect_degenerate_frames([first, second]))
        assert asyncio.run(fq.detect_degenerate_frames([first])) is None
    finally:
        os.remove(first)
        os.remove(second)


# --- 成片侧多帧抽样 ---

def test_probe_times_avoid_first_and_last_frame():
    """采样点必须内缩:短视频片头黑场/片尾淡出会被当成黑屏误杀"""
    assert fq._probe_times(5.0, 3) == [1.25, 2.5, 3.75]
    assert fq._probe_times(0, 3) == [], "时长未知时不抽样(宁可漏放)"


def _async_value(value):
    """构造一个恒返回 value 的异步桩(probe_duration/probe_size 都是协程)"""
    async def _fn(*a, **k):
        return value
    return _fn


def _patch_extract(monkeypatch, created):
    async def fake_run(cmd, **kwargs):
        if not created["ok"]:
            return {"ok": False, "stdout": "", "stderr": "boom"}
        open(cmd[-1], "wb").close()   # 产物必须真实存在,否则视为抽帧失败
        created.setdefault("files", []).append(cmd[-1])
        return {"ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(fq, "run", fake_run)


def test_video_all_frames_degenerate_is_blocked(monkeypatch):
    """整段都是彩条(实测 task 59 的成片)→ 拦下"""
    video = _temp_frame()
    created = {"ok": True}
    try:
        monkeypatch.setattr(media_prep, "probe_duration", _async_value(5.0))
        _patch_extract(monkeypatch, created)
        _patch_pixels(monkeypatch, _bytes(_COLOR_BARS))
        reason = asyncio.run(fq.detect_degenerate_video(video))
        assert reason and "彩条" in reason
        assert len(created.get("files", [])) == 3, "默认抽 3 帧"
    finally:
        os.remove(video)


def test_video_with_one_normal_frame_passes(monkeypatch):
    """成片已付费:只要有一帧正常就放行(与参考侧"任一帧退化即失败"刻意相反)"""
    video = _temp_frame()
    created = {"ok": True}
    try:
        monkeypatch.setattr(media_prep, "probe_duration", _async_value(5.0))
        _patch_extract(monkeypatch, created)

        async def fake(path, timeout=60):
            # 只有第一帧是彩条(片头黑场/淡入同理),其余正常
            return _bytes(_COLOR_BARS) if path.endswith("probe_0.jpg") else _bytes(_NORMAL_PIXELS)

        monkeypatch.setattr(fq, "_read_pixels", fake)
        assert asyncio.run(fq.detect_degenerate_video(video)) is None
    finally:
        os.remove(video)


def test_video_unknown_duration_or_extract_failure_passes(monkeypatch):
    """时长测不出 / 抽不出帧 → 放行,不做无依据的判定"""
    video = _temp_frame()
    try:
        monkeypatch.setattr(media_prep, "probe_duration", _async_value(None))
        assert asyncio.run(fq.detect_degenerate_video(video)) is None

        monkeypatch.setattr(media_prep, "probe_duration", _async_value(5.0))
        _patch_extract(monkeypatch, {"ok": False})
        assert asyncio.run(fq.detect_degenerate_video(video)) is None
    finally:
        os.remove(video)


# --- 真实 ffmpeg 生成的退化画面(不 mock 像素,验证完整取样链路)---
#
# 上面的用例用构造像素验证判定逻辑;这里用 ffmpeg 真实生成的测试卡/纯色帧再验一遍,
# 覆盖 _probe_size → ffmpeg 抽像素 → analyze_pixels 整条链路(判据是在这类画面上定的)。
# 联网的真实照片样本见 scripts/check_frame_quality_samples.py(误报率要联网量,不进 CI)。

_FFMPEG_CASES = {
    "彩条测试卡(smptebars)": "smptebars=size=640x360:rate=1:duration=1",
    "电视测试图(testsrc)": "testsrc=size=640x360:rate=1:duration=1",
    "纯黑": "color=c=black:s=640x360:d=1",
    "纯白": "color=c=white:s=640x360:d=1",
    "纯灰": "color=c=gray:s=640x360:d=1",
}


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="需要本机 ffmpeg")
def test_real_degenerate_frames_are_blocked():
    workdir = tempfile.mkdtemp(prefix="degenerate_")
    try:
        for name, filt in _FFMPEG_CASES.items():
            path = os.path.join(workdir, f"{name}.jpg")
            assert asyncio.run(run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", filt,
                "-frames:v", "1", "-q:v", "2", path,
            ], timeout=60)).get("ok"), f"生成失败: {name}"
            assert os.path.exists(path), f"没有产物: {name}"
            assert asyncio.run(fq.detect_degenerate_frame(path)), f"{name} 必须被拦下"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --- 判据阈值可配(阈值是在有限样本上定的,必须允许按素材类型调)---

def test_high_sat_threshold_default(monkeypatch):
    monkeypatch.setattr(config, "FRAME_HIGH_SAT_RATIO", "")
    assert fq._high_sat_threshold() == fq._MAX_HIGH_SAT_RATIO


def test_high_sat_threshold_configurable(monkeypatch):
    """素材普遍高饱和(花卉/霓虹)时放宽到 0.85,那张 71% 的正常画面就不会再被误杀"""
    monkeypatch.setattr(config, "FRAME_HIGH_SAT_RATIO", "0.85")
    assert fq._high_sat_threshold() == 0.85


def test_high_sat_threshold_rejects_nonsense(monkeypatch):
    """配错(非数字/越界)一律回退默认:否则一次手误就会全量误杀或全量漏放"""
    for bad in ("abc", "0.1", "1.5", "-0.7", "0"):
        monkeypatch.setattr(config, "FRAME_HIGH_SAT_RATIO", bad)
        assert fq._high_sat_threshold() == fq._MAX_HIGH_SAT_RATIO, f"{bad!r} 应回退默认"


def _mixed_pixels(high_ratio: float, count: int = 240) -> bytes:
    """按比例混合高饱和与低饱和像素:模拟"高饱和但仍有内容"的画面"""
    out = bytearray()
    n_high = int(count * high_ratio)
    for i in range(count):
        spec = _COLOR_BARS if i < n_high else _NORMAL_PIXELS
        out += bytes(spec[i % len(spec)])
    return bytes(out)


def test_threshold_actually_applies(monkeypatch):
    """同一张 71% 高饱和的画面:默认阈值(0.70)拦下,放宽到 0.85 后放行"""
    path = _temp_frame()
    try:
        _patch_pixels(monkeypatch, _mixed_pixels(0.71))
        assert asyncio.run(fq.detect_degenerate_frame(path, max_high_sat_ratio=0.70)) is not None
        assert asyncio.run(fq.detect_degenerate_frame(path, max_high_sat_ratio=0.85)) is None
        # 配置也要能改到默认值(不走参数时读配置)
        monkeypatch.setattr(config, "FRAME_HIGH_SAT_RATIO", "0.85")
        assert asyncio.run(fq.detect_degenerate_frame(path)) is None
    finally:
        os.remove(path)


# --- 参考视频像素门槛 ---

def test_reference_below_threshold_is_rejected(monkeypatch):
    monkeypatch.setattr(media_prep, "probe_size", _async_value((360, 640)))
    reason = asyncio.run(fq.check_reference_video_pixels("https://x/ref.mp4", 407696))
    assert reason and "407696" in reason and "360x640" in reason


def test_reference_above_threshold_passes(monkeypatch):
    monkeypatch.setattr(media_prep, "probe_size", _async_value((720, 1280)))
    assert asyncio.run(fq.check_reference_video_pixels("https://x/ref.mp4", 407696)) is None


def test_reference_check_disabled_when_threshold_zero(monkeypatch):
    """门槛 0 = 关闭校验(拿不到确切门槛时不猜,绝不误杀)"""
    monkeypatch.setattr(media_prep, "probe_size", _async_value((360, 640)))
    assert asyncio.run(fq.check_reference_video_pixels("https://x/ref.mp4", 0)) is None


def test_reference_probe_failure_passes(monkeypatch):
    """测不出分辨率一律放行:校验的目的是省掉注定失败的调用,不是拦任务"""
    monkeypatch.setattr(media_prep, "probe_size", _async_value(None))
    assert asyncio.run(fq.check_reference_video_pixels("https://x/ref.mp4", 407696)) is None
    assert asyncio.run(fq.check_reference_video_pixels("", 407696)) is None
