# -*- coding: utf-8 -*-
"""逐镜头逆推(P0-3):把原片每个镜头「怎么拍的」写进生成提示词

这一组用例钉三类东西:
  ① 纯函数:镜头清单、段↔镜头归属、提示词装配、解析容错;
  ② 安全底线:逆推描述**不能**把原片被替换的元素写回画面(否则"复刻白做");
  ③ 失败回退:任何一步不可用都必须安静退回既有逐段提示词。
"""
import asyncio
import os
import tempfile
from types import SimpleNamespace
from typing import Any, Dict, List

from app.core import asset_cache, compose, multiseg, shots
from app.settings import config
from app.tools.video_tool import VideoGenTool
from skills.prompt_library import (
    build_shot_reverse_prompt,
    intent_labels,
    intent_scope,
    parse_shot_prompts,
)


def _table(*ranges):
    """按 (start, end) 构造分镜表(带 index/duration,与 shots.build_shot_list 同形)"""
    return [
        {
            "index": idx,
            "start": float(start),
            "end": float(end),
            "duration": float(end) - float(start),
        }
        for idx, (start, end) in enumerate(ranges)
    ]


def _run(coro):
    return asyncio.run(coro)


def _make_tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


# --- 替换意图的维度划分 ---

def test_intent_labels_keeps_order_and_drops_unknown():
    """标签保持入参顺序、去重、识别不出的整条丢弃"""
    assert intent_labels(["person", "product"]) == ["人物", "商品"]
    assert intent_labels(["person", "person"]) == ["人物"]
    assert intent_labels(["unknown", "scene"]) == ["场景"]
    assert intent_labels(None) == []


def test_intent_scope_splits_replace_and_keep():
    """要替换 / 要保留必须严格互补 —— 逆推据此决定"哪些元素不能描述" """
    assert intent_scope(["product"]) == ("商品", "人物、场景")
    assert intent_scope(["product", "person"]) == ("商品、人物", "场景")
    # 纯复刻:没有要替换的维度,所有维度都要如实复刻
    assert intent_scope([]) == ("无(本次为纯复刻,不替换任何元素)", "商品、人物、场景")


def test_build_shot_reverse_prompt_injects_scope():
    """渲染出的提示词必须带镜头数、替换维度、保留维度,并给出 JSON 输出契约"""
    text = build_shot_reverse_prompt(3, ["product"], frames_per_shot=2)
    assert "3 个镜头" in text
    assert "**需要替换的元素**:商品" in text
    assert "**需要原样保留的元素**:人物、场景" in text
    assert '"shots"' in text and '"index"' in text


def test_reverse_prompt_resolved_from_backend_canonical():
    """复刻提示词(原 worker 专属)已收归 backend 单一来源;worker 本地不再存副本,
    能渲染即通过"worker 引用 backend"这一打通链路——否则会 KeyError。"""
    from skills.prompts import get
    assert get("shot_reverse") is not None, "worker 未从 backend 引用到 shot_reverse"
    assert get("shot_qc") is not None, "worker 未从 backend 引用到 shot_qc"


def test_build_shot_reverse_prompt_injects_hypit_methodology():
    """真实逆推链路(被 video_understand_tool / video_tool 调用)必须注入 Hypit 复刻方法论,
    证明 hypit skill 真正运用起来,而非仅归档为文件。"""
    text = build_shot_reverse_prompt(2, ["product"], frames_per_shot=2)
    assert "视频复刻方法论参考" in text, "未注入 Hypit 方法论附录"
    assert "改造透镜" in text and "生成依赖" in text and "参考视频理解" in text


def test_build_shot_reverse_prompt_injects_video_direction():
    """逆推还要拿到「视频方向」:三种控制语义(参考条件/关键帧约束/纯文本)。

    只描述静态构图(如"中景推近")不足以约束生成 —— 模型不知道该镜头是
    表演主导(保语义时间锚点)还是动作/镜头主导(用源片段约束节奏与运镜)。
    """
    text = build_shot_reverse_prompt(2, ["product"], frames_per_shot=2)
    assert "视频方向" in text
    assert "参考条件生成" in text and "关键帧约束生成" in text


# --- 逆推结果解析:三种容错 + 部分成功 ---

def test_parse_shot_prompts_standard_json():
    text = '{"shots": [{"index": 0, "shot": "中景推近"}, {"index": 1, "shot": "特写摇移"}]}'
    assert parse_shot_prompts(text, [0, 1]) == {0: "中景推近", 1: "特写摇移"}


