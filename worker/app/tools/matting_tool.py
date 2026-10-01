# -*- coding: utf-8 -*-
'''
@文件    :matting_tool.py
@说明    :AI 抠像工具 — 把源视频逐帧送到抠像网关提取前景 alpha(RGBA),再重组成带透明通道的前景视频。
@时间    :2026/09/30
@作者    :一源AI
@版本    :1.0
@说明    :这是「视频换场景(保留真人)」的 AI 抠图核心,替换写死的绿幕色键(chromakey):
            - 网关能力 matting 由 gen.route.matting 显式指向某个 gen.gw.<name>;
            - 约定:POST {网关地址}{MATTING_ENDPOINT},multipart 字段 image,返回 RGBA PNG(前景透明背景);
            - 未配置网关 / 任一帧失败 → 返回 success=False(matting_unavailable 或 error),
              由调用方(render 换场景路线)降级到绿幕色键,保证「没接 AI 抠像也能出片」。
          抠像网关是真实外部模型服务(如 RMBG / MODNet / 视频抠像 API),本工具只负责编排与合成,
          不内置任何模型权重。
'''
import asyncio
import base64
import json
import os
import shutil
import tempfile

import httpx

from app.settings import config
from app.core.plugin import logger
from app.core import gateway, compose
from app.schemas.base import ToolResult


class MattingTool:
    """AI 抠像:帧级调用抠像网关,产出 RGBA 前景视频(本地路径,生命周期由调用方管理)。"""

    capability = "matting"

    async def matte_video(
        self, video: str, task_id: str = "", notify_url: str = "", workdir: str = ""
    ) -> ToolResult:
        """逐帧抠像:抽帧 → 并发送抠像网关 → 重组成 RGBA 视频。

        参数:
          video     :本地源视频路径(调用方已下载到本地)。
          task_id   :任务 ID(仅用于日志/进度,可选)。
          notify_url:回调地址(可选,当前未透传网关,保留签名一致)。
          workdir   :调用方提供的工作目录并保持存活(本方法不负责清理);返回的 RGBA 视频位于其内。
        返回:
          success=True  → content 为本地 RGBA 视频路径,metadata 含 frames/fps;
          success=False → 无可用网关(matting_unavailable)或执行出错(error),供调用方降级。
        """
        gateways = gateway.resolve_all(self.capability)
        if not gateways:
            return ToolResult(
                content="", metadata={
                    "success": False, "matting_unavailable": True,
                    "error": "未配置 AI 抠像网关(gen.route.matting)",
                }
            )
        tmp = workdir or tempfile.mkdtemp(prefix="matting_")
        frames_in = os.path.join(tmp, "frames_in")
        frames_out = os.path.join(tmp, "frames_out")
        os.makedirs(frames_in, exist_ok=True)
        os.makedirs(frames_out, exist_ok=True)
        try:
            # 1) 抽帧:长视频按 MATTING_FRAME_FPS 降采样,降低抠像网关压力
            sample_fps = config.MATTING_FRAME_FPS
            extract = compose.build_matte_frames_extract(
                video, frames_in, sample_fps if sample_fps and sample_fps > 0 else 0.0
            )
            res = await compose.run(extract, timeout=600, cwd=tmp)
            if not res.get("ok"):
                return ToolResult(
                    content="", metadata={"success": False, "error": f"抽帧失败: {res.get('stderr')}"}
                )
            in_files = sorted(f for f in os.listdir(frames_in) if f.endswith(".png"))
            if not in_files:
                return ToolResult(content="", metadata={"success": False, "error": "抽帧结果为空"})

            # 2) 逐帧抠像:受并发上限约束,单帧失败则换下一个网关候选
            sem = asyncio.Semaphore(max(1, int(config.MATTING_CONCURRENCY)))

            async def _one(name: str) -> bool:
                src = os.path.join(frames_in, name)
                dst = os.path.join(frames_out, name)
                for gw in gateways:
                    try:
                        async with sem:
                            data = await self._matte_image(gw, src)
                        if data:
                            with open(dst, "wb") as f:
                                f.write(data)
                            return True
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"[MattingTool] 帧 {name} 经网关[{gw['name']}]失败: {exc}")
                return False

            ok_list = await asyncio.gather(*[_one(n) for n in in_files])
            if not all(ok_list):
                failed = sum(1 for ok in ok_list if not ok)
                return ToolResult(
                    content="", metadata={"success": False, "error": f"抠像失败帧数: {failed}/{len(in_files)}"}
                )

            # 3) 重组 RGBA 视频:png 编码保留 alpha 透明通道
            fps = compose.probe_fps(video) or 25.0
            rgba = os.path.join(tmp, "fg_rgba.mov")
            asm = compose.build_rgba_frames_assemble(frames_out, rgba, fps)
            res = await compose.run(asm, timeout=600, cwd=tmp)
            if not res.get("ok") or not os.path.exists(rgba):
                return ToolResult(
                    content="", metadata={"success": False, "error": f"RGBA 重组失败: {res.get('stderr')}"}
                )
            return ToolResult(content=rgba, metadata={"success": True, "frames": len(in_files), "fps": fps})
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[MattingTool] matte_video 异常: {exc}")
            return ToolResult(content="", metadata={"success": False, "error": str(exc)})
        finally:
            if not workdir:
                shutil.rmtree(tmp, ignore_errors=True)

    async def _matte_image(self, gw: dict, image_path: str) -> bytes:
        """调用单个抠像网关抠单帧,返回 RGBA PNG 字节。

        约定:POST {gw.url}{MATTING_ENDPOINT},multipart 字段 image,返回 RGBA PNG。
        支持两种响应:直接返回图片字节;或返回 JSON(含 base64 / url)。网关不可用或返回非图片时抛异常,
        由上层换下一个候选网关或整体降级。
        """
        url = (gw["url"].rstrip("/") + config.MATTING_ENDPOINT)
        headers = {"Authorization": f"Bearer {gw.get('key') or ''}"}
        async with httpx.AsyncClient(timeout=30) as client:
            with open(image_path, "rb") as f:
                files = {"image": (os.path.basename(image_path), f, "image/png")}
                resp = await client.post(url, headers=headers, files=files)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "image" in ctype:
                return resp.content
            # 部分网关返回 JSON(含 base64 或 url):尽力解析
            try:
                body = resp.json()
                if isinstance(body, dict):
                    b64 = body.get("image") or body.get("png") or body.get("data")
                    if isinstance(b64, str) and "base64," in b64:
                        b64 = b64.split("base64,")[1]
                    if b64:
                        return base64.b64decode(b64)
            except Exception:  # noqa: BLE001
                pass
            raise RuntimeError(f"抠像网关返回非图片且无法解析: ctype={ctype}")
