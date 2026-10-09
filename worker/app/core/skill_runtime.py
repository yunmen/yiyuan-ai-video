# -*- coding: utf-8 -*-
'''技能运行时:把 worker/skills 下的技能暴露成统一可调用入口(类 IDE `/技能 做什么`)。

职责:
- 维护技能注册表(name → handler),技能以 `@skill` 装饰器自描述注册;
- 把自然语言指令(instruction)经 chat 网关解析为缺失的结构化参数(plan_params);
- 统一执行入口 run_skill:查表 → 解析参数 → 调用 handler → 返回标准产物 ToolResult。

所有技能产出统一为 ToolResult(content, metadata),保证"做什么 → 标准产物"的形态一致。
'''
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from openai import AsyncOpenAI

import json

from app.core.plugin import logger
from app.core import gateway
from app.settings import config
from app.schemas.base import ToolResult


@dataclass
class SkillParam:
    """技能入参字段描述:用于 NL 解析与目录发现。"""
    name: str
    type: str = "str"
    required: bool = False
    description: str = ""


@dataclass
class SkillSpec:
    """单个技能的注册元数据 + 执行句柄。"""
    name: str
    description: str
    capability: str = ""
    input_schema: List[SkillParam] = field(default_factory=list)
    handler: Optional[Callable] = None  # async (instruction, params) -> ToolResult
    source: str = ""  # 来源技能目录(如 text-generation)


