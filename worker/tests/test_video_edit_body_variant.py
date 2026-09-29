# -*- coding: utf-8 -*-
"""视频编辑请求体形态兜底:参考视频必须真正生效(不能退化成"按 prompt 重新生成")。

真实事故:替换主角任务走中转站(非方舟原生协议),参考视频只以顶层 videos 字段提交,
中转站静默丢弃它 → 成片退化成"按 prompt 重新生成",原片动作(狗推婴儿车)整段消失、
画幅也从 540x1168 竖屏变成 1280x720 横屏,而且**不报错**,最后靠人工抽帧才发现。

因此:非方舟网关的视频编辑一律先按方舟原生形态提交(content[] 内 video_url +
顶层 ratio=adaptive / duration=-1),形态被拒时自动换回顶层 videos 形态并记住结果。

⚠️ 本文件所有用例必须**完全离线**:提交、轮询、转存三处都要 mock。
   曾经只 mock 了 client.post 而漏掉 _poll,结果轮询对着 localhost 空转直到超时,
   把 64 行 WARNING 写进了生产 worker 日志。
"""
import asyncio
from contextlib import contextmanager
from typing import Optional
from unittest.mock import AsyncMock, patch

from app.tools.video_tool import _BODY_SHAPE_PREF, VideoGenTool

REF = "https://oss/ref.mp4"
IMG = "https://oss/person.jpg"
DONE_URL = "https://oss/out.mp4"


class _HttpError(Exception):
    """带状态码的提交异常(对齐 openai SDK 的 APIStatusError 行为)"""

    def __init__(self, status_code: Optional[int], message: str):
        super().__init__(message)
        self.status_code = status_code


def _tool():
    tool = VideoGenTool(api_key="test-key", base_url="http://localhost/v1")
    _BODY_SHAPE_PREF.clear()
    return tool


def _payload():
    return {
        "model": "doubao-seedance-2-5-260628",
        "prompt": "把出镜人物换成参考图里的人",
        "videos": [REF],
        "seconds": "5",
        "generate_audio": True,
        "metadata": {"parameters": {"resolution": "720p", "ratio": "9:16", "duration": 5}},
        "images": [IMG],
    }


def _payload_without_videos():
    payload = _payload()
    payload.pop("videos")
    return payload


@contextmanager
def _offline(tool, post):
    """提交/轮询/转存全部关在本地 —— 用例绝不发真实请求、绝不写 OSS"""
    with patch.object(tool, "_poll", AsyncMock(return_value=(DONE_URL, False))), \
            patch("app.tools.video_tool.persist_url_list", AsyncMock(return_value=[DONE_URL])), \
            patch.object(tool, "client") as client:
        client.post = post
        yield client


def _run_edit(tool, payload):
    return asyncio.run(tool._submit_and_poll(payload, "视频编辑", 5, "720p", "9:16", route="edit"))


def test_edit_submits_native_body_with_video_url():
    """有参考视频时按方舟原生形态下发:video_url 进 content,比例/时长强制跟随原片"""
    tool = _tool()

    variants = tool._body_variants(_payload())
    assert variants[0] == "native", "参考视频必须以方舟原生形态提交,否则会被中转站静默丢弃"

    body = tool._body_for(_payload(), "native")
    assert body["ratio"] == "adaptive" and body["duration"] == -1
    assert body["content"][0]["type"] == "text"
    video_entries = [c for c in body["content"] if c["type"] == "video_url"]
    assert video_entries and video_entries[0]["video_url"]["url"] == REF
    assert video_entries[0]["role"] == "reference_video"
    assert "videos" not in body, "原生形态不应再带顶层 videos(避免中转站按旧形态处理)"


def test_non_edit_payload_keeps_single_variant():
    """t2v/i2v/r2v 没有参考视频,不存在形态分叉,请求体原样下发"""
    tool = _tool()
    payload = _payload_without_videos()
    assert tool._body_variants(payload) == ["legacy"]
    assert tool._body_for(payload, "legacy") is payload


def test_shape_error_falls_back_to_legacy_and_remembers():
    """网关不认原生形态(404/422)时自动换回顶层 videos 提交,并记住可用的那一种"""
    tool = _tool()
    post = AsyncMock(side_effect=[_HttpError(404, "Not Found"), {"id": "t1"}])

    with _offline(tool, post):
        first = _run_edit(tool, _payload())
        assert first.metadata["success"] is True
        assert post.await_count == 2
        # 第二次用的是兼容形态:参考视频回到顶层 videos
        assert post.await_args_list[1].kwargs["body"]["videos"] == [REF]
    assert _BODY_SHAPE_PREF["video@http://localhost/v1"] == "legacy"

    # 形态已被记住:下一单直接打兼容形态,不再白试一次原生形态
    post2 = AsyncMock(return_value={"id": "t2"})
    with _offline(tool, post2):
        second = _run_edit(tool, _payload())
        assert second.metadata["success"] is True
        assert post2.await_count == 1
        assert post2.await_args_list[0].kwargs["body"]["videos"] == [REF]


def test_content_error_is_not_retried_with_other_variant():
    """内容审核类 400(真人拦截)不是形态问题:不换形态,原样交给上层做真人兜底"""
    tool = _tool()
    post = AsyncMock(side_effect=[
        _HttpError(400, "InputImageSensitiveContentDetected.PrivacyInformation: may contain real person"),
    ])

    with _offline(tool, post):
        result = _run_edit(tool, _payload())
        assert result.metadata["success"] is False
        assert post.await_count == 1, "审核错误换形态重试只会重复被拦"
