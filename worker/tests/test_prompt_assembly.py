# -*- coding: utf-8 -*-
"""生成参数组装:备注结构化解析 + 模板上下文(纯函数)"""
from types import SimpleNamespace

from app.services.prompt_builder import (
    build_gen_params,
    build_material_hint,
    build_prompt_context,
    build_prompt_parts,
    build_structured_text,
    build_replace_requirement,
    parse_remark,
    resolve_gen_mode,
    resolve_intent,
    split_materials,
    _render_replicate_format,
)
from app.services.gen_rules import (
    REPLICATE_FORMAT_OPTIONS,
    SUPPORTED_REPLICATE_FORMATS,
    normalize_replicate_format,
)
from app.services.gen_rules import REPLICATE_FORMATS


def _template(**kw):
    base = dict(
        id=9, title="探店种草", category="餐饮探店", desc="适合餐饮门店,突出招牌菜",
        tags=["探店", "美食"], duration=12, default_text={},
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_split_materials_pulls_out_reference_video():
    """参考视频单独提出来:视频编辑要的是视频本身,不是抽帧图"""
    images, video = split_materials(["/static/a.jpg", "/static/ref.mp4", "/static/b.jpg"])
    assert video == "/static/ref.mp4"
    assert images == ["/static/a.jpg", "/static/b.jpg"]


def test_split_materials_without_video():
    images, video = split_materials(["/static/a.jpg"])
    assert video == ""
    assert images == ["/static/a.jpg"]


def test_resolve_gen_mode_prefers_video_edit():
    """有参考视频 → v2v(视频编辑),优先于按图片数量猜的模式"""
    assert resolve_gen_mode(3, has_video=True) == "v2v"
    assert resolve_gen_mode(0, has_video=True) == "v2v"
    assert resolve_gen_mode(1, has_video=False) == "i2v"


def test_build_gen_params_video_material_uses_edit_mode():
    params = build_gen_params(_template(duration=12), ["/static/a.jpg", "/static/ref.mp4"], None)
    assert params["gen_mode"] == "v2v"
    assert params["reference_video"].endswith("/static/ref.mp4")
    assert params["materials"] == ["/static/a.jpg"]  # 图片仍作商品图下发


def test_build_gen_params_always_emits_reference_video_key():
    """键必须存在(无视频时为空串):跨端契约按"是否下发"校验,缺键 worker 会静默回退 r2v"""
    params = build_gen_params(_template(), ["/static/a.jpg"], None)
    assert "reference_video" in params
    assert params["reference_video"] == ""


def test_clamp_duration_follows_configured_gears():
    """档位配置生效后 30s 不该再被压成 10s(否则多段生成永远触发不了)"""
    from app.services import gen_rules

    original = gen_rules.SUPPORTED_DURATIONS
    try:
        gen_rules.set_duration_gears("4-30")
        assert len(gen_rules.SUPPORTED_DURATIONS) == 27
        assert gen_rules.clamp_duration(30) == 30
        assert gen_rules.clamp_duration(12) == 12
        # 下界同样按配置吸附
        assert gen_rules.clamp_duration(1) == 4
    finally:
        gen_rules.SUPPORTED_DURATIONS = original


def test_product_desc_injected_as_own_section():
    """识别到商品后必须出现 [商品信息] 段:这是"替换更准"的关键输入(图片+文字双通道)"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/p1.jpg"], None,
        product_desc="白色包装的宠物猫粮,正面印有猫咪图案",
    )
    ctx = params["prompt_context"]
    assert "[商品信息]" in ctx
    assert "白色包装的宠物猫粮" in ctx
    # 该段要落在 [补充要求] 之前,与台词区([商家信息])分开
    assert ctx.index("[商品信息]") < ctx.index("[补充要求]")


def test_no_product_desc_no_empty_section():
    """没识别出来时不能留下空的 [商品信息] 段 —— 空段只会稀释模型注意力"""
    params = build_gen_params(_template(), ["/static/ref.mp4", "/static/p1.jpg"], None)
    assert "[商品信息]" not in params["prompt_context"]


def test_v2v_with_product_images_injects_replace_requirement():
    """选模板 + 上传商品图 + 选「换产品」意图 → 系统自动注入「替换商品」要求,不依赖用户手写备注

    实测用户通常不写备注,结果是成片里还是参考视频原来的商品/人物 —— 复刻等于白做。
    无明确意图时(纯上传图未选替换维度)按设计走「纯复刻」,不注入替换要求;
    这里模拟 desktop 真实上传流:上传商品图即带 intent=['product']。
    """
    params = build_gen_params(_template(), ["/static/ref.mp4", "/static/p1.jpg"], None, intent=["product"])
    assert params["gen_mode"] == "v2v"
    assert "替换为用户上传的商品图内容" in params["prompt_context"]


def test_v2v_without_product_images_has_no_replace_requirement():
    """只有参考视频、没有商品图时不该注入替换要求(没有可替换的东西)"""
    params = build_gen_params(_template(), ["/static/ref.mp4"], None)
    assert params["gen_mode"] == "v2v"
    assert "替换为用户上传的商品图内容" not in params["prompt_context"]


def test_user_remark_kept_and_ordered_after_system_requirement():
    """用户备注仍要保留,且排在系统要求之后(两者共存,用户可继续细化)

    模拟 desktop 上传商品图时带 intent=['product'],系统替换要求会注入,
    用户备注随后排在 [补充要求] 段落。
    """
    params = build_gen_params(_template(), ["/static/ref.mp4", "/static/p1.jpg"], "字幕字号再大一点", intent=["product"])
    ctx = params["prompt_context"]
    assert "字幕字号再大一点" in ctx
    assert ctx.index("替换为用户上传的商品图内容") < ctx.index("字幕字号再大一点")


def test_non_video_modes_do_not_inject_replace_requirement():
    """i2v/t2v 不该被注入视频编辑专用的替换要求"""
    single = build_gen_params(_template(), ["/static/p1.jpg"], None)
    assert "替换为用户上传的商品图内容" not in single["prompt_context"]


def test_material_hint_describes_video_edit():
    hint = build_material_hint("v2v", 2)
    assert "参考视频" in hint and "商品图" in hint
    assert "替换" in hint   # 商品图是"要出镜的主体",可替换原片主体


def test_extra_requirement_reaches_prompt_context():
    """用户写的补充要求必须进 prompt_context

    此前它只随扁平 prompt 下发,而 worker 拿到 prompt_context 后**不再读扁平 prompt**,
    于是"把视频里的人换成商品图主体"这类指令被静默丢弃 —— 用户以为写了会生效,实际没有。
    """
    params = build_gen_params(
        _template(), ["/static/a.jpg"],
        "大标题:招牌菜;把视频里的人换成我上传的商品图主体;口播文案:快来",
    )
    assert "[补充要求]" in params["prompt_context"]
    assert "把视频里的人换成我上传的商品图主体" in params["prompt_context"]


def test_no_extra_keeps_context_clean():
    """没有补充要求时不应凭空多出一个空段落(空段落会稀释模型注意力)"""
    params = build_gen_params(_template(), ["/static/a.jpg"], "大标题:招牌菜")
    assert "[补充要求]" not in params["prompt_context"]


def test_parse_remark_splits_roles():
    parsed = parse_remark("大标题:招牌小龙虾;副标题:本地人都在排队;口播文案:周末约起来")
    assert parsed["title"] == "招牌小龙虾"
    assert parsed["subtitle"] == "本地人都在排队"
    assert parsed["script"] == "周末约起来"
    assert parsed["extra"] == []


def test_parse_remark_tolerates_empty_and_unknown():
    assert parse_remark(None)["title"] == ""
    assert parse_remark("")["script"] == ""
    parsed = parse_remark("氛围:热闹;大标题:开业啦")
    assert parsed["title"] == "开业啦"
    assert parsed["extra"] == ["氛围:热闹"]


def test_parse_remark_supports_chinese_separator_and_colon():
    parsed = parse_remark("大标题：招牌菜；口播文案：赶紧来")
    assert parsed["title"] == "招牌菜"
    assert parsed["script"] == "赶紧来"


def test_structured_text_only_uses_user_confirmed_copy():
    """文案只认用户确认的那份:函数已不接受模板参数,模板默认文案无从参与"""
    structured = build_structured_text(parse_remark("大标题:自定义"))
    assert structured["title"] == "自定义"
    assert structured["subtitle"] == ""
    assert structured["script"] == ""


def test_gen_mode_by_material_count():
    """与 worker 的模式选择保持一致:0→t2v,1→i2v,多张→r2v(复刻)"""
    assert resolve_gen_mode(0) == "t2v"
    assert resolve_gen_mode(1) == "i2v"
    assert resolve_gen_mode(3) == "r2v"


def test_material_hint_distinguishes_reference_and_product():
    """复刻场景(多张)不能再说成"产品图",否则 LLM 改写方向跑偏"""
    assert "参考画面" in build_material_hint("r2v", 3)
    assert "产品图" in build_material_hint("i2v", 1)
    assert "无素材" in build_material_hint("t2v", 0)


def test_prompt_context_has_three_sections():
    structured = {"title": "招牌小龙虾", "subtitle": "本地人都在排队", "script": "周末约起来"}
    ctx = build_prompt_context(structured, "r2v", 3, ratio="9:16", duration=10)
    assert "[模板结构]" in ctx
    assert "[商家信息]" in ctx
    assert "[生成模式]" in ctx
    assert "大标题:招牌小龙虾" in ctx
    assert "副标题:本地人都在排队" in ctx
    assert "口播文案:周末约起来" in ctx
    assert "时长:10 秒" in ctx


def test_prompt_context_v2v_does_not_pin_ratio_or_duration():
    """视频编辑不能写死画幅/时长:方舟强制 ratio=adaptive、duration=-1,成片跟随参考视频

    提示词里再写"9:16 / 10 秒"会与真实参数互斥,是"成片画幅、时长与预期不符"的独立来源。
    """
    ctx = build_prompt_context({"title": "招牌小龙虾"}, "v2v", 1, ratio="9:16", duration=10)
    assert "时长:10 秒" not in ctx
    assert "跟随参考视频" in ctx


def test_prompt_context_omits_empty_merchant_section():
    """商家信息为空时不输出空段落,避免稀释模型注意力"""
    ctx = build_prompt_context({"title": "", "subtitle": "", "script": ""}, "t2v", 0)
    assert "[商家信息]" not in ctx
    assert "[生成模式]" in ctx


def test_replicate_format_and_replace_intent_matrix():
    """7 种形态与 3 种替换维度的组合均进入真实建单提示词。"""
    replacement_text = {
        "product": "视频中的商品与品牌标识必须替换",
        "person": "视频中的出镜人物必须替换",
        "scene": "视频中的场景与背景必须替换",
    }
    for replicate_format, item in REPLICATE_FORMATS.items():
        for intent, expected in replacement_text.items():
            params = build_gen_params(
                _template(),
                ["/static/ref.mp4", "/static/material.jpg"],
                None,
                intent=[intent],
                replicate_format=replicate_format,
            )
            context = params["prompt_context"]
            assert params["replicate_format"] == replicate_format
            assert f"目标形态:{item['label']}" in context
            assert item["act"] in context
            assert expected in context


def test_build_gen_params_structured_and_compatible():
    tpl = _template(duration=12)
    params = build_gen_params(tpl, ["/static/a.jpg", "/static/b.jpg", "/static/c.jpg"], "大标题:招牌菜", ratio="16:9")

    assert params["gen_mode"] == "r2v"
    assert params["gen_duration"] == 10          # 12 秒吸附到 10(模型只支持 5/10)
    assert params["duration"] == 12              # 原始值保留,兼容旧逻辑
    assert params["ratio"] == "16:9"
    assert params["resolution"] == "1080P"
    assert params["structured"]["title"] == "招牌菜"
    assert "参考画面" in params["material_hint"]
    assert "[模板结构]" in params["prompt_context"]
    # 扁平 prompt 仅作兼容兜底:模板品类文字已彻底移除,只保留用户确认的内容
    assert "适合餐饮门店" not in params["prompt"]
    assert "招牌菜" in params["prompt"]


def test_build_gen_params_single_material_uses_i2v():
    params = build_gen_params(_template(duration=5), ["/static/a.jpg"], None)
    assert params["gen_mode"] == "i2v"
    assert params["gen_duration"] == 5
    # 扁平 prompt 不再拼模板 desc(品类文字已彻底移除);无用户备注时走通用兜底
    assert params["prompt"] == "生成一段高质量短视频"


def test_parse_remark_captures_composition_parts():
    """备注里的主体/镜头/场景进三段式,不再落进 extra(否则无法覆盖模板默认)"""
    parsed = parse_remark("主体:穿围裙的女店主;镜头:中景缓慢推进;场景:深夜大排档")
    assert parsed["person"] == "穿围裙的女店主"
    assert parsed["shot"] == "中景缓慢推进"
    assert parsed["setting"] == "深夜大排档"
    assert parsed["extra"] == []


def test_prompt_parts_user_overrides_template():
    """换场景只改 setting:其余两段仍取模板默认,运营不必重写整段描述"""
    tpl = _template(prompt_parts={"person": "女店主", "shot": "中景", "setting": "门店"})
    parts = build_prompt_parts(tpl, parse_remark("场景:后厨"))
    assert parts["setting"] == "后厨"
    assert parts["person"] == "女店主"
    assert parts["shot"] == "中景"


def test_prompt_context_renders_composition_between_head_and_merchant():
    structured = {"title": "招牌菜", "subtitle": "", "script": ""}
    ctx = build_prompt_context(
        structured, "t2v", 0, parts={"person": "女店主", "setting": "大排档"},
    )
    assert "画面主体:女店主" in ctx
    assert "场景环境:大排档" in ctx
    assert "镜头语言" not in ctx          # 空段不输出
    assert ctx.index("[模板结构]") < ctx.index("[画面构成]") < ctx.index("[商家信息]")


def test_prompt_context_omits_empty_composition():
    """三段全空时不输出空段落(旧模板无该字段,行为必须不变)"""
    ctx = build_prompt_context({"title": "", "subtitle": "", "script": ""}, "t2v", 0)
    assert "[画面构成]" not in ctx


def test_build_gen_params_delivers_prompt_parts():
    params = build_gen_params(_template(prompt_parts={"setting": "大排档"}), ["/static/a.jpg"], None)
    assert params["prompt_parts"]["setting"] == "大排档"
    assert "[画面构成]" in params["prompt_context"]
    assert "场景环境:大排档" in params["prompt_context"]


def test_build_gen_params_abs_url_hook():
    params = build_gen_params(_template(), ["/static/a.jpg"], None, abs_url=lambda u: f"https://cdn{u}")
    assert params["materials"] == ["https://cdn/static/a.jpg"]


def test_resolve_intent_explicit_priority():
    """显式意图(A)优先于视觉识别类型与备注关键词兜底"""
    assert resolve_intent(["person"], "product", "把商品换成我的") == ["person"]


def test_resolve_intent_from_material_type_fallback():
    """无显式意图时,视觉识别类型(person/product/scene)作默认意图"""
    assert resolve_intent(None, "person", "") == ["person"]
    assert resolve_intent(None, "product", "") == ["product"]
    assert resolve_intent(None, "scene", "") == ["scene"]


def test_resolve_intent_from_remark_keywords():
    """再兜底:扫备注关键词(人物/商品/场景)推断意图"""
    assert resolve_intent(None, "", "把出镜人物换成我的人像") == ["person"]
    assert resolve_intent(None, "", "背景换成户外场景") == ["scene"]


def test_resolve_intent_invalid_filtered():
    """非法意图值被过滤,不污染生成参数"""
    assert resolve_intent(["person", "hack", "product"], "", "") == ["person", "product"]


def test_build_gen_params_v2v_intent_person_only():
    """选模板+参考视频+人物图+意图=person → 只注入"替换人物"指令,且称谓正确"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/person.jpg"], None,
        material_type="person", intent=["person"], product_desc="一位穿红衣的女士",
    )
    ctx = params["prompt_context"]
    assert "出镜人物必须替换为用户上传的人物参考图" in ctx
    assert "商品与品牌标识必须替换" not in ctx
    assert "[人物信息]" in ctx          # 人像不再被错叫"商品"


