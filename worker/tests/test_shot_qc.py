# -*- coding: utf-8 -*-
"""逐镜头质检(P1-7):原片与成片在同一时间位置配对比对,产出逐镜头分数

三条底线:
  ① 必须告知模型"哪些差异是替换意图要求的" —— 否则会把"商品换成了用户的"判成没复刻上;
  ② 只标记、不自动重跑 —— 重跑是额外的模型费用,属于必须确认的行为变更;
  ③ 任何一步失败都返回空,不能让质检把一次已付费的成片弄成失败任务。
"""
import asyncio
import base64
import os
import tempfile
from types import SimpleNamespace
from typing import Dict

from app.core import asset_cache, compose, shots
from app.settings import config
from app.tools.video_tool import SHOT_QC_LOW_SCORE, VideoGenTool
from skills.prompt_library import build_shot_qc_prompt, parse_shot_qc


def _table(*ranges):
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


# --- 提示词:替换意图必须说清楚 ---

def test_build_shot_qc_prompt_states_expected_differences():
    """必须写明"被替换元素的差异不扣分",否则模型会把预期结果判成没复刻上"""
    text = build_shot_qc_prompt(3, ["product"])
    assert "3 个镜头" in text
    assert "需要替换的元素:商品" in text
    assert "不要扣分" in text
    assert '"score"' in text


def test_build_shot_qc_prompt_pure_replicate():
    """纯复刻没有要替换的元素,渲染不能报错且措辞明确"""
    assert "需要替换的元素:无(本次为纯复刻,不替换任何元素)" in build_shot_qc_prompt(2, [])


def test_build_shot_qc_prompt_injects_transformation_lens():
    """质检必须注入「改造透镜」:复刻要"保留角色语义、重塑形态",
    即形态层面的差异是**达成复刻**而非失败 —— 少了这层会把正确改造的镜头判成低分。

    只注入透镜:参考理解/生成依赖与打分无关,不该白白吃掉 token。
    """
    text = build_shot_qc_prompt(2, ["product"])
    assert "视频复刻方法论参考" in text, "未注入 Hypit 方法论附录"
    assert "改造透镜" in text
    assert "生成依赖" not in text and "参考视频理解" not in text


# --- 解析 ---

def test_parse_shot_qc_standard():
    text = '{"shots": [{"index": 0, "score": 92, "issue": ""}, {"index": 1, "score": 58, "issue": "景别变了"}]}'
    assert parse_shot_qc(text, [0, 1]) == {
        0: {"score": 92, "issue": ""},
        1: {"score": 58, "issue": "景别变了"},
    }


def test_parse_shot_qc_tolerates_fence_and_prose():
    text = '质检如下:\n```json\n{"shots": [{"index": 0, "score": 88}]}\n```'
    assert parse_shot_qc(text, [0]) == {0: {"score": 88, "issue": ""}}


def test_parse_shot_qc_clamps_score():
    """分数夹到 0-100:模型偶尔给出 120 或 -5"""
    text = '{"shots": [{"index": 0, "score": 120}, {"index": 1, "score": -5}]}'
    assert parse_shot_qc(text, [0, 1]) == {0: {"score": 100, "issue": ""}, 1: {"score": 0, "issue": ""}}


def test_parse_shot_qc_skips_items_without_score():
    """取不到分数的条目直接跳过:没有分数的质检没有意义"""
    text = '{"shots": [{"index": 0, "issue": "忘了给分"}, {"index": 1, "score": 70}]}'
    assert parse_shot_qc(text, [0, 1]) == {1: {"score": 70, "issue": ""}}


def test_parse_shot_qc_allows_partial_and_position_fallback():
    """漏判的镜头不参与汇总;缺 index 时按位置对应"""
    text = '{"shots": [{"score": 80}, {"index": 9, "score": 50}]}'
    assert parse_shot_qc(text, [3, 4]) == {3: {"score": 80, "issue": ""}}


def test_parse_shot_qc_bad_payload():
    assert parse_shot_qc("模型今天不想输出 JSON", [0]) == {}
    assert parse_shot_qc("", [0]) == {}
    assert parse_shot_qc('{"shots": "not-a-list"}', [0]) == {}


# --- 质检输入清单 ---

def test_review_targets_takes_shot_middle():
    """取镜头中点:首帧紧贴切点,容易取到转场残影,不代表该镜常态画面"""
    targets = shots.review_targets(_table((0, 10), (10, 20)))
    assert targets == [{"index": 0, "time": 5.0}, {"index": 1, "time": 15.0}]


def test_review_targets_subsamples_keeping_index_pairs():
    """超上限时等距抽稀,序号与时间点始终一一对应"""
    targets = shots.review_targets(_table((0, 10), (10, 20), (20, 30)), limit=2)
    assert [row["index"] for row in targets] == [0, 1]
    assert all("time" in row for row in targets)


def test_review_targets_empty():
    assert shots.review_targets([]) == []


# --- 分数行 ---

def test_qc_rows_sorted_and_flagged():
    """按序号升序,并由 worker 统一打 low 标记(前端不重复写阈值)"""
    rows = VideoGenTool._qc_rows({
        1: {"score": SHOT_QC_LOW_SCORE - 1, "issue": "偏了"},
        0: {"score": SHOT_QC_LOW_SCORE, "issue": ""},
    })
    assert [row["index"] for row in rows] == [0, 1]
    assert rows[0]["low"] is False
    assert rows[1]["low"] is True


