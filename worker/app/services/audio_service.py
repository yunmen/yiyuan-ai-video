# -*- coding: utf-8 -*-
'''音频生成服务'''
from app.services.base import BaseGenService
from app.tools.audio_tool import AudioGenTool
from app.enums.task import GenTypeEnum


class AudioGenService(BaseGenService):
    tool_class = AudioGenTool
    gen_type = GenTypeEnum.AUDIO
    is_media = True  # 音频是媒体结果 → 回写 result_video(供管理端/用户端预览)