def test_build_gen_params_v2v_intent_all_three():
    """三者都选=商品/人物/场景全替换,产出全新一片"""
    params = build_gen_params(
        _template(),
        ["/static/ref.mp4", "/static/p.jpg", "/static/person.jpg", "/static/scene.jpg"],
        None, material_type="product", intent=["product", "person", "scene"],
    )
    ctx = params["prompt_context"]
    assert "商品与品牌标识必须替换" in ctx
    assert "出镜人物必须替换" in ctx
    assert "场景与背景必须替换" in ctx
    assert params["intent"] == ["product", "person", "scene"]


def test_build_replace_requirement_empty_falls_back_to_blanket():
    """意图为空时回退原 blanket 指令,保证改造前后 v2v 默认行为一致"""
    req = build_replace_requirement([])
    assert "商品与出镜主体必须替换" in req


def test_build_gen_params_v2v_no_recognition_falls_back_to_product_replace():
    """D4 兜底最后一道闸:视觉识别完全不可用(无 subjects、无 material_type)、

    却上传了图且没显式选意图时,仍按商品替换,保证上传图被使用、不白复刻。

    正常的 person/scene 复刻走下面的「按识别维度推断」用例,不会落到这里。
    """
    params = build_gen_params(_template(), ["/static/ref.mp4", "/static/p1.jpg"], None)
    assert params["gen_mode"] == "v2v"
    assert "替换为用户上传的商品图内容" in params["prompt_context"]
    # 识别不到类型 → 默认意图收口为商品,随参数下发(worker 据此注入替换指令)
    assert params["intent"] == ["product"]