# --- 编排:守卫与端到端 ---

class _FakeCompletions:
    def __init__(self, text: str):
        self.text = text
        self.kwargs: Dict = {}

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.text))])


def _stub_qc_infra(monkeypatch, tool, reply: str, output_download_ok: bool = True):
    """打桩抽帧/下载/缓存/chat:抽帧按文件名写内容,便于断言图片成对顺序"""
    completions = _FakeCompletions(reply)

    async def _fake_run(cmd, timeout=600, cwd=None, truncate=True):
        with open(cmd[-1], "wb") as fh:
            fh.write(os.path.basename(cmd[-1]).encode())
        return {"ok": True, "stdout": "", "stderr": ""}

    async def _no_cache(*a, **k):
        return None

    async def _store(*a, **k):
        return True

    def _fake_download(url, *args, **kwargs):
        if not output_download_ok and str(url).startswith("https://oss/final"):
            return None
        fd, path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        return path

    monkeypatch.setattr(config, "CHAT_MODEL", "chat-test")
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(compose, "run", _fake_run)
    monkeypatch.setattr(asset_cache, "fetch", _no_cache)
    monkeypatch.setattr(asset_cache, "store", _store)
    monkeypatch.setattr("app.tools.video_tool.download_to_local", _fake_download)
    monkeypatch.setattr(tool, "_chat_client", lambda gw: SimpleNamespace(
        chat=SimpleNamespace(completions=completions),
    ))
    return completions


def _decoded_images(completions) -> list:
    """取出请求里内联图片的内容(假抽帧按文件名写入,便于验证顺序)"""
    content = completions.kwargs["messages"][1]["content"]
    images = [part for part in content if part["type"] == "image_url"]
    return [base64.b64decode(part["image_url"]["url"].split(",", 1)[1]).decode() for part in images]


def test_review_shots_pairs_reference_then_output(monkeypatch):
    """端到端:每个镜头两张图,顺序必须是"先原片、后成片"(提示词就是按这个顺序声明的)"""
    tool = _make_tool()
    reply = '{"shots": [{"index": 0, "score": 92}, {"index": 1, "score": 55, "issue": "主体偏了"}]}'
    completions = _stub_qc_infra(monkeypatch, tool, reply)
    workdir = tempfile.mkdtemp(prefix="qc_")
    cleanup = []
    try:
        rows = _run(tool._review_shots_with_vision(
            "https://oss/final.mp4", "https://x/ref.mp4", "ref.mp4", workdir,
            _table((0, 5), (5, 10)), ["product"], cleanup,
        ))
    finally:
        for path in cleanup:
            if os.path.exists(path):
                os.remove(path)
        for name in os.listdir(workdir):
            os.remove(os.path.join(workdir, name))
        os.rmdir(workdir)

    assert [row["index"] for row in rows] == [0, 1]
    assert rows[1]["issue"] == "主体偏了"
    assert _decoded_images(completions) == [
        "qc_ref_0.jpg", "qc_out_0.jpg", "qc_ref_1.jpg", "qc_out_1.jpg",
    ]


def test_review_shots_skips_single_shot():
    """单镜头原片没有可比对的镜头结构,不该多花一次调用"""
    tool = _make_tool()
    assert _run(tool._review_shots_with_vision(
        "u", "src", "ref.mp4", ".", _table((0, 30)), [], [],
    )) == []


def test_review_shots_skips_without_chat_model(monkeypatch):
    monkeypatch.setattr(config, "CHAT_MODEL", "")
    tool = _make_tool()
    assert _run(tool._review_shots_with_vision(
        "u", "src", "ref.mp4", ".", _table((0, 5), (5, 10)), [], [],
    )) == []


def test_review_shots_survives_output_download_failure(monkeypatch):
    """成片下载失败 → 跳过质检,但绝不能抛出异常把成片弄丢"""
    tool = _make_tool()
    _stub_qc_infra(monkeypatch, tool, '{"shots": [{"index": 0, "score": 90}]}', output_download_ok=False)
    assert _run(tool._review_shots_with_vision(
        "https://oss/final.mp4", "src", "ref.mp4", tempfile.mkdtemp(prefix="qc_"),
        _table((0, 5), (5, 10)), [], [],
    )) == []


def test_review_shots_returns_empty_when_unparsable(monkeypatch):
    """模型没按 JSON 输出 → 空结果(不落库、不影响成片)"""
    tool = _make_tool()
    _stub_qc_infra(monkeypatch, tool, "这里是一段散文")
    workdir = tempfile.mkdtemp(prefix="qc_")
    cleanup = []
    try:
        assert _run(tool._review_shots_with_vision(
            "https://oss/final.mp4", "src", "ref.mp4", workdir,
            _table((0, 5), (5, 10)), [], cleanup,
        )) == []
    finally:
        for path in cleanup:
            if os.path.exists(path):
                os.remove(path)
        for name in os.listdir(workdir):
            os.remove(os.path.join(workdir, name))
        os.rmdir(workdir)
