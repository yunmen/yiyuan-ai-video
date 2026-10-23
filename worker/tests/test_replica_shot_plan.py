# -*- coding: utf-8 -*-
"""可信复刻快照透传、编辑消费与检查点恢复功能测试。"""
import asyncio
import copy
from unittest.mock import AsyncMock

from app.core import frame_quality, media_prep, shots
from app.schemas.base import ToolResult
from app.services.prompt_builder import build_gen_params_from_raw
from app.settings import config
from app.tools.video_tool import VideoGenTool


def _plan():
    """构造两镜头服务端快照，供消费与隔离验证。"""
    return {"version": 1, "source_task_id": 42, "shots": [
        {"index": 0, "start": 0, "end": 10, "duration": 10,
         "description": "原品牌汉堡特写", "narration": "原品牌真好吃"},
        {"index": 1, "start": 10, "end": 20, "duration": 10,
         "description": "镜头缓慢拉远", "narration": "结尾旁白"},
    ]}


def _tool():
    """仅构造客户端，不发起外部请求。"""
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _prepare(tool, manifest, plan, intent=None):
    """调用真实镜头准备逻辑，屏蔽媒体与供应商外部能力。"""
    return asyncio.run(tool._prepare_segment_shots(
        "https://x/ref.mp4", "local.mp4", "/tmp", 20, 20,
        manifest, plan, intent or [], [],
    ))


def test_raw_params_keep_snapshot_separate_from_grid():
    """原始参数组装完整保留快照，不改动九宫格字符串列表。"""
    plan = _plan()
    result = build_gen_params_from_raw({"shot_plan": plan, "deconstruct_id": 42,
                                        "shot_prompts": ["九宫格描述"]})
    assert result["shot_plan"] == plan
    assert result["deconstruct_id"] == 42
    assert result["shot_prompts"] == ["九宫格描述"]


def test_complete_plan_skips_detection_and_reverse(monkeypatch):
    """完整描述直接消费，旁白进入提示词，无重复检测或逆推。"""
    tool = _tool()
    detect = AsyncMock()
    reverse = AsyncMock()
    monkeypatch.setattr(shots, "detect_shots", detect)
    monkeypatch.setattr(tool, "_build_shot_prompts", reverse)
    manifest = {}
    table, prompts, durations, shot_map = _prepare(tool, manifest, _plan())
    detect.assert_not_awaited()
    reverse.assert_not_awaited()
    assert "原品牌汉堡特写" in prompts[0]
    assert "原品牌真好吃" in prompts[0]
    assert sum(durations) == 20
    assert manifest["shots"] == table
    assert manifest["shot_prompts"] == prompts
    assert manifest["shot_map"] == shot_map


def test_only_missing_description_is_reverse_built(monkeypatch):
    """只补缺镜头，包括多镜头计划仅缺一镜的情况。"""
    tool = _tool()
    plan = _plan()
    plan["shots"][1]["description"] = ""
    reverse = AsyncMock(return_value={1: "补充运镜"})
    monkeypatch.setattr(tool, "_build_shot_prompts", reverse)
    _, prompts, _, _ = _prepare(tool, {}, plan)
    assert [row["index"] for row in reverse.await_args.args[3]] == [1]
    assert reverse.await_args.kwargs["allow_single"] is True
    assert "原品牌汉堡特写" in prompts[0]
    assert prompts[1] == "补充运镜"


def test_checkpoint_wins_and_does_not_reverse_again(monkeypatch):
    """JSON 回读检查点优先于新快照，恢复不重复调用模型。"""
    tool = _tool()
    manifest = {"shots": _plan()["shots"], "durations": [10, 10],
                "shot_map": [[0], [1]], "shot_prompts": {"0": "固化描述", "1": "固化结尾"}}
    plan = _plan()
    plan["shots"][0]["description"] = "不应进入"
    reverse = AsyncMock()
    monkeypatch.setattr(tool, "_build_shot_prompts", reverse)
    _, prompts, durations, _ = _prepare(tool, manifest, plan)
    reverse.assert_not_awaited()
    assert prompts == {0: "固化描述", 1: "固化结尾"}
    assert durations == [10, 10]


