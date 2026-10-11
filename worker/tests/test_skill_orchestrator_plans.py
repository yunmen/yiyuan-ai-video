# -*- coding: utf-8 -*-
"""技能编排器端到端测试:确定性计划 / 工具调用式 agent 计划 / 自适应 re-plan /
步骤重试与中断 / 拓扑并发 / 跨任务记忆。

用 monkeypatch 把 run_skill / run_agent_loop / _llm_plan / 记忆 替换为可控桩,
不依赖真实 chat 网关 / Redis / ARQ,证明 agent 工作流编排逻辑全链路可用
(对应 docs/skill_agent_workflow_analysis.md §5 的「未验证」缺口)。

运行:在 worker 目录执行 `python -m pytest tests/test_skill_orchestrator_plans.py -q`
"""
import asyncio
import time

import pytest

from app.core import skill_orchestrator as orch
from app.core.skill_orchestrator import SkillPlan, SkillStep, load_workflows
from app.schemas.base import ToolResult


def _run(coro):
    """在独立的新事件循环里执行协程并返回结果。

    此前用 `_run(...)`,依赖「主线程恰好存在一个
    尚未关闭的默认事件循环」这一隐式前提:单跑本文件时成立,全量 `pytest tests/` 时,
    前面若有其它用例用 `asyncio.run`/pytest-asyncio 关掉了默认循环,Python 3.10+ 的
    `get_event_loop()` 会直接抛 `RuntimeError: There is no current event loop`,
    导致本文件 9 个用例整片红(与被测逻辑无关的假失败)。
    `asyncio.run` 每次自建并关闭循环,不依赖也不污染全局 loop 状态,单跑/全量结果一致。
    """
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _load_plans():
    # 保证 PLAN_REGISTRY 含 _workflows 下的声明式计划(导入时已加载一次,这里幂等兜底)
    load_workflows()
    yield


# —— 桩:记录调用并返回结构化产物 —— #
def _make_skill_fake(record):
    async def _fake(name, instruction, params):
        record.append({"name": name, "params": dict(params or {})})
        if name == "text-generation":
            return ToolResult(
                content={"title": "大标题", "subtitle": "副标题", "script": "口播脚本",
                         "narration": ["镜1口播", "镜2口播"], "subject": "主体", "demand": "画面要求"},
                metadata={"ok": True, "skill": name},
            )
        if name == "image-generation":
            return ToolResult(
                content=[{"prompt": "图提示词1"}, {"prompt": "图提示词2"}],
                metadata={"ok": True, "skill": name},
            )
        if name == "script-anchor":
            return ToolResult(
                content={"anchors": [{"word": "镜1", "t": 0.5}]},
                metadata={"ok": True, "skill": name},
            )
        return ToolResult(content={}, metadata={"ok": True, "skill": name})
    return _fake


def test_load_workflows_registers_three_plans():
    # _workflows 目录下 3 个 JSON 计划(两条确定性 + 一条 agent 示例)应全部载入
    assert set(orch.PLAN_REGISTRY) >= {
        "video-replicate-prep", "video-prep", "video-replicate-prep-agent",
    }
    # agent 计划必须声明 tools 且 adaptive=True(Phase 2 工具调用式 agent 步骤)
    agent = orch.PLAN_REGISTRY["video-replicate-prep-agent"]
    assert agent.adaptive is True
    assert agent.steps[0].tools == ["text-generation"]
    assert agent.steps[0].store_key == "copy"
    # 确定性计划不应触发 agent 路径
    assert orch.PLAN_REGISTRY["video-replicate-prep"].adaptive is False


def test_compile_plan_hits_agent_by_name():
    # compile_plan 应按计划名直接命中(便于显式触发 agent 编排)
    plan = _run(orch.compile_plan("video-replicate-prep-agent", {"intent": "replicate"}))
    assert plan is not None
    assert plan.name == "video-replicate-prep-agent"


def test_deterministic_plan_end_to_end(monkeypatch):
    record = []
    monkeypatch.setattr(orch, "run_skill", _make_skill_fake(record))
    plan = orch.PLAN_REGISTRY["video-replicate-prep"]
    result = _run(orch.orchestrator.run(plan, {"duration": 10}))

    bb = result.content
    # 三步均产出,且黑板键与计划 store_key 一致
    assert "copy" in bb and "img_prompts" in bb and "anchors" in bb
    # text-generation 的结构化三段文案被下游 image-generation 以 bb.copy.narration 取用
    img_call = next(c for c in record if c["name"] == "image-generation")
    assert img_call["params"]["narrations"] == ["镜1口播", "镜2口播"]
    # 质量门禁:全 ok
    assert result.metadata["quality"] == "ok"
    assert result.metadata["adaptive"] is False
    assert result.metadata["steps"] == ["text-generation", "image-generation", "script-anchor"]


