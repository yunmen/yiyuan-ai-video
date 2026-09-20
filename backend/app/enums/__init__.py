# -*- coding: utf-8 -*-
'''
@文件    :__init__.py
@说明    :自定义枚举类
@时间    :2026/01/15 23:21:13
@作者    :睿
@版本    :1.0
'''


from enum import Enum, StrEnum, IntEnum, unique
from typing import Optional


class StrCustomEnum(str, Enum):
    def __new__(cls, value: str, label: Optional[str] = None, desc: Optional[str] = None):
        """
        初始化枚举成员：
        - value: 整数
        - label: 显示名称
        - desc: 额外描述
        """
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._label_ = label
        obj._desc_ = desc
        return obj

    @property
    def label(self) -> Optional[str]:
        return self._label_

    @property
    def desc(self) -> Optional[str]:
        return self._desc_


class IntCustomEnum(int, Enum):
    def __new__(cls, value: int, label: Optional[str] = None, desc: Optional[str] = None):
        """
        初始化枚举成员：
        - value: 整数
        - label: 显示名称
        - desc: 额外描述
        """
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._label_ = label
        obj._desc_ = desc
        return obj

    @property
    def label(self) -> Optional[str]:
        return self._label_

    @property
    def desc(self) -> Optional[str]:
        return self._desc_

