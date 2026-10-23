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


def test_replicate_mode_is_explicit_and_legacy_compatible():
    """动作无需商品口播，非法模式拒绝，历史请求不改变语义。"""
    assert CreateSchema(materials=["ref.mp4"], replicate_mode="action").replicate_mode == "action"
    assert CreateSchema(materials=["ref.mp4"], replicate_mode="commerce").replicate_mode == "commerce"
    assert CreateSchema(materials=["ref.mp4"]).replicate_mode is None
    with pytest.raises(ValidationError):
        CreateSchema(materials=["ref.mp4"], replicate_mode="unknown")


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


def test_material_groups_primary_and_reuse():
    """允许同图跨元素复用，但拒绝组内重复图片与组外主图。"""
    from app.schemas.generate_task import MaterialGroupSchema
    group = {"element_id": "p1", "images": ["a", "b"], "primary_image": "b"}
    assert MaterialGroupSchema(**group).primary_image == "b"
    with pytest.raises(ValidationError):
        MaterialGroupSchema(**{**group, "primary_image": "c"})
    with pytest.raises(ValidationError):
        MaterialGroupSchema(**{**group, "images": ["a", "a"], "primary_image": "a"})
    payload = CreateSchema(materials=["ref.mp4", "a"], material_groups=[
        {"element_id": key, "images": ["a"], "primary_image": "a"} for key in ("p1", "p2")])
    assert len(payload.material_groups) == 2
