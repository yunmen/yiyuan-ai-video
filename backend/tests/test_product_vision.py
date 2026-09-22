# -*- coding: utf-8 -*-
"""多图分组识别:人物形象图 / 产品图 / 场景图 各出一段描述。

背景:用户可能**同时上传人物形象图和产品图**(真人出镜 + 手上拿产品)。
只识别第一张、只给一个主体的旧实现会丢掉另一半,文案与提示词都只能写一半。
这里锁定解析层:角色要分得开、JSON 不合规也要能退化成"至少有一段描述"。
"""
from app.services import product_vision


def test_parse_subjects_splits_person_and_product():
    """同时有人物与产品 → 两个角色字段都要落到,主描述取 primary"""
    raw = (
        '{"person":"短发女模特,米色针织衫",'
        '"product":"木质气垫梳,原木色,圆头梳齿",'
        '"scene":"","primary":"product"}'
    )
    result = product_vision._parse_subjects(raw)

    assert result["person"] == "短发女模特,米色针织衫"
    assert result["product"] == "木质气垫梳,原木色,圆头梳齿"
    assert result["type"] == "product"
    assert result["desc"] == "木质气垫梳,原木色,圆头梳齿"


def test_parse_subjects_infers_primary_when_model_omits_it():
    """模型没给 primary → 按"谁有描述就取谁"(人物优先,便于驱动换人意图)"""
    result = product_vision._parse_subjects('{"person":"女模特","product":"","scene":""}')

    assert result["type"] == "person"
    assert result["desc"] == "女模特"


def test_parse_subjects_falls_back_to_single_subject():
    """返回非法 JSON(旧模型/格式抽风)→ 退化成单主体描述,仍能注入一段,不丢信息"""
    result = product_vision._parse_subjects("一只黑白毛色的狗趴在老宅木门前")

    assert result["desc"]
    assert result["type"] in product_vision.ALLOWED_TYPES
    # 退化路径也要把描述落到角色字段上,否则多主体注入会拿不到东西
    assert any(result[role] for role in product_vision.VALID_ROLES)


def test_parse_subjects_cleans_newlines_and_padding():
    """多行/带引号的描述要压成单行短句,否则会污染提示词的分段结构"""
    result = product_vision._parse_subjects(
        '{"person":"  女模特\\n穿红裙  ","product":"","scene":""}'
    )

    assert result["person"] == "女模特 穿红裙"


def test_parse_subjects_truncates_long_desc():
    long_desc = "很长的描述" * 40
    result = product_vision._parse_subjects(
        '{"person":"","product":"%s","scene":""}' % long_desc
    )

    assert len(result["product"]) <= 80


def test_role_hint_marks_each_image_in_order():
    """角色标注要按图片顺序写成"第N张=xx":实测只让模型自己看图,产品照会被误判成场景"""
    hint = product_vision._role_hint(["person", "product"])

    assert "第1张=人物形象图" in hint
    assert "第2张=产品图" in hint


def test_role_hint_empty_without_roles():
    assert product_vision._role_hint([]) == ""
    assert product_vision._role_hint(["", "unknown"]) == ""


def test_empty_subjects_keeps_key_contract():
    """失败路径必须返回**键齐全**的空结构:调用方不做 None 判断也不会炸"""
    result = product_vision._empty_subjects()

    assert set(result) == {"person", "product", "scene", "type", "desc"}
    assert all(result[k] == "" for k in result)
