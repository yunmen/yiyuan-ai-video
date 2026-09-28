# -*- coding: utf-8 -*-
"""对标视频拆解工具:回退契约 + 快乐路径

拆解是"看懂原片"的增强能力,它的失败绝不能把一次任务弄失败 ——
因此每条回退路径都必须返回 success=True 的空分镜。这一组用例钉死该契约,
并验证快乐路径能产出结构化分镜(画面描述来自多模态逆推)。
"""
import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from app.tools import video_understand_tool as vit

# 最小合法 JPEG 字节(仅用于让 _to_data_url 能读到文件头,mime 判定只看扩展名)
_TINY_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


def _run(coro):
    return asyncio.run(coro)


def _tool():
    """构造工具时显式传 base_url/key,避免依赖运行环境里的网关配置"""
    return vit.VideoUnderstandTool(base_url="http://gw.local/v1", api_key="test-key")


def _result_shots(result):
    return json.loads(result.content).get("shots")


# --- 回退契约:任何缺失都返回空分镜且 success=True ---

def test_generate_missing_reference_returns_empty():
    result = _run(_tool().generate({"reference_video": ""}))
    assert result.metadata.get("success") is True
    assert _result_shots(result) == []


def test_generate_ffmpeg_unavailable_returns_empty(monkeypatch):
    """容器没装 ffmpeg → 不拆解、不报错"""
    monkeypatch.setattr(vit.compose, "ffmpeg_path", lambda: None)
    result = _run(_tool().generate({"reference_video": "https://x/ref.mp4"}))
    assert result.metadata.get("success") is True
    assert _result_shots(result) == []


def test_generate_download_failed_returns_empty(monkeypatch):
    """对标视频下载失败 → 空分镜,不抛异常"""
    monkeypatch.setattr(vit.compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(vit, "download_to_local", lambda *a, **k: None)
    result = _run(_tool().generate({"reference_video": "https://x/ref.mp4"}))
    assert result.metadata.get("success") is True
    assert _result_shots(result) == []


def test_generate_no_shots_returns_empty(monkeypatch):
    """镜头检测为空(未检出切点)→ 空分镜"""
    monkeypatch.setattr(vit.compose, "ffmpeg_path", lambda: "ffmpeg")

    async def _detect(source, duration, threshold=None):
        return []

    monkeypatch.setattr(vit.shots, "detect_shots", _detect)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as fp:
        video = fp.name
    monkeypatch.setattr(vit, "download_to_local", lambda *a, **k: video)
    monkeypatch.setattr(vit.compose, "run",
                        _fake_run_duration("Duration: 00:00:10.00, start: 0.000000"))
    try:
        result = _run(_tool().generate({"reference_video": "https://x/ref.mp4"}))
        assert result.metadata.get("success") is True
        assert _result_shots(result) == []
    finally:
        Path(video).unlink(missing_ok=True)


# --- 探时长 ---

def test_probe_duration_parses_ffmpeg_stderr(monkeypatch):
    """ffmpeg -i 以非零退出但会打印 Duration,仍应解析出秒数"""
    monkeypatch.setattr(vit.compose, "run",
                        _fake_run_duration("  Duration: 00:01:23.45, start: 0.000000, bitrate: 1"))
    assert _run(vit._probe_duration_async("x.mp4", "ffmpeg")) == 83.45


def test_probe_duration_returns_zero_when_unparsable(monkeypatch):
    monkeypatch.setattr(vit.compose, "run", _fake_run_duration("no duration here"))
    assert _run(vit._probe_duration_async("x.mp4", "ffmpeg")) == 0.0


# --- 辅助函数 ---

def test_to_data_url_prefixes_correct_mime():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fp:
        fp.write(_TINY_JPEG)
        path = fp.name
    try:
        url = vit._to_data_url(path)
        assert url.startswith("data:image/jpeg;base64,")
    finally:
        Path(path).unlink(missing_ok=True)


def test_vision_messages_structure():
    msgs = vit._vision_messages("sys", [{"type": "text", "text": "hi"}])
    assert msgs[0] == {"role": "system", "content": "sys"}
    assert msgs[1]["role"] == "user" and isinstance(msgs[1]["content"], list)


# --- 快乐路径:产出结构化分镜 ---

def test_generate_returns_storyboard(monkeypatch):
    """完整链路(检测→取帧→多模态逆推)应产出 shots,且描述来自逆推结果"""
    table = [{"index": 0, "start": 0.0, "end": 2.0, "duration": 2.0, "narration": "限时秒杀"}]

    async def _detect(source, duration, threshold=None):
        return table

    async def _narrate(source, shots):
        return shots

    monkeypatch.setattr(vit.shots, "detect_shots", _detect)
    monkeypatch.setattr(vit.shots, "narrate_shots", _narrate)
    monkeypatch.setattr(vit.compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(vit.gateway, "resolve_all", lambda cap: [])

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as fp:
        video = fp.name

    async def _fake_run(cmd, timeout=600, cwd=None, truncate=True):
        # 抽帧命令末位是输出图片路径:写一个最小 jpg 让 _to_data_url 能读到
        last = str(cmd[-1]) if cmd else ""
        if last.endswith(".jpg"):
            with open(last, "wb") as image:
                image.write(_TINY_JPEG)
            return {"ok": True, "stdout": "", "stderr": ""}
        return {"ok": False, "stdout": "", "stderr": "Duration: 00:00:02.00, start: 0.0"}

    monkeypatch.setattr(vit.compose, "run", _fake_run)
    monkeypatch.setattr(vit, "download_to_local", lambda *a, **k: video)
    monkeypatch.setattr(vit, "AsyncOpenAI", _fake_openai('{"shots":[{"index":0,"shot":"特写产品,推镜"}]}'))
    try:
        result = _run(_tool().generate({"reference_video": "https://x/ref.mp4"}))
        storyboard = json.loads(result.content)
        assert result.metadata.get("success") is True
        assert result.metadata.get("shot_count") == 1
        assert storyboard["shots"][0]["narration"] == "限时秒杀"
        assert storyboard["shots"][0]["description"] == "特写产品,推镜"
    finally:
        Path(video).unlink(missing_ok=True)


# --- 假的 compose.run / AsyncOpenAI ---

def _fake_run_duration(stderr: str):
    async def _inner(cmd, timeout=600, cwd=None, truncate=True):
        return {"ok": False, "stdout": "", "stderr": stderr, "error": ""}
    return _inner


def _fake_openai(text: str):
    """返回一个 AsyncOpenAI 替身:chat.completions.create 直接回给定文本"""
    class _Completions:
        async def create(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])

    class _Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=_Completions())

    return _Client
