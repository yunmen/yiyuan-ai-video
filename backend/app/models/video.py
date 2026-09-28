# -*- coding: utf-8 -*-
'''
@文件    :video.py
@说明    :视频模板与生成任务模型
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class VideoCategoryModel(BaseModel, TimestampMixin):
    """视频模板分类表(后台维护,模板表 category 字段引用其名称)"""
    name = fields.CharField(max_length=50, unique=True, description="分类名称")
    cover = fields.CharField(max_length=255, null=True, description="分类图标/封面")
    sort = fields.IntField(default=0, description="排序(倒序,越大越靠前)")
    active = fields.BooleanField(default=True, description="是否启用")
    remark = fields.CharField(max_length=255, default="", description="备注")

    class Meta:
        table = "tb_video_category"
        table_description = "视频模板分类表"


class VideoTemplateModel(BaseModel, TimestampMixin):
    """视频模板表"""
    title = fields.CharField(max_length=100, description="模板标题")
    category = fields.CharField(max_length=50, description="模板分类")
    cover = fields.CharField(max_length=255, null=True, description="封面图")
    video_url = fields.CharField(max_length=255, null=True, description="示例视频地址")
    duration = fields.IntField(default=10, description="视频时长(秒)")
    hot = fields.IntField(default=0, description="热度值")
    use_count = fields.IntField(default=0, description="使用次数")
    desc = fields.TextField(null=True, description="模板描述")
    tags = fields.JSONField(default=list, description="标签")
    example_images = fields.JSONField(default=list, description="示例图")
    default_text = fields.JSONField(default=dict, description="默认文案(大标题/副标题/口播)")
    # 画面构成三段式(person 主体 / shot 镜头 / setting 场景):运营换场景不必重写整段 prompt
    prompt_parts = fields.JSONField(default=dict, description="画面构成(主体/镜头/场景)")
    recommend = fields.BooleanField(default=False, description="是否首页推荐")
    recommend_sort = fields.IntField(default=0, description="推荐位排序(倒序)")
    sort = fields.IntField(default=0, description="排序")
    active = fields.BooleanField(default=True, description="是否上架")

    class Meta:
        table = "tb_video_template"
        table_description = "视频模板表"


class GenerateTaskModel(BaseModel, TimestampMixin):
    """视频生成任务表"""
    task_no = fields.CharField(max_length=32, unique=True, description="任务编号")
    type = fields.CharField(max_length=20, default="video", description="任务类型:video/image/audio/text/digital")
    status = fields.CharField(max_length=20, default="processing", description="任务状态")
    progress = fields.IntField(default=0, description="进度百分比")
    template = fields.ForeignKeyField("models.VideoTemplateModel", related_name="tasks", null=True, db_constraint=False, description="模板")
    materials = fields.JSONField(default=list, description="用户上传素材")
    params = fields.JSONField(null=True, description="生成参数(用于重新生成)")
    checkpoint = fields.JSONField(null=True, description="断点续跑检查点(stage + 各阶段中间产物)")
    remark = fields.TextField(null=True, description="备注")
    # 注意:成片地址可能是视频模型返回的临时直链(带签名,常 > 512 字符)。
    # 早期用 CharField(512),当 OSS 未启用/转存失败时回退直链会撑爆列宽 → 落库报
    # Data too long → backend 500 → worker notify 失败 → 任务永久卡 processing。
    # 改用 TextField 以容纳任意长度的成片地址。
    result_video = fields.TextField(null=True, description="生成结果媒体地址(视频/图片/音频)")
    result_text = fields.TextField(null=True, description="文本类结果")
    fail_reason = fields.CharField(max_length=255, null=True, description="失败原因")
    usage = fields.JSONField(null=True, description="用量与消耗(计费,worker 回调回写)")
    device = fields.CharField(max_length=20, default="desktop", description="设备类型")
    user_id = fields.BigIntField(null=True, description="关联用户Id")
    order_no = fields.CharField(max_length=64, null=True, index=True, description="关联支付订单号(付费任务)")

    class Meta:
        table = "tb_generate_task"
        table_description = "视频生成任务表"
