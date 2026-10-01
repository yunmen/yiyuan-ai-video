# -*- coding: utf-8 -*-
"""
跨端契约测试:worker 读取的 params 字段 / 常量,必须与 backend 实际下发的一致。

背景:本轮改造给 params 增加了一批结构化字段(prompt_context/structured/gen_mode/
material_hint/gen_duration/ratio/resolution),两端此前靠人工对齐。任一侧改字段名
都会静默失效(worker 读到 None 后回退旧逻辑,不报错),因此这里用源码级断言 + 隔离加载
(backend 与 worker 顶层包同名 app,单进程需临时切换)钉死。

放在 backend 侧是因为它能同时读到两端源码;若 worker 目录缺失(单独部署包)则跳过。
"""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# backend 侧(本测试在 backend 环境运行,模块顶层 import 的 app 即 backend 的):
from app.services import gen_rules
from app.services.gen_rules import SUPPORTED_RATIOS, SUPPORTED_RESOLUTIONS
from app.services.prompt_builder import VALID_INTENTS

from _cross_worker_loader import worker_app_context, load_worker_module

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = BACKEND_ROOT.parent / "worker"

# worker 运行时自行注入的字段(不在 backend 下发范围内):
# _task_id 用于命名结果文件;_notify_url 供工具层读写 backend 资产缓存(P2)
RUNTIME_KEYS = {"_task_id", "_notify_url"}
# 历史兼容回退别名:worker 仍保留读取,但 backend 已统一下发主字段,不再下发该键
FALLBACK_KEYS = {"prompt"}
# 局部重跑(O7)专用:backend 的 generate_task.regenerate_segment 仅为该子链路下发
# original_video(拼回原片的时间窗来源);segment_index/new_text 经函数参数传入,
# _regenerate_segment 由 base.py 读取分流。它们都来自 backend,不属于历史回退别名,
# 因此单独列示,避免「worker 读取了 backend 未下发的字段」契约误报。
LOCAL_RERUN_KEYS = {"original_video", "segment_index", "new_text", "_regenerate_segment"}

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


def _worker_build_gen_params(*args, **kwargs):
    """在 worker 上下文内调用 worker 的 build_gen_params(两端 app 同名,需隔离加载)"""
    with worker_app_context():
        from app.services.prompt_builder import build_gen_params
        return build_gen_params(*args, **kwargs)


def _video_params_keys() -> set:
    """backend 视频链真实下发的字段:取 worker 侧 build_gen_params_from_raw 的实际输出。

    它模拟了「backend 下发 raw + worker 组装」的完整链路(与旧链路产出一致),比单看
    build_gen_params 更全面——creative_level/hook_boost/lead_act/asset_override/qc_auto_retry/
    goal 等「backend 单独下发、worker 组装后回填/透传」的字段也只有在这里才完整出现。
    """
    raw = {
        "template_id": 7, "materials": ["/static/a.jpg"], "remark": "主打高性价比",
        "ratio": "9:16", "resolution": "1080P", "duration": 10,
        "product_desc": "", "material_type": "product", "intent": None,
        "subjects": {}, "real_person_strategy": "auto", "replicate_format": "",
        "lead_act": "", "creative_level": "normal", "hook_boost": "strong",
        "asset_override": "", "edited_prompt": "", "qc_auto_retry": False, "goal": "",
        "_template": {"id": 7, "title": "保温杯种草", "duration": 10, "prompt_parts": {}},
        "cost": 5, "webui": True,
    }
    with worker_app_context():
        from app.services.prompt_builder import build_gen_params_from_raw
        return set(build_gen_params_from_raw(raw).keys())


def _digital_params_keys() -> set:
    """backend 数字人链下发的字段(取 create_digital 中 params 字典的键)"""
    source = (BACKEND_ROOT / "app/services/generate_task.py").read_text(encoding="utf-8")
    idx = source.find('"digital_id"')
    assert idx > 0, "未找到数字人 params 组装处,契约测试需同步更新"
    return _enclosing_dict_keys(source, idx)


