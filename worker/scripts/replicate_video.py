# -*- coding: utf-8 -*-
'''
@文件    :replicate_video.py
@说明    :视频复刻脚本 — 以参考视频为模板,走项目生成链路(r2v)产出同款新视频
@用法    :python scripts/replicate_video.py --video <参考视频> --out <输出目录>
'''
import argparse
import asyncio
import base64
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENVIRONMENT", "dev")


def probe_duration(video: str) -> float:
    """读取视频时长(秒)"""
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", video],
        capture_output=True, text=True,
    )
    try:
        return float((res.stdout or "").strip())
    except ValueError:
        return 0.0


def _shots(video: str, count: int) -> List[float]:
    """按时长均匀取 count 个抽帧时间点"""
    dur = probe_duration(video)
    if dur <= 0:
        return [0.0]
    return [round(dur * i / count, 3) for i in range(count)]


def extract_frames(video: str, count: int = 4, width: int = 720) -> List[str]:
    """抽帧返回 base64 data URI(模型可直接拉取)"""
    tmp = tempfile.mkdtemp(prefix="replicate_frames_")
    uris: List[str] = []
    try:
        for idx, ts in enumerate(_shots(video, count)):
            dst = os.path.join(tmp, f"f{idx}.jpg")
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(ts), "-i", video,
                 "-frames:v", "1", "-q:v", "6", "-vf", f"scale={width}:-1", dst],
                capture_output=True,
            )
            if os.path.exists(dst):
                with open(dst, "rb") as fp:
                    data = fp.read()
                    from app.utils.oss import upload_bytes
                    import uuid
                    url = upload_bytes(data, f"generate/material/{uuid.uuid4().hex}.jpg")
                    uris.append(url or "data:image/jpeg;base64," + base64.b64encode(data).decode())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return uris


def build_context(frames: int, duration: int, ratio: str, script: str) -> str:
    """按项目格式组装 [模板结构]/[商家信息]/[生成模式] 上下文"""
    head = "\n".join([
        "[模板结构]",
        "模板:参考视频复刻",
        f"时长:{duration} 秒 | 画幅:{ratio}",
        "画面要求:复刻参考画面的场景、构图、运镜与色调,产出同款质感的新视频",
    ])
    merchant = "[商家信息]\n口播文案:" + script if script else ""
    mode = "\n".join([
        "[生成模式]",
        "参考生视频",
        f"{frames} 张参考画面(来自参考视频抽帧,请保持其场景、构图、色调与质感)",
    ])
    return "\n\n".join([head, merchant, mode]) if merchant else "\n\n".join([head, mode])


async def replicate(video, out, script, duration, ratio, model="") -> str:
    """走 worker 链路复刻一条新视频,返回成片本地路径"""
    from app.tools.video_tool import VideoGenTool
    from app.core.plugin import logger

    frames = extract_frames(video, count=4)
    if not frames:
        raise RuntimeError("参考视频抽帧失败")
    if model:
        from app.settings import config
        config.VIDEO_MODEL_R2V = model
    logger.info(f"[replicate] 抽帧完成: {len(frames)} 张")
    params = {
        "prompt_context": build_context(len(frames), duration, ratio, script),
        "materials": frames,
        "gen_mode": "r2v",
        "gen_duration": duration,
        "ratio": ratio,
        "resolution": "1080P",
    }
    result = await VideoGenTool().generate(params)
    if not result.metadata.get("success", True):
        raise RuntimeError(result.metadata.get("error") or result.content)
    url = result.content
    logger.info(f"[replicate] 生成完成: {url}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "replicated.mp4")
    import httpx
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as cli:
        resp = await cli.get(url)
        resp.raise_for_status()
        with open(path, "wb") as fp:
            fp.write(resp.content)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="以参考视频为模板复刻新视频")
    ap.add_argument("--video", required=True, help="参考视频路径")
    ap.add_argument("--out", default="output", help="成片输出目录")
    ap.add_argument("--script", default="", help="口播文案/卖点(可选)")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--ratio", default="9:16")
    ap.add_argument("--model", default="", help="覆盖参考生视频模型")
    args = ap.parse_args()
    path = asyncio.run(replicate(args.video, args.out, args.script, args.duration, args.ratio, args.model))
    print(f"成片已保存: {path}")


if __name__ == "__main__":
    main()
