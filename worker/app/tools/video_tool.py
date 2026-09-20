# -*- coding: utf-8 -*-
'''
@文件    :video_tool.py
@说明    :视频生成工具(真实接入)— OpenAI 兼容网关 /videos 提交 + 轮询到终态
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :2.0
@说明    :底层使用 AsyncOpenAI 异步 SDK,全链路 async。
          支持文生视频(t2v)/图生视频(i2v)/参考生视频(r2v);
          生成结果通过 ToolResult.metadata 携带 success/error_type/用量,
          失败不抛异常,由上层 service 统一转成 failed 回调。
'''
import asyncio
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
from openai import AsyncOpenAI

from app.schemas.base import ToolResult, Usage
from app.tools.base import BaseGenTool
from app.settings import config
from app.core import gateway
from app.core.plugin import logger
from app.utils.oss import persist_url_list

# 各模式最短时长(秒),低于下限会被网关拒绝
MIN_DURATION = 3

# LLM 脚本改写系统提示:把模板结构 + 商家信息改写成视频模型可直接消费的 prompt
PROMPT_OPTIMIZE_SYSTEM = (
    "你是短视频营销导演。把用户给出的[模板结构]与[商家信息]改写成一段可直接投喂给视频生成模型的中文 prompt。"
    "要求:1) 开头 3 秒强钩子;2) 突出卖点与促销信息;3) 结尾行动号召;"
    "4) 画面为竖版 9:16、真实探店/带货质感;5) 只输出 prompt 正文,不超过 300 字,不含引号与任何说明。"
)


