# -*- coding: utf-8 -*-
'''
@文件    :text_tool.py
@说明    :文本生成工具(真实接入)— OpenAI 兼容 Chat Completions API
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :2.0
'''
from typing import Optional

from openai import AsyncOpenAI

from app.schemas.base import ToolResult
from app.tools.base import BaseGenTool
from app.settings import config
from app.core.plugin import logger


class TextGenTool(BaseGenTool):
    """文本生成工具 — 通过 Chat Completions API 生成文本"""

    name = "text"
    description = "文本生成"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # 文本生成走主网关(CHAT_LLM_*,即 gen.llm_*),与视频网关(LLM_BASE_*)分离;主网关缺失时回退视频网关
        self.api_key = api_key or config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY
        self.base_url = (base_url or config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/")
        if not self.api_key:
            raise RuntimeError("未配置主网关 API_KEY(CHAT_LLM_API_KEY),无法调用文本生成接口")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        prompt = (params.get("prompt") or "").strip()
        if not prompt:
            return self._fail("文本生成提示词不能为空", "invalid_request")
        model = params.get("model") or config.TEXT_MODEL
        try:
            resp = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content if resp.choices else ""
            usage = resp.usage
            metadata = {
                "success": True,
                "model": model,
                "input_tokens": getattr(usage, "prompt_tokens", None),
                "output_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }
            logger.info(f"[TextGenTool] 完成 model={model} chars={len(text or '')}")
            return ToolResult(content=text, metadata=metadata)
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"文本生成失败: {exc}", "request_error")

    def _fail(self, msg: str, error_type: str = "unknown") -> ToolResult:
        logger.error(f"[TextGenTool] {msg}")
        return ToolResult(content=msg, metadata={"success": False, "error_type": error_type, "error": msg})
