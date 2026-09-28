# -*- coding: utf-8 -*-
'''对标视频拆解服务:把对标视频拆成分镜 JSON,结果经 result_text 回写 backend'''
from app.services.base import BaseGenService
from app.tools.video_understand_tool import VideoUnderstandTool
from app.enums.task import GenTypeEnum


class DeconstructService(BaseGenService):
    """拆解(分析)服务:不产出媒体,结果以文本(JSON)回写

    is_media=False → BaseGenService 把结果写入 result_text(而非 result_video),
    且 gen_type 不在 SUBTITLE_GEN_TYPES 中,不会触发字幕烧录。
    """

    tool_class = VideoUnderstandTool
    gen_type = GenTypeEnum.DECONSTRUCT
    is_media = False