def test_parse_shot_prompts_tolerates_fence_and_prose():
    """模型爱在 JSON 外面加说明与代码块围栏,必须能剥掉"""
    text = '分析如下:\n```json\n{"shots": [{"index": 0, "shot": "全景固定"}]}\n```\n以上。'
    assert parse_shot_prompts(text, [0]) == {0: "全景固定"}


def test_parse_shot_prompts_accepts_plain_string_list():
    """只给字符串数组时按 indexes 顺序对应"""
    text = '{"shots": ["第一镜", "第二镜"]}'
    assert parse_shot_prompts(text, [3, 7]) == {3: "第一镜", 7: "第二镜"}


def test_parse_shot_prompts_falls_back_to_position_when_index_missing():
    """缺 index 字段时按位置对应(模型偶尔漏字段)"""
    text = '{"shots": [{"shot": "只有描述"}]}'
    assert parse_shot_prompts(text, [5]) == {5: "只有描述"}


def test_parse_shot_prompts_allows_partial_success():
    """部分成功必须保留:漏一个镜头不该让整批逆推作废"""
    text = '{"shots": [{"index": 0, "shot": "有效"}, {"index": 1, "shot": "  "}]}'
    assert parse_shot_prompts(text, [0, 1]) == {0: "有效"}


def test_parse_shot_prompts_drops_unknown_index_and_bad_payload():
    """序号不在清单里的丢弃;整体不是 JSON 则返回空"""
    assert parse_shot_prompts('{"shots": [{"index": 9, "shot": "越界"}]}', [0, 1]) == {}
    assert parse_shot_prompts("模型今天不想输出 JSON", [0]) == {}
    assert parse_shot_prompts("", [0]) == {}


# --- 逆推输入清单 ---

def test_analysis_targets_takes_first_and_last_frame():
    """每个镜头给「开始帧 + 结束帧」两个时间点:只看一帧推不出运镜"""
    table = _table((0, 10), (10, 20))
    targets = shots.analysis_targets(table)
    assert [row["index"] for row in targets] == [0, 1]
    assert targets[0]["times"] == [0.08, 9.92]
    assert targets[1]["times"] == [10.08, 19.92]


def test_analysis_targets_carries_narration_and_subsamples():
    """台词随镜头带上;超上限时等距抽稀,且序号与时间点始终一一对应"""
    table = _table((0, 10), (10, 20), (20, 30))
    table[1]["narration"] = "限时秒杀"
    assert shots.analysis_targets(table)[1]["narration"] == "限时秒杀"

    slim = shots.analysis_targets(table, limit=2)
    assert [row["index"] for row in slim] == [0, 1]
    assert all(len(row["times"]) == 2 for row in slim)


def test_analysis_targets_empty_table():
    assert shots.analysis_targets([]) == []


# --- 抽帧命令 ---

def test_build_extract_frame_cmd_scales_and_seeks_first():
    """-ss 必须在 -i 之前(输入侧定位),并按宽度等比缩放以省图片 token"""
    cmd = compose.build_extract_frame_cmd("v.mp4", "o.jpg", 1.5, 512)
    assert cmd[:5] == ["ffmpeg", "-y", "-ss", "1.50", "-i"]
    assert "scale=512:-1" in cmd and cmd[-1] == "o.jpg"


def test_build_extract_frame_cmd_without_scale():
    """不传宽度时不做缩放(调用方可能想拿原分辨率)"""
    assert "-vf" not in compose.build_extract_frame_cmd("v.mp4", "o.jpg", 0)


# --- 段 ↔ 镜头归属 ---

def test_segment_shot_map_assigns_by_overlap():
    """按镜头切分时一个镜头正好落在一段里"""
    assert multiseg.segment_shot_map([10, 10, 10], _table((0, 10), (10, 20), (20, 30))) == [[0], [1], [2]]


def test_segment_shot_map_picks_largest_overlap():
    """按秒切分(段与镜头不对齐)时归给重叠最长的那一段"""
    assert multiseg.segment_shot_map([15, 15], _table((0, 10), (10, 20), (20, 30))) == [[0, 1], [2]]


def test_segment_shot_map_skips_insufficient_overlap():
    """只是"擦边"的镜头宁可不归,也不能把描述塞进错误的段"""
    assert multiseg.segment_shot_map([10, 10], _table((9.8, 10.2))) == [[], []]


