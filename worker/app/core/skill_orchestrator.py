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
import json

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core import gateway
from app.core.plugin import logger
from app.core.skill_runtime import registry, run_skill
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


@dataclass
class SkillPlan:
    """一个目标对应的技能流水线(声明式,可调试、可复现)。"""

    name: str
    description: str
    steps: List[SkillStep]
    handoff: str = ""  # 终态交接说明(如"去 task.create 渲染")


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


class SkillOrchestrator:
    """流水线执行器:按序跑步骤,黑板传递产物,返回复合 ToolResult。"""

    async def run(self, plan: SkillPlan, ctx: Dict[str, Any]) -> ToolResult:
        """执行计划,返回 content={各步骤 store_key: 产物},metadata 含 plan 与 handoff。

        单步失败不影响整体:run_skill 本身对未知/异常技能返回带 error 的 ToolResult,
        这里照常写入黑板,后续步骤若依赖其字段取不到则为空,由 plan_params 兜底。
        """
        blackboard: Dict[str, Any] = {}
        logger.info(f"[orchestrator] 执行计划 {plan.name} 共 {len(plan.steps)} 步")
        for step in plan.steps:
            params = _build_step_params(step, blackboard, ctx)
            try:
                result = await run_skill(step.name, step.instruction, params)
                blackboard[step.store_key] = result.content
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[orchestrator] 步骤 {step.name} 异常: {exc}")
                blackboard[step.store_key] = {"error": str(exc)}
        return ToolResult(
            content=blackboard,
            metadata={
                "ok": True,
                "plan": plan.name,
                "handoff": plan.handoff,
                "steps": [s.name for s in plan.steps],
            },
        )


# —— 预声明计划模板(确定性,不依赖 LLM 规划) ——
PLAN_REGISTRY: Dict[str, SkillPlan] = {
    "video-replicate-prep": SkillPlan(
        name="video-replicate-prep",
        description="视频复刻的 AI 内容准备:三段文案 → 逐镜英文图提示词 → 词锚点时间估算",
        steps=[
            SkillStep(
                name="text-generation",
                store_key="copy",
                instruction="为复刻视频生成带货文案",
                params={"with_demand": True},
            ),
            SkillStep(
                name="image-generation",
                store_key="img_prompts",
                instruction="根据口播生成逐镜英文图片提示词",
                inputs={"narrations": "bb.copy.script"},
            ),
            SkillStep(
                name="script-anchor",
                store_key="anchors",
                instruction="根据口播与成片时长估算词级锚点与时间",
                inputs={"script": "bb.copy.script", "duration": "ctx.duration"},
            ),
        ],
        handoff="已产出 copy/img_prompts/anchors,前端据此组装 task.create 载荷走渲染",
    ),
    # 从零生成(九宫格/商品信息链路):无需对标视频,产出三段文案 + 逐镜英文图提示词,
    # 供文生图(分镜图)与出片复用。词锚点依赖成片时长,从零生成时通常未知,故本计划不含 script-anchor。
    "video-prep": SkillPlan(
        name="video-prep",
        description="从零生成视频的 AI 内容准备:三段文案 → 逐镜英文图提示词",
        steps=[
            SkillStep(
                name="text-generation",
                store_key="copy",
                instruction="根据商品信息生成带货文案",
                params={"with_demand": True},
            ),
            SkillStep(
                name="image-generation",
                store_key="img_prompts",
                instruction="根据口播生成逐镜英文图片提示词",
                inputs={"narrations": "bb.copy.script"},
            ),
        ],
        handoff="已产出 copy/img_prompts,前端据此生成九宫格分镜图并出片",
    ),
}


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
