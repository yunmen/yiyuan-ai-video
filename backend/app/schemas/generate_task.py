# -*- coding: utf-8 -*-
'''
@文件    :generate_task.py
@说明    :生成任务Schema
@时间    :2026/09/17 20:00:00
@作者    :一源AI
@版本    :1.0
'''
from pydantic import Field, BaseModel, field_validator, model_validator
from typing import Optional, List, Dict, Any

# 复刻目标形态白名单校验(纯函数,无外部依赖,不会造成循环导入)
from app.services.gen_rules import normalize_replicate_format


class ClassifyImagesSchema(BaseModel):
    # 上传后逐张识别参考图角色(人物/产品/场景):前端把刚上传的图地址发来,后端委托 worker 视觉识别。
    # 仅做增强(预标),任何失败该张返回空角色,绝不影响上传与后续建单。
    urls: List[str] = Field(..., description="待识别的参考图地址列表(可多张)", min_length=1, max_length=9)


class DetectElementsSchema(BaseModel):
    # 原片元素槽位检测(换元素复刻增强):给定对标视频,由 worker 视觉识别原片里可替换的
    # 人物/产品/场景,返回可绑定槽位。仅做增强,失败返回空列表,绝不阻断复刻。
    reference_video: str = Field(..., description="对标视频地址,用于检测原片可替换元素")


class ElementPositionSchema(BaseModel):
    """单帧归一化位置；坐标必须正向且位于画面内。"""

    bbox: Optional[List[float]] = Field(None, min_length=4, max_length=4, description="归一化包围盒")

    @model_validator(mode="after")
    def validate_bbox(self):
        """拒绝反向、非有限或越界的包围盒。"""
        if self.bbox is not None:
            x1, y1, x2, y2 = self.bbox
            if not all(0 <= value <= 1 for value in self.bbox) or x1 >= x2 or y1 >= y2:
                raise ValueError("元素位置必须是画面内的正向包围盒")
        return self


class ElementObservationSchema(ElementPositionSchema):
    """抽帧中确认可见的记录，不代表镜头内持续出现。"""

    time: float = Field(..., ge=0, allow_inf_nan=False, description="原片观测帧秒数")
    shot_index: Optional[int] = Field(None, ge=0, description="检测镜头序号，仅供定位")
    shot_start: Optional[float] = Field(None, ge=0, allow_inf_nan=False, description="镜头起点秒")
    shot_end: Optional[float] = Field(None, ge=0, allow_inf_nan=False, description="镜头终点秒")

    @model_validator(mode="after")
    def validate_shot(self):
        """镜头上下文须完整且包含观测点。"""
        fields = (self.shot_index, self.shot_start, self.shot_end)
        if any(value is not None for value in fields):
            if any(value is None for value in fields) or not self.shot_start <= self.time < self.shot_end:
                raise ValueError("元素观测时间必须位于完整镜头范围内")
        return self


class ReferenceElementSchema(ElementPositionSchema):
    """原片元素定位信息；时间范围是识别估计值，不代表逐帧跟踪结果。"""

    id: str = Field(..., min_length=1, max_length=64, description="原片元素唯一标识")
    kind: str = Field(..., pattern="^(person|product|scene)$", description="元素类型")
    label: str = Field(..., min_length=1, max_length=200, description="原片元素描述")
    observations: List[ElementObservationSchema] = Field(default_factory=list, max_length=12, description="多次可见帧及对应镜头，非连续出现区间")
    time: Optional[float] = Field(None, ge=0, allow_inf_nan=False, description="代表帧时间秒，不能当作完整区间")
    start: Optional[float] = Field(None, ge=0, allow_inf_nan=False, description="估计出现起点秒")
    end: Optional[float] = Field(None, ge=0, allow_inf_nan=False, description="估计出现终点秒")

    @model_validator(mode="after")
    def validate_span(self):
        """估计跨度必须成对且正向提供，缺失则保留为未知。"""
        if (self.start is None) != (self.end is None):
            raise ValueError("元素时间范围必须同时提供起点和终点")
        if self.start is not None and self.end <= self.start:
            raise ValueError("元素时间终点必须大于起点")
        return self


