# -*- coding: utf-8 -*-
'''基础枚举(环境)'''
from enum import Enum


class EnvironmentEnum(str, Enum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"