def test_build_gen_params_v2v_person_image_infers_person_replace():
    """D4 修复(精确化):上传人物图被识别成 person、但用户没显式选意图 → 按「人物」复刻。

    这是实测踩过的坑:用户上传人像做换脸/换人,原代码一刀切成商品替换,把人像当商品换掉。
    复核点:意图收口为 person,替换指令只换人物,商品与场景被显式锁死(不串)。
    """
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/person.jpg"], None,
        material_type="person",
        subjects={"person": "穿红衣的女士", "product": "", "scene": "", "type": "person", "desc": "穿红衣的女士"},
    )
    assert params["intent"] == ["person"]
    ctx = params["prompt_context"]
    assert "视频中的出镜人物必须替换为用户上传的人物参考图" in ctx
    # 未选中的商品/场景不得被串成替换目标
    assert "参考视频中的商品与品牌标识、场景与背景必须保持原样" in ctx
    assert "替换为用户上传的商品图内容" not in ctx


def test_build_gen_params_v2v_scene_image_infers_scene_replace():
    """上传场景图被识别成 scene、但用户没显式选意图 → 按「场景」复刻,不串成商品替换。"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/scene.jpg"], None,
        material_type="scene",
        subjects={"person": "", "product": "", "scene": "海边咖啡馆", "type": "scene", "desc": "海边咖啡馆"},
    )
    assert params["intent"] == ["scene"]
    ctx = params["prompt_context"]
    assert "视频中的场景与背景必须替换为用户上传/指定的场景" in ctx
    assert "参考视频中的商品与品牌标识、出镜人物必须保持原样" in ctx
    assert "替换为用户上传的商品图内容" not in ctx


def test_build_gen_params_v2v_product_image_infers_product_replace():
    """上传商品图被识别成 product、但用户没显式选意图 → 收口 product(与原 D4 行为一致)"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/p1.jpg"], None,
        material_type="product",
        subjects={"person": "", "product": "红色水壶", "scene": "", "type": "product", "desc": "红色水壶"},
    )
    assert params["intent"] == ["product"]
    assert "视频中的商品与品牌标识必须替换为用户上传的商品图内容" in params["prompt_context"]