class SkillRegistry:
    """技能注册表:name → SkillSpec,进程内单例。"""

    def __init__(self) -> None:
        self._specs: Dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> None:
        self._specs[spec.name] = spec
        logger.info(f"[skill] 注册技能 {spec.name} (来源 {spec.source or '—'})")

    def get(self, name: str) -> Optional[SkillSpec]:
        return self._specs.get(name)

    def values(self) -> List[SkillSpec]:
        """返回全部已注册技能元数据(供编排器构建可用技能清单)。

        注意:早期 skill_orchestrator._llm_plan 误用 registry.values() 期望拿到 SkillSpec 列表,
        SkillRegistry 此前未实现该方法是导致 LLM 规划器抛 AttributeError 被静默吞掉、功能失效的根因。
        """
        return list(self._specs.values())

    def list(self) -> List[Dict[str, Any]]:
        """返回目录发现用的轻量元数据(不含 handler,安全可序列化)。"""
        return [
            {
                "name": s.name,
                "description": s.description,
                "capability": s.capability,
                "input_schema": [
                    {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                    for p in s.input_schema
                ],
            }
            for s in self._specs.values()
        ]


# 进程内唯一注册表
registry = SkillRegistry()


def skill(name: str, description: str, capability: str = "", input_schema: Optional[List[SkillParam]] = None,
          source: str = ""):
    """装饰器:把 async (instruction, params) -> ToolResult 的函数注册为一个技能。"""

    def deco(fn: Callable) -> Callable:
        registry.register(SkillSpec(
            name=name, description=description, capability=capability,
            input_schema=input_schema or [], handler=fn, source=source,
        ))
        return fn

    return deco


def _has_value(d: Dict[str, Any], key: str) -> bool:
    """参数是否算"已提供"(非空字符串/非 None)。"""
    v = d.get(key)
    return v is not None and (not isinstance(v, str) or v.strip() != "")


async def plan_params(spec: SkillSpec, instruction: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """把自然语言指令 + 已有参数,补全成技能所需的完整参数。

    - 已提供的必填字段直接用;
    - 缺失且给了 instruction → 用 chat 网关把指令解析为缺失字段(JSON);
    - 网关不可用 / 解析失败 → 启发式兜底(如 template_title 取指令前 20 字)。
    """
    params = dict(params or {})
    missing = [p for p in spec.input_schema if p.required and not _has_value(params, p.name)]
    if not missing or not (instruction or "").strip():
        return params
    filled = await _llm_extract(spec, instruction, missing)
    for p in missing:
        if _has_value(filled, p.name):
            params[p.name] = filled[p.name]
        else:
            params[p.name] = _heuristic_default(p, instruction)
    return params


async def _llm_extract(spec: SkillSpec, instruction: str, missing: List[SkillParam]) -> Dict[str, Any]:
    """用 chat 网关把自然语言指令解析为缺失字段的 JSON。失败返回空字典(走兜底)。"""
    gw = gateway.resolve("chat")
    if not (gw.get("url") and gw.get("key")):
        return {}
    fields = ", ".join(f"{p.name}({p.type},{p.description})" for p in missing)
    system = (
        f"你是参数解析器。技能「{spec.name}」需要以下字段:{fields}。"
        f"请从用户指令中提取对应值,只输出 JSON(不要代码块/解释),键为字段名。"
    )
    try:
        client = AsyncOpenAI(api_key=gw["key"], base_url=gw["url"].rstrip("/"), timeout=30)
        resp = await client.chat.completions.create(
            model=(config.CHAT_MODEL or "").strip(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": instruction},
            ],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.strip("`").lstrip("json").strip()
        import json
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[skill] 指令解析失败,回退启发式兜底: {exc}")
        return {}


def _heuristic_default(p: SkillParam, instruction: str) -> Any:
    """缺失字段的兜底值:尽量让技能仍可产出,而非直接报错。"""
    if p.name == "template_title":
        return (instruction or "").strip()[:20]
    if p.name == "category":
        return "零售带货"
    if p.type == "bool":
        return False
    if p.type == "list":
        return []
    return ""


async def run_skill(name: str, instruction: str, params: Dict[str, Any]) -> ToolResult:
    """技能统一执行入口:查表 → 解析参数 → handler → 标准 ToolResult。

    未知技能或执行异常均返回带 error 的 ToolResult(不抛异常中断调用方),
    metadata.ok=False 供上层判定失败。
    """
    spec = registry.get(name)
    if spec is None or spec.handler is None:
        return ToolResult(content={"error": f"未知技能: {name}"}, metadata={"ok": False, "skill": name})
    params = await plan_params(spec, instruction or "", params or {})
    try:
        result = await spec.handler(instruction or "", params)
        if not isinstance(result, ToolResult):
            result = ToolResult(content=result, metadata={})
        result.metadata.setdefault("skill", name)
        result.metadata.setdefault("ok", True)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[skill] 执行失败 name={name}: {exc}")
        return ToolResult(content={"error": str(exc)}, metadata={"ok": False, "skill": name})


def spec_to_openai_tool(spec) -> dict:
    """把技能自描述(SkillSpec)转成 OpenAI function-calling 工具声明,供 agent 步骤让模型自主选择调用。"""
    props: Dict[str, Any] = {}
    required: List[str] = []
    for p in (spec.input_schema or []):
        props[p.name] = {"type": p.type or "string", "description": p.description or ""}
        if p.required:
            required.append(p.name)
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description or "",
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


async def run_agent_loop(goal: str, tools: List[str], ctx: Dict[str, Any],
                         max_iter: int = None, system_hint: str = "") -> ToolResult:
    """工具调用(ReAct)式 agent 步骤:模型可自主选择调用已注册技能作为工具,观察结果后继续,直到给出终态答案。

    编排器仅在 SkillStep.tools 非空时调用;默认两条固定 plan 不触发,保证向后兼容。
    无 chat 网关时降级:直接执行首个可用工具,保证流程不中断;无工具则报错。
    """
    max_iter = int(max_iter if max_iter is not None else getattr(config, "AGENT_MAX_ITER", 4))
    gw = gateway.resolve("chat")
    if not (gw.get("url") and gw.get("key")):
        if tools:
            try:
                res = await run_skill(tools[0], goal, ctx or {})
                # 降级路径也收敛为 agent 步骤的统一契约 {answer, iterations},
                # 与正常 ReAct 路径一致,避免下游(如 video-replicate-prep-agent 读 bb.copy.answer)在
                # 无网关时拿到 None。answer 取结构化产物的口播/旁白文本,缺失则回退整体字符串化。
                content = res.content if isinstance(res.content, dict) else {}
                answer = content.get("script") or content.get("narration") or str(res.content)
                return ToolResult(
                    content={"answer": answer, "iterations": 0},
                    metadata={"ok": True, "skill": "agent", "degraded": True},
                )
            except Exception as exc:  # noqa: BLE001
                return ToolResult(content={"error": f"agent 降级调用失败: {exc}"}, metadata={"ok": False, "skill": "agent"})
        return ToolResult(content={"error": "未配置 chat 网关且无可用工具"}, metadata={"ok": False, "skill": "agent"})

    openai_tools = [spec_to_openai_tool(registry.get(n)) for n in tools if registry.get(n)]
    openai_tools = [t for t in openai_tools if t]
    if not openai_tools:
        return ToolResult(content={"error": f"agent 步骤声明的工具均不存在: {tools}"}, metadata={"ok": False, "skill": "agent"})

    model = getattr(config, "TEXT_MODEL", "") or getattr(config, "CHAT_MODEL", "") or "gpt-4o-mini"
    client = AsyncOpenAI(api_key=gw["key"], base_url=gw["url"].rstrip("/"), timeout=60)
    system_content = (
        "你是一个任务编排 agent。根据目标,必要时调用提供的工具(已注册技能)获取信息或产物,"
        "观察工具返回后继续,直到能给出满足目标的最终答案。只调用与目标相关的工具,不要编造工具。"
        + (system_hint or "")
    )
    ctx_hint = json.dumps(ctx or {}, ensure_ascii=False)[:1200]
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"目标:{goal}\n可用上下文:{ctx_hint}"},
    ]
    for i in range(max_iter):
        try:
            resp = await client.chat.completions.create(
                model=model, messages=messages, tools=openai_tools, tool_choice="auto",
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(content={"error": f"agent 模型调用失败: {exc}"}, metadata={"ok": False, "skill": "agent"})
        msg = resp.choices[0].message
        if not getattr(msg, "tool_calls", None):
            return ToolResult(content={"answer": (msg.content or "").strip(), "iterations": i + 1}, metadata={"ok": True, "skill": "agent"})
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
        for tc in msg.tool_calls:
            fn = tc.function
            try:
                args = json.loads(fn.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                tool_res = await run_skill(fn.name, fn.arguments or "", args)
                tool_content = json.dumps(tool_res.content, ensure_ascii=False, default=str)[:2000]
            except Exception as exc:  # noqa: BLE001
                tool_content = f"工具执行失败: {exc}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": tool_content})
    return ToolResult(content={"answer": "(达到最大迭代仍未收敛)", "iterations": max_iter}, metadata={"ok": True, "skill": "agent"})


# —— 内置技能注册(懒加载,幂等) ——
_BUILTINS_DONE = False


def register_builtin_skills() -> None:
    """注册内置技能(首个:text-generation 包 ai_copy.generate)。幂等,可重复调用。"""
    global _BUILTINS_DONE
    if _BUILTINS_DONE:
        return
    _BUILTINS_DONE = True

    # 确保工作流计划已加载(与技能注册同生命周期;编排器模块导入时也已加载一次,这里幂等兜底)
    try:
        from app.core.skill_orchestrator import load_workflows
        load_workflows()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[skill] 加载工作流失败(不阻断技能注册): {exc}")

    from app.services.ai_copy import generate as generate_copy
    from app.services.ai_rewrite import rewrite_text
    from app.services.ai_translate import translate as translate_text
    from app.services.image_prompt import generate as generate_image_prompt
    from app.services.ai_vision import classify_subjects
    from app.tools.script_anchor import build_script, estimate_timing, render_anchor_hint
    from app.tools.audio_tool import AudioGenTool

    @skill(
        name="text-generation",
        description="AI 三段带货文案生成(大标题/副标题/口播),支持图文结合与草稿润色",
        capability="text",
        source="text-generation",
        input_schema=[
            SkillParam("template_title", "str", True, "模板/主题标题"),
            SkillParam("category", "str", True, "行业分类,如 零售带货/美食探店/美妆个护"),
            SkillParam("title", "str", False, "大标题草稿(润色用)"),
            SkillParam("subtitle", "str", False, "副标题草稿"),
            SkillParam("script", "str", False, "口播草稿"),
            SkillParam("images", "list", False, "参考图 URL 列表(图文结合)"),
            SkillParam("with_demand", "bool", False, "是否返回 subject/demand 草稿"),
            SkillParam("roles", "list", False, "素材角色 person/product/scene(与 images 对应)"),
        ],
    )
    async def _text_generation(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:text-generation → 包装 ai_copy.generate 产出三段文案。"""
        result = await generate_copy(
            template_title=params.get("template_title") or "",
            category=params.get("category") or "",
            title=params.get("title"),
            subtitle=params.get("subtitle"),
            script=params.get("script"),
            images=params.get("images"),
            with_demand=bool(params.get("with_demand", False)),
            roles=params.get("roles"),
        )
        return ToolResult(content=result, metadata={"skill": "text-generation"})

    @skill(
        name="text-rewrite",
        description="长文去 AI 味改写:按 level(1..4,Mark I–IV 强度)与 tone 语气,消除 AI 套话与机器腔,保留原意",
        capability="text",
        source="text-rewrite",
        input_schema=[
            SkillParam("text", "str", True, "待改写原文(≤3000 字)"),
            SkillParam("level", "int", True, "改写强度 1..4,对应 Mark I–IV(轻度→深度)"),
            SkillParam("tone", "str", False, "语气 natural/formal/friendly/sharp/humorous,默认 natural"),
            SkillParam("max_chars", "int", False, "输出字数上限,0=不限,默认 0"),
        ],
    )
    async def _text_rewrite(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:text-rewrite → 包装 ai_rewrite.rewrite_text 产出去 AI 味改写结果。"""
        try:
            level = int(params.get("level") or 2)
        except (TypeError, ValueError):
            level = 2
        try:
            max_chars = int(params.get("max_chars") or 0)
        except (TypeError, ValueError):
            max_chars = 0
        result = await rewrite_text(
            text=params.get("text") or "",
            level=level,
            tone=params.get("tone") or "natural",
            max_chars=max_chars,
        )
        return ToolResult(content=result, metadata={"skill": "text-rewrite"})

    @skill(
        name="text-translate",
        description="批量翻译文本到目标语言(供模板多语言变体本地化复用),网关缺失/失败原样返回",
        capability="text",
        source="text-translate",
        input_schema=[
            SkillParam("texts", "list", True, "待翻译文本列表(顺序敏感)"),
            SkillParam("target_lang", "str", False, "目标语言代码 en/ja/ko/es/fr/...,默认 en"),
        ],
    )
    async def _text_translate(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:text-translate → 包装 ai_translate.translate 批量翻译。"""
        texts = params.get("texts") or []
        if isinstance(texts, str):
            texts = [texts]
        result = await translate_text(
            texts=[str(t) for t in texts],
            target_lang=params.get("target_lang") or "en",
        )
        return ToolResult(content=result, metadata={"skill": "text-translate"})

    @skill(
        name="image-generation",
        description="根据口播/旁白生成逐镜中文图片提示词(复用 image-generation 技能资产)",
        capability="image",
        source="image-generation",
        input_schema=[
            SkillParam("narrations", "list", True, "口播/旁白文本列表(逐条对应一张图提示词)"),
            SkillParam("style", "str", False, "风格描述(可选,转英文前缀拼到每条提示词前)"),
            SkillParam("min_words", "int", False, "每条提示词最少词数,默认 50"),
            SkillParam("max_words", "int", False, "每条提示词最多词数,默认 100"),
        ],
    )
    async def _image_generation(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:image-generation → 包装 image_prompt.generate 产出英文图提示词列表。"""
        narrations = params.get("narrations") or []
        if isinstance(narrations, str):
            narrations = [narrations]
        prompts = await generate_image_prompt(
            narrations=narrations,
            style=params.get("style") or None,
            min_words=int(params.get("min_words") or 50),
            max_words=int(params.get("max_words") or 100),
            reference_images=params.get("reference_images") or None,
        )
        return ToolResult(content=prompts, metadata={"skill": "image-generation"})

    @skill(
        name="script-anchor",
        description="根据口播与成片时长估算词级锚点与时间轴(复用 script-anchor 技能)",
        capability="script",
        source="script-anchor",
        input_schema=[
            SkillParam("script", "str", False, "口播/旁白文本(用于切词与锚点)"),
            SkillParam("duration", "str", False, "成片时长(秒),默认 5"),
        ],
    )
    async def _script_anchor(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:script-anchor → 包装 script_anchor 的切词/计时/锚点提示。"""
        script = params.get("script") or ""
        try:
            dur = float(params.get("duration") or 5)
        except (TypeError, ValueError):
            dur = 5.0
        structured = build_script(script) if script else {}
        timing = estimate_timing(structured or None, dur)
        hint = render_anchor_hint(structured or None)
        return ToolResult(
            content={"script": structured, "timing": timing, "anchor_hint": hint},
            metadata={"skill": "script-anchor"},
        )


    @skill(
        name="ai-recognize",
        description="视觉识别(商品/人物/场景):上传图 → 分组识别结果,供复刻/生成做素材锚点",
        capability="vision",
        source="ai-recognize",
        input_schema=[
            SkillParam("images", "list", True, "待识别图片 URL 列表"),
            SkillParam("roles", "list", False, "素材角色 person/product/scene(与 images 对应)"),
        ],
    )
    async def _ai_recognize(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:ai-recognize → 包装 classify_subjects(纯视觉网关调用,无 DB/额度)。"""
        result = await classify_subjects(params.get("images") or [], params.get("roles") or [])
        return ToolResult(content=result, metadata={"skill": "ai-recognize"})

    @skill(
        name="audio-synthesis",
        description="语音合成(TTS):文本 → 音频 URL,支持声纹复用(voice_reference)",
        capability="audio",
        source="audio-synthesis",
        input_schema=[
            SkillParam("text", "str", True, "合成文本(口播/旁白)"),
            SkillParam("voice", "str", False, "音色(不填用默认)"),
            SkillParam("voice_reference", "str", False, "声纹样本音频地址(克隆音色,可选)"),
            SkillParam("response_format", "str", False, "输出格式 mp3/wav 等,默认 mp3"),
            SkillParam("speed", "float", False, "语速(0.5x–2.0x,不填用网关默认)"),
            SkillParam("dialect", "str", False, "方言语义键(如 chuanyu/cantonese;经 audio_tool 透传,需网关支持)"),
        ],
    )
    async def _audio_synthesis(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:audio-synthesis → 包装 AudioGenTool.text_to_speech(语音网关调用)。

        未配置音频网关时构造 AudioGenTool 会抛错,run_skill 已统一捕获并返回 error 型 ToolResult,
        不向上冒泡(保持「单步失败不影响整体流水线」的契约)。
        """
        text = params.get("text") or instruction or ""
        tool = AudioGenTool()
        result = await tool.text_to_speech(
            text=text,
            voice=params.get("voice"),
            voice_reference=params.get("voice_reference"),
            response_format=params.get("response_format") or "mp3",
            speed=params.get("speed"),
            dialect=params.get("dialect"),
        )
        return result


    @skill(
        name="prompt-template",
        description="按模板名渲染结构化提示词(确定性函数,复用 worker/skills 提示词资产,不调模型)",
        capability="prompt",
        source="prompt-template",
        input_schema=[
            SkillParam("template", "str", True, "提示词模板名(对应 skills/prompts 注册名)"),
            SkillParam("vars", "dict", False, "渲染变量字典"),
        ],
    )
    async def _prompt_template(instruction: str, params: Dict[str, Any]) -> ToolResult:
        """技能 handler:prompt-template → 渲染指定提示词模板(确定性,不调模型)。

        补齐此前「有 SKILL.md 文档却未注册进运行时」的命名脱节;
        digital-human / video-generation 属重型渲染,按边界不注册为同步技能(见 docs/skill_agent_workflow_analysis.md)。
        """
        from skills.prompts import get as _get_prompt, safe_render as _safe_render

        name = params.get("template") or ""
        vars_ = params.get("vars") or {}
        asset = _get_prompt(name)
        if asset is None:
            return ToolResult(
                content={"error": f"未知提示词模板: {name}"},
                metadata={"ok": False, "skill": "prompt-template"},
            )
        try:
            rendered = _safe_render(name, "", **(vars_ or {})) if vars_ else asset.body
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                content={"error": f"模板渲染失败: {exc}"},
                metadata={"ok": False, "skill": "prompt-template"},
            )
        return ToolResult(
            content={"template": name, "prompt": rendered},
            metadata={"ok": True, "skill": "prompt-template"},
        )


async def publish_catalog(redis) -> None:
    """把运行时注册表(执行权威)序列化写 Redis,作为 /skills 目录单一来源。

    由 worker 任务入口(首次技能调用/启动)调用;backend 优先读 Redis 目录,
    未就绪时回退静态目录,消除两端漂移(见 docs/skill_agent_flow.md §9)。
    redis 为 arq 的异步连接,需 await。
    """
    if redis is None:
        return
    try:
        # 与前端/backend 消费契约一致:目录体为 {"skills": [...]},避免 worker 与消费端形状漂移
        payload = json.dumps({"skills": registry.list()}, ensure_ascii=False)
        # 注册表只在启动时变化,给较长 TTL;worker 重启会重新覆盖
        await redis.set("skill_catalog", payload, ex=86400)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[skill] 目录写 Redis 失败(不影响执行): {exc}")


async def publish_plans(redis) -> None:
    """把计划注册表(PLAN_REGISTRY)序列化写 Redis,作为 /skill/plan 预览的单一来源。

    由 worker 启动钩子与技能任务入口调用;backend /skill/plan 优先读 Redis 计划,
    未就绪时返回空,消除 backend _PLAN_SHOWCASE 与 worker PLAN_REGISTRY 的内容漂移。
    """
    if redis is None:
        return
    try:
        from dataclasses import asdict
        from app.core.skill_orchestrator import PLAN_REGISTRY
        payload = json.dumps(
            {k: asdict(v) for k, v in PLAN_REGISTRY.items()}, ensure_ascii=False
        )
        # 计划只在启动时变化,给较长 TTL;worker 重启会重新覆盖
        await redis.set("skill_plans", payload, ex=86400)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[skill] 计划写 Redis 失败(不影响执行): {exc}")
