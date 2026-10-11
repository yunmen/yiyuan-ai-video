"""元素绑定最终编辑指令与参数组装回归测试。"""
import pytest
from app.services.element_binding import build_binding_directive
from app.services.prompt_builder import build_gen_params_from_raw


def test_multi_angle_and_unbound_preservation():
    """同产品多角度共用身份，不同产品分别绑定，未绑定元素明确保留。"""
    elements = [{"id": "p1", "kind": "product", "label": "菜品", "time": 2}, {"id": "p2", "kind": "product", "label": "饮品", "start": 5, "end": 8}]
    slots = {"a.jpg": "p1", "b.jpg": "p1", "c.jpg": "p2"}
    directive = build_binding_directive(list(slots), slots, elements)
    assert '"使用参考图序号": [1, 2]' in directive
    assert '"使用参考图序号": [3]' in directive
    assert "非完整范围" in directive
    assert "未绑定元素保持原片" in directive
    out = build_gen_params_from_raw({"materials": ["https://example.com/ref.mp4"], "image_slots": slots, "reference_elements": elements})
    assert out["image_slots"] == slots
    assert out["reference_elements"] == elements


def test_missing_target_images_refused():
    """图片丢失后不能悄悄生成错误替换。"""
    with pytest.raises(ValueError, match="替换图片已丢失"):
        build_binding_directive([], {"a.jpg": "p1"}, [{"id": "p1"}])


def test_legacy_binding_without_elements_remains_compatible():
    """旧客户端仅传槽位时不臆造原片定位。"""
    assert build_binding_directive(["a.jpg"], {"a.jpg": "p1"}, []) == ""


def test_segment_window_keeps_global_and_local_coordinates():
    """原片估计窗口转换为切片相对时间，缺跨度不以单帧时间伪造范围。"""
    elements = [{"id": "p1", "kind": "product", "label": "菜品", "start": 3, "end": 8}, {"id": "p2", "kind": "product", "label": "饮品", "time": 12}]
    directive = build_binding_directive(["a.jpg", "b.jpg"], {"a.jpg": "p1", "b.jpg": "p2"}, elements, (5, 10))
    assert '"切片内估计重叠范围秒": [0, 3]' in directive
    assert '"原片代表帧秒（非完整范围）": 12' in directive
    assert "原片 5.000-10.000 秒" in directive


def test_reappearance_uses_window_local_observation():
    """重复出现仅提交当前切片的观测定位，不将空档推断为不存在。"""
    element = {"id": "p1", "kind": "product", "label": "红罐", "observations": [{"time": 1}, {"time": 9, "bbox": [0, 0, 0.5, 1]}]}
    directive = build_binding_directive(["a"], {"a": "p1"}, [element], (8, 12))
    assert '"切片内观测秒": 1' in directive
    assert '"time": 1}' not in directive
    assert "可见性未知" in directive
    assert '"bbox": [0, 0, 0.5, 1]' in directive


def test_material_groups_allow_shared_image_and_primary():
    """同图可复用到多个元素，主图排序不改变实际请求图片序号。"""
    groups = [{"element_id": "p1", "images": ["a", "b"], "primary_image": "b"},
              {"element_id": "p2", "images": ["a"], "primary_image": "a"}]
    elements = [{"id": "p1", "kind": "product"}, {"id": "p2", "kind": "product"}]
    directive = build_binding_directive(["a", "b"], {}, elements, material_groups=groups)
    assert '"使用参考图序号": [2, 1]' in directive
    assert '"使用参考图序号": [1]' in directive
    out = build_gen_params_from_raw({"materials": ["https://example.com/ref.mp4"], "material_groups": groups})
    assert out["material_groups"] == groups
