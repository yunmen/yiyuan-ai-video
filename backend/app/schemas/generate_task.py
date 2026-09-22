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


class CreateSchema(BaseModel):
    template_id: int = Field(..., description="模板Id")
    materials: List[str] = Field(..., description="素材地址列表", min_length=1, max_length=9)
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")
    user_id: Optional[int] = Field(None, description="关联用户Id")
    # 替换意图(多选):product=换产品 / person=换人物 / scene=换场景;空=参考生视频(以图为主体)
    intent: Optional[List[str]] = Field(None, description="替换意图多选:product/person/scene")
    # 图片地址 → 角色。前端已知每张图是什么(产品图/人物图/场景图),直接告知视觉识别能显著提高准确率:
    # 实测只让模型自己看时,庭院里的狗照会被判成"场景",导致"人物+产品"结合识别失败。
    # 用映射而非数组,避免与 materials 的下标错位。
    image_roles: Optional[Dict[str, str]] = Field(
        None, description="素材图地址 → 角色(product/person/scene),前端标注,用于多图分组识别",
    )

    @field_validator("materials")
    @classmethod
    def materials_not_blank(cls, v):
        if any(not str(item).strip() for item in v):
            raise ValueError("素材地址不能为空")
        return v


class EstimateSchema(BaseModel):
    """下单前花费预估(预算前置:预估 → 预扣 → 结算返还)"""
    type: str = Field("video", description="任务类型:video/image/audio/text/digital")
    template_id: Optional[int] = Field(None, description="模板Id(视频任务,用于取时长档位)")
    num_images: int = Field(1, ge=1, le=4, description="图片生成数量")
    duration: Optional[int] = Field(None, description="时长(秒,数字人任务)")


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