def test_worker_video_fields_are_delivered():
    """worker 视频工具读取的字段,必须都是 backend 真实下发的字段。

    同时覆盖 video_tool(成片生成)与 video_understand_tool(视频理解/局部重跑提示),
    两者都从 params 读取 backend 下发字段;任一字段在「backend 下发 → worker 组装透传」链路上
    断裂,这里都会报出(例如此前 qc_auto_retry / goal 被组装函数漏透传,导致用户付费开启的
    低分自动重跑与一句话目标理解静默失效)。
    """
    for rel in ("app/tools/video_tool.py", "app/tools/video_understand_tool.py"):
        used = _worker_params_keys(rel)
        assert used, f"未解析到 {rel} 读取的字段,正则可能已失效"
        missing = used - (_video_params_keys() | RUNTIME_KEYS | FALLBACK_KEYS | LOCAL_RERUN_KEYS)
        assert not missing, f"{rel} 读取了 backend 未下发的字段(会静默回退): {sorted(missing)}"


def test_worker_digital_fields_are_delivered():
    """数字人链同上:字段名漂移会让形象图/音色等关键参数拿不到"""
    used = _worker_params_keys("app/tools/digital_tool.py")
    assert used
    missing = used - (_digital_params_keys() | RUNTIME_KEYS | FALLBACK_KEYS)
    assert not missing, f"worker 读取了 backend 未下发的字段(会静默回退): {sorted(missing)}"


def _func_dict_keys(func_name: str) -> set:
    """提取某个函数体内出现的全部 "key": 字段名(覆盖 if/elif/else 多分支的字典字面量)

    render 的下发参数是按路线分支出三套字典字面量,不能只取某一对花括号,
    故扫描整个函数体的 "key": 形式,取并集作为「backend 可能下发」的字段集合。
    """
    src = (BACKEND_ROOT / "app/services/generate_task.py").read_text(encoding="utf-8")
    m = re.search(rf"(?:async def|def) {func_name}\b", src)
    assert m, f"未找到函数 {func_name}"
    start = m.start()
    # 下一个顶层 def 之前即为本函数体
    end = len(src)
    for mm in re.finditer(r"\n(?:async def|def) ", src[start + 1:]):
        end = start + 1 + mm.start()
        break
    body = src[start:end]
    return set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', body))


def test_worker_render_fields_are_delivered():
    """视频换口播:worker render_tool 读取的字段必须由 backend create_render 下发(多分支并集)"""
    used = _worker_params_keys("app/tools/render_tool.py")
    assert used
    delivered = _func_dict_keys("create_render") | RUNTIME_KEYS | FALLBACK_KEYS
    missing = used - delivered
    assert not missing, f"worker 读取了 backend 未下发的字段(会静默回退): {sorted(missing)}"


def test_supported_durations_consistent():
    """时长档位两端必须一致:worker 多认一档就会提交模型不支持的时长"""
    source = _worker_source("app/tools/video_tool.py")
    m = re.search(r"SUPPORTED_DURATIONS\s*=\s*\(([^)]*)\)", source)
    assert m, "未解析到 worker 的 SUPPORTED_DURATIONS"
    worker_durations = tuple(int(x) for x in re.findall(r"\d+", m.group(1)))
    assert worker_durations == tuple(gen_rules.SUPPORTED_DURATIONS)


def test_resolution_ladder_consistent():
    """清晰度降档阶梯两端必须一致:worker 多认一档(如 480p)会提交 backend 必拒的请求。

    backend gen_rules.SUPPORTED_RESOLUTIONS 是唯一事实源;worker 的 _RESOLUTION_LADDER
    必须是它的子集(大小写不敏感),否则降档链会白打一次必然失败的请求。
    """
    source = _worker_source("app/tools/video_tool.py")
    m = re.search(r"_RESOLUTION_LADDER\s*=\s*\(([^)]*)\)", source)
    assert m, "未解析到 worker 的 _RESOLUTION_LADDER"
    worker_ladder = {
        x.strip().strip('"').strip("'").lower()
        for x in re.findall(r"[\"']([^\"']+)[\"']", m.group(1))
    }
    backend_resolutions = {r.lower() for r in SUPPORTED_RESOLUTIONS}
    assert worker_ladder, "worker 降档阶梯不应为空"
    assert worker_ladder <= backend_resolutions, (
        f"worker 降档阶梯含 backend 不支持的档位(会白提交): {sorted(worker_ladder - backend_resolutions)}"
    )