def test_agent_plan_propagates_answer_to_downstream(monkeypatch):
    record = []
    monkeypatch.setattr(orch, "run_skill", _make_skill_fake(record))

    # agent 步骤桩:模型自主选择调用工具后给出自由文本答案(bb.copy.answer)
    async def _fake_agent(goal, tools, ctx, max_iter=4):
        return ToolResult(
            content={"answer": "AGENT_FREETEXT_COPY", "iterations": 1},
            metadata={"ok": True, "skill": "agent"},
        )
    monkeypatch.setattr(orch, "run_agent_loop", _fake_agent)

    plan = orch.PLAN_REGISTRY["video-replicate-prep-agent"]
    result = _run(orch.orchestrator.run(plan, {"duration": 10}))

    bb = result.content
    # agent 步骤产物是自由文本答案,而非结构化 copy 对象
    assert bb["copy"] == {"answer": "AGENT_FREETEXT_COPY", "iterations": 1}
    # 下游 image-generation / script-anchor 改读 bb.copy.answer(已在 JSON 中声明)
    img_call = next(c for c in record if c["name"] == "image-generation")
    assert img_call["params"]["narrations"] == "AGENT_FREETEXT_COPY"
    anchor_call = next(c for c in record if c["name"] == "script-anchor")
    assert anchor_call["params"]["script"] == "AGENT_FREETEXT_COPY"
    # 整条计划仍产出 img_prompts / anchors
    assert bb.get("img_prompts") and bb.get("anchors")
    assert result.metadata["adaptive"] is True
    assert result.metadata["quality"] == "ok"


def test_adaptive_replan_replaces_remaining_steps(monkeypatch):
    # 自适应 re-plan:每步后据黑板回灌 _llm_plan 精炼剩余步骤(有界 1 次)
    refined = SkillStep(name="refined-step", store_key="refined", instruction="精炼后的步骤")

    async def _fake_llm_plan(goal, meta, use_llm=True):
        return SkillPlan(name="refined", description="", steps=[refined])

    monkeypatch.setattr(orch, "_llm_plan", _fake_llm_plan)
    monkeypatch.setattr(orch, "run_skill", _make_skill_fake([]))

    plan = SkillPlan(
        name="adaptive-demo",
        description="",
        steps=[
            SkillStep(name="text-generation", store_key="copy", instruction="x", inputs={}),
            SkillStep(name="image-generation", store_key="img", instruction="y",
                      inputs={"narrations": "bb.copy.script"}),
        ],
        adaptive=True, adaptive_max_replans=1,
    )
    result = _run(orch.orchestrator.run(plan, {}))

    # 第一步执行后重规划,把第二步替换为 refined-step;replan_count=1
    assert result.metadata["replan_count"] == 1
    assert result.metadata["steps"] == ["text-generation", "refined-step"]
    assert "refined" in result.content


def test_step_halt_interrupts_pipeline(monkeypatch):
    # 步骤失败 + on_error=halt → 中断整条流水线,quality=failed
    calls = []

    async def _fake(name, instruction, params):
        calls.append(name)
        if name == "text-generation":
            return ToolResult(content={"error": "生成失败"}, metadata={"ok": False, "skill": name})
        return ToolResult(content={}, metadata={"ok": True, "skill": name})
    monkeypatch.setattr(orch, "run_skill", _fake)

    plan = SkillPlan(
        name="halt-demo",
        description="",
        steps=[
            SkillStep(name="text-generation", store_key="copy", instruction="x",
                      on_error="halt", max_retries=0),
            SkillStep(name="image-generation", store_key="img", instruction="y", inputs={}),
        ],
    )
    result = _run(orch.orchestrator.run(plan, {}))

    assert result.metadata["quality"] == "failed"
    # 第二步不应执行(被 halt 阻断)
    assert calls == ["text-generation"]


