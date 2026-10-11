# -*- coding: utf-8 -*-
"""自动 B-roll 服务契约测试:窗口推导(纯函数)+ 增强层失败回退(不阻断出片)。"""
from app.services import broll_service as broll


def test_derive_even_windows_spans_duration():
    """even 策略:按 interval/window 在时长内均匀铺窗,首窗从 start_offset 起。"""
    wins = broll.derive_broll_windows(
        [], {"strategy": "even", "interval": 8, "window": 3, "start_offset": 1}, 30,
    )
    assert wins and wins[0] == (1.0, 4.0)
    # 30s / 8s 间隔 → 约 4 窗,且所有窗都在时长内
    assert len(wins) == 4
    for s, e in wins:
        assert 0.0 <= s < e <= 30.0


def test_derive_mention_matches_keyword_cues():
    """mention 策略:只命中含关键词的句子时间窗(对齐"讲到商品切特写")。"""
    cues = [
        {"text": "今天推荐小龙虾", "start_ms": 1000, "end_ms": 3000},
        {"text": "再来看看烤鸭", "start_ms": 4000, "end_ms": 6000},
        {"text": " unrelated", "start_ms": 7000, "end_ms": 9000},
    ]
    wins = broll.derive_broll_windows(cues, {"strategy": "mention", "keywords": ["小龙虾", "烤鸭"]}, 12)
    assert wins == [(1.0, 3.0), (4.0, 6.0)]


def test_derive_mention_no_match_falls_back_to_even():
    """mention 无命中且 fallback_even 默认开 → 退回 even,不影响出片(仍有 B-roll 插窗)。"""
    cues = [{"text": "无关", "start_ms": 1000, "end_ms": 3000}]
    wins = broll.derive_broll_windows(cues, {"strategy": "mention", "keywords": ["商品"]}, 10)
    assert wins and len(wins) >= 1


def test_derive_mention_no_match_no_fallback_returns_empty():
    """mention 无命中且 fallback_even=False → 空窗(用户明确只要关键词命中才插)。"""
    cues = [{"text": "无关", "start_ms": 1000, "end_ms": 3000}]
    wins = broll.derive_broll_windows(
        cues, {"strategy": "mention", "keywords": ["商品"], "fallback_even": False}, 10,
    )
    assert wins == []


def test_apply_auto_broll_safe_when_disabled_or_no_source():
    """增强层:未开启 / 缺素材来源 / 时长无效 一律原样返回 content,绝不阻断出片。"""
    import asyncio
    content = "http://oss/x.mp4"
    # 未开启
    assert asyncio.run(broll.apply_auto_broll(content, {}, 10, "t1")) == content
    # 开启但无任何素材来源(goods/scene 都为空,且未给 URL)
    cfg = {"enabled": True, "source": "goods", "strategy": "even"}
    assert asyncio.run(broll.apply_auto_broll(content, cfg, 10, "t2")) == content
    # 时长无效
    assert asyncio.run(broll.apply_auto_broll(content, {"enabled": True}, 0, "t3")) == content


def test_build_gen_prompt_prefers_explicit_else_fallback():
    """source=gen 的提示词:显式 prompt 优先(去空白);缺失用通用电商特写兜底(不臆造商品信息)。"""
    assert broll._build_gen_prompt({"prompt": "  食材翻炒特写 "}) == "食材翻炒特写"
    fallback = broll._build_gen_prompt({})
    assert "电商" in fallback and "特写" in fallback


def test_generate_broll_source_returns_url_on_success():
    """source=gen 且文生图成功 → 返回首张图 URL(无需真实网关, mock ImageGenTool)。"""
    import asyncio
    from unittest.mock import patch, MagicMock, AsyncMock
    from app.schemas.base import ToolResult

    fake = ToolResult(content="http://oss/gen1.png,http://oss/gen2.png", metadata={"success": True})
    with patch("app.tools.image_tool.ImageGenTool") as MockTool:
        inst = MagicMock()
        inst.text_to_image = AsyncMock(return_value=fake)
        MockTool.return_value = inst
        url = asyncio.run(broll._generate_broll_source({"source": "gen", "prompt": "x"}, "t1"))
    assert url == "http://oss/gen1.png"
    # 调用时 ratio 透传(默认 1:1),且只取首张
    _, kwargs = inst.text_to_image.call_args
    assert kwargs.get("ratio") == "1:1"


def test_generate_broll_source_falls_back_on_failure():
    """source=gen 但文生图失败/空 → 返回 None,由调用方回退 goods/scene/URL/原片。"""
    import asyncio
    from unittest.mock import patch, MagicMock, AsyncMock

    with patch("app.tools.image_tool.ImageGenTool") as MockTool:
        inst = MagicMock()
        inst.text_to_image = AsyncMock(return_value=MagicMock(content="", metadata={}))
        MockTool.return_value = inst
        url = asyncio.run(broll._generate_broll_source({"source": "gen", "prompt": "x"}, "t1"))
    assert url is None


def test_generate_broll_source_no_image_gateway_returns_none():
    """图片网关未配置(ImageGenTool 构造抛 RuntimeError)→ 返回 None,不阻断出片。"""
    import asyncio
    from unittest.mock import patch

    with patch("app.tools.image_tool.ImageGenTool", side_effect=RuntimeError("未配置图片网关")):
        url = asyncio.run(broll._generate_broll_source({"source": "gen", "prompt": "x"}, "t1"))
    assert url is None


# —— P3-3:anchor 策略(按词锚点的真实秒插窗,替代关键词维护)——

def test_derive_anchor_uses_anchor_windows():
    """anchor 策略:直接用调用方按词锚点解析出的真实秒窗,忽略关键词/均匀启发式。"""
    wins = broll.derive_broll_windows(
        [], {"strategy": "anchor"}, 30, anchor_windows=[(2.0, 5.0), (10.0, 12.0)],
    )
    assert wins == [(2.0, 5.0), (10.0, 12.0)]


def test_derive_anchor_clamps_and_drops_invalid():
    """anchor 策略:越界窗夹到 [0,duration],零长度窗丢弃(脏锚点不产生坏窗)。"""
    wins = broll.derive_broll_windows(
        [], {"strategy": "anchor"}, 30,
        anchor_windows=[(-5.0, 3.0), (10.0, 10.0), (25.0, 40.0)],
    )
    assert wins == [(0.0, 3.0), (25.0, 30.0)]


def test_derive_anchor_no_windows_falls_back_even():
    """anchor 无可用窗且 fallback_even 默认开 → 退回 even(不因锚点缺失漏掉 B-roll)。"""
    wins = broll.derive_broll_windows(
        [], {"strategy": "anchor", "interval": 8, "window": 3, "start_offset": 1}, 30,
        anchor_windows=None,
    )
    assert wins and wins[0] == (1.0, 4.0)


def test_derive_anchor_no_windows_no_fallback_returns_empty():
    """anchor 无窗且 fallback_even=False → 空窗(用户明确只按锚点插)。"""
    wins = broll.derive_broll_windows(
        [], {"strategy": "anchor", "fallback_even": False}, 30, anchor_windows=[],
    )
    assert wins == []
