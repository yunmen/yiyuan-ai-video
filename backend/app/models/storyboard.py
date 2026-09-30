# -*- coding: utf-8 -*-
'''
@文件    :storyboard.py
@说明    :分镜与镜头领域模型 —— 把 worker 运行期的「分镜表/逐镜头质检」沉淀为可查询、可编辑、
           可局部重跑的一等公民实体。
           此前分镜/镜头只活在 worker 内存 + 任务的 JSON 文本(params/usage/result_text)里,
           无法做分镜级状态查询、编辑与局部重跑;本模型补齐这一缺口。
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class EpisodeModel(BaseModel, TimestampMixin):
    """分镜集:一条生成任务对应一个分镜集(视频复刻 / 多段生成的成片才有)"""

    task = fields.ForeignKeyField(
        "models.GenerateTaskModel", related_name="episodes", null=True,
        db_constraint=False, description="关联生成任务",
    )
    title = fields.CharField(max_length=100, default="", description="分镜集标题")
    # 来源:replicate=视频复刻逆推;multi_segment=多段生成按镜头切分
    source = fields.CharField(max_length=20, default="replicate", description="来源:replicate/multi_segment")
    shot_count = fields.IntField(default=0, description="镜头数量")
    status = fields.CharField(max_length=20, default="processing", description="状态:processing/success/failed")

    class Meta:
        table = "tb_episode"
        table_description = "分镜集表"


class ShotModel(BaseModel, TimestampMixin):
    """镜头:分镜集下的单个镜头,承载原片结构、逆推提示词、生成状态与质检分数"""

    episode = fields.ForeignKeyField(
        "models.EpisodeModel", related_name="shots", null=True,
        db_constraint=False, description="所属分镜集",
    )
    task = fields.ForeignKeyField(
        "models.GenerateTaskModel", related_name="shots", null=True,
        db_constraint=False, description="关联生成任务",
    )
    index = fields.IntField(default=0, description="镜头序号(从 0 开始)")
    start_ms = fields.IntField(default=0, description="镜头在原片起始时间(毫秒)")
    end_ms = fields.IntField(default=0, description="镜头在原片结束时间(毫秒)")
    duration_ms = fields.IntField(default=0, description="镜头时长(毫秒)")
    narration = fields.TextField(null=True, description="原片台词/旁白(ASR 归集)")
    prompt = fields.TextField(null=True, description="逐镜头逆推的生视频提示词")
    status = fields.CharField(max_length=20, default="pending", description="镜头生成状态:pending/processing/success/failed")
    result_url = fields.TextField(null=True, description="该镜头生成结果媒体地址")
    qc_score = fields.IntField(null=True, description="逐镜头质检分数(0-100,越低越差)")
    qc_low = fields.BooleanField(default=False, description="是否低分镜头(需人工核对/重跑)")
    qc_note = fields.TextField(null=True, description="质检结论说明")

    class Meta:
        table = "tb_shot"
        table_description = "镜头表"
