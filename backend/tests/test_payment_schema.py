# -*- coding: utf-8 -*-
"""支付订单参数契约回归测试。"""
from app.schemas.payment import CreateOrderSchema


def test_create_order_schema_retains_replicate_options():
    """付费订单必须保留形态和真人策略，供支付成功后的任务交付使用。"""
    payload = CreateOrderSchema(
        materials=["https://example.test/reference.mp4"],
        format="talking_head",
        real_person_strategy="drop",
    )

    assert payload.format == "talking_head"
    assert payload.real_person_strategy == "drop"