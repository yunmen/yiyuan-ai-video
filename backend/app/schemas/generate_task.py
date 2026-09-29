# -*- coding: utf-8 -*-
'''
@文件    :generate_task.py
@说明    :生成任务Schema
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import Field, BaseModel, field_validator
from typing import Optional, List, Dict

# 复刻目标形态白名单校验(纯函数,无外部依赖,不会造成循环导入)
from app.services.gen_rules import normalize_replicate_format


class CreateSchema(BaseModel):
    # 模板 Id 可选:普通生成(选平台模板)必传;视频复刻链路用户自带对标视频时无需传模板。
    # 服务层对「传了但无效」的模板仍按原规则报错,仅放开「不传」这一情形。
    template_id: Optional[int] = Field(None, description="模板Id(普通生成必传;视频复刻可不传)")
    materials: List[str] = Field(..., description="素材地址列表", min_length=1, max_length=9)
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")
    user_id: Optional[int] = Field(None, description="关联用户Id")
    # 替换意图(多选):product=换产品 / person=换人物 / scene=换场景;空=参考生视频(以图为主体)
    intent: Optional[List[str]] = Field(None, description="替换意图多选:product/person/scene")
    # 复刻目标形态(可选):决定成片的**内容结构**(口播/短剧/街采…),白名单见
    # gen_rules.REPLICATE_FORMATS。不传/非法 = 沿用原片结构。
    # 此前前端已在下发该字段(Replicate.vue 的 replicateFormat),但本 Schema 未声明 →
    # Pydantic 静默忽略,用户选了形态等于没选 —— 这正是"替换主角后一点创意也没有"的成因之一。
    format: Optional[str] = Field(
        None, description="复刻目标形态(可选):talking_head/short_drama/presenter_led_explainer/"
        "street_interview/two_person_podcast/ranking_listicle/narration_led_demo",
    )
    # 图片地址 → 角色。前端已知每张图是什么(产品图/人物图/场景图),直接告知视觉识别能显著提高准确率:
    # 实测只让模型自己看时,庭院里的狗照会被判成"场景",导致"人物+产品"结合识别失败。
    # 用映射而非数组,避免与 materials 的下标错位。
    image_roles: Optional[Dict[str, str]] = Field(
        None, description="素材图地址 → 角色(product/person/scene),前端标注,用于多图分组识别",
    )
    # 规格(可选):用户在页面显式选择的时长/画幅/清晰度;不传则由模板时长与系统配置决定。
    # 服务层用 gen_rules 的白名单/档位吸附兜底(非法值回退默认),避免"建单成功但必然失败"的任务。
    duration: Optional[int] = Field(None, ge=1, le=60, description="时长(秒,可选)")
    ratio: Optional[str] = Field(None, description="画幅(可选):9:16/16:9/1:1/4:3/3:4")
    resolution: Optional[str] = Field(None, description="清晰度(可选):720P/1080P")
    # 真人处理策略(可选,per-task 覆盖系统默认):auto=沿用系统配置 gen.image_real_person_mode;
    # stylize=写实化保留(参考图含真人时先拟态化,保住人物);drop=直接丢弃该图改按文字描述生成。
    # 不传则回退系统默认,与历史任务行为一致。
    real_person_strategy: Optional[str] = Field(
        None, description="真人处理策略:auto=系统默认;stylize=写实化保留;drop=直接丢弃",
    )
    # 复刻目标形态(可选):决定成片的内容结构(短剧/口播/街采/…),
    # 对应 backend/skills/prompts/replicate/formats/ 下的形态资产。
    # 可选项由 gen_rules.REPLICATE_FORMAT_OPTIONS 单一来源定义,并经 /gen-config 的
    # replicate_formats 下发给前端 —— 描述里**不枚举**具体形态,避免新增形态时描述与白名单漂移。
    # 不传=不指定形态,复刻沿用原片结构(与历史行为一致);非法值归一化为不指定。
    format: Optional[str] = Field(
        None, description="复刻目标形态(可选项见 /gen-config 的 replicate_formats)",
    )

    @field_validator("materials")
    @classmethod
    def materials_not_blank(cls, v):
        if any(not str(item).strip() for item in v):
            raise ValueError("素材地址不能为空")
        return v

    @field_validator("real_person_strategy")
    @classmethod
    def real_person_strategy_valid(cls, v):
        # 仅允许 auto/stylize/drop,大小写不敏感;非法值回退 None(沿用系统默认)
        if not v:
            return None
        v = str(v).strip().lower()
        return v if v in ("auto", "stylize", "drop") else None

    @field_validator("format")
    @classmethod
    def format_valid(cls, v):
        # 仅允许 7 种复刻目标形态;非法值归一化为 None(不指定形态),不因前端传错而报错
        return normalize_replicate_format(v) or None


class DeconstructSchema(BaseModel):
    """拆解对标视频分镜(带货视频复刻前置):返回结构化分镜 JSON,供前端可视化编辑

    与 CreateSchema 的区别:这里只做「看懂原片」的分析,不消耗生成额度、不产出成片;
    结果经 /task/detail 的 result_text 回写,前端轮询读取。
    """

    reference_video: str = Field(..., description="对标视频地址(用于逆向拆解分镜)")
    # 替换意图(多选):product=换产品 / person=换人物 / scene=换场景;空=仅拆解不指定替换维度
    intent: Optional[List[str]] = Field(None, description="替换意图多选:product/person/scene")
    # 已知时长(秒):前端能从上传信息拿到的可带上,缺省由 worker 用 ffmpeg 探测
    duration: Optional[int] = Field(None, ge=1, le=120, description="对标视频时长(秒,可选)")
    device: str = Field("desktop", description="设备类型")
    # 复刻目标形态(可选):与 CreateSchema.format 同源,拆解与生成必须传同一个形态,
    # 否则会出现"按短剧理解原片、却按原片结构出片"的理解与生成不一致。
    format: Optional[str] = Field(None, description="复刻目标形态(与 CreateSchema.format 一致)")

    @field_validator("format")
    @classmethod
    def format_valid(cls, v):
        # 与 CreateSchema 同一白名单;非法值归一化为 None(不指定形态)
        return normalize_replicate_format(v) or None


class EstimateSchema(BaseModel):
    """下单前花费预估(预算前置:预估 → 预扣 → 结算返还)"""
    type: str = Field("video", description="任务类型:video/image/audio/text/digital")
    template_id: Optional[int] = Field(None, description="模板Id(视频任务,用于取时长档位)")
    num_images: int = Field(1, ge=1, le=4, description="图片生成数量")
    duration: Optional[int] = Field(None, description="时长(秒,数字人任务)")
    # 规格覆盖:用户在页面切换时长/画幅/清晰度后实时重算价格(与下单扣减同源)
    ratio: Optional[str] = Field(None, description="画幅(可选)")
    resolution: Optional[str] = Field(None, description="清晰度(可选)")
    # 是否携带参考视频(用户上传或模板示例视频):用于提前告知"视频编辑能力是否可用",
    # 避免用户以为会替换原片、结果拿到一条"用上传图重画"的成片。
    has_reference_video: bool = Field(False, description="本次是否携带参考视频")


class QuerySchema(BaseModel):
    pageNum: int = Field(default=1, description="页码")
    pageSize: int = Field(default=10, description="每页数量")
    status: Optional[str] = Field(None, description="任务状态")
    task_no: Optional[str] = Field(None, description="任务编号")
    type: Optional[str] = Field(None, description="任务类型:video/image/audio/text/digital")


class CallbackSchema(BaseModel):
    """Worker 通过 notify_url 回写的任务状态负载"""
    task_id: int = Field(..., description="任务Id")
    status: str = Field(..., description="任务状态:processing/success/failed")
    progress: Optional[int] = Field(None, description="进度百分比(processing 时回传)")
    result_video: Optional[str] = Field(None, description="生成结果视频地址(success 时回传)")
    result: Optional[str] = Field(None, description="生成结果文本/其他类型结果")
    fail_reason: Optional[str] = Field(None, description="失败原因(failed 时回传)")
    usage: Optional[Dict] = Field(None, description="用量与消耗(计费用,预留)")


class ImageCreateSchema(BaseModel):
    """图片生成任务创建参数"""
    prompt: str = Field(..., description="画面描述", min_length=1, max_length=2000)
    ratio: str = Field("1:1", description="画幅:1:1/16:9/9:16/4:3/3:4")
    num_images: int = Field(1, ge=1, le=4, description="生成数量")
    materials: List[str] = Field(default_factory=list, description="参考图(有则走图生图)")
    intent: List[str] = Field(
        default_factory=list,
        description="复刻替换意图:product/person/scene;非空表示「按参考图复刻、换掉该元素」",
    )
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")


class AudioCreateSchema(BaseModel):
    """音频生成任务创建参数(tts 语音合成 / bgm 背景音乐)"""
    audio_type: str = Field("tts", description="音频类型:tts/bgm")
    text: Optional[str] = Field(None, description="语音合成文本(tts 用)")
    prompt: Optional[str] = Field(None, description="音乐风格描述(bgm 用)")
    lyrics: Optional[str] = Field(None, description="歌词(bgm 用)")
    voice: Optional[str] = Field(None, description="音色")
    is_instrumental: bool = Field(False, description="是否纯音乐")
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")


class TextCreateSchema(BaseModel):
    """文本生成任务创建参数"""
    prompt: str = Field(..., description="提示词", min_length=1, max_length=5000)
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")


class DigitalCreateSchema(BaseModel):
    """数字人口播任务创建参数(数字人形象 + 口播文案/音频 → 口型驱动视频)"""
    digital_id: int = Field(..., description="数字人Id")
    text: Optional[str] = Field(None, max_length=2000, description="口播文案(留空则用数字人默认文案)")
    audio: Optional[str] = Field(None, description="口播音频地址(提供则直接使用,不再合成语音)")
    voice: Optional[str] = Field(None, description="音色(覆盖数字人默认音色)")
    pose: Optional[str] = Field(None, description="派生视图名称(留空用主视图)")
    duration: int = Field(8, ge=3, le=15, description="成片时长(秒),口播时长以音频为准时该值仅作占位")
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")


class CacheQuery(BaseModel):
    """Worker 读取资产缓存(内部接口)"""
    cache_key: str = Field(..., description="缓存键(产物类型 + 入参哈希)")
    asset_type: str = Field("", description="产物类型:tts_audio/optimized_prompt")


class CacheSchema(BaseModel):
    """Worker 回写资产缓存(内部接口)

    只缓存「同一输入必然产出同一结果」的中间产物(如 TTS 音频、LLM 改写结果);
    视频/图片成片本身不缓存 —— 每次生成都是新作品。
    """
    cache_key: str = Field(..., description="缓存键")
    asset_type: str = Field(..., description="产物类型:tts_audio/optimized_prompt")
    content: str = Field(..., description="产物内容(URL 或文本)")
    task_type: str = Field("", description="任务类型,便于按类型清理")
    meta: Optional[Dict] = Field(None, description="附加信息(模型/音色等,便于排查)")


class CheckpointQuery(BaseModel):
    """Worker 拉取断点检查点(内部接口)"""
    task_id: int = Field(..., description="任务Id")


class CheckpointSchema(BaseModel):
    """Worker 回写断点检查点(内部接口)

    stage 语义:
      1 = prompt 已改写完成(可复用 optimized_prompt)
      2 = 已提交外部生成任务(可复用 external_task_id 继续轮询,避免重复扣费)
      3 = 已轮询拿到原始视频 raw_url(仅需转存 OSS)
    data 携带对应阶段的中间产物。
    """
    task_id: int = Field(..., description="任务Id")
    stage: int = Field(..., description="已完成阶段:1/2/3")
    data: Optional[Dict] = Field(None, description="阶段中间产物(optimized_prompt/external_task_id/raw_url 等)")
    progress: Optional[int] = Field(None, description="进度百分比(与阶段对齐,可选)")