def test_prompt_labels_cover_all_supported_values():
    """提示词文案表要覆盖全部可选画幅/清晰度,否则新档位在提示词里会退化成裸比例"""
    source = _worker_source("app/tools/prompt_template.py")

    def _label_keys(name: str) -> set:
        m = re.search(rf"{name}\s*=\s*\{{(.*?)\}}", source, re.S)
        return set(re.findall(r"""["']([^"']+)["']\s*:""", m.group(1))) if m else set()

    assert set(SUPPORTED_RATIOS) <= _label_keys("RATIO_LABELS"), "画幅文案表未覆盖全部可选画幅"
    assert set(SUPPORTED_RESOLUTIONS) <= _label_keys("RESOLUTION_LABELS"), "清晰度文案表未覆盖全部可选清晰度"


def test_replicate_format_options_consistent():
    """B-shape:复刻目标形态选项两端必须逐条一致(单一来源约束)。

    backend/app/services/gen_rules.py 与 worker/app/services/gen_rules.py 各维护一份
    REPLICATE_FORMAT_OPTIONS(key/label/desc)。它们现在内容相同但分两处维护,改一端文案或
    增删形态而另一端没跟上,就会出现"前端能选、worker 校验不过"或反之的漂移。这里钉死
    两份逐条一致:任一端改了 key/label/desc 都会立刻红。
    """
    backend_opts = {o["key"]: (o["label"], o["desc"]) for o in gen_rules.REPLICATE_FORMAT_OPTIONS}
    with worker_app_context():
        from app.services.gen_rules import REPLICATE_FORMAT_OPTIONS as WORKER_OPTS
        worker_opts = {o["key"]: (o["label"], o["desc"]) for o in WORKER_OPTS}
    assert backend_opts == worker_opts, (
        "复刻目标形态选项两端不一致(副本漂移):\n"
        f"  backend={backend_opts}\n  worker={worker_opts}"
    )


def test_script_anchor_implementations_consistent():
    """词锚点两端同构:worker 镜像实现与 backend 必须逐字节一致地算出同一结果。

    backend 已把脚本锚点逻辑收敛到 worker 独占(backend/app/services/script_schema.py 已删除),
    因此这里只校验 **worker 内部** script_anchor 与 script_schema 两份实现同源——
    任一侧改了分词/锚点规则而另一侧没跟上,此测试立刻失败。
    """
    with worker_app_context():
        worker = load_worker_module("app/tools/script_anchor.py", "worker_script_anchor")
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
    from app.services import asset_cache

    with worker_app_context():
        worker = load_worker_module("app/core/asset_cache.py", "worker_asset_cache")
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


