# -*- coding: utf-8 -*-
'''
@文件    :storyboard.py
@说明    :分镜/镜头接口 Schema(请求与响应)
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


class ShotQuery(BaseModel):
    """按任务查询分镜/镜头列表"""
    task_id: int = Field(..., description="生成任务Id")
    page_num: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=200, description="每页数量")


class ShotUpdate(BaseModel):
    """编辑单个镜头(覆盖提示词/台词/时长),供局部重跑使用。

    前端分镜列表来自任务 usage.shots,只有镜头 index,没有数据库主键,
    故用 task_id + index 作为定位键(与 worker 回写的镜头序号一致)。
    """
    task_id: int = Field(..., description="生成任务Id")
    index: int = Field(..., description="镜头序号(与 usage.shots 的 index 一致)")
    prompt: Optional[str] = Field(None, description="覆盖的生视频提示词")
    narration: Optional[str] = Field(None, description="覆盖的台词/旁白")
    # 镜头时长编辑(可选):用户在分镜页微调镜头起止时间以控制成片节奏。
    # 两端必须成对传入(见字段校验):只改一端会写出零长度镜头,
    # 局部重跑按时间窗定位时就会切到一个空窗口。
    start_ms: Optional[int] = Field(None, ge=0, description="镜头起始时间(毫秒)")
    end_ms: Optional[int] = Field(None, ge=0, description="镜头结束时间(毫秒)")

    @model_validator(mode="after")
    def timing_pair_valid(self):
        """时长两端必须成对且 end > start,否则拒绝而不是写入坏数据"""
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("镜头时长必须同时提供起始与结束时间")
        if self.start_ms is not None and self.end_ms <= self.start_ms:
            raise ValueError("镜头结束时间必须大于起始时间")
        return self


class ShotItem(BaseModel):
    id: int
    index: int
    start_ms: int
    end_ms: int
    duration_ms: int
    narration: Optional[str] = None
    prompt: Optional[str] = None
    status: str
    result_url: Optional[str] = None
    qc_score: Optional[int] = None
    qc_low: bool = False
    qc_note: Optional[str] = None


class EpisodeItem(BaseModel):
    id: int
    task_id: Optional[int] = None
    title: str
    source: str
    shot_count: int
    status: str
    shots: List[ShotItem] = []


class ShotListResp(BaseModel):
    total: int
    episode: Optional[EpisodeItem] = None
    shots: List[ShotItem]