def test_build_gen_params_v2v_no_image_stays_pure_replicate():
    """只有参考视频、没有商品图时不应注入任何替换要求(纯复刻,保持原主体)"""
    params = build_gen_params(_template(), ["/static/ref.mp4"], None)
    assert params["gen_mode"] == "v2v"
    assert "替换为用户上传的商品图内容" not in params["prompt_context"]
    # 无素材 → 意图保持为空(不误触发替换)
    assert params["intent"] == []


# --- 多图分组识别:人物形象图 + 产品图 各自成段 ---

def test_prompt_context_injects_person_and_product_sections():
    """同时传人物形象图与产品图 → 两段各自注入,替换指令分别下发(不互相覆盖)"""
    ctx = build_prompt_context(
        {"title": "招牌菜", "subtitle": "", "script": ""}, "v2v", 2,
        intent=["person", "product"],
        subjects={
            "person": "短发女模特,米色针织衫",
            "product": "木质气垫梳,原木色",
            "scene": "", "type": "product", "desc": "木质气垫梳,原木色",
        },
    )
    assert "[人物信息]" in ctx and "[商品信息]" in ctx
    assert "人物主体(视觉识别):短发女模特,米色针织衫" in ctx
    assert "商品主体(视觉识别):木质气垫梳,原木色" in ctx
    assert "替换参考视频中的原有人物主体" in ctx
    assert "替换参考视频中的原有商品主体" in ctx
    assert ctx.index("[人物信息]") < ctx.index("[商品信息]")   # 注入顺序固定


