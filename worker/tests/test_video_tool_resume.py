# -*- coding: utf-8 -*-
"""视频工具:断点续跑 —— 复用已完成阶段的中间产物,跳过对应阶段。"""
import asyncio
from unittest.mock import AsyncMock

from app.tools.video_tool import VideoGenTool


def _make_tool():
    # 仅构造客户端,不发起网络请求
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def test_resume_skips_prompt_rewrite_but_submits():
    """stage>=1 且已有 optimized_prompt:跳过 LLM 改写,但仍需提交新外部任务。"""
    async def run():
        tool = _make_tool()
        optimize = AsyncMock(side_effect=AssertionError("断点续跑不应再调用 LLM 改写"))
        tool._optimize_prompt = optimize
        tool.client.post = AsyncMock(return_value={"id": "task-new"})
        # _poll 返回 (直链, 是否被上游判失败);False = 正常拿到结果
        poll = AsyncMock(return_value=("https://x/final.mp4", False))
        tool._poll = poll

        cp = {"stage": 1, "optimized_prompt": "已缓存的prompt"}
        result = await tool.generate({"prompt": "x", "materials": []}, checkpoint=cp, on_stage=AsyncMock())

        assert result.metadata["success"] is True
        assert result.content == "https://x/final.mp4"
        optimize.assert_not_called()                      # 复用了缓存 prompt
        tool.client.post.assert_awaited_once()            # 仍提交生成任务
        # 当前 env 的 VIDEO_MODEL_T2V 属 seedance-2 系,提交前按模型上限压到 720p
        # (见 video_tool._MODEL_RESOLUTION_CAP);换模型名要同步这里的断言。
        poll.assert_awaited_once_with("task-new", "文生视频", 5, "720p", "9:16")

    asyncio.run(run())


def test_resume_reuses_external_task_id_skips_submit():
    """stage>=2 且已有 external_task_id:跳过提交,直接复用该任务 ID 继续轮询。"""
    async def run():
        tool = _make_tool()
        tool._optimize_prompt = AsyncMock(return_value="p")
        tool.client.post = AsyncMock(side_effect=AssertionError("stage>=2 不应再提交外部任务"))
        poll = AsyncMock(return_value=("https://x/final.mp4", False))
        tool._poll = poll

        cp = {"stage": 2, "external_task_id": "task-abc"}
        result = await tool.generate({"prompt": "x", "materials": []}, checkpoint=cp, on_stage=AsyncMock())

        assert result.content == "https://x/final.mp4"
        tool.client.post.assert_not_called()              # 复用已提交任务,不重复扣费
        # 同上:seedance-2 系模型被压到 720p 后才会提交/轮询
        poll.assert_awaited_once_with("task-abc", "文生视频", 5, "720p", "9:16")

    asyncio.run(run())
