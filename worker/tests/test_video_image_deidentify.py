# -*- coding: utf-8 -*-
"""参考图被判定含真人 → 本地处理(丢弃=图转文 / 拟态化)后重试一次。

用户场景:换人物时上传的**真人形象图**会被方舟按隐私策略拒(detect 到 real person);
参考视频可以去身份化(打码),但图片正是"要被替换成的目标",打码等于没有目标 ——
所以只能走「丢弃该图改按文字描述生成」或「拟态化后再提交」,且必须覆盖 r2v / i2v / v2v 三条链路。
"""
import asyncio
from unittest.mock import AsyncMock

from app.core import deidentify, media_prep
from app.settings import config
from app.schemas.base import ToolResult
from app.tools.video_tool import VideoGenTool

IMG1 = "https://oss/a.jpg"
IMG2 = "https://oss/b.jpg"
REF = "https://oss/ref.mp4"

# content[1] 指向第一张图(text 占 content[0])
BLOCK_IMG = (
    '参考生视频提交异常(候选网关已全部尝试): 方舟返回 400: {"error":{"code":'
    '"InputImageSensitiveContentDetected.PrivacyInformation","message":"The request failed '
    "because the input image 'content[1]' may contain real person.\"}}"
)
# 无下标:多图场景无法定位,按"不猜"处理
BLOCK_IMG_NO_INDEX = (
    '方舟返回 400: {"error":{"code":"InputImageSensitiveContentDetected",'
    '"message":"the input may contain real person."}}'
)
BLOCK_VIDEO = (
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


def test_parse_blocked_index():
    """从方舟报错里解析 content[N];解析不到返回 None"""
    assert deidentify.parse_blocked_index(BLOCK_IMG) == 1
    assert deidentify.parse_blocked_index("... contents[4] ...") == 4
    assert deidentify.parse_blocked_index(BLOCK_IMG_NO_INDEX) is None


def test_image_fix_mode_falls_back_to_drop(monkeypatch):
    """策略配置非法时一律回退 drop(安全侧:stylize 多一次付费调用)"""
    from app.tools.video_tool import IMAGE_FIX_DROP, IMAGE_FIX_STYLIZE, _image_fix_mode

    monkeypatch.setattr(config, "IMAGE_REAL_PERSON_MODE", "stylize")
    assert _image_fix_mode() == IMAGE_FIX_STYLIZE
    # 大小写/空白差异应被归一化(不能因此误判成非法值)
    monkeypatch.setattr(config, "IMAGE_REAL_PERSON_MODE", "  StYlIzE  ")
    assert _image_fix_mode() == IMAGE_FIX_STYLIZE
    for bad in ("", "   ", "unknown", None):
        monkeypatch.setattr(config, "IMAGE_REAL_PERSON_MODE", bad)
        assert _image_fix_mode() == IMAGE_FIX_DROP, f"{bad!r} 应回退 drop"


def test_r2v_drops_blocked_image_and_retries(monkeypatch):
    """r2v:被拦的那张图被移除,剩余参考图继续提交;处理标记必须回写"""
    tool = _tool()
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.reference_to_video("p", reference_images=[IMG1, IMG2]))

    assert result.metadata["success"] is True
    assert result.metadata.get("image_fixed") is True
    assert "移除" in (result.metadata.get("image_note") or "")
    assert submit.await_count == 2
    # 第二次提交必须已不含被拦的那张图,否则等于白重试
    assert submit.await_args_list[1].args[0]["images"] == [IMG2]


def test_r2v_single_image_blocked_falls_back_to_text(monkeypatch):
    """r2v 只有一张参考图且被拦 → 处理掉后没有参考图,退化为文生视频(而非失败)"""
    tool = _tool()
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.reference_to_video("p", reference_images=[IMG1]))

    assert result.metadata["success"] is True
    assert result.metadata.get("image_note")
    assert submit.await_count == 2
    fallback_payload = submit.await_args_list[1].args[0]
    assert "images" not in fallback_payload
    assert fallback_payload["model"] == config.VIDEO_MODEL_T2V      # 确实是文生视频链路


def test_i2v_blocked_first_frame_falls_back_to_text(monkeypatch):
    """i2v:首帧图被拦 → 无首帧可用,退化为文生视频"""
    tool = _tool()
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.image_to_video("p", input_image=IMG1))

    assert result.metadata["success"] is True
    assert result.metadata.get("image_note")
    fallback_payload = submit.await_args_list[1].args[0]
    assert "image" not in fallback_payload
    assert fallback_payload["model"] == config.VIDEO_MODEL_T2V


