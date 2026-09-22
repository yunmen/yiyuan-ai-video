# -*- coding: utf-8 -*-
"""视频编辑:输入视频被判定含真人 → 本地去身份化后重试**一次**,且"已打码"必须可感知。

用户场景(desktop):上传一段真人视频,想把真人替换成参考图。
方舟对含真人的输入视频直接拒绝(平台隐私策略),所以这条路径必须能自动兜底;
但兜底有画面代价(打码处就是要被替换的主体),因此不能静默、也不能反复重试。
"""
import asyncio
from unittest.mock import AsyncMock

from app.core import media_prep
from app.schemas.base import ToolResult
from app.tools.video_tool import VideoGenTool

REF = "https://oss/ref.mp4"
IMG = "https://oss/a.jpg"
BLOCKED = (
    '视频编辑提交异常(候选网关已全部尝试): 方舟返回 400: {"error":{"code":'
    '"InputVideoSensitiveContentDetected.PrivacyInformation","message":"The request failed '
    "because the input video 'content[1]' may contain real person.\"}}"
)


def _tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _ok(url="https://oss/v.mp4"):
    return ToolResult(content=url, metadata={"success": True, "model": "m"})


def _fail(err):
    return ToolResult(content="", metadata={"success": False, "error": err})


def _stub(monkeypatch, tool, submit_results, deid_url="https://oss/deid.mp4"):
    """打桩:跳过参考视频预处理、固定提交结果、记录去身份化调用"""
    async def fake_fit(url, **kwargs):
        return url

    monkeypatch.setattr(media_prep, "fit_reference_video", fake_fit)
    submit = AsyncMock(side_effect=submit_results)
    monkeypatch.setattr(tool, "_submit_and_poll", submit)
    deid = AsyncMock(return_value=deid_url)
    monkeypatch.setattr(media_prep, "deidentify_reference_video", deid)
    return submit, deid


def test_retries_with_deidentified_video_after_block(monkeypatch):
    tool = _tool()
    submit, deid = _stub(monkeypatch, tool, [_fail(BLOCKED), _ok()])

    result = asyncio.run(tool.edit_video("p", reference_video=REF, images=[IMG]))

    assert result.metadata["success"] is True
    assert result.metadata.get("deidentified") is True     # 必须可感知,不能静默打码
    assert result.metadata.get("deidentify_note")
    deid.assert_awaited_once_with(REF)
    assert submit.await_count == 2
    # 第二次提交用的必须是去身份化后的视频,否则等于白重试
    retry_payload = submit.await_args_list[1].args[0]
    assert retry_payload["videos"] == ["https://oss/deid.mp4"]


def test_no_retry_on_unrelated_error(monkeypatch):
    """余额/鉴权类错误与素材无关,去真人也没用 —— 立即失败,不做无谓重试"""
    tool = _tool()
    submit, deid = _stub(monkeypatch, tool, [_fail('方舟返回 401: {"code":"AuthenticationError"}')])

    result = asyncio.run(tool.edit_video("p", reference_video=REF, images=[IMG]))

    assert result.metadata["success"] is False
    deid.assert_not_awaited()
    assert submit.await_count == 1


def test_no_retry_when_nothing_detected(monkeypatch):
    """去身份化没检出真人(返回原 URL)→ 不能再提交一次(那是白花钱的重复生成)"""
    tool = _tool()
    submit, _ = _stub(monkeypatch, tool, [_fail(BLOCKED)], deid_url=REF)

    result = asyncio.run(tool.edit_video("p", reference_video=REF, images=[IMG]))

    assert result.metadata["success"] is False
    assert submit.await_count == 1


def test_failed_retry_reports_retry_error(monkeypatch):
    """重试仍失败 → 回报重试那次的原因(而不是第一次的旧错误,否则排查会被带偏)"""
    tool = _tool()
    _, _ = _stub(monkeypatch, tool, [_fail(BLOCKED), _fail("重试也挂了")])

    result = asyncio.run(tool.edit_video("p", reference_video=REF, images=[IMG]))

    assert result.metadata["success"] is False
    assert "重试也挂了" in str(result.metadata["error"])


def test_no_retry_when_external_task_already_submitted(monkeypatch):
    """断点续跑场景(checkpoint 已有 external_task_id)不重试:
    此时应复用已提交任务继续轮询,重新提交会重复扣费"""
    tool = _tool()
    submit, deid = _stub(monkeypatch, tool, [_fail(BLOCKED)])

    result = asyncio.run(tool.edit_video(
        "p", reference_video=REF, images=[IMG],
        checkpoint={"stage": 2, "external_task_id": "cgt-1"},
    ))

    assert result.metadata["success"] is False
    deid.assert_not_awaited()
    assert submit.await_count == 1
