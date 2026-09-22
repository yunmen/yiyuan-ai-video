# -*- coding: utf-8 -*-
'''数字人口播生成服务'''
from app.services.base import BaseGenService
from app.tools.digital_tool import DigitalHumanTool
from app.enums.task import GenTypeEnum


class DigitalGenService(BaseGenService):
    tool_class = DigitalHumanTool
    gen_type = GenTypeEnum.DIGITAL
    is_media = True
