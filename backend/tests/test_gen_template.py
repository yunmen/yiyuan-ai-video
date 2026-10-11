# -*- coding: utf-8 -*-
"""工程模板(参数模板化)纯逻辑测试:merge_template_params 合并且只保留合法字段。"""
from app.services.gen_template import merge_template_params


def test_merge_keeps_allowed_overrides_filters_dirty_keys():
    """模板快照 + 覆盖项 + 新素材合并;非 CreateSchema 字段(如 UI 态 foo)必须被剔除。"""
    allowed = {"materials", "ratio", "duration", "overlay_ranking", "remark"}
    template_params = {
        "ratio": "9:16",
        "overlay_ranking": {"title": "榜", "items": [{"label": "A", "value": "1"}]},
        "foo": "ui-state",  # 模板保存时混进来的脏键
    }
    overrides = {"duration": 20, "bar": "x"}  # bar 不是合法字段
    final = merge_template_params(
        template_params, overrides, materials=["http://oss/x.mp4"], remark="变体1", allowed_fields=allowed
    )
    assert final["ratio"] == "9:16"
    assert final["overlay_ranking"]["title"] == "榜"
    assert final["duration"] == 20
    assert final["materials"] == ["http://oss/x.mp4"]
    assert final["remark"] == "变体1"
    # 脏键被过滤
    assert "foo" not in final and "bar" not in final
    # 覆盖项优先级高于模板快照(若模板也有 duration 会被覆盖;此处模板无 duration)


def test_merge_materials_always_overridden_by_caller():
    """生成变体时,素材必须由调用方提供,materials 不被模板旧值污染。"""
    allowed = {"materials", "ratio"}
    final = merge_template_params(
        {"materials": ["old.mp4"], "ratio": "1:1"},
        {},
        materials=["new.mp4"],
        remark=None,
        allowed_fields=allowed,
    )
    assert final["materials"] == ["new.mp4"]


def test_generate_merges_template_and_calls_create():
    """端到端契约:generate() 必须把模板快照 + 覆盖项 + 新素材合并成合法 CreateSchema,
    并交给既有 create_video 链路入队(此处 mock 掉 create,不依赖 DB/Redis/ARQ)。"""
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app.services.gen_template import service

    # 模板快照(来自前端 buildTemplateParams 的真实形状子集)
    fake_template = type("T", (), {
        "params": {
            "ratio": "9:16",
            "creative_level": "faithful",
            "overlay_ranking": {"title": "榜", "items": [{"label": "A", "value": "1"}]},
        }
    })()

    captured = {}

    async def fake_create(data, user=None):
        captured["data"] = data.model_dump()
        captured["user"] = user
        return {"task_no": "T1"}

    with patch.object(service, "get", return_value=fake_template), \
         patch("app.services.generate_task.service") as MockSvc:
        MockSvc.create = AsyncMock(side_effect=fake_create)
        user = type("U", (), {"id": 7})()
        res = asyncio.run(
            service.generate(1, user, ["http://oss/x.mp4"], {"duration": 15}, "变体")
        )

    assert res == {"task_no": "T1"}
    d = captured["data"]
    # 合并结果:调用方素材覆盖模板旧值
    assert d["materials"] == ["http://oss/x.mp4"]
    # 模板快照透传
    assert d["ratio"] == "9:16"
    assert d["creative_level"] == "faithful"
    assert d["overlay_ranking"]["title"] == "榜"
    # 覆盖项生效
    assert d["duration"] == 15
    assert d["remark"] == "变体"
    # 用户透传(后续 create 会写入 user_id)
    assert captured["user"].id == 7


def test_delete_returns_false_when_missing():
    """删除不存在的模板 → 返回 False,不抛异常(前端按结果提示)。"""
    import asyncio
    from unittest.mock import patch

    from app.services.gen_template import service

    with patch.object(service, "get", return_value=None):
        ok = asyncio.run(service.delete(999, 1))
    assert ok is False


def test_delete_soft_marks_deleted_and_blocks_cross_user():
    """软删除:本用户模板标记 deleted=True 返回 True;跨用户 / 公共模板返回 False,不误删。"""
    import asyncio
    from unittest.mock import AsyncMock, patch

    from app.services.gen_template import service

    mine = type("M", (), {"user_id": 1, "deleted": False, "save": AsyncMock()})()
    with patch.object(service, "get", return_value=mine):
        ok = asyncio.run(service.delete(1, 1))
    assert ok is True
    assert mine.deleted is True

    # 跨用户:obj.user_id 与传入 user_id 不一致 → 拒绝
    with patch.object(service, "get", return_value=mine):
        ok = asyncio.run(service.delete(1, 2))
    assert ok is False

    # 平台公共模板(user_id=None)普通用户不可删
    public = type("P", (), {"user_id": None, "deleted": False, "save": AsyncMock()})()
    with patch.object(service, "get", return_value=public):
        ok = asyncio.run(service.delete(1, 1))
    assert ok is False

