# -*- coding: utf-8 -*-
"""原片元素槽位检测单测(worker/app/services/element_detect.py)。

覆盖:
  - 正常解析:含可选 bbox 与时间跨度(start/end)的元素被解析为带定位信息的槽位;
  - 可选字段容错:bbox 为 null / 非法种类 / 空 label 的元素被正确忽略或降级;
  - 视觉返回非 JSON → 解析降级为空(不阻断复刻);
  - 视觉调用抛异常 → 整体降级为空(增强能力,绝不阻断);
  - 下载失败 / ffmpeg 不可用 / 空视频地址 → 直接返回空(边界与降级)。
"""
import asyncio
import os
import tempfile

from app.services import element_detect


def _patch(monkeypatch, vision_return, *, download=True, duration="00:00:12.00"):
    """把检测链路依赖的统一替成可控桩:下载/上传/视觉/ffmpeg。

    download=True(默认) → 在真实临时目录建一个本地文件,抽帧输出目录(dirname)一定存在,
    避免 Windows/Linux 路径差异导致的假失败;download=False → 模拟下载失败(返回 None)。
    compose.run 桩:抽帧命令(-frames:v)在输出路径(命令末位)创建空文件,
    满足 _extract_frames 的 os.path.exists 校验;其余视为时长探测返回 Duration。
    """
    # 注意:download_to_local / upload_local_file 真实实现是同步函数,
    # 由代码以 asyncio.to_thread 调用,因此这里用普通函数(非 async)打桩。
    local_path = None
    if download is True:
        tmp = tempfile.mkdtemp()
        local_path = os.path.join(tmp, "ref.mp4")
        with open(local_path, "w"):
            pass
    elif isinstance(download, str):
        local_path = download

    def fake_download(url, suffix=".mp4"):
        return local_path

    def fake_upload(path, key):
        return f"http://oss/{key}"

    async def fake_run(cmd, timeout=60, truncate=True):
        if "-frames:v" in cmd:
            out = cmd[-1]
            try:
                parent = os.path.dirname(out) or "."
                os.makedirs(parent, exist_ok=True)
                with open(out, "w"):
                    pass
            except OSError:
                pass
            return {"ok": True, "stdout": "", "stderr": ""}
        return {"stderr": f"Duration: {duration}, start: 0.000", "stdout": ""}

    async def fake_vision(payload):
        if isinstance(vision_return, Exception):
            raise vision_return
        return vision_return

    monkeypatch.setattr(element_detect, "download_to_local", fake_download)
    monkeypatch.setattr(element_detect, "upload_local_file", fake_upload)
    monkeypatch.setattr(element_detect, "vision_chat", fake_vision)
    monkeypatch.setattr(element_detect.compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(element_detect.compose, "run", fake_run)


def test_detect_elements_parses_slots_with_bbox_and_span(monkeypatch):
    """视觉返回含 bbox 与时间跨度的元素 → 解析为带定位信息的槽位列表"""
    _patch(monkeypatch, (
        '{"elements":['
        '{"kind":"person","label":"戴眼镜的男士","frame_index":0,"bbox":[0.1,0.2,0.5,0.8],"start":0,"end":8},'
        '{"kind":"product","label":"红色易拉罐","frame_index":2,"bbox":null,"start":3,"end":12}'
        ']}'
    ))
    result = asyncio.run(element_detect.detect_elements("http://oss/ref.mp4"))

    assert len(result) == 2
    assert result[0]["id"] == "e0"
    assert result[0]["kind"] == "person"
    assert result[0]["label"] == "戴眼镜的男士"
    assert result[0]["bbox"] == [0.1, 0.2, 0.5, 0.8]
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 8.0
    # bbox 为 null 的元素不纳入 bbox 字段,但时间跨度仍保留
    assert "bbox" not in result[1]
    assert result[1]["start"] == 3.0
    assert result[1]["end"] == 12.0


def test_detect_elements_ignores_invalid_kind_and_missing_label(monkeypatch):
    """非法 kind / 空 label 的元素被过滤,不影响其余"""
    _patch(monkeypatch, (
        '{"elements":['
        '{"kind":"unknown","label":"怪东西"},'
        '{"kind":"person","label":""},'
        '{"kind":"scene","label":"咖啡馆室内","frame_index":1}'
        ']}'
    ))
    result = asyncio.run(element_detect.detect_elements("http://oss/ref.mp4"))
    assert [e["kind"] for e in result] == ["scene"]


def test_detect_elements_clamps_span_to_duration(monkeypatch):
    """时间跨度被夹取到 [0, 视频时长],避免模型臆造超出范围"""
    _patch(monkeypatch, (
        '{"elements":['
        '{"kind":"person","label":"主角","frame_index":0,"start":-5,"end":999}'
        ']}'
    ), duration="00:00:10.00")
    result = asyncio.run(element_detect.detect_elements("http://oss/ref.mp4"))
    assert len(result) == 1
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 10.0


def test_detect_elements_empty_when_vision_not_json(monkeypatch):
    """视觉返回非 JSON → 解析降级为空列表(不阻断复刻)"""
    _patch(monkeypatch, "抱歉,我无法识别这段视频")
    assert asyncio.run(element_detect.detect_elements("http://oss/ref.mp4")) == []


def test_detect_elements_empty_when_vision_raises(monkeypatch):
    """视觉调用抛异常 → 整体降级为空列表(增强能力,绝不阻断)"""
    _patch(monkeypatch, RuntimeError("视觉网关 500"))
    assert asyncio.run(element_detect.detect_elements("http://oss/ref.mp4")) == []


def test_detect_elements_empty_when_download_fails(monkeypatch):
    """对标视频下载失败 → 跳过检测返回空(不阻断)"""
    _patch(monkeypatch, "", download=False)
    assert asyncio.run(element_detect.detect_elements("http://oss/ref.mp4")) == []


def test_detect_elements_empty_when_no_ffmpeg(monkeypatch):
    """ffmpeg 不可用 → 跳过检测返回空"""
    async def fake_download(url, suffix=".mp4"):
        return "/tmp/ref.mp4"

    monkeypatch.setattr(element_detect, "download_to_local", fake_download)
    monkeypatch.setattr(element_detect.compose, "ffmpeg_path", lambda: "")
    assert asyncio.run(element_detect.detect_elements("http://oss/ref.mp4")) == []


def test_detect_elements_empty_when_no_reference():
    """空视频地址直接返回空(边界)"""
    assert asyncio.run(element_detect.detect_elements("")) == []


def test_observations_keep_reappearance_without_filling_gap():
    """离场后再次出现归属同一元素，但不补齐中间空档或接受未上传帧。"""
    text = '{"elements":[{"kind":"product","label":"红罐","observations":[{"frame_index":0,"bbox":[0,0,0.4,0.4]},{"frame_index":2},{"frame_index":1},{"frame_index":99}]}]}'
    table = [{"index": 0, "start": 0, "duration": 4}, {"index": 1, "start": 4, "duration": 4}, {"index": 2, "start": 8, "duration": 4}]
    result = element_detect._parse_elements(text, [1, 5, 9], ["a", None, "c"], 12, table)
    assert [point["time"] for point in result[0]["observations"]] == [1, 9]
    assert [point["shot_index"] for point in result[0]["observations"]] == [0, 2]
    assert "start" not in result[0]
    assert element_detect._parse_bbox({"bbox": [0.5, 0, 0.1, 1]}) == {}
    assert element_detect._parse_span({"start": 2}, 12) == {}
    assert element_detect._parse_span({"start": 2, "end": 2}, 12) == {}
