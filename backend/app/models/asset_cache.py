# -*- coding: utf-8 -*-
'''
@文件    :asset_cache.py
@说明    :生成资产缓存(P2)— 跨任务复用中间产物,直接降本
@时间    :2026/09/21 10:00:00
@作者    :一源AI
@版本    :1.0
@说明    :checkpoint 只解决「同一任务断点续跑」,重跑/换主播时依然会重新调用付费接口。
          这里按**内容哈希**键控(而非任务 id),同一份输入在 TTL 内只调一次真实接口:
          换主播重跑时口播文案没变 → TTS 音频直接命中;换文案重跑时 prompt 改写结果
          若上下文未变同样命中。表随 generate_schemas 自动创建。
'''
from tortoise import fields

from app.models.base import BaseModel, TimestampMixin


class GenAssetCacheModel(BaseModel, TimestampMixin):
    """生成中间产物缓存:键为输入内容哈希,值为可复用的产物(URL / 文本)"""

    cache_key = fields.CharField(max_length=64, unique=True, description="缓存键(输入内容哈希)")
    asset_type = fields.CharField(max_length=32, index=True, description="产物类型:tts_audio/optimized_prompt")
    task_type = fields.CharField(max_length=32, default="", description="任务类型,便于按类型清理")
    content = fields.TextField(description="产物内容(URL 或文本)")
    meta = fields.JSONField(default=dict, description="附加信息(模型/音色等,便于排查)")
    hit_count = fields.IntField(default=0, description="命中次数(用于验证降本效果)")
    expire_time = fields.DatetimeField(null=True, description="过期时间(为空表示不过期)")

    class Meta:
        table = "tb_gen_asset_cache"
        table_description = "生成中间产物缓存(P2 资产复用)"
