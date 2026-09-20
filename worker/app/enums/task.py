# -*- coding: utf-8 -*-
'''生成类型枚举'''
from enum import Enum


class GenTypeEnum(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