def test_replacement_reuses_only_timeline(monkeypatch):
    """替换时不让来源品牌和旁白覆盖新产品，并保持快照不可变。"""
    tool = _tool()
    plan = _plan()
    original = copy.deepcopy(plan)
    reverse = AsyncMock(return_value={0: "新产品构图", 1: "安全拉远"})
    monkeypatch.setattr(tool, "_build_shot_prompts", reverse)
    manifest = {}
    table, prompts, _, _ = _prepare(tool, manifest, plan, ["product"])
    assert all(not row["description"] and not row["narration"] for row in table)
    assert reverse.await_args.args[4] == ["product"]
    assert "汉堡" not in str(prompts)
    assert plan == original
    reverse.reset_mock()
    _prepare(tool, manifest, plan, ["product"])
    reverse.assert_not_awaited()


def test_missing_plan_keeps_automatic_analysis(monkeypatch):
    """未传快照仍沿用原有自动检测与逆推路径。"""
    tool = _tool()
    table = _plan()["shots"]
    for row in table:
        row.pop("description")
    detect = AsyncMock(return_value=table)
    narrate = AsyncMock(return_value=table)
    reverse = AsyncMock(return_value={0: "自动描述"})
    monkeypatch.setattr(shots, "detect_shots", detect)
    monkeypatch.setattr(shots, "narrate_shots", narrate)
    monkeypatch.setattr(tool, "_build_shot_prompts", reverse)
    _prepare(tool, {}, None)
    detect.assert_awaited_once()
    narrate.assert_awaited_once()
    reverse.assert_awaited_once()


def test_short_video_consumes_plan_without_forcing_segments(monkeypatch):
    """短片分镜描述实际传入整片编辑，不新增分段或分析调用。"""
    tool = _tool()
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "test-edit")
    monkeypatch.setattr(media_prep, "probe_duration", AsyncMock(return_value=20))
    monkeypatch.setattr(media_prep, "probe_size", AsyncMock(return_value=(1080, 1920)))
    monkeypatch.setattr(frame_quality, "check_reference_video_pixels", AsyncMock(return_value=None))
    monkeypatch.setattr(tool, "_optimize_prompt", AsyncMock(return_value="整体要求"))
    monkeypatch.setattr(tool, "_check_output_against_reference", AsyncMock())
    edit = AsyncMock(return_value=ToolResult(content="https://x/final.mp4", metadata={"success": True}))
    multi = AsyncMock()
    monkeypatch.setattr(tool, "edit_video", edit)
    monkeypatch.setattr(tool, "_generate_multi_segment", multi)
    params = {"reference_video": "https://x/ref.mp4", "gen_mode": "v2v",
              "duration": 20, "script_text": "用户文案", "shot_plan": _plan()}
    saved = {}

    async def save_stage(stage, data):
        """模拟真实检查点合并保存，保留优化提示词与独立分镜约束。"""
        saved.update(data)
        saved["stage"] = stage

    result = asyncio.run(tool.generate(params, on_stage=save_stage))
    assert result.content == "https://x/final.mp4"
    first_prompt = edit.await_args.args[0]
    assert "原品牌汉堡特写" in first_prompt
    assert "结尾旁白" in first_prompt
    assert "[可信分镜约束]" not in saved["optimized_prompt"]
    # 恢复只重新拼装一次独立约束，不在已含分镜的提示词上继续追加。
    asyncio.run(tool.generate(params, checkpoint=saved))
    assert edit.await_args.args[0] == first_prompt
    assert edit.await_args.args[0].count("[可信分镜约束]") == 1
    tool._optimize_prompt.assert_awaited_once()
    multi.assert_not_awaited()


