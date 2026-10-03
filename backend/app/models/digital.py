# -*- coding: utf-8 -*-
'''
@文件    :digital.py
@说明    :数字人模型
@时间    :2026/09/18 12:00:00
@作者    :一源AI
@版本    :1.0
'''
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class DigitalHumanModel(BaseModel, TimestampMixin):
    """数字人表"""
    name = fields.CharField(max_length=50, description="数字人名称")
    avatar = fields.CharField(max_length=255, null=True, description="头像")
    gender = fields.CharField(max_length=10, default="女", description="性别")
    style = fields.CharField(max_length=50, null=True, description="风格")
    desc = fields.TextField(null=True, description="简介")
    tags = fields.JSONField(default=list, description="标签")
    preview_video = fields.CharField(max_length=255, null=True, description="预览视频")
    # ===== 口播生成所需字段(数字人形象 + 音色 + 模型) =====
    image = fields.CharField(max_length=255, null=True, description="形象图(口型驱动底图,留空回退 avatar)")
    voice = fields.CharField(max_length=100, null=True, description="音色(TTS voice,留空用网关默认音色)")
    # 声纹复用(voice-casting):一段约 5s 的试音音频地址,绑定到本数字人;
    # 同一数字人跨任务/跨镜头都复用同一声纹(而不是每次用 TTS voice 字符串重新合成),
    # 实现"表演角色"与"画面呈现"解耦 —— 出镜表演与纯音频旁白是同一声纹的两种用法。
    voice_reference = fields.CharField(max_length=512, null=True, description="声纹样本音频地址(可复用声纹,优先级高于 voice)")
    model = fields.CharField(max_length=100, null=True, description="生成模型(留空用全局配置 gen.digital_model)")
    default_text = fields.TextField(null=True, description="默认口播文案(用户未填写时使用)")
    # 主视图派生:同一形象的多个姿势/景别视图,生成时以主图 image 为 reference,
    # 解决「换个姿势就变脸」—— 派生视图只换姿势,不换人
    pose_variants = fields.JSONField(default=list, description="派生视图[{name,image}]")
    sort = fields.IntField(default=0, description="排序")
    active = fields.BooleanField(default=True, description="是否上架")
    # 专属数字人归属:平台数字人 user_id 为空;用户自助上传形象生成的专属数字人绑定到对应用户,
    # 仅本人可在口播任务中使用(防越权),便于做"自己的脸对口型"的个人 IP 场景。
    user_id = fields.IntField(null=True, description="归属用户(专属数字人);空表示平台数字人")

    class Meta:
        table = "tb_digital_human"
        table_description = "数字人表"