def test_d4_fallback_infers_dimension_from_recognition():
    """D4 修复的跨端契约:worker 读取的 intent / prompt_context 必须随上传图的实际维度走。

    backend 把 v2v + 上传图 + 无显式意图时的默认替换维度,从「一刀切 product」改为
    「按视觉识别维度推断(person/scene/product)」。这条行为必须钉死在契约边界上:
    backend 下发的 intent 字段(worker 据此分流替换维度)和 prompt_context 里的替换指令
    不能退化回 product,否则用户上传的人像/场景参考图会被错当商品换掉。

    视觉识别不可用(无 subjects)时的最后回退仍是 product,见
    test_build_gen_params_v2v_no_recognition_falls_back_to_product_replace。
    """
    # worker 实际读取的 intent 字段必须存在且为列表(契约字段,缺失会静默回退旧逻辑)
    assert "intent" in _video_params_keys(), "build_gen_params 未下发 intent 字段"

    def _gen(subjects, material_type):
        return _worker_build_gen_params(
            SimpleNamespace(id=1, title="t", category="c", tags=[], desc="", duration=8, default_text={}),
            ["/static/ref.mp4", "/static/x.jpg"], None,
            material_type=material_type, subjects=subjects,
        )

    # 人物图 → 收口 person,且 prompt_context 含人物替换指令(worker 据此执行换人)
    person = _gen({"person": "红衣女士", "product": "", "scene": "", "type": "person", "desc": "红衣女士"}, "person")
    assert person["intent"] == ["person"], "人物图未推断为 person 复刻"
    assert "视频中的出镜人物必须替换为用户上传的人物参考图" in person["prompt_context"]

    # 场景图 → 收口 scene,且 prompt_context 含场景替换指令
    scene = _gen({"person": "", "product": "", "scene": "海边咖啡馆", "type": "scene", "desc": "海边咖啡馆"}, "scene")
    assert scene["intent"] == ["scene"], "场景图未推断为 scene 复刻"
    assert "视频中的场景与背景必须替换为用户上传/指定的场景" in scene["prompt_context"]

    # 产品图 → 收口 product(与原行为一致)
    product = _gen({"person": "", "product": "水壶", "scene": "", "type": "product", "desc": "水壶"}, "product")
    assert product["intent"] == ["product"], "产品图未推断为 product 复刻"
    assert "视频中的商品与品牌标识必须替换为用户上传的商品图内容" in product["prompt_context"]


def test_prompt_optimize_system_has_no_hardcoded_ratio():
    """改写系统提示必须走参数注入:写死画幅会与可配置的 gen.video_ratio 矛盾。

    改写模板已迁移到 MD 资产(worker/skills/video-generation/assets/video_optimize.md),由
    prompt_template.build_prompt_optimize_system 经 render 注入 {ratio}/{resolution};
    此处直接校验该资产与渲染结果,避免再因「常量搬家」而误报失败。
    """
    md_path = WORKER_ROOT / "skills/video-generation/assets/video_optimize.md"
    if not md_path.exists():
        pytest.skip(f"未找到改写提示资产({md_path}),跳过校验")
    md_text = md_path.read_text(encoding="utf-8")
    assert "{" + "ratio" + "}" in md_text and "{" + "resolution" + "}" in md_text
    assert "9:16" not in md_text, "改写提示里又出现了硬编码画幅"

    # 渲染路径也要走注入:build_prompt_optimize_system 必须把比例/清晰度标签渲染进结果
    with worker_app_context():
        prompt_template = load_worker_module("app/tools/prompt_template.py", "worker_prompt_template")
        rendered = prompt_template.build_prompt_optimize_system(ratio="9:16", resolution="1080P")
    assert "竖版 9:16" in rendered, "比例标签未注入到渲染结果"
    assert "1080P 高清" in rendered, "清晰度标签未注入到渲染结果"


# —— 副本漂移守护 ——
# backend 与 worker 是两套独立部署包,以下契约专门钉死"任一侧改了、另一端没跟上"就会
# 静默失效的耦合点(B1 配置键 / B4 意图维度 / B8 OSS 上传 / B9 网关能力)。


