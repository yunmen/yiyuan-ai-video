# -*- coding: utf-8 -*-
'''工具统一返回结构与用量结构'''
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ToolResult:
    """每个生成工具的统一返回:content 结果 + metadata 用量"""
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Usage:
    """用量与消耗(计费用,预留)"""
    model: str = ""
    tokens: int = 0
    images: int = 0
    seconds: int = 0
    chars: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "tokens": self.tokens,
            "images": self.images,
            "seconds": self.seconds,
            "chars": self.chars,
        }
