# -*- coding: utf-8 -*-
'''技能编排器:Agent 工作流的核心(把多个技能串成流水线,黑板传递标准产物)。

职责:
- 用声明式 SkillPlan/SkillStep 描述「一个目标 → 多个有序技能步骤」;
- SkillOrchestrator.run 按序执行步骤,每步把 ToolResult.content 写入黑板(blackboard),
  后续步骤从黑板 / 下发 ctx 取上游产物当入参,实现技能之间自己协调;
- PLAN_REGISTRY + compile_plan 把高层目标(如「复刻这段视频」)映射成计划;
  已知意图命中预声明模板(确定性、可调试、可复现),未命中时升级为 LLM 规划器
  (compile_plan → _llm_plan,用 chat 网关把目标解析成技能步骤 DAG),
  模型调用只在 worker,符合 backend 业务 / worker 模型网关分层。

边界(见 docs/skill_agent_flow.md §6):
- 同步内容技能(text-generation/image-generation/script-anchor 等纯 LLM)进入注册表自由组合;
- 重型渲染(process_video/process_digital/process_render/process_deconstruct)不进流水线,
  由流水线终态 handoff 提示前端走既有 task.create(可计费、可断点续跑、有人工卡点)。
'''
import os
import json
import glob
import asyncio

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core import gateway
from app.core.plugin import logger
from app.core.skill_runtime import registry, run_skill, run_agent_loop
from app.core.skill_memory import remember as mem_remember, recall_prompt as mem_recall_prompt
from app.schemas.base import ToolResult
from app.settings import config


@dataclass
class SkillStep:
    """流水线中的一个步骤:执行某个技能,并把产物存入黑板。

    inputs 形如 {"narrations": "bb.copy.script", "duration": "ctx.duration"}:
      - "bb.<key>.<field>" : 取黑板里某步骤产物的字段(黑板的 key=该步骤 store_key);
      - "ctx.<field>"      : 取下发时的 ctx 字段(对标视频/时长/形态等用户侧元数据);
      - 其它字面量(非上述前缀) : 原样作为该参数值。
    params 为字面量覆盖,与 inputs 解析结果合并(同名字面量优先)。
    """

    name: str
    store_key: str
    instruction: str = ""
    inputs: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 0          # 步骤级重试次数(失败且未达上限时重跑)
    on_error: str = "continue"    # 重试耗尽后的处置:continue(写错误进黑板,继续) / halt(中断整条流水线)
    tools: List[str] = field(default_factory=list)  # 工具调用式 agent 步骤:声明的技能名作为可调用工具,模型自主选用


@dataclass
class SkillPlan:
    """一个目标对应的技能流水线(声明式,可调试、可复现)。"""

    name: str
    description: str
    steps: List[SkillStep]
    handoff: str = ""  # 终态交接说明(如"去 task.create 渲染")
    adaptive: bool = False  # 是否启用自适应 re-plan(每步后据黑板回灌 LLM 规划器精炼剩余步骤)
    adaptive_max_replans: int = 1  # 自适应 re-plan 上限次数(有界,防失控与成本爆炸)


def _resolve_value(token: str, blackboard: Dict[str, Any], ctx: Dict[str, Any]) -> Any:
    """解析 inputs 里的取值来源:bb./ctx. 前缀取对应结构,否则按字面量返回。"""
    if not isinstance(token, str):
        return token
    if token.startswith("bb."):
        path = token[3:].split(".", 1)
        node = blackboard.get(path[0])
        if node is None or len(path) < 2:
            return node
        return (node or {}).get(path[1]) if isinstance(node, dict) else None
    if token.startswith("ctx."):
        return ctx.get(token[4:])
    return token


