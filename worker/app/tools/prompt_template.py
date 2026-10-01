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

from skills.prompts import render  # 提示词散文已迁移到 worker/skills/video-generation/assets/video_optimize.md

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

# prompt 改写系统提示(散文)已迁移到 worker/skills/video-generation/assets/video_optimize.md:
# 画幅/清晰度由下方 ratio_label / resolution_label 注入,通过 skills.prompts.render 渲染。


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
    ratio: Optional[str] = None, resolution: Optional[str] = None, edit: bool = False,
) -> str:
    """渲染 prompt 改写系统提示(画幅/清晰度取自本次任务实际参数,不写死)。

    ratio 传 None 表示画幅由首帧图片决定(i2v),提示词中不指定画幅。
    edit=True 表示视频编辑/复刻链路(v2v):改写基调是「保持原片结构与体裁、只按替换指令改元素」,
    渲染 video_optimize_edit —— 不能沿用带货营销导演基调,否则用户拿非广告原片换人物,
    成片仍被强行写成带货广告(实测踩坑)。散文分别来自
    worker/skills/video-generation/assets/video_optimize.md 与 worker/skills/video-generation/assets/video_optimize_edit.md,此处仅做装配。
    """
    if edit:
        # 编辑指令不指定画幅/时长:方舟按编辑任务强制 ratio=adaptive、duration=-1,跟随参考视频
        return render("video_optimize_edit")
    return render(
        "video_optimize",
        ratio=ratio_label(ratio),
        resolution=resolution_label(resolution),
    )
