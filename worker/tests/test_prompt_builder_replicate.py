# -*- coding: utf-8 -*-
"""复刻「保留原片结构」护栏注入契约测试。

核心回归:纯复刻(只传对标视频、不上传替换图、无替换意图)此前因注入条件
`gen_mode == "v2v" and len(materials) > 0` 永远不成立,拿不到「保留原片结构」指令,
v2v 编辑自由发挥,成片像「另一个 AI 视频」。放宽为「只要走 v2v 就注入」后,
纯复刻也必须拿到 gen_reference_requirement(严格保留原片主体/场景/品牌,不得重画)。
"""
import pytest

from app.services.prompt_builder import build_gen_params


def test_pure_replicate_injects_keep_original_requirement():
    """只传对标视频(无替换图、无意图)→ 必须注入保留原片护栏,且 gen_mode=v2v"""
    out = build_gen_params(
        template={},
        materials=["https://example.com/ref.mp4"],  # 视频被 split_materials 提为参考视频,图片列表为空
        remark="",
    )
    assert out["gen_mode"] == "v2v", f"纯复刻应走 v2v,实际 {out['gen_mode']}"
    ctx = out["prompt_context"]
    # 默认兜底文案(资产缺失时):明确"严格保留原片…不得重画"
    assert "严格保留参考视频的画面主体" in ctx, "纯复刻未注入保留原片结构护栏"


def test_replicate_with_materials_uses_replace_requirement():
    """有替换图 + 替换意图 → 注入替换指令(非纯复刻护栏),仍走 v2v"""
    out = build_gen_params(
        template={},
        materials=["https://example.com/ref.mp4", "https://example.com/product.jpg"],
        remark="",
        intent=["product"],
    )
    assert out["gen_mode"] == "v2v"
    ctx = out["prompt_context"]
    # 有意图时走 build_replace_requirement:要求替换商品且保留其余(默认文案含"商品与品牌标识必须替换")
    assert "商品与品牌标识必须替换" in ctx


def test_non_v2v_no_keep_original_requirement():
    """无参考视频(纯文生 t2v)→ 不应注入 v2v 保留原片护栏"""
    out = build_gen_params(template={}, materials=[], remark="")
    assert out["gen_mode"] == "t2v"
    ctx = out["prompt_context"]
    assert "严格保留参考视频的画面主体" not in ctx
