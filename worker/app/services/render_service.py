# -*- coding: utf-8 -*-
'''视频换口播生成服务'''
from app.services.base import BaseGenService
from app.tools.render_tool import RenderTool
from app.enums.task import GenTypeEnum


class RenderGenService(BaseGenService):
    tool_class = RenderTool
    gen_type = GenTypeEnum.RENDER
    is_media = True
