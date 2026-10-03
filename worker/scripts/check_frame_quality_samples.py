# -*- coding: utf-8 -*-
'''退化画面检测的真实样本验证:量误报率与漏报率

为什么要这个脚本:`detect_degenerate_frame` 的判据(高饱和占比 ≥ 0.70 / 唯一颜色数 ≤ 8)
是在**一张**彩条成片和**一张**正常图上定出来的,样本太少 —— 误杀的代价是「正常成片被判
失败 + 白扣用户额度」,上线前必须用一批真实画面量一遍误报率。

两组样本:
  1. 正常画面(必须**放行**):默认从 picsum(真实摄影作品,含人物/街景/商品/自然)按种子
     稳定取 N 张;也可用 --dir 指定本地真实素材目录(更贴近带货画面,优先推荐)。
     另取若干张灰度图:灰度照片饱和度天然为 0,用来验证"低饱和 ≠ 无内容"。
  2. 退化画面(必须**拦截**):本地用 ffmpeg 生成彩条/测试卡/纯黑/纯白/纯灰/纯红,
     不需要联网 —— 这正是线上会遇到的废片形态。

用法(在 worker 目录执行):
  python scripts/check_frame_quality_samples.py                 # 默认 30 张
  python scripts/check_frame_quality_samples.py --count 50
  python scripts/check_frame_quality_samples.py --dir D:/真实素材
'''
import argparse
import asyncio
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402

from app.core import frame_quality as fq  # noqa: E402
from app.core.compose import run  # noqa: E402

# 真实摄影作品(按种子稳定取图,同一 seed 每次是同一张);灰度图用于验证低饱和不该被误杀
_PHOTO_URL = "https://picsum.photos/seed/{seed}/640/360"
_GRAY_URL = "https://picsum.photos/seed/{seed}/640/360?grayscale"
# 部分站点拒绝无 UA 的请求
_UA = {"User-Agent": "yiyuan-frame-quality-check/1.0 (offline evaluation script)"}
# 退化画面对照:全部本地生成(ffmpeg lavfi),与线上"彩条/测试卡/纯色"废片同形
_DEGENERATE_CASES = {
    "彩条测试卡(smptebars)": "smptebars=size=640x360:rate=1:duration=1",
    "电视测试图(testsrc)": "testsrc=size=640x360:rate=1:duration=1",
    "纯黑": "color=c=black:s=640x360:d=1",
    "纯白": "color=c=white:s=640x360:d=1",
    "纯灰": "color=c=gray:s=640x360:d=1",
    "纯红": "color=c=red:s=640x360:d=1",
}


async def _generate(name: str, workdir: str) -> str:
    """用 ffmpeg 生成一张退化画面(不需要联网)"""
    path = os.path.join(workdir, f"{name}.jpg")
    await run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", _DEGENERATE_CASES[name],
        "-frames:v", "1", "-q:v", "2", path,
    ], timeout=60)
    return path


