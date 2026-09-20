# -*- coding: utf-8 -*-
'''
@文件    :system_config.py
@说明    :系统业务配置Service(模型/画幅/定价等,admin 可改,worker 热更新拉取)
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
from typing import Dict, List, Tuple
from tortoise.expressions import Q
from app.cruds.system_config import crud
from app.schemas.system_config import QuerySchema, UpsertSchema

# 私密配置(is_public=False)在列表中的打码占位符;upsert 收到该占位符视为"未改动",保留库中原值,
# 避免管理员编辑说明/未改密钥时把密钥覆盖成占位符。
MASK = "******"

# 默认配置(首次启动播种,之后以数据库为准)
DEFAULT_CONFIGS: List[Dict] = [
    {"key": "gen.chat_model", "value": "qwen3.7-max", "remark": "prompt 改写对话模型"},
    {"key": "gen.video_model_t2v", "value": "happyhorse-1.1-t2v", "remark": "文生视频模型"},
    {"key": "gen.video_model_i2v", "value": "happyhorse-1.1-i2v", "remark": "图生视频模型"},
    {"key": "gen.video_model_r2v", "value": "happyhorse-1.1-r2v", "remark": "参考生视频模型"},
    {"key": "gen.video_ratio", "value": "9:16", "remark": "视频画幅"},
    {"key": "gen.video_resolution", "value": "1080P", "remark": "视频清晰度"},
    {"key": "gen.text_model", "value": "qwen3.7-max", "remark": "文本生成模型"},
    {"key": "gen.image_model", "value": "qwen-image-2.0", "remark": "图片生成(文生图)模型"},
    {"key": "gen.image_model_edit", "value": "", "remark": "图片编辑(图生图)模型,留空复用文生图"},
    {"key": "gen.image_ratio", "value": "1:1", "remark": "图片默认画幅"},
    {"key": "gen.audio_model", "value": "qwen-audio-3.0-tts-plus", "remark": "语音合成模型"},
    {"key": "gen.music_model", "value": "fun-music-v1", "remark": "背景音乐生成模型"},
    {"key": "gen.video_price", "value": "9.90", "remark": "单次视频生成价格(元)"},
    {"key": "gen.daily_free_credits", "value": "3", "remark": "每日免费额度(次,0点重置)"},
    {"key": "sign.daily_credits", "value": "1", "remark": "每日签到赠送额度(次,0=关闭签到)"},
    # 主网关(敏感,不下发用户端):backend 文案润色 + worker prompt 改写(chat)走此网关(A);
    # 为空时回退 env。双网关模式下与 worker 视频专用网关(B)分离。
    {"key": "gen.llm_base_url", "value": "", "remark": "主网关地址(backend 文案润色 + worker prompt 改写,空则回退 env)", "is_public": False},
    {"key": "gen.llm_api_key", "value": "", "remark": "主网关 Key(backend 文案润色 + worker prompt 改写,空则回退 env)", "is_public": False},
    # Worker 视频专用网关(B):生视频用;留空回退主网关 gen.llm_*;实现"润色走 A 中转站、生视频走 B 中转站"
    {"key": "gen.worker_llm_base_url", "value": "", "remark": "Worker 视频专用网关地址(生视频用,留空回退 gen.llm_base_url)", "is_public": False},
    {"key": "gen.worker_llm_api_key", "value": "", "remark": "Worker 视频专用网关密钥(生视频用,留空回退 gen.llm_api_key)", "is_public": False},
    # 音频专用网关:火山方舟无 /audio 接口,语音/音乐需独立网关(如支持 /audio 的 OpenAI 兼容中转站);留空回退媒体网关
    {"key": "gen.audio_llm_base_url", "value": "", "remark": "音频专用网关地址(语音/音乐;方舟无 /audio,留空回退媒体网关)", "is_public": False},
    {"key": "gen.audio_llm_api_key", "value": "", "remark": "音频专用网关密钥(留空回退媒体网关)", "is_public": False},
    # ================= 灵活网关:命名网关 + 能力路由 =================
    # 定义网关:gen.gw.<名字>.url / .key / .proto(openai|ark,空=按URL自动判断)
    # 指定路由:gen.route.<能力> = <名字>(能力:chat/text/image/video/audio/music)
    # 未配置 route 时回退上面的固定槽位(gen.llm_*/worker_llm_*/audio_llm_*),向后兼容。
    {"key": "gen.gw.deepseek.url", "value": "", "remark": "网关[deepseek]地址,如 https://api.deepseek.com", "is_public": False},
    {"key": "gen.gw.deepseek.key", "value": "", "remark": "网关[deepseek]密钥", "is_public": False},
    {"key": "gen.gw.deepseek.proto", "value": "", "remark": "网关[deepseek]协议:openai|ark(空=自动)", "is_public": False},
    {"key": "gen.gw.ark.url", "value": "", "remark": "网关[ark/火山方舟]地址,如 https://ark.cn-beijing.volces.com/api/v3", "is_public": False},
    {"key": "gen.gw.ark.key", "value": "", "remark": "网关[ark]密钥", "is_public": False},
    {"key": "gen.gw.ark.proto", "value": "", "remark": "网关[ark]协议:openai|ark(火山原生填 ark)", "is_public": False},
    {"key": "gen.gw.ali.url", "value": "", "remark": "网关[ali/阿里百炼]地址,如 https://dashscope.aliyuncs.com/compatible-mode/v1", "is_public": False},
    {"key": "gen.gw.ali.key", "value": "", "remark": "网关[ali]密钥", "is_public": False},
    {"key": "gen.gw.ali.proto", "value": "", "remark": "网关[ali]协议:openai|ark(空=自动)", "is_public": False},
    {"key": "gen.gw.relay.url", "value": "", "remark": "网关[relay/中转站]地址,如 https://xx/v1", "is_public": False},
    {"key": "gen.gw.relay.key", "value": "", "remark": "网关[relay/中转站]密钥", "is_public": False},
    {"key": "gen.gw.relay.proto", "value": "", "remark": "网关[relay]协议:openai|ark(空=自动)", "is_public": False},
    {"key": "gen.route.chat", "value": "", "remark": "文案润色/prompt改写 走哪个网关名(空=回退主网关)", "is_public": False},
    {"key": "gen.route.text", "value": "", "remark": "文本生成 走哪个网关名(空=回退主网关)", "is_public": False},
    {"key": "gen.route.image", "value": "", "remark": "图片生成 走哪个网关名(空=回退媒体网关)", "is_public": False},
    {"key": "gen.route.video", "value": "", "remark": "视频生成 走哪个网关名(空=回退媒体网关)", "is_public": False},
    {"key": "gen.route.audio", "value": "", "remark": "语音合成 走哪个网关名(空=回退音频/媒体网关)", "is_public": False},
    {"key": "gen.route.music", "value": "", "remark": "背景音乐 走哪个网关名(空=回退音频/媒体网关)", "is_public": False},
]


class Service:
    async def init_config_data(self) -> None:
        """启动播种:缺失的默认配置自动补齐"""
        for item in DEFAULT_CONFIGS:
            obj = await crud.get_by_key(item["key"])
            if not obj:
                await crud.create({**item, "group": "gen", "is_public": item.get("is_public", True)})

    async def list(self, payload: QuerySchema) -> Tuple[int, List[Dict]]:
        q = Q()
        if payload.keyword:
            q &= Q(key__contains=payload.keyword) | Q(remark__contains=payload.keyword)
        if payload.group:
            q &= Q(group=payload.group)
        total = await crud.model.filter(q).count()
        rows = await crud.model.filter(q).order_by("group", "key").offset(
            (payload.pageNum - 1) * payload.pageSize
        ).limit(payload.pageSize).all()
        # 敏感配置(is_public=False,如 LLM API Key)在列表里打码,避免明文入库/入操作日志
        result = []
        for r in rows:
            item = r.to_dict()
            if not item.get("is_public", True) and item.get("value"):
                item["value"] = MASK
                item["masked"] = True
            result.append(item)
        return total, result

    async def upsert(self, payload: UpsertSchema) -> Dict:
        obj = await crud.get_by_key(payload.key)
        data = payload.model_dump()
        # 私密配置列表中被打码为 MASK,前端编辑弹窗会原样回填;若值仍为占位符说明未改动 → 保留库中原密钥,
        # 防止"只改说明/懒改值"把真实密钥覆盖成 ******。
        if obj and data.get("value") == MASK:
            data["value"] = obj.value or ""
        if obj:
            await crud.model.filter(id=obj.id).update(**data)
            obj = await crud.get_by_key(payload.key)
        else:
            obj = await crud.create(data)
        return obj.to_dict()

    async def get_public_map(self) -> Dict[str, str]:
        """公开配置(免登录可读;敏感配置 is_public=False 不下发)"""
        rows = await crud.model.filter(is_public=True).all()
        return {r.key: r.value for r in rows}

    async def get_full_map(self) -> Dict[str, str]:
        """全量配置(含敏感网关密钥),仅限 worker 经 X-Worker-Token 鉴权后拉取,用于网关热更新"""
        rows = await crud.model.all()
        return {r.key: r.value for r in rows}


service = Service()