def test_prompt_context_multi_subject_skips_empty_roles():
    """只识别到人物时不该凭空造出一个空的商品段"""
    ctx = build_prompt_context(
        {"title": "t", "subtitle": "", "script": ""}, "v2v", 1,
        intent=["person", "product"],
        subjects={
            "person": "女模特", "product": "", "scene": "",
            "type": "person", "desc": "女模特",
        },
    )
    assert "[人物信息]" in ctx
    assert "[商品信息]" not in ctx


def test_build_gen_params_passes_subjects_through():
    """subjects 要一路透传到 prompt_context(否则"多图结合"在建单链路上断掉)"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/p.jpg", "/static/person.jpg"], None,
        intent=["person", "product"],
        subjects={
            "person": "女模特", "product": "气垫梳", "scene": "",
            "type": "product", "desc": "气垫梳",
        },
    )
    ctx = params["prompt_context"]
    assert "[人物信息]" in ctx and "[商品信息]" in ctx
    assert "女模特" in ctx and "气垫梳" in ctx


def test_prompt_context_drops_roles_outside_intent():
    """识别把"照片背景"也归纳成 scene 时,不能凭空多出一条「替换场景」指令

    用户只勾了换人物+换产品,参考视频的场景必须原样保留 —— 多注入的 scene 段
    会变成"把场景也换掉",属于实测踩过的偏航。
    """
    ctx = build_prompt_context(
        {"title": "t", "subtitle": "", "script": ""}, "v2v", 2,
        intent=["person", "product"],
        subjects={
            "person": "女模特", "product": "气垫梳",
            "scene": "机舱门外蓝天白云、庭院红漆木门",
            "type": "person", "desc": "女模特",
        },
    )
    assert "[人物信息]" in ctx and "[商品信息]" in ctx
    assert "[场景信息]" not in ctx
    assert "替换参考视频中的原有场景" not in ctx


def test_prompt_context_keeps_description_when_intent_filters_all():
    """过滤后一段不剩时不能丢描述(识别只给出 other 也要能注入,否则模型完全看不到参考图信息)"""
    ctx = build_prompt_context(
        {"title": "t", "subtitle": "", "script": ""}, "v2v", 1,
        intent=["person"],
        subjects={
            "person": "", "product": "", "scene": "一只黑狗趴在木门前",
            "type": "scene", "desc": "一只黑狗趴在木门前",
        },
    )
    # 单主体 + 单意图 → 称谓跟随意图,描述必须保留
    assert "[人物信息]" in ctx
    assert "一只黑狗趴在木门前" in ctx


# ——— 复刻目标形态(replicate formats)———

def test_replicate_format_whitelist_normalizes():
    """形态白名单收口:合法值保留(大小写不敏感),非法/空值一律归为「不指定」"""
    assert len(SUPPORTED_REPLICATE_FORMATS) == 7
    assert normalize_replicate_format("short_drama") == "short_drama"
    assert normalize_replicate_format("SHORT_DRAMA") == "short_drama"
    # 非法值不抛错:前端传错也不该把建单打挂,归为不指定即可
    assert normalize_replicate_format("bad_value") == ""
    assert normalize_replicate_format(None) == ""
    assert normalize_replicate_format("") == ""


def test_replicate_format_options_are_single_source():
    """形态选项与校验白名单必须同源(白名单由选项派生),且每项都要带展示文案

    前端的形态标签由后端 `REPLICATE_FORMAT_OPTIONS` 下发;若两者各存一份,
    新增形态会出现"前端能选、后端校验不过"或反之的漂移。
    """
    assert tuple(o["key"] for o in REPLICATE_FORMAT_OPTIONS) == SUPPORTED_REPLICATE_FORMATS
    for opt in REPLICATE_FORMAT_OPTIONS:
        assert opt.get("label") and opt.get("desc"), f"形态[{opt['key']}]缺少展示文案"


def test_replicate_format_assets_match_whitelist():
    """磁盘上的形态资产与白名单**双向**对齐:新增或删除 .md 都必须同步白名单

    资产目录在 backend/skills/prompts/replicate/formats(worker 加载器扫描 backend 路径)。
    """
    from pathlib import Path

    from skills.prompts import _BACKEND_PROMPTS

    fmt_dir = Path(_BACKEND_PROMPTS) / "replicate" / "formats"
    on_disk = {p.stem for p in fmt_dir.glob("*.md")}
    assert on_disk == set(SUPPORTED_REPLICATE_FORMATS), (
        f"形态资产与白名单不一致:仅磁盘有={on_disk - set(SUPPORTED_REPLICATE_FORMATS)},"
        f"仅白名单有={set(SUPPORTED_REPLICATE_FORMATS) - on_disk}"
    )


def test_all_replicate_formats_have_prompt_asset():
    """7 种形态必须都有对应提示词资产,否则选了形态却注入不了内容(静默失效最难排查)"""
    for key in SUPPORTED_REPLICATE_FORMATS:
        assert _render_replicate_format(key).startswith("[复刻目标形态]"), f"形态[{key}]缺少提示词资产"


def test_build_gen_params_always_emits_format_key():
    """键必须存在(不指定时为空串):跨端契约按"是否下发"校验,worker 读到空串即跳过注入"""
    params = build_gen_params(_template(), ["/static/a.jpg"], None)
    assert "format" in params
    assert params["format"] == ""


def test_build_gen_params_with_format_injects_section():
    """指定形态 → 下发 format 键,并把形态资产注入 prompt_context"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/p1.jpg"], None,
        replicate_format="short_drama",
    )
    assert params["format"] == "short_drama"
    assert "[复刻目标形态]" in params["prompt_context"]
    # 形态段落要紧跟 [模板结构] 之后:越早声明越不易被后面的细节稀释
    ctx = params["prompt_context"]
    assert ctx.index("[模板结构]") < ctx.index("[复刻目标形态]") < ctx.index("[生成模式]")


def test_build_gen_params_invalid_format_injects_nothing():
    """非法形态 → 归一化为不指定,行为与改造前完全一致(老客户端/脏数据都不受影响)"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/p1.jpg"], None,
        replicate_format="not_a_format",
    )
    assert params["format"] == ""
    assert "[复刻目标形态]" not in params["prompt_context"]


def test_format_section_coexists_with_replace_requirement():
    """形态与替换意图互不覆盖:换了产品也能同时按短剧形态重塑结构"""
    params = build_gen_params(
        _template(), ["/static/ref.mp4", "/static/p1.jpg"], None,
        intent=["product"], replicate_format="short_drama",
    )
    ctx = params["prompt_context"]
    assert "[复刻目标形态]" in ctx
    assert "替换为用户上传的商品图内容" in ctx