def _build_step_params(step: SkillStep, blackboard: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """解析步骤入参:inputs 来源 + 字面量 params,并按技能 input_schema 做类型修正(如 list 包装)。"""
    params: Dict[str, Any] = {}
    spec = registry.get(step.name)
    list_fields = {p.name for p in (spec.input_schema if spec else []) if p.type == "list"}
    for key, token in step.inputs.items():
        val = _resolve_value(token, blackboard, ctx)
        # 声明为 list 但解析到的是单值(如口播字符串)→ 包装成单元素列表,适配 generate 签名
        if key in list_fields and val is not None and not isinstance(val, list):
            val = [val]
        params[key] = val
    # 字面量覆盖优先(已解析的同名字段被覆盖)
    params.update(step.params)
    return params


def _summarize(blackboard: Dict[str, Any], max_len: int = 200) -> Dict[str, Any]:
    """压缩黑板(避免把大产物回灌 LLM 规划器撑爆上下文),只留可读摘要。"""
    out: Dict[str, Any] = {}
    for k, v in (blackboard or {}).items():
        try:
            s = json.dumps(v, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            s = str(v)
        out[k] = s[:max_len]
    return out


class SkillOrchestrator:
    """流水线执行器:拓扑分层并行 + 步骤级重试 + 质量门禁 + 自适应 re-plan。

    - 按黑板依赖做拓扑分层,同层无相互依赖的步骤 asyncio.gather 并行(agent 的 fan-out);
    - 单步失败按 max_retries 重试;重试耗尽按 on_error 处置(continue 写错误进黑板 / halt 中断整条);
    - 聚合 quality(ok/degraded/failed)、degraded_steps、adaptive 进 metadata,供前端感知降级;
    - plan.adaptive=True 时,首步执行后调用 LLM 规划器精炼剩余步骤(有界一次,防失控)。
    """

    # —— 拓扑分层:返回层级列表,每层步骤可并行;依赖必须在前面层级 —— #
    @staticmethod
    def _step_deps(step: "SkillStep") -> set:
        """步骤从黑板读取的 store_key 集合(仅 bb.<key> 前缀计入依赖)。"""
        deps: set = set()
        for token in (step.inputs or {}).values():
            if isinstance(token, str) and token.startswith("bb."):
                deps.add(token[3:].split(".", 1)[0])
        return deps

    def _topo_levels(self, steps: List["SkillStep"]) -> List[List["SkillStep"]]:
        """按依赖拓扑分层;出现环或非法依赖时降级为顺序(逐条入层,防死循环)。"""
        remaining = list(steps)
        levels: List[List["SkillStep"]] = []
        done: set = set()
        while remaining:
            level = [s for s in remaining if self._step_deps(s) <= done]
            if not level:
                level = [remaining[0]]  # 防死循环:强制推进
            levels.append(level)
            for s in level:
                done.add(s.store_key)
                remaining.remove(s)
        return levels

    async def _exec_step(self, step: "SkillStep", blackboard: dict, ctx: dict):
        """执行单步(含 max_retries 重试),返回 (ToolResult|None, Exception|None)。

        若步骤声明了 tools(工具调用式 agent 步骤),改走 ReAct 代理循环:
        模型自主选择调用已注册技能作为工具,观察结果后继续,直到给出终态答案。
        """
        params = _build_step_params(step, blackboard, ctx)
        if step.tools:
            return await run_agent_loop(
                goal=step.instruction or step.name,
                tools=list(step.tools),
                ctx=params,
                max_iter=getattr(config, "AGENT_MAX_ITER", 4),
            ), None
        last = None
        last_err = None
        for _ in range((step.max_retries or 0) + 1):
            try:
                last = await run_skill(step.name, step.instruction, params)
                last_err = None
                if last is not None and last.metadata.get("ok", True):
                    return last, None
            except Exception as exc:  # noqa: BLE001
                last_err = exc
        return last, last_err

    @staticmethod
    def _absorb(step: "SkillStep", result, err) -> tuple:
        """把单步产物收进黑板,返回 (是否成功, 收进黑板的内容)。"""
        if err is not None:
            return False, {"error": str(err)}
        if result is None:
            return False, {"error": "无产物"}
        if not result.metadata.get("ok", True):
            content = result.content
            return False, content if isinstance(content, dict) else {"error": str(content)}
        return True, result.content

    async def run(self, plan: SkillPlan, ctx: Dict[str, Any]) -> ToolResult:
        """执行计划,返回 content=黑板, metadata 含质量与降级信息。"""
        blackboard: Dict[str, Any] = {}
        degraded_steps: List[str] = []
        failed = False
        logger.info(f"[orchestrator] 执行计划 {plan.name} 共 {len(plan.steps)} 步")

        # 自适应 re-plan:每步执行后据黑板回灌 LLM 规划器精炼剩余步骤(有界 adaptive_max_replans 次,防失控)
        steps = list(plan.steps)
        adaptive = bool(getattr(plan, "adaptive", False))
        max_replans = int(getattr(plan, "adaptive_max_replans", 1) or 1)
        replan_count = 0

        async def _maybe_refine(idx: int):
            nonlocal steps, replan_count
            # 已达上限 / 已是最后一步 / 未开启 → 不重规划
            if not (adaptive and replan_count < max_replans and idx + 1 < len(steps)):
                return
            replan_count += 1
            memories = await mem_recall_prompt(plan.name, plan.name)
            new_plan = await _llm_plan(
                goal=plan.name,
                meta={**ctx, "blackboard": _summarize(blackboard),
                      "remaining": [s.name for s in steps[idx + 1:]],
                      "memories": memories},
            )
            if new_plan and new_plan.steps:
                # 仅替换当前步之后的步骤,保留已执行的路径
                steps = steps[:idx + 1] + new_plan.steps

        if adaptive:
            # 自适应需逐步观察,走顺序执行(不并行);用 while 以便重规划后安全续跑
            idx = 0
            while idx < len(steps):
                step = steps[idx]
                res, err = await self._exec_step(step, blackboard, ctx)
                ok, content = self._absorb(step, res, err)
                blackboard[step.store_key] = content
                if not ok:
                    degraded_steps.append(step.store_key)
                    if step.on_error == "halt":
                        failed = True
                        break
                await _maybe_refine(idx)
                idx += 1
        else:
            for level in self._topo_levels(steps):
                if any(s.on_error == "halt" for s in level):
                    # 含 halt 的层必须顺序执行:并行 gather 无法在中途停止同层后续步骤
                    for step in level:
                        res, err = await self._exec_step(step, blackboard, ctx)
                        ok, content = self._absorb(step, res, err)
                        blackboard[step.store_key] = content
                        if not ok:
                            degraded_steps.append(step.store_key)
                            if step.on_error == "halt":
                                failed = True
                                break
                    if failed:
                        break
                else:
                    results = await asyncio.gather(
                        *(self._exec_step(s, blackboard, ctx) for s in level)
                    )
                    for step, (res, err) in zip(level, results):
                        ok, content = self._absorb(step, res, err)
                        blackboard[step.store_key] = content
                        if not ok:
                            degraded_steps.append(step.store_key)
                            if step.on_error == "halt":
                                failed = True
                    if failed:
                        break

        quality = "failed" if failed else ("degraded" if degraded_steps else "ok")
        # 跨任务记忆:把本次计划黑板摘要记入进程内记忆,供后续计划/技能复用(见 skill_memory.py)
        try:
            await mem_remember(plan.name, "last_blackboard", _summarize(blackboard))
            if degraded_steps:
                await mem_remember(plan.name, "last_degraded", degraded_steps)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[orchestrator] 写入记忆失败(不影响主流程): {exc}")
        return ToolResult(
            content=blackboard,
            metadata={
                "ok": not failed,
                "plan": plan.name,
                "handoff": plan.handoff,
                "steps": [s.name for s in steps],
                "quality": quality,
                "degraded_steps": degraded_steps,
                "adaptive": adaptive,
                "replan_count": replan_count if adaptive else 0,
            },
        )


# —— 预声明计划模板:从 worker/skills/_workflows/*.json 加载(声明式、可调试、可复现),文件为单一来源。
# 不再硬编码在代码中,避免两端漂移;新增 / 调整流水线只需改 JSON 文件并重启 worker。
PLAN_REGISTRY: Dict[str, SkillPlan] = {}


def _workflows_dir() -> str:
    """定位 worker/skills/_workflows(与技能目录同级),兼容不同启动工作目录。"""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "skills", "_workflows",
    )


def load_workflows(directory: str = None) -> int:
    """从 worker/skills/_workflows/*.json 加载声明式计划,注册进 PLAN_REGISTRY(文件优先于任何硬编码)。

    每个 JSON 对应一个 SkillPlan(name/steps/handoff/adaptive/adaptive_max_replans);
    steps 是 SkillStep 列表(name/store_key/instruction/inputs/params/max_retries/on_error/tools)。
    加载失败或定义非法的文件仅告警跳过,不影响其它计划与已注册技能。
    """
    directory = directory or _workflows_dir()
    count = 0
    if not os.path.isdir(directory):
        logger.warning(f"[orchestrator] 工作流目录不存在: {directory}")
        return count
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[orchestrator] 工作流文件读取失败 {path}: {exc}")
            continue
        try:
            steps = [
                SkillStep(
                    name=s["name"],
                    store_key=s.get("store_key", ""),
                    instruction=s.get("instruction", ""),
                    inputs=s.get("inputs", {}) or {},
                    params=s.get("params", {}) or {},
                    max_retries=int(s.get("max_retries", 0) or 0),
                    on_error=s.get("on_error", "continue"),
                    tools=list(s.get("tools", []) or []),
                )
                for s in data.get("steps", [])
            ]
            plan = SkillPlan(
                name=data["name"],
                description=data.get("description", ""),
                steps=steps,
                handoff=data.get("handoff", ""),
                adaptive=bool(data.get("adaptive", False)),
                adaptive_max_replans=int(data.get("adaptive_max_replans", 1) or 1),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[orchestrator] 工作流定义非法 {path}: {exc}")
            continue
        PLAN_REGISTRY[plan.name] = plan
        count += 1
        logger.info(f"[orchestrator] 已加载工作流 {plan.name} ({len(steps)} 步) <- {os.path.basename(path)}")
    return count


# 模块导入即加载,保证 PLAN_REGISTRY 在任何调用(compile_plan / publish_plans)前就绪。
load_workflows()


# 意图关键词 → 计划名(与 frontend §7.2 功能项映射对齐)
_INTENT_PLANS = {
    "replicate": "video-replicate-prep",
    "generate": "video-prep",
}


async def _llm_plan(goal: str, meta: Dict[str, Any]) -> Optional[SkillPlan]:
    """用 chat 网关把高层目标解析成技能步骤 DAG(返回 SkillPlan)。

    模型调用只在 worker(符合 backend 业务 / worker 模型网关分层)。失败或网关未配置时返回 None,
    由 compile_plan 退化为已知模板 / 单技能 run_skill。
    """
    gw = gateway.resolve("chat")
    if not (gw.get("url") and gw.get("key")):
        return None
    # 复用跨任务记忆:把此前同类计划经验注入规划提示,让规划"越跑越聪明"(无记忆则为空串)
    try:
        memory_hint = await mem_recall_prompt("*", goal)
    except Exception:  # noqa: BLE001
        memory_hint = ""
    # 组装可用技能清单(只暴露已注册技能,约束 LLM 只能选这些 name,避免执行未注册技能)
    catalog: List[str] = []
    for spec in registry.values():
        fields = ", ".join(f"{p.name}({p.type})" for p in (spec.input_schema or []))
        catalog.append(f"- {spec.name}: {spec.description}。入参:{fields or '无'}")
    skills_text = "\n".join(catalog)
    system = (
        "你是视频生成流水线规划器,把用户的「目标」拆成有序的 AI 内容准备步骤。\n"
        "可用技能(只能从下列 name 中选,且必须已列出):\n"
        f"{skills_text}\n\n"
        "约束:\n"
        "- 步骤之间用黑板传参:inputs 用 'bb.<前一步store_key>.<字段>' 引用上一步产物,如 'bb.copy.script';\n"
        "  'ctx.<字段>' 引用用户侧元数据(如 ctx.duration 成片时长)。\n"
        "- 每步需含 name(必须是上述技能之一)、store_key(英文,作黑板键)、instruction(自然语言指令);\n"
        "  字面量参数放 params(如 {\"with_demand\": true});需要上一步产物时放 inputs。\n"
        "- 不包含重型渲染步骤(渲染由前端 task.create 处理,本流水线只做 AI 内容准备)。\n"
        "- 只输出 JSON,不要代码块/解释。形如:\n"
        "{\"name\":\"<计划名>\",\"description\":\"...\",\"steps\":["
        "{\"name\":\"text-generation\",\"store_key\":\"copy\",\"instruction\":\"...\",\"params\":{\"with_demand\":true}},"
        "{\"name\":\"image-generation\",\"store_key\":\"img_prompts\",\"instruction\":\"...\",\"inputs\":{\"narrations\":\"bb.copy.script\"}}"
        "],\"handoff\":\"...\"}\n"
    )
    ctx_hint = json.dumps(meta, ensure_ascii=False) if meta else "{}"
    user = f"目标:{goal}\n用户元数据:{ctx_hint}\n请输出计划 JSON。"
    if memory_hint:
        system += (
            f"\n\n# 参考经验(此前同类目标跑通过的编排,优先复用其中行之有效的步骤组合)\n{memory_hint}"
        )
    try:
        client = AsyncOpenAI(api_key=gw["key"], base_url=gw["url"].rstrip("/"), timeout=30)
        resp = await client.chat.completions.create(
            model=(config.CHAT_MODEL or "").strip(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.strip("`").lstrip("json").strip()
        data = json.loads(text)
        if not isinstance(data, dict) or not data.get("steps"):
            return None
        steps: List[SkillStep] = []
        for s in data["steps"]:
            name = s.get("name")
            if name not in registry:
                # 未知技能名 → 跳过该步(不阻断整体),避免执行器拿到未注册技能
                logger.warning(f"[orchestrator] LLM 计划含未注册技能 {name},跳过")
                continue
            # 容错:LLM 可能把 params/inputs 返回非字典,这里强制收敛,避免编排器在 try 外崩任务
            raw_params = s.get("params")
            params = raw_params if isinstance(raw_params, dict) else {}
            raw_inputs = s.get("inputs")
            inputs = {k: v for k, v in raw_inputs.items() if isinstance(v, str)} if isinstance(raw_inputs, dict) else {}
            steps.append(SkillStep(
                name=name,
                store_key=str(s.get("store_key") or name),
                instruction=str(s.get("instruction") or ""),
                inputs=inputs,
                params=params,
            ))
        if not steps:
            return None
        return SkillPlan(
            name=str(data.get("name") or "llm-plan"),
            description=str(data.get("description") or ""),
            steps=steps,
            handoff=str(data.get("handoff") or "已产出 AI 内容准备,前端据此组装 task.create 渲染"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[orchestrator] LLM 规划失败,回退单技能: {exc}")
        return None


async def compile_plan(goal: str, meta: Optional[Dict[str, Any]] = None, use_llm: bool = True) -> Optional[SkillPlan]:
    """把高层目标编译成计划。

    匹配优先级:
      1. goal 直接命中某个计划名(便于调试/显式调用);
      2. meta.intent 命中意图映射(见 _INTENT_PLANS)→ 对应计划;
      3. goal 含「复刻/对标」→ video-replicate-prep;含「生成/九宫格」→ video-prep;
      4. 未命中且 use_llm=True → 调 chat 网关把目标解析成技能步骤 DAG(_llm_plan);
      5. 均未命中 → None(调用方退化为单技能 run_skill)。
    """
    meta = meta or {}
    if goal in PLAN_REGISTRY:
        return PLAN_REGISTRY[goal]
    intent = str(meta.get("intent", "")).lower()
    if intent in _INTENT_PLANS:
        return PLAN_REGISTRY[_INTENT_PLANS[intent]]
    if any(k in (goal or "") for k in ("复刻", "对标", "replicate")):
        return PLAN_REGISTRY["video-replicate-prep"]
    if any(k in (goal or "") for k in ("生成", "九宫格", "generate")):
        return PLAN_REGISTRY["video-prep"]
    if use_llm:
        return await _llm_plan(goal, meta)
    return None


# 单例执行器
orchestrator = SkillOrchestrator()
