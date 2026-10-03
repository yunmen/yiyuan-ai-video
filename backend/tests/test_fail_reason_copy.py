# -*- coding: utf-8 -*-
"""用户端失败文案(C 端提示):素材类失败必须给出「换什么」的一句话指引

worker 侧报的是技术原文(含像素数/分辨率/检测原因),直接抛给用户既看不懂、
也不知道下一步该做什么。这里钉死:命中素材类失败时返回的是**可执行的一句话**,
而不是技术细节,也不是"请稍后重试"(重试同一个素材必然再次失败)。
"""
from app.services.generate_task import friendly_fail_reason


def test_invalid_reference_frame_is_actionable():
    raw = (
        "参考视频画面无实际内容(画面 85% 的像素为高饱和纯色,"
        "是彩条/测试图一类无实际内容的画面)。已终止本次生成并原路返还额度/退款,"
        "请更换有真实画面的参考视频"
    )
    text = friendly_fail_reason(raw)
    assert "换一段有真实画面的原片" in text
    assert "85%" not in text and "像素为高饱和" not in text, "技术细节不该出现在用户文案里"


def test_low_resolution_reference_is_actionable():
    raw = (
        "参考视频不满足生成要求:参考视频分辨率 360x640(230400 像素)低于模型要求的最低 "
        "407696 像素,请换用更高分辨率的参考视频。已终止本次生成并原路返还额度/退款"
    )
    text = friendly_fail_reason(raw)
    assert "分辨率太低" in text and "更清晰的原片" in text
    assert "407696" not in text, "模型门槛数字对用户没有意义"


def test_invalid_output_is_actionable():
    raw = "视频编辑成片画面无实际内容(画面只有 1 种颜色,是纯色/黑屏一类无实际内容的画面),未交付。..."
    text = friendly_fail_reason(raw)
    assert "换一段素材重试" in text
    assert "纯色/黑屏" not in text


def test_other_errors_keep_existing_behavior():
    """与素材无关的失败仍走原分类话术,不能把文案串味"""
    assert "审核" in friendly_fail_reason("InputImageSensitiveContentDetected")
    assert "超时" in friendly_fail_reason("生成超时,任务未完成")
    assert friendly_fail_reason("Error code: 401 - invalid api key") == friendly_fail_reason("Error code: 403 - forbidden")