def test_segment_shot_map_shape_and_empty_inputs():
    """返回值与 segments 等长(调用方按索引取),空输入不炸"""
    assert multiseg.segment_shot_map([15, 15], []) == [[], []]
    assert multiseg.segment_shot_map([], _table((0, 10))) == []


# --- 提示词装配:安全底线 ---

def test_segment_prompt_without_hint_keeps_existing_shape():
    """没有逆推描述时,输出必须与改造前逐字节一致(不影响既有行为)"""
    text = VideoGenTool._segment_prompt("基础提示词", ["第一段台词"], 0)
    assert text == "基础提示词\n[本段台词] 第一段台词\n请只表现本段台词的内容,不要念其他段落的台词。"


def test_segment_prompt_declares_replacement_priority():
    """注入镜头结构的同时,必须声明"元素以替换要求为准"

    少了这句,逆推描述里保留的原片场景/构图会把原片商品人物一起带回来,
    与用户的替换意图直接打架 —— 那正是「复刻白做」的成因。
    """
    text = VideoGenTool._segment_prompt("基础提示词", ["台词"], 0, "中景推近,主体居中")
    assert "[原片镜头结构] 中景推近,主体居中" in text
    assert "以替换要求为准" in text
    assert "[本段台词] 台词" in text


def test_segment_prompt_handles_missing_script():
    """没有台词时返回提示词本身;只有镜头描述时也要组合出来"""
    assert VideoGenTool._segment_prompt("基础提示词", [], 3) == "基础提示词"
    assert VideoGenTool._segment_prompt("基础提示词", [], 0, "全景固定").startswith(
        "基础提示词\n[原片镜头结构] 全景固定"
    )


def test_shot_hint_joins_covered_shots():
    """一段覆盖多个镜头时,描述按镜头顺序拼起来"""
    prompts = {0: "镜头零", 1: "镜头一", 2: "镜头二"}
    assert VideoGenTool._shot_hint(prompts, [[0, 1], [2]], 0) == "镜头零；镜头一"
    assert VideoGenTool._shot_hint(prompts, [[0], [2]], 1) == "镜头二"


def test_shot_hint_returns_empty_when_unavailable():
    """没有可用描述 / 段索引越界时返回空串,调用方据此走原有提示词"""
    assert VideoGenTool._shot_hint({}, [[0]], 0) == ""
    assert VideoGenTool._shot_hint({0: "A"}, [], 0) == ""
    assert VideoGenTool._shot_hint({0: "A"}, [[0]], 5) == ""
    assert VideoGenTool._shot_hint({0: "A"}, [[1]], 0) == ""


# --- 逆推调用:守卫与端到端 ---

def test_build_shot_prompts_skips_single_shot():
    """单镜头原片没有镜头结构可逆推,不该多花一次调用"""
    tool = _make_tool()
    assert _run(tool._build_shot_prompts("https://x/ref.mp4", "ref.mp4", ".", _table((0, 30)), [], [])) == {}


def test_build_shot_prompts_skips_without_chat_model(monkeypatch):
    """未配 chat 模型时直接跳过,连抽帧都不做"""
    monkeypatch.setattr(config, "CHAT_MODEL", "")
    called = {"run": False}

    async def _fail(cmd, **kwargs):
        called["run"] = True
        return {"ok": True, "stdout": "", "stderr": ""}

    monkeypatch.setattr(compose, "run", _fail)
    tool = _make_tool()
    assert _run(tool._build_shot_prompts("u", "ref.mp4", ".", _table((0, 5), (5, 10)), [], [])) == {}
    assert called["run"] is False


class _FakeCompletions:
    """假的多模态调用:记录请求体,按预设文本返回"""

    def __init__(self, text: str):
        self.text = text
        self.kwargs: Dict[str, Any] = {}

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.text))])


def _stub_reverse_infra(monkeypatch, tool, reply: str):
    """把抽帧、缓存、chat 全部打桩,只留逆推编排本身被验证"""
    completions = _FakeCompletions(reply)

    async def _fake_run(cmd, timeout=600, cwd=None, truncate=True):
        # 抽帧命令的最后一个参数是输出路径
        with open(cmd[-1], "wb") as fh:
            fh.write(b"jpeg")
        return {"ok": True, "stdout": "", "stderr": ""}

    async def _no_cache(*a, **k):
        return None

    async def _store(*a, **k):
        return True

    monkeypatch.setattr(config, "CHAT_MODEL", "chat-test")
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(compose, "run", _fake_run)
    monkeypatch.setattr(asset_cache, "fetch", _no_cache)
    monkeypatch.setattr(asset_cache, "store", _store)
    monkeypatch.setattr(tool, "_chat_client", lambda gw: SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    ))
    return completions