def test_short_replacement_omits_source_subjects():
    """短片替换不新增逆推调用，仅采用可信时间轴。"""
    hint = VideoGenTool._snapshot_edit_hint(_plan(), ["product"])
    assert "10–20秒" in hint
    assert "汉堡" not in hint
    assert "原品牌真好吃" not in hint


def test_long_replacement_adds_migration_rules_and_freezes(monkeypatch):
    """逆推失败也注入动作适配规则，检查点恢复不重复编译或调用模型。"""
    tool = _tool()
    reverse = AsyncMock(return_value={})
    monkeypatch.setattr(tool, "_build_shot_prompts", reverse)
    manifest = {}
    _, prompts, _, _ = _prepare(tool, manifest, _plan(), ["product"])
    assert "中性外观展示" in prompts[0]
    assert "汉堡" not in str(manifest["replica_pipeline"])
    frozen = copy.deepcopy(manifest)
    reverse.reset_mock()
    _prepare(tool, manifest, _plan(), ["product"])
    reverse.assert_not_awaited()
    assert manifest == frozen


def test_short_replacement_automatically_migrates_and_restores(monkeypatch):
    """无拆解短片自动迁移，仍整片编辑，恢复不重复追加规则。"""
    tool = _tool()
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "test-edit")
    monkeypatch.setattr(media_prep, "probe_duration", AsyncMock(return_value=20))
    monkeypatch.setattr(media_prep, "probe_size", AsyncMock(return_value=(1080, 1920)))
    monkeypatch.setattr(frame_quality, "check_reference_video_pixels", AsyncMock(return_value=None))
    monkeypatch.setattr(tool, "_optimize_prompt", AsyncMock(return_value="整体要求"))
    monkeypatch.setattr(tool, "_check_output_against_reference", AsyncMock())
    edit = AsyncMock(return_value=ToolResult(content="https://x/final.mp4", metadata={"success": True}))
    multi = AsyncMock()
    monkeypatch.setattr(tool, "edit_video", edit)
    monkeypatch.setattr(tool, "_generate_multi_segment", multi)
    params = {"reference_video": "https://x/ref.mp4", "gen_mode": "v2v", "intent": ["product"],
              "duration": 20, "script_text": "用户文案"}
    saved = {}

    async def save_stage(stage, data):
        """模拟业务检查点合并，供真实 generate 恢复使用。"""
        saved.update(data)
        saved["stage"] = stage

    asyncio.run(tool.generate(params, on_stage=save_stage))
    first = edit.await_args.args[0]
    assert "中性外观展示" in first
    assert saved["replica_pipeline"]["reference_dna"]["status"] == "partial"
    asyncio.run(tool.generate(params, checkpoint=saved))
    assert edit.await_args.args[0] == first
    assert first.count("[后台迁移约束]") == 1
    multi.assert_not_awaited()


def test_submitted_legacy_edit_does_not_receive_new_rules(monkeypatch):
    """已提交旧任务不在恢复时更改冻结提示词。"""
    tool = _tool()
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "test-edit")
    monkeypatch.setattr(media_prep, "probe_duration", AsyncMock(return_value=20))
    monkeypatch.setattr(media_prep, "probe_size", AsyncMock(return_value=(1080, 1920)))
    monkeypatch.setattr(frame_quality, "check_reference_video_pixels", AsyncMock(return_value=None))
    monkeypatch.setattr(tool, "_check_output_against_reference", AsyncMock())
    edit = AsyncMock(return_value=ToolResult(content="https://x/final.mp4", metadata={"success": True}))
    monkeypatch.setattr(tool, "edit_video", edit)
    params = {"reference_video": "https://x/ref.mp4", "gen_mode": "v2v", "intent": ["product"],
              "duration": 20, "script_text": "用户文案"}
    asyncio.run(tool.generate(params, checkpoint={"stage": 2, "optimized_prompt": "旧提示词",
                                                "external_task_id": "already-submitted"}))
    assert edit.await_args.args[0] == "旧提示词"
