# -*- coding: utf-8 -*-
"""
跨端契约测试:worker 读取的 params 字段 / 常量,必须与 backend 实际下发的一致。

背景:本轮改造给 params 增加了一批结构化字段(prompt_context/structured/gen_mode/
material_hint/gen_duration/ratio/resolution),两端此前靠人工对齐。任一侧改字段名
都会静默失效(worker 读到 None 后回退旧逻辑,不报错),因此这里用源码级断言钉死。

放在 backend 侧是因为它能同时读到两端源码;若 worker 目录缺失(单独部署包)则跳过。
"""
import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import gen_rules
from app.services.gen_rules import SUPPORTED_RATIOS, SUPPORTED_RESOLUTIONS
from app.services.prompt_builder import build_gen_params

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = BACKEND_ROOT.parent / "worker"

# worker 运行时自行注入的字段(不在 backend 下发范围内):
# _task_id 用于命名结果文件;_notify_url 供工具层读写 backend 资产缓存(P2)
RUNTIME_KEYS = {"_task_id", "_notify_url"}
# 历史兼容回退别名:worker 仍保留读取,但 backend 已统一下发主字段,不再下发该键
FALLBACK_KEYS = {"prompt"}

_PARAM_GET_RE = re.compile(r"""params\.get\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']""")


def _worker_source(rel: str) -> str:
    path = WORKER_ROOT / rel
    if not path.exists():
        pytest.skip(f"未找到 worker 源码({path}),跳过跨端契约校验")
    return path.read_text(encoding="utf-8")


def _worker_params_keys(rel: str) -> set:
    """提取 worker 从 params 中读取的全部字段名"""
    return set(_PARAM_GET_RE.findall(_worker_source(rel)))


def _enclosing_dict_keys(source: str, idx: int) -> set:
    """从 idx 所属的最近一个 {...} 块中提取 "key": 形式的字段名"""
    start = source.rfind("{", 0, idx)
    if start < 0:
        return set()
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return set(re.findall(r"""["']([A-Za-z_][A-Za-z0-9_]*)["']\s*:""", source[start:i]))
    return set()


def _load_worker_module(rel: str, name: str):
    """按文件路径加载 worker 的纯函数模块(worker 与 backend 包名都是 app,不能常规 import)"""
    if name in sys.modules:
        return sys.modules[name]
    path = WORKER_ROOT / rel
    if not path.exists():
        pytest.skip(f"未找到 worker 源码({path}),跳过跨端契约校验")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _video_params_keys() -> set:
    """backend 视频链真实下发的字段(取 build_gen_params 的实际输出)"""
    template = SimpleNamespace(
        id=1, title="模板", category="餐饮", tags=["探店"], desc="画面要求", duration=8,
        default_text={"title": "默认标题"},
    )
    return set(build_gen_params(template, ["m1"], "大标题:xx;口播:yy").keys())


def _digital_params_keys() -> set:
    """backend 数字人链下发的字段(取 create_digital 中 params 字典的键)"""
    source = (BACKEND_ROOT / "app/services/generate_task.py").read_text(encoding="utf-8")
    idx = source.find('"digital_id"')
    assert idx > 0, "未找到数字人 params 组装处,契约测试需同步更新"
    return _enclosing_dict_keys(source, idx)


def test_worker_video_fields_are_delivered():
    """worker 视频工具读取的字段,必须都是 backend 真实下发的字段"""
    used = _worker_params_keys("app/tools/video_tool.py")
    assert used, "未解析到 worker 读取的字段,正则可能已失效"
    missing = used - (_video_params_keys() | RUNTIME_KEYS | FALLBACK_KEYS)
    assert not missing, f"worker 读取了 backend 未下发的字段(会静默回退): {sorted(missing)}"


def test_worker_digital_fields_are_delivered():
    """数字人链同上:字段名漂移会让形象图/音色等关键参数拿不到"""
    used = _worker_params_keys("app/tools/digital_tool.py")
    assert used
    missing = used - (_digital_params_keys() | RUNTIME_KEYS | FALLBACK_KEYS)
    assert not missing, f"worker 读取了 backend 未下发的字段(会静默回退): {sorted(missing)}"


