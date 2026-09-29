# -*- coding: utf-8 -*-
"""成片自检必须把"参考视频没生效"暴露出来,而不是靠裁切把它掩盖掉。

真实事故(task=20,替换主角):编辑模型返回的成片是 1280x720 横版,而参考原片是 540x1168
竖版 —— 说明模型压根没把原片当编辑输入(替换必然没发生)。但旧逻辑只把画幅偏差当"小问题",
顺手居中裁成 9:16 就交付了;16:9 裁成 9:16 只保留约 31% 宽度,主体被整段切走,
用户看到的就是"主角没看到、狗推婴儿车也没了"。

现在两条硬规则:
  · 主体位置识别失败时,成片修正**不赌居中裁切** —— 放弃修正、保留原片(allow_center_crop);
  · 成片画幅既不像目标、也不像原片 → 打 reference_ignored;有替换意图时判失败,
    不交付"看着成功、其实没替换"的片子。无替换意图的纯复刻仍只打标不阻断。
"""
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock

from app.core import media_prep
from app.schemas.base import ToolResult
from app.settings import config
from app.tools.video_tool import VideoGenTool

URL = "https://oss.example.com/ref.mp4"


def _tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _async(value):
    async def _fn(*a, **k):
        return value
    return _fn


def _temp_file(suffix=".mp4"):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def _ffmpeg_ok(captured, created):
    async def _run(cmd, **kwargs):
        captured.setdefault("cmds", []).append(cmd)   # 抽帧也会调 ffmpeg,故记录全部命令
        open(cmd[-1], "wb").close()   # 产物必须真实存在,否则 media_prep 视为失败
        created.append(cmd[-1])
        return {"ok": True, "stdout": "", "stderr": ""}
    return _run


def _cropped(captured):
    """是否出现"裁切+缩放"那一路 ffmpeg 命令(抽帧命令里也有 -vf,不能用它判断)"""
    return any(any("crop=" in str(part) for part in cmd) for cmd in captured.get("cmds", []))


# --- 主体位置识别失败时的裁切策略 ---

def test_fit_reference_video_skips_crop_when_subject_unknown(monkeypatch):
    """不允许居中兜底时:主体识别失败 → 不裁、不转码、保留原片

    成片修正场景专用。居中硬裁会切走主体,而用户看不出成片已被切坏 ——
    宁可画幅不修正(由上层判失败),也不要交付一个主体残缺的片子。
    """
    captured, created, uploaded = {}, [], {"n": 0}
    monkeypatch.setattr(media_prep, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(media_prep, "probe_duration", _async(9.0))
    monkeypatch.setattr(media_prep, "probe_size", _async((1280, 720)))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: _temp_file())
    monkeypatch.setattr(media_prep, "run", _ffmpeg_ok(captured, created))
    monkeypatch.setattr(media_prep, "_subject_position_pct", _async(None))

    def _count_upload(*a, **k):
        uploaded["n"] += 1
        return "https://oss/fixed.mp4"

    monkeypatch.setattr(media_prep, "upload_local_file", _count_upload)

    result = asyncio.run(
        media_prep.fit_reference_video(URL, ratio="9:16", allow_center_crop=False)
    )

    assert result == URL, "放弃裁切时必须原样返回,让上层据 output_mismatch 判失败"
    assert not _cropped(captured), "主体位置未知时不得裁切(裁切就是赌博)"
    assert uploaded["n"] == 0, "没有产物就不该上传"


def test_fit_reference_video_center_crops_by_default(monkeypatch):
    """默认(参考视频规整阶段)仍允许居中兜底:不裁会让编辑任务画幅必然跑偏"""
    captured, created = {}, []
    monkeypatch.setattr(media_prep, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(media_prep, "probe_duration", _async(9.0))
    monkeypatch.setattr(media_prep, "probe_size", _async((1280, 720)))
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: _temp_file())
    monkeypatch.setattr(media_prep, "run", _ffmpeg_ok(captured, created))
    monkeypatch.setattr(media_prep, "_subject_position_pct", _async(None))
    monkeypatch.setattr(media_prep, "upload_local_file", lambda *a, **k: "https://oss/fixed.mp4")

    result = asyncio.run(media_prep.fit_reference_video(URL, ratio="9:16"))

    assert result == "https://oss/fixed.mp4"
    assert any("crop=404:720:438:0,scale=720:1280" in str(part)
               for cmd in captured["cmds"] for part in cmd), "居中兜底裁切必须仍然生效"


# --- 成片画幅三态判定 ---

def _setup(monkeypatch, tool, out_size, ref_size):
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "seedance-2-5-260628")
    monkeypatch.setattr(media_prep, "download_to_local", lambda *a, **k: "")

    async def fake_size(url):
        return out_size if "edit" in url else ref_size

    async def fake_duration(url):
        return 7.0

    monkeypatch.setattr(media_prep, "probe_size", fake_size)
    monkeypatch.setattr(media_prep, "probe_duration", fake_duration)

    async def fake_edit(prompt, **kwargs):
        return ToolResult(content="https://x/edit.mp4", metadata={"success": True})

    tool.edit_video = fake_edit


def _generate(tool, intent=None):
    params = {
        "prompt": "复刻",
        "materials": ["https://x/a.jpg"],
        "reference_video": "https://x/ref.mp4",
    }
    if intent:
        params["intent"] = intent
    return asyncio.run(tool.generate(params))


def test_reference_video_ignored_is_flagged(monkeypatch):
    """成片画幅既不像目标(9:16)、也不像原片(540x1168) → 明确标注参考视频未生效"""
    tool = _tool()
    _setup(monkeypatch, tool, out_size=(1280, 720), ref_size=(540, 1168))

    result = _generate(tool)   # 纯复刻,无替换意图

    mismatch = result.metadata.get("output_mismatch") or {}
    assert mismatch.get("reference_ignored") is True
    assert "参考视频未生效" in (mismatch.get("reason") or "")
    assert result.metadata["success"] is True, "纯复刻仍只打标:成片已付费,残缺也比没有强"


def test_replace_intent_fails_when_reference_video_ignored(monkeypatch):
    """有替换意图时判失败:交付"看着成功其实没替换"的片子比失败更糟"""
    tool = _tool()
    _setup(monkeypatch, tool, out_size=(1280, 720), ref_size=(540, 1168))

    result = _generate(tool, intent=["person"])

    assert result.metadata["success"] is False
    assert result.metadata["error_type"] == "output_mismatch"
    assert "替换人物失败" in result.metadata["error"]
    assert "返还额度" in result.metadata["error"], "失败必须说清额度会返还,否则用户以为白扣"


def test_output_following_reference_is_not_flagged(monkeypatch):
    """成片画幅 ≈ 原片画幅 → 编辑确实采用了原片,不得误报(否则判失败会误伤正常单)"""
    tool = _tool()
    _setup(monkeypatch, tool, out_size=(540, 1168), ref_size=(540, 1168))

    result = _generate(tool, intent=["person"])

    mismatch = result.metadata.get("output_mismatch") or {}
    assert mismatch.get("reference_ignored") is None
    assert result.metadata["success"] is True
