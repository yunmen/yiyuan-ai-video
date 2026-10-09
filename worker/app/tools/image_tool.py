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
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from app.schemas.base import ToolResult
from app.tools.base import BaseGenTool
from app.settings import config
from skills.prompt_library import build_image_direction_prompt
from app.core import gateway
from app.core.retry import with_transient_retry
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
        # 图片走"能力路由"(gen.route.image)解析的网关;未配置则回退媒体/文本网关
        gw = gateway.resolve("image")
        self.api_key = api_key or gw["key"] or config.LLM_BASE_API_KEY or config.CHAT_LLM_API_KEY
        self.base_url = (base_url or gw["url"] or config.LLM_BASE_API_URL or config.CHAT_LLM_BASE_URL).rstrip("/")
        self.proto = gw["proto"] if not base_url else gateway.auto_proto(self.base_url)
        self._pinned = bool(base_url)
        if not self.api_key:
            raise RuntimeError("未配置图片网关 API_KEY,无法调用图片生成接口")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        prompt = (params.get("prompt") or "").strip()
        # 九宫格拼合(grid)/分割(split)模式解析(早于 prompt 校验,因这两类可无提示词)
        grid = params.get("grid") or None
        split = bool(params.get("split"))
        materials: List[str] = [m for m in (params.get("materials") or []) if m]
        input_image = params.get("input_image") or (materials[0] if materials else None)
        # 仅"生成类"需要提示词:分割、纯拼合(上传多图无提示词)不强制
        need_prompt = not split and not (grid and not prompt and len(materials) >= 2)
        if need_prompt and not prompt:
            return self._fail("图片生成提示词不能为空", "invalid_request")

        # 可选风格预设:传 style(如 stick_figure / minimal / concept)时,把预设描述拼到提示词前。
        # 未传 style 则保持原提示词不变(不影响既有调用方)。
        style = params.get("style")
        if style and style in IMAGE_STYLE_PRESETS and prompt:
            prompt = apply_image_prefix(prompt, IMAGE_STYLE_PRESETS[style]["description"])

        # 复刻换图(带替换意图):先用 chat 按「图像方向」方法论改写提示词,再交给图片模型。
        # 该方法是给"写提示词的模型"看的元指引,直接拼进图片模型 prompt 会干扰出图、
        # 甚至产生文字伪影,所以走一次改写而不是拼接。无意图则完全不触发。
        intent = [str(i).strip() for i in (params.get("intent") or []) if str(i).strip()]
        if intent and prompt:
            prompt = await self._apply_image_direction(prompt, intent)

        ratio = params.get("ratio") or config.IMAGE_RATIO
        try:
            num = int(params.get("num_images") or 1)
        except (TypeError, ValueError):
            num = 1
        # 九宫格(grid)模式允许一次出 9 张;普通图生图仍限 4 张
        num = max(1, min(num, 9 if grid else 4))
        task_id = str(params.get("_task_id") or uuid.uuid4().hex)

        # 分割模式:上传单张九宫格图 → 按网格切 9 张单图(行优先)
        if split:
            src = input_image or (materials[0] if materials else None)
            if not src:
                return self._fail("分割模式需上传一张九宫格图片", "invalid_request")
            from app.tools.grid_tool import split_grid
            urls = await split_grid(src, spec=grid or "3x3", task_id=task_id)
            if not urls:
                return self._fail("九宫格分割失败(图片下载或上传异常)", "request_error")
            return ToolResult(
                content=",".join(urls),
                metadata={"success": True, "mode": "split", "num_images": len(urls),
                          "ratio": ratio, "watermark_removed": True},
            )

        # 网格拼合模式:输出一张九宫格图
        if grid:
            from app.tools.grid_tool import compose_grid
            # 纯拼合:无提示词但传入多张图(用户上传 9 张)→ 直接拼合,不调模型
            if not prompt and len(materials) >= 2:
                url = await compose_grid(materials, spec=grid, task_id=task_id)
                if not url:
                    return self._fail("九宫格拼合失败(图片下载或上传异常)", "request_error")
                return ToolResult(
                    content=url,
                    metadata={"success": True, "mode": "compose", "num_images": len(materials),
                              "ratio": ratio, "watermark_removed": True},
                )
            # 提示词生成:文生图/图生图生成 num 张 → 拼合成九宫格
            if input_image:
                res = await self.image_to_image(
                    prompt, input_image=input_image, model=params.get("model"),
                    ratio=ratio, num_images=num, negative_prompt=params.get("negative_prompt"),
                    task_id=task_id,
                )
            else:
                res = await self.text_to_image(
                    prompt, model=params.get("model"), ratio=ratio, num_images=num, task_id=task_id,
                )
            if not res.metadata.get("success"):
                return res
            gen_urls = [u for u in (res.content or "").split(",") if u]
            url = await compose_grid(gen_urls, spec=grid, task_id=task_id)
            if not url:
                # 拼合失败但图已生成:退化为返回多张逗号拼接,不阻断出片
                logger.warning(f"[ImageGenTool] 九宫格拼合失败,回退返回原始多图 task={task_id}")
                return res
            return ToolResult(
                content=url,
                metadata={**res.metadata, "mode": "grid", "watermark_removed": True},
            )

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

    def _is_ark(self) -> bool:
        """是否火山方舟原生协议(proto=ark):图片走 /images/generations(经 AsyncOpenAI extra_body)"""
        return self.proto == "ark"

    async def _apply_image_direction(self, prompt: str, intent: List[str]) -> str:
        """复刻换商品/人物/场景时,按「图像方向」方法论改写图片提示词。

        只在**有替换意图**时触发 —— 普通文生图/图生图完全不受影响(不带意图就不多这次调用)。
        任何失败(未配 chat 模型 / 网关全挂 / 资产缺失)都回退原提示词,绝不因增强丢单。
        """
        system = build_image_direction_prompt()
        if not system or not config.CHAT_MODEL:
            return prompt
        candidates = gateway.resolve_all("chat") or [{
            "name": "env",
            "url": (config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL or "").rstrip("/"),
            "key": config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY,
            "proto": "openai",
        }]
        user = (
            f"本次替换意图:{'、'.join(intent)}\n"
            f"原图片提示词:{prompt}\n"
            "请按上述图像方向改写这条提示词,只输出改写后的提示词本身,不要解释。"
        )
        for gw in candidates:
            try:
                client = AsyncOpenAI(
                    api_key=gw.get("key") or self.api_key,
                    base_url=(gw.get("url") or "").rstrip("/") or self.base_url,
                )
                resp = await client.chat.completions.create(
                    model=config.CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    timeout=60,
                )
                text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
                if text:
                    logger.info(f"[ImageGenTool] 图像方向改写完成: {text[:60]}")
                    return text
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[ImageGenTool] 图像方向改写经 [{gw.get('name')}] 失败,尝试下一个: {exc}")
        return prompt

    async def _ark_image(
        self, *, model: str, prompt: str, size: str,
        image: Optional[str] = None, negative_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """调用方舟图片生成接口,返回原始 JSON(data[].url)

        单次调用遇 429 限流 / 5xx 内部错误时按 with_transient_retry 退避重试,
        避免整条图片任务因瞬时错误失败(方舟 seedream 实测会返 429 RPM 限流)。
        改用 AsyncOpenAI 客户端的 images.generate 统一走 OpenAI 兼容协议
        (方舟 OpenAI 兼容端点同样提供 /images/generations);image / negative_prompt /
        watermark / response_format 等非标准字段经 extra_body 透传。
        """
        # response_format 是 OpenAI 标准字段,直接传;watermark/image/negative_prompt
        # 为方舟扩展字段,经 extra_body 透传(避免与非标准键碰撞)。
        extra_body: Dict[str, Any] = {"watermark": False}
        if image:
            extra_body["image"] = image  # 图生图/编辑参考图
        if negative_prompt:
            extra_body["negative_prompt"] = negative_prompt

        async def _do() -> Dict[str, Any]:
            resp = await self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                response_format="url",
                extra_body=extra_body,
            )
            return resp.model_dump()

        return await with_transient_retry(_do, label="方舟图片生成")

    async def _text2img_once(self, model: str, prompt: str, num_images: int, size: str) -> List[str]:
        """一次文生图请求(当前网关):方舟原生逐张生成,OpenAI 兼容走 SDK"""
        if self._is_ark():
            urls: List[str] = []
            for _ in range(num_images):
                data = await self._ark_image(model=model, prompt=prompt, size=size)
                urls += [d.get("url") for d in (data.get("data") or []) if d.get("url")]
            return urls
        resp = await self.client.images.generate(model=model, prompt=prompt, n=num_images, size=size)
        return [d.url for d in resp.data if getattr(d, "url", None)]

    async def text_to_image(
        self, prompt: str, model: Optional[str] = None, ratio: str = "1:1",
        num_images: int = 1, task_id: Optional[str] = None,
    ) -> ToolResult:
        """文生图 — 方舟原生走 /images/generations;OpenAI 兼容中转站走 SDK images.generate"""
        use_model = model or config.IMAGE_MODEL
        size = RATIO_SIZE.get(ratio, "1024x1024")
        prefix = task_id or uuid.uuid4().hex
        try:
            urls = await self._with_failover(
                "image",
                lambda _gw: self._text2img_once(use_model, prompt, num_images, size),
                label="文生图",
            )
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

    async def _img2img_once(
        self, model: str, prompt: str, input_image: str, num_images: int,
        size_px: str, negative_prompt: Optional[str],
    ) -> Tuple[List[str], Any]:
        """一次图生图请求(当前网关),返回 (图片 URL 列表, 原始响应——仅用于错误提示)"""
        if self._is_ark():
            # 方舟:同端点 /images/generations,用 image 字段传参考图
            urls: List[str] = []
            for _ in range(num_images):
                data = await self._ark_image(
                    model=model, prompt=prompt, size=size_px,
                    image=input_image, negative_prompt=negative_prompt,
                )
                urls += [d.get("url") for d in (data.get("data") or []) if d.get("url")]
            return urls, {"data": [{"url": u} for u in urls]}
        # 中转站 edits 接口:size 要求 width*height(星号分隔)
        size = size_px.replace("x", "*")
        parameters: Dict[str, Any] = {"size": size, "n": num_images, "prompt_extend": True, "watermark": False}
        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt
        resp = await self.client.post(
            "/images/edits",
            cast_to=dict,
            body={
                "model": model,
                "prompt": prompt,
                "input": {"messages": [{"role": "user", "content": [{"image": input_image}, {"text": prompt}]}]},
                "parameters": parameters,
            },
        )
        data = resp.get("data") if isinstance(resp, dict) else None
        urls = [d["url"] for d in (data or []) if isinstance(d, dict) and d.get("url")]
        return urls, resp

    async def image_to_image(
        self, prompt: str, input_image: str, model: Optional[str] = None, ratio: str = "1:1",
        num_images: int = 1, negative_prompt: Optional[str] = None, task_id: Optional[str] = None,
    ) -> ToolResult:
        """图生图/图片编辑 — POST /images/edits(OpenAI 兼容)"""
        if not input_image:
            return self._fail("图生图失败:未提供参考图片", "invalid_request")
        use_model = model or config.IMAGE_MODEL_EDIT or config.IMAGE_MODEL
        size_px = RATIO_SIZE.get(ratio, "1024x1024")
        prefix = task_id or uuid.uuid4().hex
        try:
            urls, resp = await self._with_failover(
                "image",
                lambda _gw: self._img2img_once(use_model, prompt, input_image, num_images, size_px, negative_prompt),
                label="图生图",
            )
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
