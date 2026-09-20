# -*- coding: utf-8 -*-
"""生成任务:参数组装与工具函数(纯函数,无需数据库/Redis)"""
from types import SimpleNamespace

from app.services.generate_task import (
    JOB_BY_TYPE,
    _abs_url,
    _build_gen_params,
    _gen_task_no,
    calc_stage,
)
from app.settings import config


def test_abs_url_prefixes_relative_only():
    assert _abs_url("/static/a.jpg") == f"{config.BACKEND_PUBLIC_URL}/static/a.jpg"
    assert _abs_url("https://cdn.example.com/a.jpg") == "https://cdn.example.com/a.jpg"
    assert _abs_url("") == ""


def test_build_gen_params_merges_desc_and_remark():
    tpl = SimpleNamespace(id=9, title="探店模板", desc="适合餐饮门店", duration=12)
    params = _build_gen_params(tpl, ["/static/a.jpg"], "突出招牌菜")
    assert params["template_id"] == 9
    assert params["duration"] == 12
    assert "适合餐饮门店" in params["prompt"]
    assert "突出招牌菜" in params["prompt"]
    assert params["materials"][0] == f"{config.BACKEND_PUBLIC_URL}/static/a.jpg"


def test_calc_stage_thresholds():
    assert calc_stage(0) == "解析模板结构"
    assert calc_stage(100) == "优化输出成片"


def test_job_by_type_covers_all_capabilities():
    assert JOB_BY_TYPE == {
        "video": "process_video",
        "image": "process_image",
        "audio": "process_audio",
        "text": "process_text",
    }


def test_gen_task_no_prefix_and_unique():
    a, b = _gen_task_no(), _gen_task_no()
    assert a.startswith("GY")
    assert a != b
