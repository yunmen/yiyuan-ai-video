# -*- coding: utf-8 -*-
"""本地真人处理 CLI —— 对参考视频里的真人区域去打码,让"含真人的素材"能通过方舟隐私审核。

核心实现在 `app/core/deidentify.py`:worker 的自动兜底(提交被"含真人"拦下时自动处理并重试)
与此脚本**共用同一份逻辑** —— 手测效果与线上行为才可能一致,不会出现两套实现各自漂移。

用法:
    python scripts/deidentify_person.py --video in.mp4 --out out.mp4
    # 只输出到本地文件;线上链路是自己去重+上传 COS(见 media_prep.deidentify_reference_video)
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import deidentify  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="本地真人处理(去身份化):抽样检测 + 固定框打码")
    ap.add_argument("--video", required=True, help="输入视频(本地路径)")
    ap.add_argument("--out", required=True, help="输出视频(本地路径)")
    ap.add_argument("--blocks", type=int, default=deidentify.DEFAULT_BLOCKS,
                    help=f"马赛克块数(越小越糊,默认 {deidentify.DEFAULT_BLOCKS})")
    ap.add_argument("--pad", type=float, default=deidentify.BOX_PAD,
                    help=f"检测框外扩比例(默认 {deidentify.BOX_PAD})")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        print(f"输入不存在: {args.video}")
        return 1

    t0 = time.time()
    try:
        info = deidentify.deidentify_video(args.video, args.out, args.blocks, args.pad)
    except Exception as exc:  # noqa: BLE001
        print(f"处理失败: {exc}")
        return 1

    if not info.get("detected"):
        print(f"未检测到真人(耗时 {time.time() - t0:.1f}s):无需处理,保持原片")
        return 3
    print(f"完成: {args.out}(耗时 {time.time() - t0:.1f}s)")
    print(f"  源尺寸={info.get('size')} 检测命中={info.get('hits')} 打码区={info.get('box')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