def test_runtime_config_keys_are_defined_backend():
    """B1:worker 热更新 KEY_MAP 引用的 gen.* 键,backend 必须在 DEFAULT_CONFIGS 中定义。

    worker runtime_config.KEY_MAP 把 backend 下发的 gen.* 键映射到本地属性;
    若某个键在 backend 没播种(DEFAULT_CONFIGS 缺失),worker 永远收不到该配置、静默回退默认值,
    且运营在 admin 也看不到该配置项 —— 典型「改了不生效」漂移。这里钉死 KEY_MAP ⊆ DEFAULT_CONFIGS。
    """
    worker_src = _worker_source("app/core/runtime_config.py")
    m = re.search(r"KEY_MAP\s*=\s*\{(.*?)\}", worker_src, re.S)
    assert m, "未解析到 worker 的 KEY_MAP"
    worker_keys = set(re.findall(r'["\'](gen\.[^"\']+)["\']\s*:', m.group(1)))
    backend_src = (BACKEND_ROOT / "app/services/system_config.py").read_text(encoding="utf-8")
    backend_keys = set(re.findall(r'\{"key":\s*["\']([^"\']+)["\']', backend_src))
    missing = worker_keys - backend_keys
    assert not missing, (
        f"worker KEY_MAP 引用的 gen.* 键在 backend DEFAULT_CONFIGS 缺失(改了不生效): {sorted(missing)}"
    )


def test_intent_labels_consistent():
    """B4:替换意图维度集合必须两端一致。

    backend prompt_builder.VALID_INTENTS 与 worker prompt_library.INTENT_LABELS
    是同一组维度的两处定义;任一侧新增维度而另一端没跟上,用户选的意图在另一端会被丢弃/误判。
    """
    with worker_app_context():
        worker_pl = load_worker_module("skills/prompt_library.py", "worker_prompt_library")
        assert set(VALID_INTENTS) == set(worker_pl.INTENT_LABELS.keys()), (
            f"替换意图维度两端不一致: backend={sorted(VALID_INTENTS)} "
            f"worker={sorted(worker_pl.INTENT_LABELS.keys())}"
        )


def test_oss_core_method_consistent():
    """B8:backend 与 worker 的 TencentCos 实现必须都提供 put_object(核心上传契约)。

    两份实现独立维护、字段命名不同(OSS_SERVICE_* vs OSS_CONFIG);上传方法被改名会直接
    让「结果转存 OSS」整条链路失效且不报错。这里钉死核心上传方法存在;字段命名差异为已知
    部署耦合,不在此强求统一(统一需同步改部署配置,超出本测试范围)。
    """
    backend_src = (BACKEND_ROOT / "app/core/oss.py").read_text(encoding="utf-8")
    worker_src = _worker_source("plugin/oss.py")
    for label, src in (("backend", backend_src), ("worker", worker_src)):
        methods = set(re.findall(r"def\s+(\w+)\s*\(", src))
        assert "put_object" in methods, f"{label} 的 TencentCos 缺少 put_object(核心上传方法)"


def test_backend_gateway_capabilities_supported_by_worker():
    """B9:worker 侧 ai_vision/ai_copy 按 gen.route.<能力> 路由的能力名,worker gateway 必须能解析。

    worker 的 ai_vision/ai_copy 用 gateway.resolve("<cap>") 查命名网关;
    若某个能力 worker gateway.py 的 _FALLBACK/_CAPABILITY_ALIAS 没登记,worker 会把该能力
    路由成空网关(静默回退),导致文案润色/视觉走错网关。这里钉死 worker 用到的能力 ⊆ worker 支持的能力。
    """
    caps = set()
    for fname in ("app/services/ai_vision.py", "app/services/ai_copy.py"):
        src = _worker_source(fname)
        caps |= set(re.findall(r'resolve\(\s*["\']([a-z_]+)["\']', src))
    worker_src = _worker_source("app/core/gateway.py")
    fb = re.search(r"_FALLBACK\s*=\s*\{(.*?)\}", worker_src, re.S)
    assert fb, "未解析到 worker 的 _FALLBACK"
    supported = set(re.findall(r'["\']([a-z_]+)["\']\s*:', fb.group(1)))
    alias = re.search(r"_CAPABILITY_ALIAS\s*=\s*\{(.*?)\}", worker_src, re.S)
    if alias:
        supported |= set(re.findall(r'["\']([a-z_]+)["\']\s*:', alias.group(1)))
    missing = caps - supported
    assert not missing, f"worker 路由的能力 worker gateway 未登记(会静默回退): {sorted(missing)}"
