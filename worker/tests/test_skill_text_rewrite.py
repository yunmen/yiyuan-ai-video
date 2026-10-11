# -*- coding: utf-8 -*-
"""去 AI 味改写:text-rewrite 技能注册、参数契约、档位映射与降级(跨端契约单测)"""
import asyncio

from app.core import skill_runtime
from app.core.skill_runtime import registry, register_builtin_skills
from app.services import ai_rewrite


def test_skill_registered():
    """register_builtin_skills 必须含 text-rewrite,且 input_schema 含 text/level。"""
    register_builtin_skills()
    spec = registry.get("text-rewrite")
    assert spec is not None, "text-rewrite 未注册"
    names = {p.name for p in spec.input_schema}
    assert {"text", "level"}.issubset(names), "text-rewrite 缺少必填参数 text/level"


def test_level_and_tone_mapping():
    """档位/语气映射:越界回退、未知语气回退自然。"""
    assert "轻度" in ai_rewrite._level_desc(1)
    assert "深度" in ai_rewrite._level_desc(4)
    assert "中度" in ai_rewrite._level_desc(999)  # 越界回退 2
    assert "自然" in ai_rewrite._tone_desc("natural")
    assert "自然" in ai_rewrite._tone_desc("unknown")  # 未知回退 natural


def test_rewrite_fallback_without_gateway(monkeypatch):
    """未配 chat 网关时走规则兜底,fallback=True 且去掉 AI 套话。"""
    monkeypatch.setattr(
        ai_rewrite.gateway, "resolve",
        lambda name: {} if name == "chat" else {"url": "", "key": ""},
    )
    # 用套话词表中确实存在的短语验证兜底清理
    out = asyncio.run(ai_rewrite.rewrite_text(text="首先,综上所述,这个产品真的很好用。", level=2, tone="natural"))
    assert out["fallback"] is True, "无网关应降级"
    assert out["level"] == 2 and out["tone"] == "natural"
    assert out["src_chars"] > 0
    # 兜底应去掉「首先」「综上所述」等套话
    assert "首先" not in out["rewritten"]
    assert "综上所述" not in out["rewritten"]


def test_rewrite_params_delivered_to_runtime(monkeypatch):
    """run_skill 把 params 经 handler 原样下发给 rewrite_text(level 强转 int)。

    handler 内为 `from app.services.ai_rewrite import rewrite_text` 局部绑定,
    故需在调用 register_builtin_skills 之前先把 ai_rewrite.rewrite_text 替换成 fake,
    重置注册标志后重注册,使导入绑定到 fake。
    """
    monkeypatch.setattr(skill_runtime, "_BUILTINS_DONE", False)

    async def fake_rewrite(text, level=2, tone="natural", max_chars=0):
        return {"rewritten": "x", "level": level, "tone": tone,
                "src_chars": len(text), "dst_chars": 1, "fallback": False, "note": ""}

    monkeypatch.setattr(ai_rewrite, "rewrite_text", fake_rewrite)
    register_builtin_skills()
    res = asyncio.run(skill_runtime.run_skill(
        "text-rewrite", "", {"text": "原文", "level": "3", "tone": "sharp"}
    ))
    # handler 内 level 经 int() 强转,字符串 "3" 应收敛为 int 3
    assert res.metadata.get("skill") == "text-rewrite"
    # 产物 content 体现 level 强转与透传(直接在 result.content 上断言,不依赖 captured 闭包)
    assert res.content.get("level") == 3
    assert res.content.get("tone") == "sharp"