class VideoGenTool(BaseGenTool):
    """视频生成工具 — 三种模式:文生/图生/参考生,提交任务 + 轮询完成。

    成功:ToolResult.content 为视频 URL,metadata.success=True 并附用量;
    失败:ToolResult.content 为错误信息,metadata.success=False 并附 error_type/error。
    """

    name = "video"
    description = "视频生成(文生/图生/参考生)"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        poll_interval: Optional[int] = None,
        poll_timeout: Optional[int] = None,
    ):
        gw = gateway.resolve("video")
        self.api_key = api_key or gw["key"] or config.LLM_BASE_API_KEY
        self.base_url = (base_url or gw["url"] or config.LLM_BASE_API_URL).rstrip("/")
        # 协议:显式配置优先;若构造时传入 base_url(如测试),按 URL 嗅探
        self.proto = gw["proto"] if not base_url else gateway.auto_proto(self.base_url)
        self.poll_interval = poll_interval or config.VIDEO_POLL_INTERVAL
        self.poll_timeout = poll_timeout or config.VIDEO_POLL_TIMEOUT
        if not self.api_key:
            raise RuntimeError("未配置视频网关 API_KEY,无法调用视频生成接口")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        self.task_prefix = uuid4().hex  # 结果转存 OSS 时的文件名前缀
        self._chat_client = None  # prompt 改写专用 client(走 chat 能力网关,懒加载)

    async def generate(self, params: dict, checkpoint: Optional[dict] = None, on_stage=None) -> ToolResult:
        """按素材数量自动选择生成模式:1 张图→图生,多张图→参考生,无素材→文生。

        支持断点续跑:checkpoint 携带已完成阶段(stage)与中间产物,各阶段完成后通过 on_stage 回写。
        阶段划分:1=改写 prompt 完成;2=已提交外部任务(external_task_id);3=已轮询拿到 raw_url(仅需转存)。
        """
        checkpoint = checkpoint or {}
        stage = int(checkpoint.get("stage", 0) or 0)

        prompt = params.get("prompt") or params.get("template_title") or "生成一段高质量短视频"
        materials: List[str] = [m for m in (params.get("materials") or []) if m]
        duration = self._clamp_duration(params.get("duration"))
        ratio = params.get("ratio") or config.VIDEO_RATIO
        resolution = params.get("resolution") or config.VIDEO_RESOLUTION
        self.task_prefix = str(params.get("_task_id") or uuid4().hex)

        logger.info(
            f"[VideoGenTool] 生成模式选择 materials={len(materials)} duration={duration} "
            f"ratio={ratio} resolution={resolution} prompt={prompt[:60]}"
        )
        # 阶段1:prompt 改写(可复用缓存,跳过 LLM 调用)
        if stage >= 1 and checkpoint.get("optimized_prompt"):
            prompt = checkpoint["optimized_prompt"]
            logger.info(f"[VideoGenTool] 断点续跑:复用缓存 prompt,跳过 LLM 改写 task={self.task_prefix}")
        else:
            prompt = await self._optimize_prompt(prompt, len(materials))
            if on_stage:
                await on_stage(1, {"optimized_prompt": prompt})

        if len(materials) == 1:
            return await self.image_to_video(
                prompt, duration=duration, ratio=ratio, resolution=resolution,
                input_image=materials[0], checkpoint=checkpoint, on_stage=on_stage,
            )
        if len(materials) > 1:
            return await self.reference_to_video(
                prompt, duration=duration, ratio=ratio, resolution=resolution,
                reference_images=materials, checkpoint=checkpoint, on_stage=on_stage,
            )
        return await self.text_to_video(
            prompt, duration=duration, ratio=ratio, resolution=resolution,
            checkpoint=checkpoint, on_stage=on_stage,
        )

    async def _optimize_prompt(self, prompt: str, material_count: int) -> str:
        """LLM 改写视频 prompt(钩子→卖点→CTA)。改写失败不影响主流程,回退原始 prompt。
        改写走主网关(CHAT_LLM_*,即 gen.llm_*),与视频网关(LLM_BASE_*)分离,实现双网关。"""
        if not config.CHAT_MODEL:
            return prompt
        try:
            if self._chat_client is None:
                gw = gateway.resolve("chat")
                chat_base = (gw["url"] or config.CHAT_LLM_BASE_URL or config.LLM_BASE_API_URL).rstrip("/")
                chat_key = gw["key"] or config.CHAT_LLM_API_KEY or config.LLM_BASE_API_KEY
                self._chat_client = AsyncOpenAI(api_key=chat_key, base_url=chat_base)
            resp = await self._chat_client.chat.completions.create(
                model=config.CHAT_MODEL,
                messages=[
                    {"role": "system", "content": PROMPT_OPTIMIZE_SYSTEM},
                    {"role": "user", "content": f"模板/需求:{prompt}\n素材:{material_count} 张产品图"},
                ],
                timeout=30,
            )
            text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
            if text:
                logger.info(f"[VideoGenTool] prompt 改写完成: {text[:60]}")
                return text
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[VideoGenTool] prompt 改写失败(回退原始 prompt): {exc}")
        return prompt

    async def text_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "16:9",
        resolution: str = "720P", checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """根据文字描述生成一段视频"""
        payload = {
            "model": model or config.VIDEO_MODEL_T2V,
            "prompt": prompt,
            "seconds": str(duration),
            "metadata": {"parameters": {"resolution": resolution, "ratio": ratio, "duration": duration}},
        }
        return await self._submit_and_poll(payload, "文生视频", duration, resolution, ratio, checkpoint=checkpoint, on_stage=on_stage)

    async def image_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "9:16",
        resolution: str = "1080P", input_image: Optional[str] = None,
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """基于首帧图片 + 文字描述生成视频。
        注意:i2v 模型(happyhorse-1.1-i2v)不支持 ratio 参数,画幅由首帧图片自身比例决定。"""
        if not input_image:
            return self._fail("图生视频失败:未提供首帧图片 URL", "invalid_request")
        payload = {
            "model": model or config.VIDEO_MODEL_I2V,
            "prompt": prompt,
            "image": input_image,
            "seconds": str(duration),
            "metadata": {"parameters": {"resolution": resolution, "duration": duration}},
        }
        return await self._submit_and_poll(payload, "图生视频", duration, resolution, None, checkpoint=checkpoint, on_stage=on_stage)

    async def reference_to_video(
        self, prompt: str, model: Optional[str] = None, duration: int = 5, ratio: str = "16:9",
        resolution: str = "720P", reference_images: Optional[List[str]] = None,
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """基于参考图片 + 文字描述生成视频"""
        if not reference_images:
            return self._fail("参考生视频失败:未提供参考图片", "invalid_request")
        payload = {
            "model": model or config.VIDEO_MODEL_R2V,
            "prompt": prompt,
            "images": reference_images,
            "seconds": str(duration),
            "metadata": {"parameters": {"resolution": resolution, "ratio": ratio, "duration": duration}},
        }
        return await self._submit_and_poll(payload, "参考生视频", duration, resolution, ratio, checkpoint=checkpoint, on_stage=on_stage)

    def _is_ark(self) -> bool:
        """是否火山方舟原生网关(协议 proto=ark):视频走 /contents/generations/tasks,而非 OpenAI /videos"""
        return self.proto == "ark"

    def _ark_body(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """把内部统一 payload 转成方舟原生请求体:model + content(text/image_url)。
        分辨率/比例/时长按方舟约定附加在 text 末尾(--resolution/--ratio/--duration)。"""
        params = (payload.get("metadata") or {}).get("parameters") or {}
        parts = [str(payload.get("prompt") or "")]
        resolution = params.get("resolution") or payload.get("resolution")
        ratio = params.get("ratio") or payload.get("ratio")
        duration = params.get("duration") or payload.get("seconds")
        if resolution:
            parts.append(f"--resolution {str(resolution).lower()}")
        if ratio:
            parts.append(f"--ratio {ratio}")
        if duration:
            parts.append(f"--duration {int(float(duration))}")
        content: List[Dict[str, Any]] = [{"type": "text", "text": " ".join(parts)}]
        single = payload.get("image")
        if single:
            content.append({"type": "image_url", "image_url": {"url": single}})
        for url in (payload.get("images") or []):
            content.append({"type": "image_url", "image_url": {"url": url}})
        return {"model": payload.get("model"), "content": content}

    async def _ark_request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """调用火山方舟原生接口(用 httpx,避免 OpenAI SDK 对非 OpenAI 端点的解析问题)"""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.request(method, f"{self.base_url}{path}", json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _submit_and_poll(
        self, payload: Dict[str, Any], label: str, duration: int, resolution: Optional[str], ratio: Optional[str],
        checkpoint: Optional[dict] = None, on_stage=None,
    ) -> ToolResult:
        """提交视频任务并轮询直到完成(全链路异步)。支持断点续跑:
        - stage>=2 且已保存 external_task_id → 跳过提交,直接复用该任务 ID 继续轮询(避免重复扣费生成);
        - stage>=3 且已保存 raw_url → 跳过轮询,直接转存 OSS。
        """
        checkpoint = checkpoint or {}
        stage = int(checkpoint.get("stage", 0) or 0)
        logger.info(f"[VideoGenTool] {label}请求参数: {payload}")

        # 阶段2:提交(或复用已提交任务 ID 续跑轮询)
        if stage >= 2 and checkpoint.get("external_task_id"):
            external_task_id = checkpoint["external_task_id"]
            logger.info(f"[VideoGenTool] 断点续跑:复用 external_task_id={external_task_id},跳过提交直接轮询")
        else:
            # 火山方舟原生网关走 /contents/generations/tasks(httpx);OpenAI 兼容中转站走 SDK /videos
            ark = self._is_ark()
            submit_path = "/contents/generations/tasks" if ark else "/videos"
            logger.info(f"[VideoGenTool] {label}提交地址: {self.base_url}{submit_path}")
            try:
                if ark:
                    resp = await self._ark_request("POST", submit_path, self._ark_body(payload))
                else:
                    resp = await self.client.post(submit_path, cast_to=dict, body=payload)
            except Exception as exc:
                return self._fail(f"{label}提交异常: {exc}", "request_error")
            external_task_id = (resp or {}).get("id") or (resp or {}).get("task_id")
            if not external_task_id:
                return self._fail(f"{label}失败:接口未返回任务ID({resp})", "invalid_request")
            logger.info(f"[VideoGenTool] {label}任务已提交: external_task_id={external_task_id}")
            if on_stage:
                await on_stage(2, {
                    "external_task_id": external_task_id,
                    "duration": duration, "resolution": resolution, "ratio": ratio,
                })

        # 阶段3:轮询(或复用已取回的 raw_url 跳过轮询)
        raw_url = checkpoint.get("raw_url") if stage >= 3 else None
        if raw_url:
            logger.info(f"[VideoGenTool] 断点续跑:复用 raw_url,跳过轮询")
        else:
            raw_url = await self._poll(external_task_id, label, duration, resolution, ratio)
            if not raw_url:
                return self._fail(f"{label}生成未完成(轮询结束仍无结果)", "timeout")
            if on_stage:
                await on_stage(3, {"raw_url": raw_url})

        # 终态:转存 OSS(未启用时原样返回),避免模型临时直链过期
        persisted = await persist_url_list([raw_url], self.task_prefix)
        url = persisted[0] if persisted else raw_url
        usage = self._usage(duration, resolution, ratio)
        logger.info(f"[VideoGenTool] {label}完成: external_task_id={external_task_id}, url={url}")
        return ToolResult(content=url, metadata={"success": True, **usage})

    async def _poll(self, external_task_id: str, label: str, duration: int, resolution: Optional[str], ratio: Optional[str]) -> Optional[str]:
        """轮询外部视频任务直到完成,返回原始视频直链;失败/超时返回 None(由上层转 failed)。"""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < self.poll_timeout:
            await asyncio.sleep(self.poll_interval)
            try:
                if self._is_ark():
                    # 方舟:GET /contents/generations/tasks/{id},结果取 content.video_url
                    task = await self._ark_request("GET", f"/contents/generations/tasks/{external_task_id}")
                    status = (task or {}).get("status")
                    if status in ("succeeded", "success", "completed"):
                        return ((task or {}).get("content") or {}).get("video_url")
                    if status in ("failed", "error", "canceled"):
                        logger.error(f"[VideoGenTool] {label}生成失败: {(task or {}).get('error') or status}")
                        return None
                else:
                    task = await self.client.videos.retrieve(external_task_id)
                    status = getattr(task, "status", None)
                    metadata = getattr(task, "metadata", None)
                    url = metadata.get("url") if isinstance(metadata, dict) else None
                    if status in ("completed", "succeeded", "success") and url:
                        return url
                    if status in ("failed", "error", "canceled"):
                        reason = getattr(task, "error", None) or status
                        logger.error(f"[VideoGenTool] {label}生成失败: {reason}")
                        return None
            except Exception as exc:
                logger.warning(f"[VideoGenTool] {label}轮询异常(继续重试): external_task_id={external_task_id}, {exc}")
                continue
        logger.error(f"[VideoGenTool] {label}生成超时: external_task_id={external_task_id}")
        return None

    @staticmethod
    def _clamp_duration(value: Any) -> int:
        """时长兜底:转 int 并收敛到 [MIN_DURATION, 15]"""
        try:
            d = int(value)
        except (TypeError, ValueError):
            d = 5
        return max(MIN_DURATION, min(d, 15))

    @staticmethod
    def _usage(duration: int, resolution: Optional[str], ratio: Optional[str]) -> Dict[str, Any]:
        """组装用量信息(供 backend 计费/展示)"""
        usage = Usage(model=config.VIDEO_MODEL, seconds=duration).to_dict()
        usage.update({"resolution": resolution, "ratio": ratio})
        return usage

    def _fail(self, msg: str, error_type: str = "unknown") -> ToolResult:
        """统一的失败返回,交由上层 service 转 failed 回调"""
        logger.error(f"[VideoGenTool] {msg}")
        return ToolResult(content=msg, metadata={"success": False, "error_type": error_type, "error": msg})
