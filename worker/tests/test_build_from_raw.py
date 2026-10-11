# -*- coding: utf-8 -*-
"""端到端契约测试:backend 下发的「原始参数 + 序列化模板」经 worker 组装应产出完整生成参数。

这是 backend→worker 提示词组装迁移的核心回归:backend 不再持有组装逻辑,只下发业务输入与
序列化后的 _template(仅含 id/title/duration/prompt_parts);worker 在 process_video 里调用
build_gen_params_from_raw 完成组装。本测试验证两端契约对齐、组装结果与旧链路一致。
"""
from app.services.prompt_builder import build_gen_params_from_raw


def _backend_style_raw():
    """模拟 backend _build_raw_params 产出的下发包(字段与 generate_task._build_raw_params 对齐)。"""
    return {
        "template_id": 7,
        "materials": ["https://cdn.example.com/a.jpg"],
        "remark": "主打高性价比保温杯",
        "ratio": "9:16",
        "resolution": "1080P",
        "duration": 10,
        "product_desc": "智能保温杯",
        "material_type": "product",
        "intent": None,
        "subjects": {"person": "年轻妈妈", "scene": "厨房"},
        "real_person_strategy": "auto",
        "replicate_format": "",
        "lead_act": "",
        "creative_level": "normal",
        "hook_boost": "strong",
        "asset_override": "",
        # 序列化模板:backend 只下发这四个字段(旧链路模板对象字段更多,worker 只取所需)
        "_template": {
            "id": 7,
            "title": "保温杯种草",
            "duration": 10,
            # 画面构成三段式:backend 序列化模板只透传这三个键(person/shot/setting),
            # 与 PROMPT_PARTS 契约一致;其它键名会被 build_prompt_parts 静默忽略。
            "prompt_parts": {
                "person": "年轻妈妈出镜演示",
                "shot": "近景特写保温杯",
                "setting": "明亮厨房场景",
            },
        },
        # backend 侧可能附带的下游透传字段
        "cost": 5,
        "webui": True,
    }


def test_build_from_raw_assembles_prompt_context():
    """序列化模板 + 原始参数经 worker 组装后应得到非空 prompt_context(组装确实发生)。"""
    assembled = build_gen_params_from_raw(_backend_style_raw())
    assert isinstance(assembled, dict)
    assert assembled.get("prompt_context"), "prompt_context 必须被组装出来(非空)"
    # 模板三段式应进入上下文(画面构成)
    assert "年轻妈妈出镜演示" in assembled["prompt_context"]
    assert "明亮厨房场景" in assembled["prompt_context"]
    # 结构化画面构成也随 prompt_parts 透传
    assert assembled["prompt_parts"] == {
        "person": "年轻妈妈出镜演示",
        "shot": "近景特写保温杯",
        "setting": "明亮厨房场景",
    }


def test_build_from_raw_normalizes_ratio_and_intent():
    """画幅/意图应被归一化,且视觉识别分组 subjects 原样回传。"""
    assembled = build_gen_params_from_raw(_backend_style_raw())
    assert assembled["ratio"] == "9:16"
    assert assembled["resolution"] == "1080P"
    # material_type=product 且无显式意图 → 默认商品替换意图
    assert assembled["intent"] == ["product"]
    # 多图分组识别结果原样回传(供 worker 强制替换指令使用)
    assert assembled["subjects"] == {"person": "年轻妈妈", "scene": "厨房"}
    # 模板元信息随 _template 透传
    assert assembled["template_id"] == 7
    assert assembled["template_title"] == "保温杯种草"


def test_build_from_raw_passthrough_fields():
    """backend 单独下发的 per-task 覆盖字段与下游透传字段必须保留,不破坏下游读取。"""
    assembled = build_gen_params_from_raw(_backend_style_raw())
    # per-task 覆盖字段(原始组装函数不产出)
    assert assembled["creative_level"] == "normal"
    assert assembled["hook_boost"] == "strong"
    assert assembled["lead_act"] == ""
    assert assembled["asset_override"] == ""
    # 兼容键:下游可能按 gen_ratio/gen_resolution 读取
    assert assembled["gen_ratio"] == "9:16"
    assert assembled["gen_resolution"] == "1080P"
    # 下游透传字段
    assert assembled["cost"] == 5
    assert assembled["webui"] is True
    # 参考视频键必须存在(即便为空串),否则 worker 会静默回退普通 r2v
    assert "reference_video" in assembled


def test_build_from_raw_passthrough_p3_synthesis_fields():
    """P3 合成层字段(B-roll/信息卡·角标·动效/音效)必须透传到组装结果。

    组装函数只产出提示词相关字段;这些字段由 backend 下发、base.run 在成片收尾阶段消费。
    一旦被组装结果覆盖丢弃,主视频链路(process_video)的 P3 能力会静默失效且无日志,
    因此用本用例把「透传白名单」钉死,防止再次回退。
    """
    raw = _backend_style_raw()
    raw.update({
        "auto_broll": {"enabled": True, "source": "https://cdn.example.com/b.mp4"},
        "overlay_card": {"title": "卖点", "body": "正文"},
        "overlay_reveal": {"text": "揭秘", "ref": "moment:reveal"},
        "overlay_flash": {"color": "#FF0000", "at_ms": 300},
        "overlay_sticker": {"text": "好评", "anchor": "selection:product"},
        "sound_effects": [{"url": "https://cdn.example.com/ding.mp3", "at_ms": 800}],
    })
    assembled = build_gen_params_from_raw(raw)
    assert assembled["auto_broll"]["enabled"] is True
    assert assembled["overlay_card"]["title"] == "卖点"
    assert assembled["overlay_reveal"]["ref"] == "moment:reveal"
    assert assembled["overlay_flash"]["at_ms"] == 300
    assert assembled["overlay_sticker"]["anchor"] == "selection:product"
    assert assembled["sound_effects"][0]["url"] == "https://cdn.example.com/ding.mp3"
