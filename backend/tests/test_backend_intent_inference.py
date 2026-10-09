# -*- coding: utf-8 -*-
"""后端「替换意图」推断对齐测试(复刻链路后端兜底)。

mobile 端简化直出:只上传「对标视频 + 商品图」、不显式传 intent/remark。
此前 backend 完全不推断,只靠 worker 侧 D4 兜底才生效,导致 /precheck、/task/create
的缺失判定与 worker 实际出片口径漂移(后端判定"无替换意图",worker 却按 product 替换)。
本测试锁定 backend resolve_intent 与 worker D4 同口径,防止再次漂移。
"""
from app.services.prompt_builder import resolve_intent, VALID_INTENTS


def test_explicit_intent_wins():
    # 显式意图(A)优先于任何兜底
    assert resolve_intent(
        ["product"], subjects={"scene": "海边"},
        has_reference_video=True, has_images=True,
    ) == ["product"]


def test_subjects_dimension_inferred():
    # 多图分组识别(subjects)命中 → 直接采用该维度
    assert resolve_intent(
        None, subjects={"product": "红色杯子"},
        has_reference_video=True, has_images=True,
    ) == ["product"]


def test_material_type_fallback():
    # subjects 为空时退回视觉单类型识别
    assert resolve_intent(
        None, material_type="person",
        has_reference_video=True, has_images=True,
    ) == ["person"]


def test_remark_keyword_fallback():
    # 备注关键词兜底命中
    assert resolve_intent(
        None, remark="帮我换商品",
        has_reference_video=True, has_images=True,
    ) == ["product"]


def test_d4_fallback_to_product():
    # 有对标视频 + 有图,但无任何识别维度 → 默认按商品替换(D4 兜底,避免白复刻)
    assert resolve_intent(None, has_reference_video=True, has_images=True) == ["product"]


def test_no_image_no_d4_fallback():
    # 仅有对标视频、无替换图 → 不臆造 product(纯复刻走保留原片分支)
    assert resolve_intent(None, has_reference_video=True, has_images=False) == []


def test_consistent_with_worker_d4():
    # 与 worker 侧 D4 关键分支一致:有图 + 有视频必推断(至少 product),绝不静默忽略素材
    assert "product" in resolve_intent([], has_reference_video=True, has_images=True)
    # 维度必须落在白名单内
    for d in resolve_intent([], has_reference_video=True, has_images=True):
        assert d in VALID_INTENTS
