# -*- coding: utf-8 -*-
'''
@文件    :content.py
@说明    :用户端-内容生成入口(对外的产品功能接口,不暴露内部技能/编排概念)。
         前端只看到产品功能(文案 / 图片提示词 / 语音 / 内容准备),
         具体由哪个 worker 技能(text-generation / image-generation / audio-synthesis /
         video-replicate-prep 流水线)执行,全部在服务端硬编码映射,绝不进入 URL 或响应,
         避免把内部实现细节暴露给终端用户与竞品。
         POST /content/copy         生成带货文案(映射 text-generation)
         POST /content/image-prompt 生成中文图片提示词(映射 image-generation)
         POST /content/voice        语音合成(映射 audio-synthesis)
         POST /content/prepare      内容准备流水线(映射 video-replicate-prep / video-prep 计划)
         POST /content/result       轮询异步产物(仅按 task_id,不含技能名)
         路由统一挂在 router 前缀 /content 下。
@时间    :2026/10/01
@作者    :一源AI
@版本    :1.0
'''
from typing import Dict, Optional

from fastapi import APIRouter, Body, Request, Depends
from app.core.dependencies import OptionalUserToken

from app.core.routeclass import OperationLogRoute
from app.core.response import Success, Fail
from app.core import ratelimit


router = APIRouter(route_class=OperationLogRoute)

# 内容生成按 IP 限流,防止被刷模型额度
CONTENT_LIMIT_PER_MINUTE = 10

# 内部技能名(仅在服务端出现,严禁外泄到 URL / 响应 / 日志)
_SKILL_COPY = "text-generation"
_SKILL_IMAGE = "image-generation"
_SKILL_VOICE = "audio-synthesis"
_SKILL_REWRITE = "text-rewrite"
_SKILL_TRANSLATE = "text-translate"


@router.post("/copy", summary="生成带货文案(大标题/副标题/口播)")
async def content_copy(
    request: Request,
    instruction: str = Body("", description="自然语言指令(可选,缺字段时由模型解析补充)"),
    params: Optional[dict] = Body(None, description="结构化参数:template_title/category/title/subtitle/script/with_demand/images/roles"),
):
    """生成/润色三段带货文案,返回 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 text-generation 技能(ai_copy.generate),技能名不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_copy", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "文案生成请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(_SKILL_COPY, instruction, params or {})
    return Success(data=data)


@router.post("/image-prompt", summary="生成中文图片提示词")
async def content_image_prompt(
    request: Request,
    instruction: str = Body("", description="自然语言指令(可选)"),
    params: Optional[dict] = Body(None, description="结构化参数:narrations/style/min_words"),
):
    """根据口播/旁白生成逐镜中文图片提示词,返回 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 image-generation 技能,技能名不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_img", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "图片提示词生成请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(_SKILL_IMAGE, instruction, params or {})
    return Success(data=data)


