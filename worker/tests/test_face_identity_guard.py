# -*- coding: utf-8 -*-
"""「换人物 → 脸部特征保真」注入契约测试。

背景:此前「视频中的出镜人物必须替换为用户上传的人物参考图」只给了**方向**,
没有任何"脸要像"的具体约束 —— 下游模型拿不到五官依据就自由发挥,成片主角的脸
与参考图对不上,用户观感就是"我明明传了自己的照片,怎么换成个陌生人了"。

本次落地由两部分配套构成,缺一不可:
  ① 识别层(ai_vision.SUBJECT_PROMPT):要求人物描述写出面部特征 —— 脸保真的**输入源**;
  ② 提示词层(gen_face_identity_guard):换人物时追加保真强约束 —— 脸保真的**执行约束**。
只做①则模型没有强约束、只做②则模型没有可依据的五官描述,两头缺一头都不生效。
"""
import pytest

from app.services.ai_vision import SUBJECT_PROMPT
from app.services.prompt_builder import (
    DEFAULT_FACE_IDENTITY_GUARD,
    build_gen_params,
    build_replace_requirement,
    load_skill_prompt,
)

# 锚点里必须出现的"脸保真"语义(取这些词而非整句,文案微调不至于让测试误报)
_GUARD_MARKERS = ("面部特征", "脸型", "五官")


def _template():
    """最小模板对象:build_gen_params 只读取 duration 等少数字段"""
    return {}


def test_person_replace_injects_face_identity_guard():
    """换人物 → 必须注入脸部保真锚点(这是本次改动的核心断言)"""
    req = build_replace_requirement(["person"])
    for marker in _GUARD_MARKERS:
        assert marker in req, f"换人物未注入脸部保真约束(缺「{marker}」)"


def test_face_guard_follows_person_replace_directive():
    """锚点必须**紧跟**在"替换为参考图人物"之后:先说换成谁、再说脸要怎么像。

    顺序颠倒(锚点排在前面)时,后一句会被前一句的方向带偏,约束失效。
    """
    req = build_replace_requirement(["person"])
    idx_replace = req.find("出镜人物必须替换")
    idx_guard = req.find("面部特征")
    assert idx_replace >= 0, "未注入 gen_replace_person 替换指令"
    assert idx_guard > idx_replace, "脸部保真锚点必须排在人物替换指令之后"


def test_face_guard_not_injected_for_other_intents():
    """只换商品/场景时**不得**注入脸部保真约束:避免给无关任务加噪"""
    assert "面部特征" not in build_replace_requirement(["product"])
    assert "面部特征" not in build_replace_requirement(["scene"])


def test_face_guard_not_injected_for_pure_replicate():
    """纯复刻(无替换意图)→ 不注入锚点,保持"严格保留原片主体"语义不变"""
    assert "面部特征" not in build_replace_requirement([])


def test_pure_replicate_still_keeps_keep_guard():
    """回归:空意图回退 blanket 指令(行为不因本次改动而变)"""
    assert "商品与出镜主体必须替换" in build_replace_requirement([])


def test_gen_params_v2v_person_carries_face_guard():
    """端到端:上传人物图 + person 意图 → prompt_context 里同时含替换指令与脸部锚点"""
    out = build_gen_params(
        _template(),
        ["/static/ref.mp4", "/static/person.jpg"],
        None,
        intent=["person"],
        subjects={"person": "圆脸短发的年轻女性", "product": "", "scene": "", "type": "person", "desc": ""},
    )
    assert out["gen_mode"] == "v2v"
    ctx = out["prompt_context"]
    assert "出镜人物必须替换为用户上传的人物参考图" in ctx
    for marker in _GUARD_MARKERS:
        assert marker in ctx, f"端到端 prompt_context 缺脸部保真约束「{marker}」"


def test_subject_prompt_requires_face_features():
    """识别层必须要求面部特征:人物描述里没有五官,②的强约束就无据可依"""
    assert "面部特征" in SUBJECT_PROMPT
    for kw in ("脸型", "发型", "肤色"):
        assert kw in SUBJECT_PROMPT, f"SUBJECT_PROMPT 未要求描述「{kw}」"


def test_face_guard_fallback_matches_asset():
    """内联兜底文案与 MD 资产语义一致(都要求面部特征/脸型/五官)。

    只校验关键词而非整句相等:两者都失效时(资产加载失败)提示词仍须保住核心约束。
    """
    body = load_skill_prompt("gen_face_identity_guard", default="")
    if not body:
        pytest.skip("提示词资产 gen_face_identity_guard.md 缺失,跳过一致性校验")
    for marker in _GUARD_MARKERS:
        assert marker in body, f"MD 资产缺「{marker}」"
        assert marker in DEFAULT_FACE_IDENTITY_GUARD, f"内联兜底缺「{marker}」"