def test_build_shot_prompts_inlines_frames_and_parses(monkeypatch):
    """端到端:每镜头抽首尾两帧内联成 data URL,并按序号解析回描述"""
    tool = _make_tool()
    reply = '{"shots": [{"index": 0, "shot": "中景推近"}, {"index": 1, "shot": "特写固定"}]}'
    completions = _stub_reverse_infra(monkeypatch, tool, reply)
    workdir = tempfile.mkdtemp(prefix="shot_rev_")
    cleanup: List[str] = []
    try:
        result = _run(tool._build_shot_prompts(
            "https://x/ref.mp4", "ref.mp4", workdir, _table((0, 5), (5, 10)), ["product"], cleanup,
        ))
    finally:
        for path in cleanup:
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(workdir)

    assert result == {0: "中景推近", 1: "特写固定"}
    content = completions.kwargs["messages"][1]["content"]
    # 1 段说明文字 + 2 个镜头 × 2 帧
    assert content[0]["type"] == "text"
    images = [part for part in content if part["type"] == "image_url"]
    assert len(images) == 4
    assert all(part["image_url"]["url"].startswith("data:image/jpeg;base64,") for part in images)
    # 抽出来的帧文件交由调用方统一清理
    assert len(cleanup) == 4


def test_build_shot_prompts_falls_back_when_unparsable(monkeypatch):
    """模型没按 JSON 输出 → 返回空字典,调用方回退既有逐段提示词"""
    tool = _make_tool()
    _stub_reverse_infra(monkeypatch, tool, "这里是一段散文,不是 JSON")
    workdir = tempfile.mkdtemp(prefix="shot_rev_")
    try:
        assert _run(tool._build_shot_prompts(
            "u", "ref.mp4", workdir, _table((0, 5), (5, 10)), [], [],
        )) == {}
    finally:
        for name in os.listdir(workdir):
            os.remove(os.path.join(workdir, name))
        os.rmdir(workdir)


def test_build_shot_prompts_aborts_on_frame_failure(monkeypatch):
    """抽帧少一张会让图片与镜头序号错位 → 必须整体放弃逆推,而不是给出错位的描述"""
    tool = _make_tool()
    _stub_reverse_infra(monkeypatch, tool, '{"shots": [{"index": 0, "shot": "x"}]}')

    async def _broken_run(cmd, timeout=600, cwd=None, truncate=True):
        return {"ok": False, "stdout": "", "stderr": "boom"}

    monkeypatch.setattr(compose, "run", _broken_run)
    workdir = tempfile.mkdtemp(prefix="shot_rev_")
    try:
        assert _run(tool._build_shot_prompts(
            "u", "ref.mp4", workdir, _table((0, 5), (5, 10)), [], [],
        )) == {}
    finally:
        os.rmdir(workdir)


def test_build_shot_prompts_asset_renders_intent_scope():
    """提示词资产必须能被资产层渲染:变量缺失或占位符写错会在这里直接报错"""
    text = build_shot_reverse_prompt(2, ["scene"])
    assert "**需要替换的元素**:场景" in text
    assert "**需要原样保留的元素**:商品、人物" in text


def test_build_shot_reverse_prompt_injects_replicate_format():
    """指定复刻目标形态 → 逆推提示词追加形态资产,按该形态组织画面而非照抄原片结构"""
    base = build_shot_reverse_prompt(2, ["product"], frames_per_shot=2)
    text = build_shot_reverse_prompt(2, ["product"], frames_per_shot=2, fmt="short_drama")
    assert "复刻目标形态" in text, "未注入复刻目标形态附录"
    assert len(text) > len(base)
    # 形态资产由 backend 单一来源持有,worker 引用复用、不复制
    from skills.prompts import get
    assert get("replicate_format_short_drama") is not None


def test_build_shot_reverse_prompt_format_unspecified_or_invalid_is_identical():
    """未指定 / 非法形态必须与不传完全一致:老任务重跑与脏数据都不改变既有逆推结果"""
    base = build_shot_reverse_prompt(2, ["product"], frames_per_shot=2)
    assert build_shot_reverse_prompt(2, ["product"], frames_per_shot=2, fmt="") == base
    assert build_shot_reverse_prompt(2, ["product"], frames_per_shot=2, fmt="not_a_format") == base
