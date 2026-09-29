# -*- coding: utf-8 -*-
"""替换目标图含真人时:不重画(不换脸),只做「图转文 + 补语义」。

真实事故:用户选「替换主角」,方舟按隐私策略拒收真人参考图,worker 兜底用图生图把
照片"写实化"重画了一遍再提交 —— 那已经**不是用户上传的那个人**了,与"把这个人换进
视频"的目标直接冲突(用户反馈"成片里主角没看到"),还白花一次 Seedream 调用。

现在的规则:
  · 被拦图是替换目标/首帧主体(keep_person=True) → 一律不重画,丢图并把主体文字描述
    确定性补进 prompt 末尾,保证"换成什么样的人"仍有依据,并回写 person_identity_lost
    让前端能明确告知用户"成片人物不会与上传照片一致";
  · 被拦图只是顺带的辅助参考图(keep_person=False) → 仍按 gen.image_real_person_mode
    决定是否写实化(既有行为不变,见 test_video_image_deidentify.py)。
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


def test_edit_chain_never_redraws_replacement_target(monkeypatch):
    """编辑链路(keep_person):即使后台配了 stylize 也不重画,直接丢图 + 补语义"""
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
    stylize.assert_not_awaited(), "重画出来的不是用户上传的那个人,替换主角场景下绝不能做"
    assert result.metadata.get("image_fixed") is True
    assert result.metadata.get("person_identity_lost") is True
    retried = submit.await_args_list[1].args[0]
    assert not retried.get("images"), "被拦的替换图必须移除,否则重试等于原样再撞一次审核"
    assert "【被移除素材的文字描述" in retried["prompt"]
    assert DESC in retried["prompt"], "图没了就必须有文字锚点,否则模型不知道要换成什么样的人"


def test_all_image_chains_treat_reference_image_as_target(monkeypatch):
    """i2v 首帧 / r2v 参考图同样不重画:它们就是"要出现在成片里的主体"

    keep_person 由各链路的调用方显式传入(i2v/r2v/edit 都是 True)——
    这正是 stylize 在当前产品形态下恒不触发的原因,不能靠"某条链路忘了传"来兜。
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
        stylize.assert_not_awaited(), f"{name} 重画了主体图,成品里的主体就不再是用户上传的那个"
        assert result.metadata.get("person_identity_lost") is True, name


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