class CreateSchema(BaseModel):
    # 模板 Id 可选:普通生成(选平台模板)必传;视频复刻链路用户自带对标视频时无需传模板。
    # 服务层对「传了但无效」的模板仍按原规则报错,仅放开「不传」这一情形。
    template_id: Optional[int] = Field(None, description="模板Id(普通生成必传;视频复刻可不传)")
    materials: List[str] = Field(..., description="素材地址列表", min_length=1, max_length=9)
    # 逐镜出片(九宫格链路):materials 为 N 张分镜图时,每张独立生成一段视频再拼接。
    # 为什么需要显式开关:历史行为是「多图 → r2v(参考图生视频)」,不能因新增分支改变老任务语义,
    # 因此只有前端显式声明 per_shot 才走逐镜链路。
    shot_mode: Optional[str] = Field(
        None, description="逐镜出片模式:per_shot=每张分镜图独立成段再拼接;不传沿用原链路",
    )
    # 逐镜提示词(可选):与 materials 一一对应,描述该镜头的画面/运镜;
    # 缺失时各段复用整体 prompt(仍按各自首帧生成)。
    shot_prompts: Optional[List[str]] = Field(
        None, description="逐镜提示词(与 materials 一一对应),用于每段各自生成",
    )
    # 每段时长(秒,可选):不传由 worker 按模型档位取默认。
    per_shot_seconds: Optional[int] = Field(None, ge=3, le=15, description="逐镜每段时长(秒)")
    # 代码渲染层·信息卡(可选,对齐 Hypit lower-thirds):提供则在成片叠加"下三分之一"信息卡。
    # 仅当显式提供才叠加,绝不臆造商品信息;缺省不影响出片。
    overlay_card: Optional[Dict[str, Any]] = Field(
        None,
        description="可选信息卡(代码渲染层):{title(标题),body(正文),corner(bl/br/tl/tr,默认bl),"
                    "margin(边距px,默认40)};仅显式提供才叠加,不臆造商品信息",
    )
    # 代码渲染层·角标(可选,对齐 Hypit badge):提供则在成片角落叠加胶囊标签(品牌/卖点/水印)。
    overlay_badge: Optional[Dict[str, Any]] = Field(
        None,
        description="可选角标(代码渲染层):{text(标签文字),corner(tr/br/tl/bl,默认tr),margin(边距px,默认36)}",
    )
    # 代码渲染层·动效信息层(对齐 Hypit 动效组件):以下四类均仅显式提供才叠加,绝不臆造。
    overlay_ranking: Optional[Dict[str, Any]] = Field(
        None,
        description="可选排行榜(代码渲染层):{title,items:[{label,value}],corner(bl/br/tl/tr,默认bl),"
                    "start_ms(首条出现ms),stagger_ms(逐条错峰ms,默认500),end_ms(整块结束ms,默认到结尾)}",
    )
    overlay_reveal: Optional[Dict[str, Any]] = Field(
        None,
        description="可选揭示板(代码渲染层):{text,emoji(默认✨),at_ms(出现ms),duration_ms(停留ms,默认1800),corner(默认br),"
                    "ref(可选词锚点如moment:reveal,未显式给 at_ms 时按其真实秒回填)}",
    )
    overlay_flash: Optional[Dict[str, Any]] = Field(
        None,
        description="可选彩色闪烁(代码渲染层):{color(#RRGGBB),at_ms(出现ms),duration_ms(时长ms,默认400),"
                    "ref(可选词锚点,未显式给 at_ms 时按其真实秒回填)}",
    )
    overlay_sticker: Optional[Dict[str, Any]] = Field(
        None,
        description="可选评论贴纸(代码渲染层):{text,side(l/r,默认l),at_ms(出现ms),duration_ms(停留ms,默认2500),"
                    "avatar_color(头像色,#RRGGBB,默认品牌绿),ref(可选词锚点,未显式给 at_ms 时按其真实秒回填)}",
    )
    # 自动 B-roll 增强层(对齐 Hypit B-roll 素材镜头承接):显式开启才生效,失败自动回退原片,绝不阻断出片。
    auto_broll: Optional[Dict[str, Any]] = Field(
        None,
        description="可选自动 B-roll(代码渲染层):{enabled(bool),source(goods/scene/URL/gen,默认用商品图;"
                    "gen=无素材时自动文生图产出 B-roll 素材),prompt(gen 用,描述生成画面,缺失用通用电商特写),"
                    "strategy(even 均匀插窗/mention 关键词命中句插窗/anchor 词锚点真实秒插窗,默认 even),"
                    "keywords(mention 用,如['小龙虾']),anchors(anchor 用,词锚点引用如['selection:product'],"
                    "改台词后时间轴自动重排),"
                    "interval(even 间隔秒,默认8),window(单窗秒,默认3),position(center/br/bl/tr/tl,默认center),"
                    "scale(默认1.0),fade(淡入淡出秒,默认0.3)}",
    )
    # 音效卡点(P3-5,可选):在词锚点/显式毫秒处把短音效叠进成片音轨;无真实素材不叠加,失败保留原片。
    sound_effects: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="可选音效卡点(代码渲染层):[{url(音效文件直链,必填),at_ms(出现毫秒,可选),"
                    "ref(可选词锚点如'moment:hook',未给 at_ms 时按其真实秒回填),volume(增益0~1,默认0.8)}];"
                    "无 url 或无时间码的项自动跳过,不阻断出片",
    )
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
    # 原片元素绑定(可选):换元素复刻时,用户把上传的替换图精确绑定到原片某个元素槽位
    # (槽位由 /detect-elements 给出)。键为素材图地址,值为元素槽位 id,
    # 用于让生成更精确地替换「对的那个人/物」,减少多人/多物视频的错位。
    image_slots: Optional[Dict[str, str]] = Field(
        None, description="素材图地址 → 原片元素槽位 id(换元素复刻增强,可选)",
    )
    reference_elements: Optional[List[ReferenceElementSchema]] = Field(
        None, max_length=30, description="原片人物、场景、产品定位描述，与 image_slots 联合使用",
    )

    @model_validator(mode="after")
    def validate_element_bindings(self):
        """新客户端提供元素表时校验引用完整性；旧客户端仅传槽位仍兼容。"""
        if self.reference_elements is None:
            return self
        elements = {element.id: element for element in self.reference_elements}
        if len(elements) != len(self.reference_elements):
            raise ValueError("原片元素标识不能重复")
        for url, slot in (self.image_slots or {}).items():
            if url not in self.materials or slot not in elements:
                raise ValueError("素材绑定必须引用已提交图片与原片元素")
            role = (self.image_roles or {}).get(url)
            if role and role != elements[slot].kind:
                raise ValueError("素材分类与绑定元素类型不一致")
        return self

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
    # 成片品牌水印/台标去除(可选,per-task 覆盖系统默认 gen.watermark_removal):
    # auto=自动检测后分级处理(贴边水印裁剪并缩放回原比例 + 画面内部水印 delogo 插值,默认);
    # crop=只裁剪;delogo=只插值修补;off=关闭。
    # 不传则沿用系统配置(默认开启);检测不到水印或处理失败均保留原片,不影响生成成功。
    remove_watermark: Optional[str] = Field(
        None, description="成片去品牌水印/台标:auto/crop/delogo/off;不传则用系统默认(开启)",
    )
    # 复刻目标形态(可选):决定成片的内容结构(短剧/口播/街采/…),
    # 对应 backend/skills/prompts/replicate/formats/ 下的形态资产。
    # 可选项由 gen_rules.REPLICATE_FORMAT_OPTIONS 单一来源定义,并经 /gen-config 的
    # replicate_formats 下发给前端 —— 描述里**不枚举**具体形态,避免新增形态时描述与白名单漂移。
    # 不传=不指定形态,复刻沿用原片结构(与历史行为一致);非法值归一化为不指定。
    format: Optional[str] = Field(
        None, description="复刻目标形态(可选项见 /gen-config 的 replicate_formats)",
    )
    # 主角表现(可选):仅在替换意图含 person(换人物)时生效,决定新主角以什么方式表演
    # (跟随原片/跳舞律动/推广种草)。可选项由 prompt_builder.LEAD_ACT_OPTIONS 单一来源定义,
    # 并经 /gen-config 的 lead_acts 下发给前端渲染。不传=跟随原片,行为与改造前一致;
    # 非法值由 build_gen_params 归一化为"不指定",不因此报错。
    lead_act: Optional[str] = Field(
        None, description="主角表现(可选项见 /gen-config 的 lead_acts),仅换人物时生效",
    )
    # 创意档位(可选):决定在原片骨架上"改写多少" —— 忠实复刻/轻度改写/爆款改写。
    # 可选项由 prompt_builder.CREATIVE_LEVEL_OPTIONS 单一来源定义,并经 /gen-config 的
    # replicate_creative_levels 下发给前端渲染。**不传 ≠ 忠实复刻**:不传保留改造前的
    # 全量方法论注入(老客户端/老任务重跑行为不变),显式传 faithful 才按新档位精简注入。
    # 非法值由 build_gen_params 归一化为"不指定",不因此报错。
    creative_level: Optional[str] = Field(
        None, description="创意档位(可选项见 /gen-config 的 replicate_creative_levels)",
    )
    # 开头钩子强化(可选):前 3 秒决定短视频留存,单独成档是为了不干扰
    # "完整照搬原片"的用户(不传时按创意档位联动兜底:忠实复刻取 off 不动开头,其余档位才取 strong,详见 gen_rules.resolve_hook_boost_default);可选项见 /gen-config 的 replicate_hook_boosts。
    hook_boost: Optional[str] = Field(
        None, description="开头钩子强化(normal/strong/off);不传时按创意档位联动兜底:忠实复刻=不动开头,其余档位=强化开头;显式传值优先",
    )
    # 提示词资产覆盖(专家模式,可选):用户为**本次任务**追加的创作要求片段,
    # 会被拼在 [创作要求] 段末尾(位置即优先级:排在档位资产之后)。
    # 长度上限在 Schema 层收口 —— 不限制会让用户把整篇外部文档塞进提示词,
    # 反而挤掉结构化约束,效果更差。
    asset_override: Optional[str] = Field(
        None, max_length=500, description="专家模式:本次任务追加的创作要求(≤500字)",
    )
    # 生成模式(可选):storyboard=九宫格分镜编排(9 张分镜图各自 i2v + 运镜 + 转场合成一条视频);
    # 不传=按素材数量自动选择 t2v/i2v/r2v。仅允许 storyboard,非法值归一化为 None(不指定)。
    gen_mode: Optional[str] = Field(
        None, description="生成模式(可选):storyboard=九宫格分镜编排;不传=按素材自动选择",
    )
    # 一句话目标(小白主入口):用户用自然语言描述"想要什么"(如"换成我的产品,做成口播")。
    # 与结构化旋钮的关系:goal 是**意图来源**,结构化字段是**已确定的取值**;
    # 两者都下发给 worker,worker 优先用结构化字段,goal 只在字段缺失时指导方案推断,
    # 避免"用户说了却没生效"与"用户没说却被擅自改写"两个极端。
    goal: Optional[str] = Field(
        None, max_length=200, description="一句话目标(选填):用自然语言描述想做成什么样",
    )
    # 逐镜头质检低分自动重跑(可选):默认 None = 沿用 worker 的 VIDEO_QC_AUTO_RETRY 配置。
    # 重跑会产生**新的模型费用**,因此全局默认关闭;这里只提供"按任务显式开启"的通道,
    # 由业务侧决定是否对小白链路开启,禁止在代码里静默改成默认开启。
    qc_auto_retry: Optional[bool] = Field(
        None, description="低分镜头自动重跑(会产生额外费用);不传=沿用 worker 配置",
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
        # 仅允许 8 种复刻目标形态;非法值归一化为 None(不指定形态),不因前端传错而报错
        return normalize_replicate_format(v) or None

    @field_validator("gen_mode")
    @classmethod
    def gen_mode_valid(cls, v):
        # 仅允许 storyboard;其余(含 None)统一归一化为 None,避免前端传错触发未知分支
        return "storyboard" if str(v or "").strip().lower() == "storyboard" else None


class PrecheckSchema(BaseModel):
    """建单前预检:检查素材是否齐全,返回**结构化缺失项**(而不是一段报错文案)

    面向"只上传素材"的小白:前端拿 missing 渲染"还缺什么、为什么、怎么补",
    用户看到的是可执行的一步操作,而不是"生成失败"后自己猜原因。
    不做扣额度、不做识别,纯校验,可随时调用。
    """

    materials: List[str] = Field(default_factory=list, description="素材地址列表(可含参考视频)")
    intent: Optional[List[str]] = Field(None, description="替换意图多选:product/person/scene")
    reference_video: Optional[str] = Field(None, description="对标视频地址(复刻链路显式传入)")
    # 图片角色标注(可选):{图片URL: 角色} 或 {URL: "person,product"} 多角色逗号拼接,
    # 用于预检时精确推断替换维度(与 CreateSchema.image_roles 同源,缺省则由视觉识别兜底)。
    image_roles: Optional[Dict[str, str]] = Field(None, description="图片角色标注(URL→角色),用于精确推断替换意图")
    # 对标视频真实时长(秒,可选):带上才能校验"视频是否太短"
    duration: Optional[float] = Field(None, ge=0, le=600, description="对标视频时长(秒,可选)")


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
    # 创意档位(可选):与 CreateSchema.creative_level 同源,同样必须与生成侧一致 ——
    # 拆解按"忠实复刻"理解原片、生成却按"爆款改写"出片,会让用户看到的分镜描述
    # 与实际成片对不上。拆解侧只把它透传给 worker 的逐镜头逆推做资产选择。
    creative_level: Optional[str] = Field(
        None, description="创意档位(与 CreateSchema.creative_level 一致)",
    )
    # 开头钩子强化(可选):与 CreateSchema.hook_boost 同源,拆解侧用于让首镜逆推
    # 直接产出"钩子式"画面描述,而不是等生成阶段再改。
    hook_boost: Optional[str] = Field(
        None, description="开头钩子强化(与 CreateSchema.hook_boost 一致)",
    )
    # 一句话目标(可选):与 CreateSchema.goal 同源。拆解侧带上它,是为了让「看懂原片」
    # 与「出片」按同一目标组织分镜描述,否则用户会看到分镜与成片口径不一致。
    goal: Optional[str] = Field(
        None, max_length=200, description="一句话目标(选填,与 CreateSchema.goal 一致)",
    )

    @field_validator("format")
    @classmethod
    def format_valid(cls, v):
        # 与 CreateSchema 同一白名单;非法值归一化为 None(不指定形态)
        return normalize_replicate_format(v) or None


class EstimateSchema(BaseModel):
    """下单前花费预估(预算前置:预估 → 预扣 → 结算返还)"""
    type: str = Field("video", description="任务类型:video/image/audio/text/digital")
    template_id: Optional[int] = Field(None, description="模板Id(视频任务,用于取时长档位)")
    num_images: int = Field(1, ge=1, le=9, description="图片生成数量(grid 九宫格模式可达 9)")
    # 逐镜出片预估(九宫格链路):分镜数与每段时长 → 总时长 = shot_count × per_shot_seconds
    shot_count: Optional[int] = Field(None, ge=1, le=9, description="逐镜出片的分镜张数")
    per_shot_seconds: Optional[int] = Field(None, ge=3, le=15, description="逐镜每段时长(秒)")
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
    # 结构化失败码(worker 回写):前端据此给可执行动作(换素材/去数字人/重试),
    # 不必从一段文案里猜怎么处理
    fail_code: Optional[str] = Field(None, max_length=64, description="结构化失败码(failed 时回传)")
    usage: Optional[Dict] = Field(None, description="用量与消耗(计费用,预留)")


class ImageCreateSchema(BaseModel):
    """图片生成任务创建参数(支持九宫格成片)

    三模式(均走 image 任务类型):
      - 普通图生图:prompt 必填,materials 可选(图生图);
      - 九宫格生成:prompt + grid="3x3" → 生成 9 张拼成网格图;
      - 九宫格纯拼合:materials(≥2 张,通常 9 张) + grid="3x3" 无 prompt → 直接拼合;
      - 九宫格分割:materials(恰好 1 张九宫格原图) + split=True → 拆成 9 张单图。
    """
    # 提示词:生成类(普通/九宫格生成)必填;split 分割 / grid 纯拼合可空
    prompt: Optional[str] = Field(None, description="画面描述(生成模式必填;split/纯拼合可空)", max_length=2000)
    ratio: str = Field("1:1", description="画幅:1:1/16:9/9:16/4:3/3:4")
    num_images: int = Field(1, ge=1, le=9, description="生成数量(grid 九宫格模式固定 9)")
    materials: List[str] = Field(default_factory=list, description="参考图(grid 纯拼合需 9 张;split 需 1 张九宫格原图)")
    intent: List[str] = Field(
        default_factory=list,
        description="复刻替换意图:product/person/scene;非空表示「按参考图复刻、换掉该元素」",
    )
    # 九宫格成片:grid=拼合规格(如 3x3,非空表示输出一张九宫格网格图);
    # split=True 表示"上传单张九宫格图 → 拆分为 9 张单图"。两者互斥。
    grid: Optional[str] = Field(None, description="网格拼合规格:3x3(九宫格);非空表示生成/拼合后输出一张网格图")
    split: bool = Field(False, description="分割模式:上传单张九宫格图拆分为 9 张单图(与 grid 互斥)")
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")

    @model_validator(mode="after")
    def _check_grid(self) -> "ImageCreateSchema":
        """九宫格成片三模式的参数校验(grid 与 split 互斥,分别对应拼合与分割)

        生成类(普通/九宫格生成)必须给提示词;split 必须恰好 1 张原图;
        grid 纯拼合需≥2 张图;grid 生成模式强制 num_images=9(吸附,与 gen_rules 一致)。
        """
        if self.split and self.grid:
            raise ValueError("grid 与 split 互斥,不能同时设置")
        if self.split:
            if len(self.materials) != 1:
                raise ValueError("分割模式需上传恰好 1 张九宫格图片")
            return self
        if self.grid:
            if not (self.prompt or "").strip() and len(self.materials) < 2:
                raise ValueError("九宫格拼合需提供提示词(生成)或至少 2 张图片(纯拼合)")
            # 九宫格固定 9 格,生成模式强制 9 张
            self.num_images = 9
        else:
            # 普通图生图:提示词必填
            if not (self.prompt or "").strip():
                raise ValueError("图片生成提示词不能为空")
        return self


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
    # 声纹复用(voice-casting):现成声纹样本音频地址;优先级高于 voice,使同一数字人跨任务声音一致
    voice_reference: Optional[str] = Field(None, description="声纹样本音频地址(可复用声纹,优先级高于 voice)")
    # 语速(0.5x–2.0x):TTS 合成语速,经音频网关 extra_body 透传;留空用网关默认语速
    speed: Optional[float] = Field(None, ge=0.5, le=2.0, description="语速(0.5x–2.0x,留空用网关默认语速)")
    # 方言:方言语义键(如 chuanyu/cantonese),经 worker 透传给 TTS 网关(extra_body + 可选指令模板);
    # 网关不支持则忽略。与口播文案解耦 —— 用户写「用重庆方言说」会被识别并转成该字段,不污染台词。
    dialect: Optional[str] = Field(None, max_length=30, description="方言语义键(如 chuanyu/cantonese;留空=普通话)")
    pose: Optional[str] = Field(None, description="派生视图名称(留空用主视图)")
    # 换动作(motion):数字人的动作/姿态意图(如「挥手介绍商品」),由 worker 放进网关自定义
    # 参数区 metadata.parameters.motion 透传;网关未支持该能力时自行忽略,留空由模型自行表演。
    motion: Optional[str] = Field(None, max_length=200, description="动作/姿态描述(透传数字人网关,留空由模型自行表演)")
    duration: int = Field(8, ge=3, le=15, description="单段成片时长(秒),口播时长以音频为准时该值仅作占位")
    ratio: Optional[str] = Field(None, description="画幅(9:16/16:9/1:1 等,留空用系统默认)")
    resolution: Optional[str] = Field(None, description="清晰度(720P/1080P,留空用系统默认)")
    background: Optional[str] = Field(None, description="背景/场景参考图地址(留空使用数字人默认场景)")
    # 带货模式:商品图地址;提供则作为数字人出镜的商品场景背景(主播立于商品场景中口播)。
    # 注:本栈图像工具仅单参考图,无法可靠合成「数字人手持真实商品」静帧,故商品图复用场景背景机制,
    # 升级为「人物+商品合成静帧」需多参考图图像模型/ComfyUI 工作流(参考 Pixelle digital_image.json)。
    goods: Optional[str] = Field(None, description="商品图地址(带货模式,作为数字人出镜场景背景)")
    # talking-head 进阶:多段脚本 —— 提供则逐段生成(每段一个镜头)后拼接成一条成片;
    # 段内 text/audio 二选一(或传 audio),duration 为该段时长(留空按字数估算)。
    segments: Optional[List[Dict[str, Any]]] = Field(None, description="多段口播:每段 {text?, audio?, duration?};提供则逐段生成后拼接")
    # 画中画(presenter-led-explainer):提供背景视频则把数字人成片缩成小窗叠到该背景之上
    overlay: Optional[str] = Field(None, description="画中画背景视频地址(提供则把数字人成片缩成小窗叠到背景上)")
    pip: Optional[Dict[str, Any]] = Field(
        None,
        description="画中画参数 {position:br/tl/..., scale:0.3, bg_volume:0~1(背景原声音量,0=静音)};"
                    "仅 overlay 存在时生效,缺省 bg_volume 用 worker 统一默认值 0.2",
    )
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")


class VideoReNarrateSchema(BaseModel):
    """视频换口播任务:上传视频 + 提示词 → 按所选变换重渲染(换声 / 换数字人 / 换场景 / 组合)

    路线由字段组合派生(互斥优先级):
      - 填 digital_id        → 数字人路线:生成数字人按提示词口播,合成到视频 A(或场景 B);
      - 未填但填 scene        → 换场景路线:把真人从 A 抠出贴到场景 B(需抠像);
      - 两者都不填            → 只换声音:保留真人画面,仅用提示词重新配音。
    """

    source_video: str = Field(..., description="源视频地址(用户上传的视频 A)")
    prompt: str = Field(..., min_length=1, max_length=2000, description="要口播的提示词/文案")
    # 数字人路线:填了走数字人,留空走换声/换场景
    digital_id: Optional[int] = Field(None, description="数字人Id(填了走数字人路线)")
    voice: Optional[str] = Field(None, description="音色(覆盖数字人默认音色;换声/数字人路线生效)")
    # 声纹复用:现成声纹样本音频地址,优先级高于 voice
    voice_reference: Optional[str] = Field(None, description="声纹样本音频地址(可复用声纹,优先级高于 voice)")
    # 语速(0.5x–2.0x):数字人/换声路线 TTS 合成语速,经音频网关 extra_body 透传;留空用网关默认
    speed: Optional[float] = Field(None, ge=0.5, le=2.0, description="语速(0.5x–2.0x,留空用网关默认语速)")
    # 方言:方言语义键(如 chuanyu/cantonese),与数字人路线一致经 worker 透传 TTS 网关
    dialect: Optional[str] = Field(None, max_length=30, description="方言语义键(如 chuanyu/cantonese;留空=普通话)")
    audio: Optional[str] = Field(None, description="口播音频地址(提供则直接使用,不再合成语音)")
    # 换场景路线必填;数字人路线作背景图/视频
    scene: Optional[str] = Field(None, description="目标场景 B 地址(换场景路线必填;数字人路线作背景)")
    # 预留:数字人路线透传给网关的动作/姿态描述(依赖网关能力)
    motion: Optional[str] = Field(None, description="动作/姿态描述(预留,数字人路线透传网关)")
    pose: Optional[str] = Field(None, description="数字人派生视图(留空用主视图)")
    duration: int = Field(8, ge=3, le=15, description="成片时长(秒),口播时长以音频为准时仅作占位")
    ratio: Optional[str] = Field(None, description="画幅(9:16/16:9/1:1 等,留空用系统默认)")
    resolution: Optional[str] = Field(None, description="清晰度(720P/1080P,留空用系统默认)")
    background: Optional[str] = Field(None, description="数字人背景/场景参考图(留空用数字人默认场景)")
    # 带货模式:商品图地址(数字人路线生效);作为数字人出镜商品场景背景,主播立于商品场景中口播
    goods: Optional[str] = Field(None, description="商品图地址(带货模式,数字人路线作为出镜场景背景)")
    # 可选 B-roll 素材层:讲解到商品时把素材叠到成片指定时间窗(对齐 Hypit 的 B-roll 承接/覆盖)
    broll: Optional[Dict] = Field(
        None,
        description="可选 B-roll 层:{asset(素材地址),start,end(秒),fade(淡入淡出,默认0.3),"
                    "scale(相对主视频宽比,默认1.0),position(center/br/bl/tr/tl,默认center),"
                    "type(image/video,默认image)}",
    )
    remark: Optional[str] = Field(None, description="备注")
    device: str = Field("desktop", description="设备类型")
    # 字幕跟随头部(caption-tracking,对齐 Hypit production/caption-tracking.md):
    # 开启后字幕锚定到说话人头部上沿中心;需配置 gen.route.head 头部检测网关,未配置自动回退底部字幕。
    # head_track 为预标注 RegionTimeline,提供则跳过自动检测(对齐 Hypit 的外部准备步骤约定)。
    caption_tracking: bool = Field(False, description="字幕跟随头部(需配置 gen.route.head,未配置回退底部字幕)")
    head_track: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="可选预标注头部轨迹:[{t(秒),box:[x,y,w,h](归一化0-1)}];提供则跳过自动头部检测",
    )
    # 声音混音 ducking(提升听感):开启后 BGM 在人声段自动压低,突出口播清晰度。
    # 任务级可关(ducking=False 时整轨 BGM 铺底不做压低);duck_level 覆盖全局下压音量。
    ducking: bool = Field(True, description="背景音乐人声段自动压低(ducking),突出口播清晰度")
    duck_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="ducking 时人声段 BGM 音量(0~1,留空用全局默认)")
    # 字幕风格预设(对齐 Hypit captions「Fine styles」):提供多种字幕视觉风格,留空用默认白字黑边。
    caption_style: Optional[str] = Field(None, description="字幕风格预设:default/highlight/minimal/variety,留空用默认")
    # 代码渲染层·信息卡(可选,对齐 Hypit lower-thirds):提供则在成片叠加"下三分之一"信息卡。
    # 仅当显式提供才叠加,绝不臆造商品信息;缺省不影响出片。
    overlay_card: Optional[Dict[str, Any]] = Field(
        None,
        description="可选信息卡(代码渲染层):{title(标题),body(正文),corner(bl/br/tl/tr,默认bl),"
                    "margin(边距px,默认40)};仅显式提供才叠加,不臆造商品信息",
    )
    # 代码渲染层·角标(可选,对齐 Hypit badge):提供则在成片角落叠加胶囊标签(品牌/卖点/水印)。
    overlay_badge: Optional[Dict[str, Any]] = Field(
        None,
        description="可选角标(代码渲染层):{text(标签文字),corner(tr/br/tl/bl,默认tr),margin(边距px,默认36)}",
    )
    # 代码渲染层·动效信息层(对齐 Hypit 动效组件):以下四类均仅显式提供才叠加,绝不臆造。
    overlay_ranking: Optional[Dict[str, Any]] = Field(
        None,
        description="可选排行榜(代码渲染层):{title,items:[{label,value}],corner(bl/br/tl/tr,默认bl),"
                    "start_ms(首条出现ms),stagger_ms(逐条错峰ms,默认500),end_ms(整块结束ms,默认到结尾)}",
    )
    overlay_reveal: Optional[Dict[str, Any]] = Field(
        None,
        description="可选揭示板(代码渲染层):{text,emoji(默认✨),at_ms(出现ms),duration_ms(停留ms,默认1800),corner(默认br),"
                    "ref(可选词锚点如moment:reveal,未显式给 at_ms 时按其真实秒回填)}",
    )
    overlay_flash: Optional[Dict[str, Any]] = Field(
        None,
        description="可选彩色闪烁(代码渲染层):{color(#RRGGBB),at_ms(出现ms),duration_ms(时长ms,默认400),"
                    "ref(可选词锚点,未显式给 at_ms 时按其真实秒回填)}",
    )
    overlay_sticker: Optional[Dict[str, Any]] = Field(
        None,
        description="可选评论贴纸(代码渲染层):{text,side(l/r,默认l),at_ms(出现ms),duration_ms(停留ms,默认2500),"
                    "avatar_color(头像色,#RRGGBB,默认品牌绿),ref(可选词锚点,未显式给 at_ms 时按其真实秒回填)}",
    )
    # 自动 B-roll 增强层(对齐 Hypit B-roll 素材镜头承接):显式开启才生效,失败自动回退原片,绝不阻断出片。
    auto_broll: Optional[Dict[str, Any]] = Field(
        None,
        description="可选自动 B-roll(代码渲染层):{enabled(bool),source(goods/scene/URL/gen,默认用商品图;"
                    "gen=无素材时自动文生图产出 B-roll 素材),prompt(gen 用,描述生成画面,缺失用通用电商特写),"
                    "strategy(even 均匀插窗/mention 关键词命中句插窗/anchor 词锚点真实秒插窗,默认 even),"
                    "keywords(mention 用,如['小龙虾']),anchors(anchor 用,词锚点引用如['selection:product'],"
                    "改台词后时间轴自动重排),"
                    "interval(even 间隔秒,默认8),window(单窗秒,默认3),position(center/br/bl/tr/tl,默认center),"
                    "scale(默认1.0),fade(淡入淡出秒,默认0.3)}",
    )
    # 音效卡点(P3-5,可选):三路线(换数字人/换场景/只换声)通用,在锚点/显式毫秒处叠短音效。
    sound_effects: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="可选音效卡点(代码渲染层):[{url(音效文件直链,必填),at_ms(出现毫秒,可选),"
                    "ref(可选词锚点如'moment:hook',未给 at_ms 时按其真实秒回填),volume(增益0~1,默认0.8)}];"
                    "无 url 或无时间码的项自动跳过,不阻断出片",
    )


class CacheQuery(BaseModel):
    """Worker 读取资产缓存(内部接口)"""
    cache_key: str = Field(..., description="缓存键(产物类型 + 入参哈希)")
    asset_type: str = Field("", description="产物类型:tts_audio/optimized_prompt/image/digital_video")


class CacheSchema(BaseModel):
    """Worker 回写资产缓存(内部接口)

    缓存按「决定产物的全部入参」哈希键控,只复用**输入完全相同**的产物,
    涵盖 TTS 音频、LLM 改写结果,以及 image(文生图/图生图/形象图派生)/
    digital_video(数字人口播成片)这类媒体资产。
    换主播、换文案、换画幅都会改变入参 → 键随之变化 → 正常重跑,不会因缓存而"每次都一样"。
    """
    cache_key: str = Field(..., description="缓存键")
    asset_type: str = Field(..., description="产物类型:tts_audio/optimized_prompt/image/digital_video")
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
