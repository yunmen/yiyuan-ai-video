"""原片元素定位及多产品图片绑定入参校验。"""
import pytest
from pydantic import ValidationError
from app.schemas.generate_task import CreateSchema


def test_element_binding_validates_references_and_roles():
    """新契约允许同元素多图，但拒绝悬空引用、分类冲突与反向跨度。"""
    payload = dict(materials=["ref.mp4", "a.jpg", "b.jpg"], image_slots={"a.jpg": "p1", "b.jpg": "p1"}, image_roles={"a.jpg": "product"}, reference_elements=[dict(id="p1", kind="product", label="菜品", start=1, end=4)])
    assert len(CreateSchema(**payload).image_slots) == 2
    with pytest.raises(ValidationError):
        CreateSchema(**{**payload, "image_slots": {"a.jpg": "missing"}})
    with pytest.raises(ValidationError):
        CreateSchema(**{**payload, "image_roles": {"a.jpg": "person"}})
    with pytest.raises(ValidationError):
        CreateSchema(**{**payload, "reference_elements": [dict(id="p1", kind="product", label="菜品", start=4, end=1)]})


def test_old_slot_contract_remains_valid():
    """旧客户端没有元素描述表时继续接受原有槽位字段。"""
    assert CreateSchema(materials=["a.jpg"], image_slots={"a.jpg": "p1"}).reference_elements is None


def test_observation_position_and_shot_validation():
    """观测位置与镜头上下文结构化保留，非法坐标和跨窗时间被拒绝。"""
    from app.schemas.generate_task import ReferenceElementSchema
    element = dict(id="p1", kind="product", label="红罐", bbox=[0, 0, 0.5, 1])
    observation = dict(time=9, shot_index=2, shot_start=8, shot_end=12)
    assert ReferenceElementSchema(**element, observations=[observation]).observations[0].time == 9
    with pytest.raises(ValidationError):
        ReferenceElementSchema(**{**element, "bbox": [0.7, 0, 0.2, 1]})
    with pytest.raises(ValidationError):
        ReferenceElementSchema(**element, observations=[{**observation, "time": 5}])
