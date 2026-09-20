# -*- coding: utf-8 -*-
'''图像生成服务'''
from app.services.base import BaseGenService
from app.tools.image_tool import ImageGenTool
from app.enums.task import GenTypeEnum


class ImageGenService(BaseGenService):
    tool_class = ImageGenTool
    gen_type = GenTypeEnum.IMAGE
    is_media = False
