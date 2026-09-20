# -*- coding: utf-8 -*-
'''生成工具基类'''
from app.schemas.base import ToolResult


class BaseGenTool:
    name: str = "base"
    description: str = ""

    async def generate(self, params: dict) -> ToolResult:
        raise NotImplementedError
