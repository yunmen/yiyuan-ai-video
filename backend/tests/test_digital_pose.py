# -*- coding: utf-8 -*-
"""主视图派生:派生视图解析(纯函数)"""
from app.services.digital import resolve_pose_variant

VARIANTS = [{"name": "挥手", "image": "/static/wave.png"}, {"name": "坐姿", "image": "/static/sit.png"}]


def test_resolve_pose_variant_by_name():
    assert resolve_pose_variant(VARIANTS, "坐姿")["image"] == "/static/sit.png"


def test_resolve_pose_variant_falls_back_to_main_view():
    """未指定/未命中/数据脏 → 回退主视图,不报错阻断生成"""
    assert resolve_pose_variant(VARIANTS, None) is None
    assert resolve_pose_variant(VARIANTS, "") is None
    assert resolve_pose_variant(VARIANTS, "不存在的姿势") is None
    assert resolve_pose_variant(None, "挥手") is None
    assert resolve_pose_variant("脏数据", "挥手") is None
    assert resolve_pose_variant([None, "x"], "挥手") is None
