# -*- coding: utf-8 -*-
"""替换目标图含真人时:拟态化后再提交,不直接丢弃素材。

产品决策变更:用户要求"检测到真人,对真人素材进行拟态化处理再次提交,不能直接自动移除素材"。
故被拦图(无论是否替换目标/首帧主体)一律先走非写实风格化(图生图)再提交,保留"有这个人"的语义;
仅当拟态化失败/仍被拦才回退丢弃(图转文 + 补语义),作为最后兜底。
"""
import asyncio
from unittest.mock import AsyncMock

from app.core import media_prep
from app.settings import config
from app.schemas.base import ToolResult
from app.tools.video_tool import VideoGenTool

IMG1 = "https://oss/person.jpg"
REF = "https://oss/ref.mp4"
# content[1] 指向第一张图(text 占 content[0])
BLOCK_IMG = (
    '视频编辑提交异常(候选网关已全部尝试): 方舟返回 400: {"error":{"code":'
    '"InputImageSensitiveContentDetected.PrivacyInformation","message":"The request failed '
    "because the input image 'content[1]' may contain real person.\"}}"
)
DESC = "年轻女性,深棕长直发,蓝眼,浅灰针织高领毛衣"


def _tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _ok(url="https://oss/v.mp4"):
    return ToolResult(content=url, metadata={"success": True, "model": "m"})


def _fail(err):
    return ToolResult(content="", metadata={"success": False, "error": err})


async def _passthrough(url, *a, **k):
    return url


def test_edit_chain_stylizes_replacement_target(monkeypatch):
    """编辑链路(keep_person):被拦图含真人时先拟态化再提交,而非丢弃素材"""
    monkeypatch.setattr(config, "IMAGE_REAL_PERSON_MODE", "stylize")
    monkeypatch.setattr(media_prep, "fit_reference_video", _passthrough)
    tool = _tool()
    tool._replace_subjects = {"person": DESC}
    stylize = AsyncMock(return_value="https://oss/style.jpg")
    monkeypatch.setattr(tool, "_stylize_reference_image", stylize)
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.edit_video("换人物", reference_video=REF, images=[IMG1]))

    assert result.metadata["success"] is True
    stylize.assert_awaited(), "替换目标图含真人时应拟态化后再提交,而非直接丢弃素材"
    assert result.metadata.get("image_fixed") is True
    assert result.metadata.get("person_identity_lost") is not True, "拟态化保住了人物,不应标记人物丢失"
    retried = submit.await_args_list[1].args[0]
    assert retried.get("images") == ["https://oss/style.jpg"], "被拦的替换图应被拟态化结果替换,而非移除"
    assert "【被移除素材的文字描述" not in retried["prompt"], "图未被丢弃,不应补文字锚点"


def test_all_image_chains_stylize_reference_image(monkeypatch):
    """i2v 首帧 / r2v 参考图同样拟态化:它们就是"要出现在成片里的主体",
    保留同一人的非写实风格化形象后再提交,而不是直接丢弃。
    """
    monkeypatch.setattr(config, "IMAGE_REAL_PERSON_MODE", "stylize")
    monkeypatch.setattr(media_prep, "fit_reference_video", _passthrough)

    for name, call in (
        ("i2v", lambda t, s: t.image_to_video("p", input_image=IMG1)),
        ("r2v", lambda t, s: t.reference_to_video("p", reference_images=[IMG1, IMG1 + "?2"])),
    ):
        tool = _tool()
        tool._replace_subjects = {"person": DESC}
        stylize = AsyncMock(return_value="https://oss/style.jpg")
        monkeypatch.setattr(tool, "_stylize_reference_image", stylize)
        submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
        monkeypatch.setattr(tool, "_submit_and_poll", submit)

        result = asyncio.run(call(tool, submit))

        assert result.metadata["success"] is True, name
        stylize.assert_awaited(), f"{name} 含真人参考图应拟态化后再提交"
        assert result.metadata.get("person_identity_lost") is not True, name


def test_append_subject_desc_is_idempotent_and_skips_when_absent():
    """没有主体描述时不硬编造;重复调用不重复追加"""
    tool = _tool()
    assert tool._append_subject_desc({"prompt": "p"}) == []

    tool._replace_subjects = {"person": DESC, "product": "草莓味气泡水"}
    payload = {"prompt": "p"}
    assert tool._append_subject_desc(payload) == ["人物", "商品"]
    once = payload["prompt"]
    assert DESC in once and "草莓味气泡水" in once

    tool._append_subject_desc(payload)
    assert payload["prompt"] == once, "重复追加会把同一段描述塞两次,稀释模型注意力"