def _download(url: str, path: str, timeout: float = 20.0) -> bool:
    """下载一张真实画面;失败返回 False(不抛异常,网络问题不该中断整轮验证)"""
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers=_UA)
        if resp.status_code != 200 or not resp.content:
            return False
        with open(path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception:  # noqa: BLE001 —— 单张取不到只记一次,继续跑剩下的
        return False


def _local_images(dir_path: str):
    """收集本地目录里的图片(按扩展名过滤,不递归过深)"""
    exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    found = []
    for root, _dirs, files in os.walk(dir_path):
        for name in files:
            if name.lower().endswith(exts):
                found.append(os.path.join(root, name))
    return sorted(found)


def _hue_buckets(data: bytes) -> int:
    """色相桶数(12 桶,每桶 30°):只统计"够鲜艳"的像素(S>=0.5)。

    彩条把 12 个色相桶占掉大半(实测 10/12),而真实照片通常集中在 1~3 个色相
    (日落橙、草地绿…)。可作为"高饱和但仍是真实画面"的反向证据。
    """
    buckets = set()
    for i in range(0, len(data) - 2, 3):
        r, g, b = data[i], data[i + 1], data[i + 2]
        mx, mn = max(r, g, b), min(r, g, b)
        if mx == 0 or (mx - mn) / mx < 0.5:
            continue
        d = float(mx - mn)
        if mx == r:
            hue = ((g - b) / d) % 6
        elif mx == g:
            hue = (b - r) / d + 2
        else:
            hue = (r - g) / d + 4
        buckets.add(int(hue * 60 / 360) % 12)
    return len(buckets)


def _mean_gradient(data: bytes, width: int) -> float:
    """水平相邻像素的平均亮度差(细节/纹理强度)

    彩条是大块平坦纯色 → 梯度低;真实画面即便大片高饱和,也有丰富纹理 → 梯度高。
    """
    if width <= 1:
        return 0.0
    total, count = 0, 0
    row_len = width * 3
    for y in range(0, len(data) // row_len):
        row = data[y * row_len:(y + 1) * row_len]
        for x in range(0, len(row) - 6, 3):
            lum_a = (row[x] * 299 + row[x + 1] * 587 + row[x + 2] * 114) / 1000
            lum_b = (row[x + 3] * 299 + row[x + 4] * 587 + row[x + 5] * 114) / 1000
            total += abs(lum_a - lum_b)
            count += 1
    return (total / count) if count else 0.0


async def _measure(path: str):
    """返回 (是否判为退化, 原因, 高饱和占比, 颜色数, 色相桶数, 平均梯度)"""
    data = await fq._read_pixels(path, timeout=60)
    if not data:
        return None, "取不到像素", None, None, None, None
    colors, high_sat, total = fq.analyze_pixels(data)
    reason = await fq.detect_degenerate_frame(path)
    ratio = (high_sat / total) if total else None
    size = await fq._probe_size(path, 60)
    width = fq._sample_size(*size)[0] if size else 0
    return bool(reason), reason or "", ratio, colors, _hue_buckets(data), _mean_gradient(data, width)


async def main_async(count: int, local_dir: str, video: str = "") -> int:
    workdir = tempfile.mkdtemp(prefix="frame_samples_")
    started = time.monotonic()
    normal, missing = [], []
    try:
        # ① 真实画面:优先本地目录,否则联网取
        if local_dir:
            paths = _local_images(local_dir)
            if not paths:
                print(f"[样本] 目录里没有图片: {local_dir}")
            for path in paths[:max(count, 1)]:
                normal.append((os.path.basename(path), path))
        else:
            for i in range(1, count + 1):
                # 每 10 张掺 1 张灰度:验证"低饱和 ≠ 无内容"不会被误杀
                url = (_GRAY_URL if i % 10 == 0 else _PHOTO_URL).format(seed=i)
                path = os.path.join(workdir, f"real_{i}.jpg")
                if _download(url, path):
                    normal.append((os.path.basename(path), path))
                else:
                    missing.append(url)

        print(f"[样本] 真实画面 {len(normal)} 张" + (f",取不到 {len(missing)} 张" if missing else ""))

        false_block = []      # 误杀:正常画面被判退化
        ratio_max = 0.0
        for name, path in normal:
            blocked, reason, ratio, colors, buckets, grad = await _measure(path)
            if ratio is not None:
                ratio_max = max(ratio_max, ratio)
            if blocked:
                false_block.append((name, reason, ratio, colors))
            print(f"  放行={not blocked} 高饱和={ratio:.3f} 颜色数={colors} "
                  f"色相桶={buckets} 梯度={grad:.2f} {name}")

        # ② 退化画面对照(本地生成,必须全部拦下)
        print("[样本] 退化画面对照(ffmpeg 生成):")
        missed = []
        for name in _DEGENERATE_CASES:
            path = await _generate(name, workdir)
            blocked, reason, ratio, colors, buckets, grad = await _measure(path)
            if not blocked:
                missed.append(name)
            print(f"  拦截={blocked} 高饱和={ratio} 颜色数={colors} "
                  f"色相桶={buckets} 梯度={grad:.2f} {name} {reason}")

        # ③ 真实成片(可选):直接走成片侧多帧检测,验证线上那类废片确实被拦
        if video:
            print(f"[样本] 真实成片检测: {video}")
            reason = await fq.detect_degenerate_video(video)
            print(f"  成片判定={'拦截:' + reason if reason else '放行'}")
            missed += [] if reason else [f"真实成片未被拦截({video})"]

        total_normal = len(normal)
        fp_rate = (len(false_block) / total_normal) if total_normal else 0.0
        print("")
        print("==== 结果 ====")
        print(f"真实画面 {total_normal} 张:误杀 {len(false_block)} 张,误报率 {fp_rate:.1%}"
              f"(最高高饱和占比 {ratio_max:.3f},阈值 {fq._MAX_HIGH_SAT_RATIO})")
        print(f"退化画面 {len(_DEGENERATE_CASES)} 张:漏放 {len(missed)} 张 {missed}")
        print(f"耗时 {time.monotonic() - started:.1f}s")
        if false_block:
            print("误杀明细(这些必须复核 —— 说明阈值过严):")
            for name, reason, ratio, colors in false_block:
                print(f"  {name}: {reason} (高饱和占比={ratio}, 颜色数={colors})")
        return 1 if (false_block or missed) else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="退化画面检测的真实样本验证(误报率/漏报率)")
    parser.add_argument("--count", type=int, default=30, help="联网取样的真实画面张数(默认 30)")
    parser.add_argument("--dir", default="", help="本地真实素材目录(给了就不联网)")
    parser.add_argument("--video", default="", help="真实成片地址/路径(可选):走成片侧多帧检测")
    args = parser.parse_args()
    return asyncio.run(main_async(args.count, args.dir, args.video))


if __name__ == "__main__":
    raise SystemExit(main())
