# -*- coding: utf-8 -*-
'''视频生成服务'''
from app.services.base import BaseGenService
from app.tools.video_tool import VideoGenTool
from app.enums.task import GenTypeEnum


class VideoGenService(BaseGenService):
    tool_class = VideoGenTool
    gen_type = GenTypeEnum.VIDEO
    is_media = True