def test_stylize_mode_replaces_image(monkeypatch):
    """开关为 stylize 时:先用图生图拟态化,再拿新图重试(保留"有个人"但非本人)"""
    monkeypatch.setattr(config, "IMAGE_REAL_PERSON_MODE", "stylize")
    tool = _tool()
    stylize = AsyncMock(return_value="https://oss/style.jpg")
    monkeypatch.setattr(tool, "_stylize_reference_image", stylize)
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.reference_to_video("p", reference_images=[IMG1, IMG2]))

    assert result.metadata["success"] is True
    assert "拟态化" in (result.metadata.get("image_note") or "")
    stylize.assert_awaited_once_with(IMG1)
    assert submit.await_args_list[1].args[0]["images"] == ["https://oss/style.jpg", IMG2]


def test_stylize_failure_falls_back_to_drop(monkeypatch):
    """拟态化失败(返回空)→ 回退丢弃该图,保证仍能出片,不能因增强项把任务搞失败"""
    monkeypatch.setattr(config, "IMAGE_REAL_PERSON_MODE", "stylize")
    tool = _tool()
    monkeypatch.setattr(tool, "_stylize_reference_image", AsyncMock(return_value=""))
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.reference_to_video("p", reference_images=[IMG1, IMG2]))

    assert result.metadata["success"] is True
    assert "移除" in (result.metadata.get("image_note") or "")
    assert submit.await_args_list[1].args[0]["images"] == [IMG2]


def test_multi_image_without_index_is_not_guessed(monkeypatch):
    """多图且报错无 content 下标:不猜是哪张(猜错会误丢正常商品图),按原失败返回"""
    tool = _tool()
    submit = AsyncMock(return_value=_fail(BLOCK_IMG_NO_INDEX))
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.reference_to_video("p", reference_images=[IMG1, IMG2]))

    assert result.metadata["success"] is False
    assert submit.await_count == 1
    assert not result.metadata.get("image_note")


def test_notes_not_attached_on_final_failure(monkeypatch):
    """重试仍失败时不回写处理标记(失败结果不落库,标记无处附着)"""
    tool = _tool()
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _fail("重试也挂了")])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.reference_to_video("p", reference_images=[IMG1, IMG2]))

    assert result.metadata["success"] is False
    assert "重试也挂了" in str(result.metadata["error"])
    assert not result.metadata.get("image_note")


def test_no_retry_when_external_task_already_submitted(monkeypatch):
    """断点续跑已提交外部任务:重提交等于重复扣费,不做素材修正"""
    tool = _tool()
    submit = AsyncMock(return_value=_fail(BLOCK_IMG))
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.reference_to_video(
        "p", reference_images=[IMG1, IMG2],
        checkpoint={"stage": 2, "external_task_id": "cgt-1"},
    ))

    assert result.metadata["success"] is False
    assert submit.await_count == 1


def test_edit_video_fixes_image_then_video(monkeypatch):
    """真人视频 + 真人形象图的组合:先丢弃被拦的参考图,再去身份化参考视频,各修正一次"""
    async def _passthrough(url, *a, **k):
        return url

    monkeypatch.setattr(media_prep, "fit_reference_video", _passthrough)
    deid = AsyncMock(return_value="https://oss/deid.mp4")
    monkeypatch.setattr(media_prep, "deidentify_reference_video", deid)

    tool = _tool()
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _fail(BLOCK_VIDEO), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.edit_video("换人物", reference_video=REF, images=[IMG1]))

    assert result.metadata["success"] is True
    assert result.metadata.get("image_fixed") is True
    assert result.metadata.get("image_note")
    assert result.metadata.get("deidentified") is True
    assert result.metadata.get("deidentify_note")
    assert submit.await_count == 3
    # 第二次已无参考图(被丢),第三次参考视频换成去身份化产物
    assert "images" not in submit.await_args_list[1].args[0]
    assert submit.await_args_list[2].args[0]["videos"] == ["https://oss/deid.mp4"]
    deid.assert_awaited_once_with(REF)


def test_edit_video_keeps_other_images_after_drop(monkeypatch):
    """多图编辑:只丢被拦的那张,其余参考图必须保留(否则会把商品图一起丢掉)"""
    async def _passthrough(url, *a, **k):
        return url

    monkeypatch.setattr(media_prep, "fit_reference_video", _passthrough)
    tool = _tool()
    submit = AsyncMock(side_effect=[_fail(BLOCK_IMG), _ok()])
    monkeypatch.setattr(tool, "_submit_and_poll", submit)

    result = asyncio.run(tool.edit_video("换人物", reference_video=REF, images=[IMG1, IMG2]))

    assert result.metadata["success"] is True
    assert submit.await_args_list[1].args[0]["images"] == [IMG2]
