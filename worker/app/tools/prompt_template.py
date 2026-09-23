# -*- coding: utf-8 -*-
'''
@文件    :prompt_template.py
@说明    :提示词模板(纯函数)— 把画幅/清晰度等生成参数注入提示词,杜绝硬编码
@时间    :2026/09/21 15:00:00
@作者    :一源AI
@版本    :1.0
@说明    :此前 rewrite 系统提示里写死「竖版 9:16」,而画幅已做成系统可配置
          (gen.video_ratio),两者会互相矛盾:运营改成 16:9 后,提示词仍在要求竖版构图。
          这里把画幅/清晰度做成模板参数,由本次任务的实际下发值渲染;
          未知画幅原样描述(不谎报成竖版),后续新增档位无需改代码。
'''
from typing import Optional

# 画幅 → 提示词描述(键与 backend app/services/gen_rules.py 的 SUPPORTED_RATIOS 对齐)
RATIO_LABELS = {
    "9:16": "竖版 9:16",
    "16:9": "横版 16:9",
    "1:1": "方形 1:1",
    "4:3": "横版 4:3",
    "3:4": "竖版 3:4",
}

# 清晰度 → 提示词描述
RESOLUTION_LABELS = {
    "1080P": "1080P 高清",
    "720P": "720P 标清",
}

# 图生视频(i2v):画幅由首帧图片自身比例决定,模型不接受 ratio 参数,
# 此时提示词里不能指定画幅,否则与模型实际行为矛盾。
RATIO_BY_FIRST_FRAME = "画幅以首帧图片为准"

# prompt 改写系统提示模板:{ratio} / {resolution} 由调用方按任务实际参数注入
PROMPT_OPTIMIZE_SYSTEM_TEMPLATE = (
    "你是短视频营销导演。把用户给出的结构化上下文改写成一段可直接投喂给视频生成模型的中文 prompt。"
    "输入可能包含这些段落:[模板结构]、[画面构成]、[生成模式]、[商家信息]、"
    "[人物信息]/[商品信息]/[场景信息](用户上传素材的视觉识别结果)、[补充要求]。"
    "要求:1) 开头 3 秒强钩子;2) 突出卖点与促销信息;3) 结尾行动号召;"
    "4) 画面为{ratio}、{resolution}、真实探店/带货质感;"
    "5) 只输出 prompt 正文,不超过 300 字,不含引号与任何说明;"
    "6) **台词必须逐字照用**:[商家信息]里的「大标题/副标题/口播文案」是用户提供的准确内容,"
    "视频里要说的话必须与之一字不差,不得改写、浓缩、扩写或替换措辞;"
    "7) **[补充要求]是硬性约束,必须整条保留其含义**:其中「替换…」「必须保持原样」"
    "「不得残留」「不得改动」等要求,必须原样体现在输出里,不得删除、弱化,也不得改写成营销话术;"
    "[生成模式]里的素材用途、[画面构成]里的镜头/场景要求同样不得丢弃;"
    "8) [人物信息]/[商品信息]描述的是**用户上传、要替换进去的人物/商品主体外观**,"
    "只能用于说明「要替换成什么样」,**不得据此编造或改写成片的场景、背景与镜头**;"
    "成片的场景、背景、运镜与节奏一律遵循参考视频或[画面构成]"
    "(实测:把素材图背景当成成片场景写进去,会与参考视频的画面打架);"
    "若输入含[场景信息],它表示用户要求替换成的场景,按[补充要求]的替换指令使用;"
    "9) 当[生成模式]为「视频编辑」时,输出的是**编辑指令**(替换哪些元素、保持哪些不变),"
    "不要另编分镜,也不要新增原片中不存在的场景或人物。"
    "只有画面描述可以自由创作 —— 画面为你服务,台词与替换约束为用户服务。"
)


def ratio_label(ratio: Optional[str]) -> str:
    """画幅文案:i2v 等由首帧决定画幅的场景传 None。"""
    r = str(ratio or "").strip()
    if not r:
        return RATIO_BY_FIRST_FRAME
    return RATIO_LABELS.get(r, f"比例 {r}")


def resolution_label(resolution: Optional[str]) -> str:
    """清晰度文案:未知档位原样输出,不臆造。"""
    r = str(resolution or "").strip().upper()
    return RESOLUTION_LABELS.get(r) or (r or "高清画质")


def build_prompt_optimize_system(
    ratio: Optional[str] = None, resolution: Optional[str] = None,
) -> str:
    """渲染 prompt 改写系统提示(画幅/清晰度取自本次任务实际参数,不写死)。

    ratio 传 None 表示画幅由首帧图片决定(i2v),提示词中不指定画幅。
    """
    return PROMPT_OPTIMIZE_SYSTEM_TEMPLATE.format(
        ratio=ratio_label(ratio),
        resolution=resolution_label(resolution),
    )
