# -*- coding: utf-8 -*-
"""生成任务:参数组装与工具函数(纯函数,无需数据库/Redis)"""
import asyncio
import inspect
from types import SimpleNamespace

from app.services.generate_task import (
    JOB_BY_TYPE,
    _abs_url,
    _expand_image_roles,
    _gen_task_no,
    calc_stage,
)
from app.schemas.generate_task import CreateSchema, DeconstructSchema
from app.services.gen_rules import resolve_gen_defaults
from app.settings import config

from _cross_worker_loader import worker_app_context


def _worker_build_gen_params(*args, **kwargs):
    """在 worker 上下文内调用 worker 的 build_gen_params(两端 app 同名,需隔离加载)"""
    with worker_app_context():
        from app.services.prompt_builder import build_gen_params
        return build_gen_params(*args, **kwargs)


def test_gen_defaults_keys_fit_into_build_gen_params():
    """resolve_gen_defaults 的返回键里,backend 实际透传给 worker 的(ratio/resolution/duration)
    必须被 worker 的 build_gen_params_from_raw 接受 —— 多传一个不接受的关键字建单就 500。

    这个坑真实踩过:给 resolve_gen_defaults 加了 durations(时长档位展示用)之后,
    建单接口直接报 "unexpected keyword argument 'durations'"。
    """
    defaults = resolve_gen_defaults({
        "gen.video_ratio": "9:16",
        "gen.video_resolution": "1080P",
        "gen.video_durations": "4-15",
    })
    # worker 的 app 与 backend 同名,需在隔离上下文内加载(见 _cross_worker_loader)。
    # backend 把 ratio/resolution/duration 透传到 raw,worker 的 build_gen_params(被
    # build_gen_params_from_raw 调用)直接按命名参数接收,这里钉死签名,防止「透传键 worker 不认」导致建单 500。
    with worker_app_context():
        from app.services.prompt_builder import build_gen_params
        sig = inspect.signature(build_gen_params)
    passed = {"ratio", "resolution", "duration"}
    extra = sorted(passed - set(sig.parameters))
    assert not extra, f"build_gen_params 不接受 {extra},建单将报 500"


def test_refund_precharge_calls_refund(monkeypatch):
    """建单失败要退回预扣额度 —— 否则用户扣了额度却没拿到任务"""
    from app.services import credit as credit_mod
    from app.services.generate_task import Service

    called = {}

    async def fake_refund(log_id, remark=""):
        called["log_id"] = log_id
        return 1

    monkeypatch.setattr(credit_mod.service, "refund_consume_log", fake_refund)
    asyncio.run(Service._refund_precharge(99))
    assert called["log_id"] == 99


def test_refund_precharge_swallows_refund_failure(monkeypatch):
    """退款自身失败不能掩盖原始异常(原始异常才是排查入口),也不能再抛出去"""
    from app.services import credit as credit_mod
    from app.services.generate_task import Service

    async def boom(log_id, remark=""):
        raise RuntimeError("db down")

    monkeypatch.setattr(credit_mod.service, "refund_consume_log", boom)
    asyncio.run(Service._refund_precharge(99))  # 不抛异常即通过


def test_refund_precharge_noop_without_log():
    """没扣过额度(付费订单任务)时不做任何事"""
    from app.services.generate_task import Service
    asyncio.run(Service._refund_precharge(None))


def test_abs_url_prefixes_relative_only():
    assert _abs_url("/static/a.jpg") == f"{config.BACKEND_PUBLIC_URL}/static/a.jpg"
    assert _abs_url("https://cdn.example.com/a.jpg") == "https://cdn.example.com/a.jpg"
    assert _abs_url("") == ""


def test_build_gen_params_merges_desc_and_remark():
    # 真实链路里 materials 已由 backend 用 BACKEND_PUBLIC_URL abs 成绝对地址再下发,
    # 这里传绝对地址以避免 worker 侧再次 abs(会按 worker 配置补出不同 base)
    abs_mat = f"{config.BACKEND_PUBLIC_URL}/static/a.jpg"
    tpl = SimpleNamespace(id=9, title="探店模板", desc="适合餐饮门店", duration=12)
    params = _worker_build_gen_params(tpl, [abs_mat], "突出招牌菜")
    assert params["template_id"] == 9
    assert params["duration"] == 12
    # 模板品类文字不再进扁平 prompt;只保留用户确认的内容
    assert "适合餐饮门店" not in params["prompt"]
    assert "突出招牌菜" in params["prompt"]
    assert params["materials"][0] == abs_mat


def test_calc_stage_thresholds():
    assert calc_stage(0) == "解析模板结构"
    assert calc_stage(100) == "回传成片"


def test_calc_stage_by_task_type():
    """数字人任务有独立的阶段划分,不复用视频阶段"""
    assert calc_stage(0, "digital") == "解析口播文案"
    assert calc_stage(20, "digital") == "合成口播音频"
    assert calc_stage(100, "digital") == "回传成片"


def test_job_by_type_covers_all_capabilities():
    assert JOB_BY_TYPE == {
        "video": "process_video",
        "image": "process_image",
        "audio": "process_audio",
        "text": "process_text",
        "digital": "process_digital",
        # 带货视频复刻的前置拆解任务(只分析,不产出媒体)
        "deconstruct": "process_deconstruct",
    }


