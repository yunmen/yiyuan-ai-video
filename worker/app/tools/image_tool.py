# -*- coding: utf-8 -*-
'''
@文件    :image_tool.py
@说明    :图像生成工具(真实接入)— 文生图 / 图生图,结果转存 OSS
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :2.1
@说明    :文生图走 /images/generations;图生图(传入 input_image / materials)走 /images/edits。
          两者结果统一转存自有 OSS,失败保留原始直链。
'''
import uuid
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.schemas.base import ToolResult
from app.tools.base import BaseGenTool
from app.settings import config
from app.core.plugin import logger
from app.utils.oss import persist_url_list

# 画幅 → 尺寸映射(文生图用 x 分隔)
RATIO_SIZE = {
    "1:1": "1024x1024",
    "16:9": "1280x720",
    "9:16": "720x1280",
    "4:3": "1152x896",
    "3:4": "896x1152",
}


class ImageGenTool(BaseGenTool):
    """图片生成工具 — 文生图 / 图生图,结果转存自有 OSS"""

    name = "image"
    description = "图像生成(文生图/图生图)"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # 图片生成走主网关(CHAT_LLM_*,即 gen.llm_*),与视频网关(LLM_BASE_*)分离;主网关缺失时回退视频网关
        self.api_key = api_key or config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY
        self.base_url = (base_url or config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/")
        if not self.api_key:
            raise RuntimeError("未配置主网关 API_KEY(CHAT_LLM_API_KEY),无法调用图片生成接口")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        prompt = (params.get("prompt") or "").strip()
        if not prompt:
            return self._fail("图片生成提示词不能为空", "invalid_request")

        materials: List[str] = [m for m in (params.get("materials") or []) if m]
        input_image = params.get("input_image") or (materials[0] if materials else None)
        ratio = params.get("ratio") or config.IMAGE_RATIO
        try:
            num = int(params.get("num_images") or 1)
        except (TypeError, ValueError):
            num = 1
        num = max(1, min(num, 4))
        task_id = str(params.get("_task_id") or uuid.uuid4().hex)

        # 有参考图 → 图生图;否则文生图
        if input_image:
            return await self.image_to_image(
                prompt, input_image=input_image, model=params.get("model"),
                ratio=ratio, num_images=num, negative_prompt=params.get("negative_prompt"),
                task_id=task_id,
            )
        return await self.text_to_image(
            prompt, model=params.get("model"), ratio=ratio, num_images=num, task_id=task_id,
        )

    async def text_to_image(
        self, prompt: str, model: Optional[str] = None, ratio: str = "1:1",
        num_images: int = 1, task_id: Optional[str] = None,
    ) -> ToolResult:
        """文生图 — POST /images/generations"""
        use_model = model or config.IMAGE_MODEL
        size = RATIO_SIZE.get(ratio, "1024x1024")
        prefix = task_id or uuid.uuid4().hex
        try:
            resp = await self.client.images.generate(model=use_model, prompt=prompt, n=num_images, size=size)
            urls = [d.url for d in resp.data if getattr(d, "url", None)]
            if not urls:
                return self._fail("图片生成失败:接口未返回图片 URL", "invalid_request")
            urls = await persist_url_list(urls, prefix)
            logger.info(f"[ImageGenTool] 文生图完成 model={use_model} ratio={ratio} 张数={len(urls)}")
            return ToolResult(
                content=",".join(urls),
                metadata={"success": True, "mode": "text2img", "model": use_model, "num_images": len(urls), "ratio": ratio},
            )
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"图片生成失败: {exc}", "request_error")

    async def image_to_image(
        self, prompt: str, input_image: str, model: Optional[str] = None, ratio: str = "1:1",
        num_images: int = 1, negative_prompt: Optional[str] = None, task_id: Optional[str] = None,
    ) -> ToolResult:
        """图生图/图片编辑 — POST /images/edits(OpenAI 兼容)"""
        if not input_image:
            return self._fail("图生图失败:未提供参考图片", "invalid_request")
        use_model = model or config.IMAGE_MODEL_EDIT or config.IMAGE_MODEL
        # edits 接口 size 要求 width*height(星号分隔)
        size = RATIO_SIZE.get(ratio, "1024x1024").replace("x", "*")
        parameters: Dict[str, Any] = {"size": size, "n": num_images, "prompt_extend": True, "watermark": False}
        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt
        prefix = task_id or uuid.uuid4().hex
        try:
            resp = await self.client.post(
                "/images/edits",
                cast_to=dict,
                body={
                    "model": use_model,
                    "prompt": prompt,
                    "input": {"messages": [{"role": "user", "content": [{"image": input_image}, {"text": prompt}]}]},
                    "parameters": parameters,
                },
            )
            data = resp.get("data") if isinstance(resp, dict) else None
            urls = [d["url"] for d in (data or []) if isinstance(d, dict) and d.get("url")]
            if not urls:
                return self._fail(f"图生图失败:接口未返回图片 URL({resp})", "invalid_request")
            urls = await persist_url_list(urls, prefix)
            logger.info(f"[ImageGenTool] 图生图完成 model={use_model} ratio={ratio} 张数={len(urls)}")
            return ToolResult(
                content=",".join(urls),
                metadata={"success": True, "mode": "img2img", "model": use_model, "num_images": len(urls), "ratio": ratio},
            )
        except Exception as exc:  # noqa: BLE001
            return self._fail(f"图生图失败: {exc}", "request_error")

    def _fail(self, msg: str, error_type: str = "unknown") -> ToolResult:
        logger.error(f"[ImageGenTool] {msg}")
        return ToolResult(content=msg, metadata={"success": False, "error_type": error_type, "error": msg})
