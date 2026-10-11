# -*- coding: utf-8 -*-
"""mobile 复刻链路对齐测试(后端必须按 mobile 真实请求形状出片)。

mobile 端「视频复刻」表单的真实请求形状(buildRemakePayload):
  - materials = [对标视频URL, 商品图URL?]   // 视频直接放 materials,不单独传 reference_video
  - device = 'mobile'
  - 不传 intent / remark / image_roles       // 没有替换维度选择器,只有「商品图」一个图片槽
  - creative_level 默认回填 defaultCreativeLevel(来自 /gen-config 的 replicate_defaults.creative_level)

核心对齐点:
  1. mobile 只传视频(纯复刻)时,后端不能阻断,且 intent 为空(保留原片)。
  2. mobile 传「视频 + 商品图」但不选 intent 时,后端必须兜底推断为 product(换产品复刻),
     这正是修复「上传商品图却没换产品」的关键 —— 此前 backend 完全不推断、只靠 worker 兜底,
     导致 /precheck、/task/create 判定与 worker 出片口径漂移。
  3. mobile 默认 creative_level='creative' 必须被后端尊重,不被「复刻默认 faithful」覆盖
     (faithful 默认仅对「不传 creative_level」生效;mobile 总显式传值,故保持适度改造)。
"""
from app.services.generate_task import _detect_missing
from app.services.prompt_builder import normalize_creative_level, resolve_intent

VIDEO = "http://oss/ref.mp4"
PRODUCT = "http://oss/product.jpg"


def test_mobile_pure_remake_no_intent_passes():
    # 只传对标视频、不选 intent → 纯复刻:后端不应阻断,intent 为空(保留原片)
    intents = resolve_intent(None, has_reference_video=True, has_images=False)
    assert intents == []
    assert _detect_missing([VIDEO], intents) == []


def test_mobile_remake_with_product_image_infers_product():
    # 传「视频 + 商品图」但不选 intent → 后端 D4 兜底推断 product,且放行(已有替换图)
    intents = resolve_intent(None, has_reference_video=True, has_images=True)
    assert intents == ["product"]
    # 有 product 意图 + 有商品图,不缺替换素材,不应阻断
    assert _detect_missing([VIDEO, PRODUCT], intents) == []


def test_mobile_remake_creative_level_passthrough():
    # mobile 默认 creative_level='creative' 必须被后端尊重(不被 faithful 默认覆盖)
    assert normalize_creative_level("creative") == "creative"
    # 显式传 creative 时,后端 create 的 _creative 推导不会回落到 faithful
    assert normalize_creative_level("creative") or "faithful" == "creative"
