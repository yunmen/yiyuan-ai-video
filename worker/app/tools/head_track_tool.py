# -*- coding: utf-8 -*-
'''
@文件    :head_track_tool.py
@说明    :头部检测工具 — 把成片按采样帧送到头部检测网关,产出头部 RegionTimeline,
        供「字幕跟随头部(caption-tracking)」把每条字幕锚定到说话人头部上沿中心。
@时间    :2026/10/01
@作者    :一源AI
@版本    :1.0
@说明    :对齐 Hypit production/caption-tracking.md。头部检测是可选外部能力,由 gen.route.head
        显式指向某个 gen.gw.<name> 网关;未配置 / 任一帧失败 → 返回 None,
        由调用方(subtitle 烧录)降级到普通底部字幕,保证「没接头部检测也能出片」。
        网关约定:POST {网关地址}{HEAD_ENDPOINT} 上传图片(multipart 字段 image),
        返回 JSON {"regions":[{"t":秒,"box":[x,y,w,h]}]}(x/y/w/h 归一化 0~1,
        框为完整头部含头发/帽子余量)。稳定输入是 RegionTimeline,检测器调用可置于项目侧准备步骤。
'''
import asyncio
import os
import shutil
import tempfile
from typing import List, Optional, Tuple

import httpx

from app.settings import config
from app.core.plugin import logger
from app.core import gateway, compose


class HeadTrackTool:
    """头部检测:采样成片帧 → 送检 → 产出 RegionTimeline(归一化头部框序列)。

    返回:[(t, x, y, w, h), ...](t 秒,x/y/w/h 归一化 0~1);无网关 / 无头 / 失败返回 None。
    """

    capability = "head"

    async def detect(
        self, video_local: str, sample_fps: Optional[float] = None,
    ) -> Optional[list]:
        """检测成片中的头部轨迹,返回 [(t,x,y,w,h)...] 或 None(降级用)。

        参数:
          video_local:本地成片路径(调用方已下载到本地)。
          sample_fps :采样帧率(默认 config.HEAD_SAMPLE_FPS,每秒 1 帧足够且省检测开销)。
        """
        gateways = gateway.resolve_all(self.capability)
        if not gateways:
            logger.info("[HeadTrackTool] 未配置头部检测网关(gen.route.head),字幕跟随头部降级为底部字幕")
            return None
        fps = sample_fps if sample_fps and sample_fps > 0 else (config.HEAD_SAMPLE_FPS or 1.0)
        tmp = tempfile.mkdtemp(prefix="headtrack_")
        try:
            frames = self._sample_frames(video_local, tmp, fps)
            if not frames:
                logger.warning("[HeadTrackTool] 抽帧为空,跳过头部检测")
                return None
            sem = asyncio.Semaphore(max(1, int(config.HEAD_CONCURRENCY)))
            # 逐帧送检:同一帧失败换下一个网关候选;整帧都失败则该帧无头部(字幕回退底部)
            async def _one(item):
                t, path = item
                for gw in gateways:
                    try:
                        async with sem:
                            box = await self._detect_image(gw, path)
                        if box:
                            return (t, box[0], box[1], box[2], box[3])
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"[HeadTrackTool] 帧 t={t} 经网关[{gw['name']}]失败: {exc}")
                return None

            results = await asyncio.gather(*[_one(it) for it in frames])
            boxes = [r for r in results if r]
            if not boxes:
                logger.info("[HeadTrackTool] 未检测到任何头部,降级底部字幕")
                return None
            return boxes
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[HeadTrackTool] detect 异常,降级底部字幕: {exc}")
            return None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _sample_frames(self, video: str, out_dir: str, fps: float) -> List[tuple]:
        """按 fps 均匀抽帧,返回 [(t秒, 本地帧路径), ...];ffmpeg 不可用时返回 []。"""
        ffmpeg = compose.ffmpeg_path()
        if not ffmpeg:
            return []
        out = os.path.join(out_dir, "frame_%04d.png")
        cmd = [ffmpeg, "-y", "-i", video, "-vf", f"fps={fps}", out]
        res = compose.run(cmd, timeout=120, cwd=out_dir)
        if not res.get("ok"):
            logger.warning(f"[HeadTrackTool] 抽帧失败: {res.get('stderr')}")
            return []
        files = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
        # fps 采样是均匀的:第 i 帧时间 ≈ i / fps(从 0 起算)
        return [(i / fps, os.path.join(out_dir, f)) for i, f in enumerate(files)]

    async def _detect_image(self, gw: dict, image_path: str) -> Optional[List[float]]:
        """调用单个头部检测网关检单帧,返回 [x,y,w,h](归一化) 或 None。

        支持响应:直接 {"box":[...]} / {"regions":[{"box":[...]}]} / 列表。
        取框内面积最大者(同一画面多张脸时优先主体)。
        """
        url = (gw["url"].rstrip("/") + config.HEAD_ENDPOINT)
        headers = {"Authorization": f"Bearer {gw.get('key') or ''}"}
        async with httpx.AsyncClient(timeout=20) as client:
            with open(image_path, "rb") as f:
                files = {"image": (os.path.basename(image_path), f, "image/png")}
                resp = await client.post(url, headers=headers, files=files)
            resp.raise_for_status()
            body = resp.json()
        return self._parse_box(body)

    @staticmethod
    def _parse_box(body) -> Optional[List[float]]:
        """从网关响应里尽力解析出 [x,y,w,h](归一化);解析不出返回 None。"""
        if isinstance(body, list) and body:
            body = body[0]
        if not isinstance(body, dict):
            return None
        cand = body.get("box") or body.get("regions")
        boxes: List[List[float]] = []
        if isinstance(cand, list):
            if cand and isinstance(cand[0], dict):
                boxes = [c.get("box") for c in cand if isinstance(c, dict)]
            elif all(isinstance(c, (int, float)) and len(cand) == 4 for c in cand):
                boxes = [cand]
        boxes = [b for b in boxes if isinstance(b, list) and len(b) == 4
                 and all(isinstance(v, (int, float)) for v in b)]
        if not boxes:
            return None
        # 取面积最大者(主体头部),避免把听众/采访者的脸误当主讲
        return max(boxes, key=lambda b: float(b[2]) * float(b[3]))