def test_my_list_trims_heavy_shot_fields(monkeypatch):
    """列表页必须剔除 usage 里的重字段(原片分镜/逐镜头逆推)

    单条任务的 shots/shot_prompts 可达数 KB(最多 30 镜头),整页响应会成倍膨胀;
    详情接口仍完整返回,前端从 /detail 读取。这里钉死裁剪行为,防止回归。
    """
    from app.services import generate_task as gt
    from app.schemas.generate_task import QuerySchema

    obj = SimpleNamespace(id=1, template_id=None)

    async def _list(page_num=1, page_size=10, search=None, order=None):
        return 1, [obj]

    async def _detail(self, target, save=True, template=None, for_admin=False):
        return {
            "id": 1,
            "usage": {
                "shots": [{"index": 0, "start": 0.0}],
                "shot_prompts": {"0": "特写"},
                "seconds": 8,
                "cost": {"cost": 2},
            },
        }

    async def _template_map(objs):
        return {}

    monkeypatch.setattr(gt.crud, "list", _list)
    monkeypatch.setattr(gt.Service, "_to_detail", _detail)
    monkeypatch.setattr(gt.Service, "_template_map", staticmethod(_template_map))

    total, items = asyncio.run(gt.Service().my_list(7, QuerySchema()))
    assert total == 1
    assert items[0]["usage"] == {"seconds": 8, "cost": {"cost": 2}}


def test_my_list_keeps_usage_without_heavy_fields(monkeypatch):
    """usage 里没有重字段时原样保留,不做无意义改写"""
    from app.services import generate_task as gt
    from app.schemas.generate_task import QuerySchema

    obj = SimpleNamespace(id=1, template_id=None)

    async def _list(page_num=1, page_size=10, search=None, order=None):
        return 1, [obj]

    async def _detail(self, target, save=True, template=None, for_admin=False):
        return {"id": 1, "usage": {"cost": {"cost": 1}}}

    async def _template_map(objs):
        return {}

    monkeypatch.setattr(gt.crud, "list", _list)
    monkeypatch.setattr(gt.Service, "_to_detail", _detail)
    monkeypatch.setattr(gt.Service, "_template_map", staticmethod(_template_map))

    _, items = asyncio.run(gt.Service().my_list(7, QuerySchema()))
    assert items[0]["usage"] == {"cost": {"cost": 1}}


def test_gen_task_no_prefix_and_unique():
    a, b = _gen_task_no(), _gen_task_no()
    assert a.startswith("GY")
    assert a != b


def test_expand_image_roles_single_role_backward_compat():
    """旧契约:每 URL 一个角色串,仍按出现顺序原样展开"""
    roles = _expand_image_roles(
        {"u1": "product", "u2": "person"},
        ["u1", "u2", "u3"],
    )
    assert roles == ["product", "person", ""]


def test_expand_image_roles_multi_role_same_url():
    """一键三换:同一张图被同时用作 product/person/scene,按下标依次取角色"""
    roles = _expand_image_roles(
        {"same": "product,person,scene"},
        ["ref1", "same", "same", "same", "logo"],
    )
    assert roles == ["", "product", "person", "scene", ""]


def test_expand_image_roles_missing_key_is_empty():
    """没有 image_roles 或 URL 不在映射里 → 该位置为空串,不报错"""
    assert _expand_image_roles(None, ["u1"]) == [""]
    assert _expand_image_roles({}, ["u1", "u2"]) == ["", ""]


def test_build_gen_params_carries_structured_context():
    """除兼容用的扁平 prompt 外,还需下发结构化上下文与模型实际档位"""
    tpl = SimpleNamespace(
        id=9, title="探店模板", desc="适合餐饮门店", category="餐饮", tags=["探店"],
        duration=12, default_text={"title": "默认标题"},
    )
    params = _worker_build_gen_params(tpl, ["/static/a.jpg", "/static/b.jpg"], "大标题:招牌菜", ratio="9:16", resolution="1080P")
    assert params["gen_mode"] == "r2v"
    assert params["gen_duration"] == 10      # 模板 12 秒 → 吸附到 10
    assert params["ratio"] == "9:16"
    assert params["resolution"] == "1080P"
    assert params["structured"]["title"] == "招牌菜"
    assert "[模板结构]" in params["prompt_context"]
    assert len(params["materials"]) == 2


# ——— 复刻目标形态(replicate formats)———

def test_create_schema_format_normalized():
    """建单形态走白名单:合法值保留,非法值归一化为 None(不指定),不把请求打挂"""
    assert CreateSchema(materials=["/static/a.jpg"], format="short_drama").format == "short_drama"
    assert CreateSchema(materials=["/static/a.jpg"], format="BAD").format is None
    # 不传 → 不指定形态,与老客户端行为一致
    assert CreateSchema(materials=["/static/a.jpg"]).format is None


def test_deconstruct_schema_format_normalized():
    """拆解与建单共用同一白名单:两侧必须取到同一个形态,否则"理解原片"与"重塑出片"会打架"""
    d = DeconstructSchema(reference_video="/static/ref.mp4", format="talking_head")
    assert d.format == "talking_head"
    assert DeconstructSchema(reference_video="/static/ref.mp4", format="BAD").format is None


def test_build_gen_params_carries_replicate_format():
    """形态随建单参数下发到 worker:指定时原样带出,未指定时为空串(键必须存在)"""
    tpl = SimpleNamespace(id=9, title="t", duration=12, default_text={})
    assert _worker_build_gen_params(tpl, ["/static/a.jpg"], None, replicate_format="short_drama")["format"] == "short_drama"
    assert _worker_build_gen_params(tpl, ["/static/a.jpg"], None)["format"] == ""
    # 非法形态同样归一化为不指定,脏数据不会导致建单失败
    assert _worker_build_gen_params(tpl, ["/static/a.jpg"], None, replicate_format="BAD")["format"] == ""