@router.post("/voice", summary="语音合成(TTS)")
async def content_voice(
    request: Request,
    instruction: str = Body("", description="自然语言指令(可选)"),
    params: Optional[dict] = Body(None, description="结构化参数:text/voice/voice_reference/audio"),
):
    """文本转语音,返回音频直链 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 audio-synthesis 技能,技能名不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_voice", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "语音合成请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(_SKILL_VOICE, instruction, params or {})
    return Success(data=data)


@router.post("/prepare", summary="内容准备流水线(目标 → 多步骤内容生成)")
async def content_prepare(
    request: Request,
    goal: str = Body("", description="高层目标,如'复刻这段视频'"),
    meta: Optional[dict] = Body(None, description="计划上下文(用户侧元数据,intent/duration/reference_video 等)"),
    plan: Optional[dict] = Body(None, description="可选:调用方下发声明式计划(覆盖默认编译)"),
    g=Depends(OptionalUserToken),
):
    """下发内容准备流水线到 worker 异步执行,返回 task_id 供前端轮询 /content/result。

    内部映射到 video-replicate-prep / video-prep 等计划模板,按顺序产出文案/图提示词/词锚点,
    技能与编排概念均不对外暴露。
    """
    await ratelimit.check(
        ratelimit.build_key("content_prep", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "内容准备请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_pipeline

    context = dict(meta or {})
    if context.get("analysis_id"):
        from fastapi.exceptions import HTTPException
        from app.services.replica_analysis import load_analysis, get_verified_shots
        from app.services.user_material import verify_materials
        from app.schemas.generate_task import MaterialGroupSchema
        if not g:
            return Fail(msg="请登录后准备复刻文案")
        analysis = await load_analysis(context["analysis_id"], context.get("analysis_version"), g.id, context.get("reference_video"))
        images = context.get("images") or []
        await verify_materials(g.id, images)
        elements = {item["id"]: item for item in analysis["elements"]}
        groups = [MaterialGroupSchema.model_validate(item) for item in context.get("material_groups", [])]
        if any(group.element_id not in elements or any(url not in images for url in group.images) for group in groups):
            raise HTTPException(status_code=200, detail="文案素材组与当前原片不匹配")
        context["material_groups"] = [{**group.model_dump(), "kind": elements[group.element_id]["kind"],
                                       "label": elements[group.element_id]["label"]} for group in groups]
        context["speech_windows"] = None
        if context.get("deconstruct_id"):
            shots = await get_verified_shots(context["deconstruct_id"], g.id, context.get("reference_video"))
            context["speech_windows"] = [{"start": shot["start"], "end": shot["end"], "shot_index": index}
                                         for index, shot in enumerate(shots) if str(shot.get("narration") or "").strip()] or None
            # ASR 未启用或识别失败也会返回空台词，不能据此推断原片无口播。
        context["product_facts"] = []  # 原片商品信息不能当作替换商品事实。
        goal = "video-replicate-prep"
        context["intent"] = "replicate"
        plan = None  # 使用已注册的服务端复刻计划，不允许客户端切换其他计划。
    data = await enqueue_skill_pipeline(goal, context, plan)
    return Success(data=data)


@router.post("/translate", summary="批量翻译(多语言本地化)")
async def content_translate(
    request: Request,
    instruction: str = Body("", description="自然语言指令(可选,预留)"),
    params: Optional[dict] = Body(None, description="结构化参数:texts(文本列表,顺序敏感)/target_lang(目标语言代码)"),
):
    """批量翻译文本到目标语言,返回 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 text-translate 技能(ai_translate.translate),技能名不对外暴露。
    用于「模板多语言变体一键本地化」:把视频画面上的信息卡/角标/揭示/贴纸文案与创作目标整组翻译。
    """
    p = params or {}
    texts = p.get("texts") or []
    if isinstance(texts, str):
        texts = [texts]
    target_lang = str(p.get("target_lang") or "en").strip() or "en"
    if not texts:
        return Fail(message="待翻译文本不能为空")
    await ratelimit.check(
        ratelimit.build_key("content_translate", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "翻译请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(
        _SKILL_TRANSLATE, "", {"texts": [str(t) for t in texts], "target_lang": target_lang},
    )
    return Success(data=data)


@router.post("/rewrite", summary="长文去 AI 味改写")
async def content_rewrite(
    request: Request,
    text: str = Body("", description="待改写原文(必填,≤3000 字)"),
    level: int = Body(2, description="改写强度 1..4,对应 Mark I–IV(轻度→深度)"),
    tone: str = Body("natural", description="语气 natural/formal/friendly/sharp/humorous"),
    max_chars: int = Body(0, description="输出字数上限,0=不限"),
):
    """长文去 AI 味改写,返回 task_id 供前端轮询 /content/result。

    内部映射到 worker 的 text-rewrite 技能(ai_rewrite.rewrite_text),技能名不对外暴露。
    text 为空或超过 3000 字直接返回业务失败(Fail),不下发 worker。
    """
    src = (text or "").strip()
    if not src:
        return Fail(message="原文不能为空")
    if len(src) > 3000:
        return Fail(message="原文不能超过 3000 字")
    try:
        level = int(level)
    except (TypeError, ValueError):
        level = 2
    if level < 1 or level > 4:
        level = 2
    await ratelimit.check(
        ratelimit.build_key("content_rewrite", ratelimit.client_ip(request)),
        CONTENT_LIMIT_PER_MINUTE, 60, "去 AI 味改写请求过于频繁,请稍后再试",
    )
    from app.core.task_queue import enqueue_skill_task

    data = await enqueue_skill_task(
        _SKILL_REWRITE, "",
        {"text": src, "level": level, "tone": (tone or "natural"), "max_chars": int(max_chars or 0)},
    )
    return Success(data=data)


@router.post("/result", summary="轮询内容生成结果(异步接口,前端轮询)")
async def content_result(
    request: Request,
    task_id: str = Body(..., embed=True, description="/content/* 返回的 task_id"),
):
    """轮询内容生成标准产物。

    返回 data.status:
      - done     : 执行完成,data.result 为产物序列化体 {content, metadata}
      - pending  : 任务仍在执行中(继续轮询)
      - not_found: 任务不存在或已过期
    """
    from app.core.task_queue import read_skill_result

    status, data = await read_skill_result(task_id)
    if status == "done":
        return Success(data={"status": "done", "result": data})
    if status == "not_found":
        return Success(data={"status": "not_found"})
    return Success(data={"status": "pending"})
