# -*- coding: utf-8 -*-
'''文本生成服务'''
from app.services.base import BaseGenService
from app.tools.text_tool import TextGenTool
from app.enums.task import GenTypeEnum


class TextGenService(BaseGenService):
    tool_class = TextGenTool
    gen_type = GenTypeEnum.TEXT
    is_media = False