def test_step_continue_marks_degraded(monkeypatch):
    # 步骤失败 + on_error=continue → 写错误进黑板继续,quality=degraded
    calls = []

    async def _fake(name, instruction, params):
        calls.append(name)
        if name == "text-generation":
            return ToolResult(content={"error": "生成失败"}, metadata={"ok": False, "skill": name})
        return ToolResult(content={}, metadata={"ok": True, "skill": name})
    monkeypatch.setattr(orch, "run_skill", _fake)

    plan = SkillPlan(
        name="continue-demo",
        description="",
        steps=[
            SkillStep(name="text-generation", store_key="copy", instruction="x",
                      on_error="continue", max_retries=0),
            SkillStep(name="image-generation", store_key="img", instruction="y", inputs={}),
        ],
    )
    result = _run(orch.orchestrator.run(plan, {}))

    assert "copy" in result.metadata["degraded_steps"]
    assert result.metadata["quality"] == "degraded"
    # 第二步仍执行(未中断)
    assert "image-generation" in calls


def test_topo_levels_groups_independent_steps(monkeypatch):
    # 拓扑分层:无相互依赖的步骤应在同一层,可并行执行
    plan = SkillPlan(
        name="conc",
        description="",
        steps=[
            SkillStep(name="text-generation", store_key="a", instruction="x", inputs={}),
            SkillStep(name="image-generation", store_key="b", instruction="y", inputs={}),
        ],
    )
    levels = orch.orchestrator._topo_levels(plan.steps)
    # 两个独立步骤同层 → 一次 gather 并行
    assert len(levels) == 1 and len(levels[0]) == 2


def test_independent_steps_run_concurrently(monkeypatch):
    # 同层无依赖步骤应真正并发(总耗时约等于单次,而非两倍)
    events = []

    async def _fake(name, instruction, params):
        events.append(("start", name))
        await asyncio.sleep(0.05)
        events.append(("end", name))
        return ToolResult(content={}, metadata={"ok": True, "skill": name})
    monkeypatch.setattr(orch, "run_skill", _fake)

    plan = SkillPlan(
        name="conc",
        description="",
        steps=[
            SkillStep(name="t", store_key="a", instruction="x", inputs={}),
            SkillStep(name="i", store_key="b", instruction="y", inputs={}),
        ],
    )
    start = time.monotonic()
    _run(orch.orchestrator.run(plan, {}))
    elapsed = time.monotonic() - start
    # 并发:两个各 0.05s 的步骤应 ~0.05s 完成(允许调度余量),而非 ~0.1s 串行
    assert elapsed < 0.09
    # 且两步骤的 start 都在任一 end 之前(存在重叠)
    starts = [e[1] for e in events if e[0] == "start"]
    ends = [e[1] for e in events if e[0] == "end"]
    assert len(starts) == 2 and len(ends) == 2


def test_run_agent_loop_degraded_returns_answer_contract(monkeypatch):
    # 无 chat 网关降级时,仍应返回 agent 步骤统一契约 {answer, iterations},
    # 而非 run_skill 的原始结构化产物(否则下游读 bb.copy.answer 会拿到 None)
    from app.core import skill_runtime, gateway as gw_mod

    async def _fake_skill(name, instruction, params):
        return ToolResult(
            content={"script": "降级口播文本", "narration": ["a", "b"], "title": "T"},
            metadata={"ok": True, "skill": name},
        )
    monkeypatch.setattr(skill_runtime, "run_skill", _fake_skill)
    monkeypatch.setattr(gw_mod, "resolve", lambda name: {"url": "", "key": ""})

    result = _run(skill_runtime.run_agent_loop("做文案", ["text-generation"], {}))
    assert result.content["answer"] == "降级口播文本"
    assert result.content["iterations"] == 0


def test_memory_written_after_run(monkeypatch):
    # 跨任务记忆:每次计划运行后把黑板摘要写入进程内记忆(供后续 _llm_plan 复用)
    mem_calls = []

    async def _spy_remember(scope, key, value):
        mem_calls.append((scope, key))
    async def _spy_recall(*a, **k):
        return None
    monkeypatch.setattr(orch, "mem_remember", _spy_remember)
    monkeypatch.setattr(orch, "mem_recall_prompt", _spy_recall)
    monkeypatch.setattr(orch, "run_skill", _make_skill_fake([]))

    plan = orch.PLAN_REGISTRY["video-replicate-prep"]
    _run(orch.orchestrator.run(plan, {}))

    assert any(scope == plan.name for scope, _ in mem_calls)
    assert any(key == "last_blackboard" for _, key in mem_calls)