def test_supported_durations_consistent():
    """时长档位两端必须一致:worker 多认一档就会提交模型不支持的时长"""
    source = _worker_source("app/tools/video_tool.py")
    m = re.search(r"SUPPORTED_DURATIONS\s*=\s*\(([^)]*)\)", source)
    assert m, "未解析到 worker 的 SUPPORTED_DURATIONS"
    worker_durations = tuple(int(x) for x in re.findall(r"\d+", m.group(1)))
    assert worker_durations == tuple(gen_rules.SUPPORTED_DURATIONS)


def test_prompt_labels_cover_all_supported_values():
    """提示词文案表要覆盖全部可选画幅/清晰度,否则新档位在提示词里会退化成裸比例"""
    source = _worker_source("app/tools/prompt_template.py")

    def _label_keys(name: str) -> set:
        m = re.search(rf"{name}\s*=\s*\{{(.*?)\}}", source, re.S)
        return set(re.findall(r"""["']([^"']+)["']\s*:""", m.group(1))) if m else set()

    assert set(SUPPORTED_RATIOS) <= _label_keys("RATIO_LABELS"), "画幅文案表未覆盖全部可选画幅"
    assert set(SUPPORTED_RESOLUTIONS) <= _label_keys("RESOLUTION_LABELS"), "清晰度文案表未覆盖全部可选清晰度"


def test_script_anchor_implementations_consistent():
    """词锚点两端同构:worker 镜像实现与 backend 必须逐字节一致地算出同一结果。

    worker 与 backend 是独立部署包,无法共享模块,只能靠这里钉死;
    任一侧改了分词/锚点规则而另一侧没跟上,此测试立刻失败。
    """
    worker = _load_worker_module("app/tools/script_anchor.py", "worker_script_anchor")
    from app.services import script_schema

    structured = {
        "title": "夏日龙虾节开幕",
        "subtitle": "招牌小龙虾 39 元一份",
        "script": "欢迎来到本店,招牌小龙虾现在特惠,赶紧下单吧",
    }
    extras = ["锚点:product=3-7", "瞬时:reveal=招牌小龙虾"]

    assert worker.split_words(structured["script"]) == script_schema.split_words(structured["script"])
    assert worker.build_segments(structured) == script_schema.build_segments(structured)
    assert worker.build_script(structured, extras) == script_schema.build_script(structured, extras)

    script = script_schema.build_script(structured, extras)
    for ref in ("selection:product", "moment:reveal", "selection:ghost"):
        assert worker.resolve_window(script, ref) == script_schema.resolve_window(script, ref)
    assert worker.estimate_timing(script, 10) == script_schema.estimate_timing(script, 10)


def test_cache_key_implementations_consistent():
    """P2 资产缓存:两端键必须逐字节一致。

    worker 与 backend 是独立部署包,缓存键漂移的表现是「缓存写了但永远读不到」——
    不报错、只是一次次重复付费调用,因此必须钉死。
    """
    worker = _load_worker_module("app/core/asset_cache.py", "worker_asset_cache")
    from app.services import asset_cache

    payloads = [
        {"text": "招牌小龙虾现在特惠", "voice": "alloy", "model": "qwen-audio", "format": "mp3"},
        {"model": "gpt-4o", "system": "你是提示词专家", "user": "[模板结构]\n标题:xx"},
        {},
    ]
    for payload in payloads:
        for asset_type in ("tts_audio", "optimized_prompt"):
            assert worker.build_cache_key(asset_type, payload) == asset_cache.build_cache_key(
                asset_type, payload
            ), f"缓存键两端不一致 type={asset_type} payload={payload}"


def test_gen_params_delivers_script():
    """视频链必须下发词锚点脚本(P0),否则 worker 全程无锚点可用"""
    params = _video_params_keys()
    assert "script" in params, "build_gen_params 未下发 script 字段"


def test_prompt_optimize_system_has_no_hardcoded_ratio():
    """改写系统提示必须走参数注入:写死画幅会与可配置的 gen.video_ratio 矛盾"""
    source = _worker_source("app/tools/prompt_template.py")
    m = re.search(r"PROMPT_OPTIMIZE_SYSTEM_TEMPLATE\s*=\s*\((.*?)\n\)", source, re.S)
    assert m, "未解析到改写系统提示模板"
    template = m.group(1)
    assert "{" + "ratio" + "}" in template and "{" + "resolution" + "}" in template
    assert "9:16" not in template, "改写提示里又出现了硬编码画幅"
