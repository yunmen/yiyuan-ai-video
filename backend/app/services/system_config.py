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
    {"key": "gen.chat_model", "value": "glm-4-flash-260828", "remark": "prompt 改写对话模型(需与 gen.route.chat 指向的网关支持的模型一致)"},
    {"key": "gen.vision_model", "value": "doubao-seed-2-1-lite-260915", "remark": "视觉(多模态)模型:把参考视频画面喂给模型写文案;留空=纯文本。默认 doubao-seed-2-1-lite-260915(方舟直调模型名,需支持 image_url 多模态输入;按网关实际支持调整)"},
    {"key": "gen.route.vision", "value": "", "remark": "视觉模型走哪个网关名(空=回退 gen.route.chat 的网关)", "is_public": False},
    {"key": "gen.video_model_t2v", "value": "doubao-seedance-2-0-fast-260128", "remark": "文生视频模型(Seedance 2.x)"},
    {"key": "gen.video_model_i2v", "value": "doubao-seedance-2-0-fast-260128", "remark": "图生视频模型(Seedance 2.x)"},
    {"key": "gen.video_model_r2v", "value": "doubao-seedance-2-0-fast-260128", "remark": "参考生视频模型(Seedance 2.x)"},
    {"key": "gen.video_model_edit", "value": "doubao-seedance-2-5-260628", "remark": "视频编辑模型(参考视频+商品图+新台词);留空则不启用视频编辑,走 r2v。方舟模型名须带 doubao- 前缀、短横分隔(如 doubao-seedance-2-5-260628),请按网关实际开通的模型名核对/在管理端调整"},
    {"key": "gen.video_durations", "value": "5,10", "remark": "视频时长档位(秒):只认固定档的模型填 5,10;支持连续时长的模型(如 Seedance 2.x 支持 4-15s)填 4-15"},
    {"key": "gen.video_ratio", "value": "9:16", "remark": "视频画幅"},
    {"key": "gen.replicate_follow_reference_ratio", "value": "0", "remark": "复刻时成片画幅是否跟随参考视频(1=跟随,不强制裁切;0=按系统画幅裁切)"},
    {"key": "gen.video_resolution", "value": "1080P", "remark": "视频清晰度"},
    {"key": "gen.video_edit_max_seconds", "value": "30", "remark": "视频编辑(复刻)参考视频时长上限(秒):方舟编辑任务实测 4~30s,超过直接 400;按模型真实上限调整,避免走失败降级"},
    {"key": "gen.video_resolution_cap", "value": "seedance-2:720p", "remark": "各编辑/参考生视频模型清晰度上限(模型名子串:档位,分号分隔,如 seedance-2:720p);换支持1080P的模型时放开,否则成片被压720p", "is_public": False},
    {"key": "gen.reference_short_side", "value": "720", "remark": "参考视频(视频编辑输入)输出短边像素:默认 720;换到支持 1080P 的编辑模型后填 1080,否则上传原片会被压到 720p"},
    {"key": "gen.image_real_person_mode", "value": "drop", "remark": "参考图含真人时的处理方式:drop=丢弃该图改按文字描述生成(默认);stylize=先用图生图拟态化再提交(输出非本人形象)"},
    {"key": "gen.shot_scene_threshold", "value": "0.3", "remark": "镜头切分(参考视频解析)场景变化阈值(0~1):越大越不易切镜;碎剪素材可调高、长镜头可调低,非法值回退 0.3", "is_public": False},
    {"key": "gen.asr_model", "value": "whisper-1", "remark": "语音识别(ASR)模型:词级时间戳对齐字幕;留空=只用成片音轨停顿做句子级对齐。默认 whisper-1(需网关支持 transcriptions 接口,按网关实际支持调整)"},
    {"key": "gen.subtitle_word_level", "value": "1", "remark": "字幕是否优先词级对齐(1=优先,需 gen.asr_model;0=只用句子级停顿对齐)"},
    {"key": "gen.text_model", "value": "qwen3.7-max", "remark": "文本生成模型"},
    {"key": "gen.image_model", "value": "doubao-seedream-6-0-pro-260828", "remark": "图片生成(文生图)模型"},
    {"key": "gen.image_model_edit", "value": "", "remark": "图片编辑(图生图)模型,留空复用文生图"},
    {"key": "gen.image_ratio", "value": "1:1", "remark": "图片默认画幅"},
    {"key": "gen.audio_model", "value": "qwen-audio-3.0-tts-plus", "remark": "语音合成模型"},
    {"key": "gen.music_model", "value": "fun-music-v1", "remark": "背景音乐生成模型"},
    # 数字人口播:形象图 + 口播音频 → 口型驱动视频;留空表示未接入该能力(任务会以明确原因失败)
    {"key": "gen.digital_model", "value": "", "remark": "数字人口播模型(留空=未接入,数字人任务不可用)"},
    {"key": "gen.video_price", "value": "9.90", "remark": "单次视频生成价格(元)"},
    {"key": "gen.daily_free_credits", "value": "3", "remark": "每日免费额度(次,0点重置)"},
    # 预算前置:各任务类型单次消耗额度(次),留空用代码默认值(均为 1)
    {"key": "gen.cost.video", "value": "1", "remark": "视频生成消耗额度(次)"},
    {"key": "gen.cost.image", "value": "1", "remark": "图片生成消耗额度(次)"},
    {"key": "gen.cost.audio", "value": "1", "remark": "音频生成消耗额度(次)"},
    {"key": "gen.cost.text", "value": "1", "remark": "文本生成消耗额度(次)"},
    {"key": "gen.cost.digital", "value": "1", "remark": "数字人口播消耗额度(次)"},
    # 附加项(0=不加价,与历史行为一致;大于 0 时才在预估与实扣中累加)
    {"key": "gen.cost.duration_10", "value": "0", "remark": "10 秒档额外消耗额度(0=不加价)"},
    {"key": "gen.cost.resolution_1080p", "value": "0", "remark": "1080P 额外消耗额度(0=不加价)"},
    {"key": "gen.cost.image_extra", "value": "0", "remark": "每多生成 1 张图的额外消耗额度(0=不加价)"},
    # P2 资产缓存(跨任务复用中间产物,直接降本)
    {"key": "gen.cache.enabled", "value": "1", "remark": "启用中间产物缓存(1=启用,0=关闭)"},
    {"key": "gen.cache.ttl_days", "value": "7", "remark": "中间产物缓存天数(0=不过期)"},
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
    # 指定路由:gen.route.<能力> = <名字>(能力:chat/text/image/video/video_edit/audio/music/digital/asr)
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
    {"key": "gen.route.video_edit", "value": "", "remark": "视频编辑(参考视频→新片)走哪个网关名(空=跟随 gen.route.video)", "is_public": False},
    {"key": "gen.route.audio", "value": "", "remark": "语音合成 走哪个网关名(空=回退音频/媒体网关)", "is_public": False},
    {"key": "gen.route.music", "value": "", "remark": "背景音乐 走哪个网关名(空=回退音频/媒体网关)", "is_public": False},
    {"key": "gen.route.digital", "value": "", "remark": "数字人口播 走哪个网关名(空=回退媒体网关)", "is_public": False},
    # AI 抠像(视频换场景保留真人):专用网关,必须由 gen.route.matting 显式指向某个 gen.gw.<name>;
    # 未配置时 render 的换场景路线自动降级为绿幕色键(chromakey),保证「没接 AI 抠像也能出片」。
    {"key": "gen.route.matting", "value": "", "remark": "AI 抠像(视频换场景保留真人)走哪个网关名(空=未接入,换场景降级绿幕色键)", "is_public": False},
    {"key": "gen.gw.matting.url", "value": "", "remark": "网关[抠像]地址,如 https://xx/v1", "is_public": False},
    {"key": "gen.gw.matting.key", "value": "", "remark": "网关[抠像]密钥", "is_public": False},
    {"key": "gen.gw.matting.proto", "value": "", "remark": "网关[抠像]协议:openai|ark(空=自动)", "is_public": False},
    # ASR 词级对齐路由:指向支持 /v1/audio/transcriptions(含 timestamp_granularities=["word"]) 的网关;
    # 留空则回退音频网关链(AUDIO_LLM_*→LLM_BASE_*→CHAT_LLM_*)。多数 TTS 专属网关(如火山方舟)不提供该端点,
    # 推荐单独定义 gen.gw.<名字>.* 后在此指向它,与 TTS 网关解耦。需配合 gen.asr_model 设置转写模型名。
    {"key": "gen.route.asr", "value": "", "remark": "语音识别(ASR)走哪个网关名(空=回退音频/媒体网关;推荐单独指向支持 transcriptions 的网关)", "is_public": False},
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
        if obj:
            # 仅更新请求显式传入的字段(exclude_unset):
            # 否则 UpsertSchema 的默认值(is_public=True / group="gen" / remark="")会覆盖库中真实的私密配置,
            # 导致网关密钥被翻成公开并经免登录接口泄漏给任意用户。前端编辑弹窗虽会回传全部字段,
            # 但此处兜底,避免直接调接口或前端改动时遗漏 is_public 而酿成越权泄露。
            data = payload.model_dump(exclude_unset=True)
            # 私密配置列表中被打码为 MASK,前端编辑弹窗会原样回填;若值仍为占位符说明未改动 → 保留库中原密钥,
            # 防止"只改说明/懒改值"把真实密钥覆盖成 ******。
            if data.get("value") == MASK:
                data["value"] = obj.value or ""
            await crud.model.filter(id=obj.id).update(**data)
            obj = await crud.get_by_key(payload.key)
        else:
            data = payload.model_dump()
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
