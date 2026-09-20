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

    @field_validator("materials")
    @classmethod
    def materials_not_blank(cls, v):
        if any(not str(item).strip() for item in v):
            raise ValueError("素材地址不能为空")
        return v


class QuerySchema(BaseModel):
    pageNum: int = Field(default=1, description="页码")
    pageSize: int = Field(default=10, description="每页数量")
    status: Optional[str] = Field(None, description="任务状态")
    task_no: Optional[str] = Field(None, description="任务编号")
    type: Optional[str] = Field(None, description="任务类型:video/image/audio/text")


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
