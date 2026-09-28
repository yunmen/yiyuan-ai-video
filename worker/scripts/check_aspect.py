# -*- coding: utf-8 -*-
"""成片画幅校验:批量量真实宽高,判定是否满足竖版 9:16 硬要求。

为什么需要它
    产品硬要求「成片默认竖版 9:16」,但成片画幅会被多处影响:
      · 视频编辑(复刻)在 `gen.replicate_follow_reference_ratio=1` + 纯复刻时**跟随原片画幅**;
      · 图生视频 i2v 的画幅由 ratio 参数与首帧共同决定;
      · 多段拼接、数字人、九宫格出片各有自己的 ratio 来源。
    靠肉眼看/口算既慢又易错,这里用 ffprobe 读**真实像素宽高**做客观判定,
    输出「分辨率 / 宽高比 / 方向 / 偏差% / 结论」,并支持 JSON 便于存档。

术语
    · 目标画幅 target:形如 9:16 / 16:9 / 1:1(默认 9:16);
    · 偏差:实际宽高比与目标宽高比的**相对差**(%),超过 tolerance(默认 3%)即判定不通过。

用法
    # 直接量若干条(URL 或本地文件均可)
    python worker/scripts/check_aspect.py --video https://cos/xx/1.mp4 --video /tmp/2.mp4

    # 从清单文件批量量(每行:URL,或 `标签 | URL`,# 开头为注释)
    python worker/scripts/check_aspect.py --file videos.txt --target 9:16 --tolerance 3

    # 输出 JSON(便于 CI 存档/二次解析)
    python worker/scripts/check_aspect.py --file videos.txt --json

退出码
    0 = 全部通过;1 = 存在不通过 / 读取失败(可用于发布前卡点)。
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

# 目标画幅白名单(与 backend gen_rules.SUPPORTED_RATIOS 对齐)
SUPPORTED_TARGETS = ("9:16", "16:9", "1:1", "4:3", "3:4")
DEFAULT_TARGET = "9:16"
# 相对偏差容忍阈值(%):超过即判定「画幅不符」
DEFAULT_TOLERANCE = 3.0
# 常见竖版 9:16 目标分辨率(仅作提示,不参与判定)
COMMON_9_16 = ((1080, 1920), (720, 1280))

# 复刻/生成链路需要覆盖的入口(仅作覆盖提醒,不强制)
EXPECTED_ENTRIES = (
    "t2v", "i2v", "r2v", "edit", "multiseg", "replicate", "storyboard", "digital",
)


def parse_ratio(text: str) -> Optional[Tuple[int, int]]:
    """把 '9:16' 解析成 (9, 16);非法返回 None"""
    raw = str(text or "").strip().replace("：", ":")
    if ":" not in raw:
        return None
    left, _, right = raw.partition(":")
    try:
        w, h = int(left.strip()), int(right.strip())
    except (TypeError, ValueError):
        return None
    return (w, h) if w > 0 and h > 0 else None


def judge(width: int, height: int, target: Tuple[int, int], tolerance: float = DEFAULT_TOLERANCE) -> Dict[str, Any]:
    """判定某条成片的画幅是否符合目标(纯函数)

    返回:分辨率/实际宽高比/方向/偏差%/是否通过/结论说明。
    偏差 = |实际比 - 目标比| / 目标比 * 100;方向按宽高比较命名。
    """
    if not width or not height:
        return {"ok": False, "note": "分辨率非法"}
    actual = width / float(height)
    target_ratio = target[0] / float(target[1])
    deviation = abs(actual - target_ratio) / target_ratio * 100.0
    ok = deviation <= float(tolerance)
    if height > width:
        orientation = "竖版"
    elif width > height:
        orientation = "横版"
    else:
        orientation = "方形"
    note = "画幅符合目标" if ok else f"画幅不符(期望 {target[0]}:{target[1]},{orientation})"
    # 约简宽高比,便于与目标(如 9:16)直接比对;1080x1920 → 9:16
    divisor = math.gcd(width, height) or 1
    return {
        "ok": ok,
        "width": width,
        "height": height,
        "ratio": f"{width // divisor}:{height // divisor}",
        "orientation": orientation,
        "deviation_pct": round(deviation, 2),
        "note": note,
    }


def probe_size(ffprobe: str, path_or_url: str, timeout: int = 60) -> Optional[Tuple[int, int]]:
    """用 ffprobe 读取视频首个视频流的 (宽,高);读取失败返回 None

    与 media_prep.probe_size 同款命令;这里用同步 subprocess,便于脚本独立运行。
    """
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path_or_url],
            capture_output=True, text=True, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        raw = (proc.stdout or "").strip().splitlines()[0]
        w, h = raw.split("x")[:2]
        return int(w), int(h)
    except (ValueError, IndexError):
        return None


def parse_list_file(path: str) -> List[Tuple[str, str]]:
    """解析清单文件:每行 `URL` 或 `标签 | URL`;# 开头/空行为注释

    返回 [(标签, URL)];标签缺省为 '-'。
    """
    rows: List[Tuple[str, str]] = []
    with open(path, "r", encoding="utf-8") as fp:
        for line in fp:
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            if "|" in text:
                label, _, url = text.partition("|")
                rows.append((label.strip() or "-", url.strip()))
            else:
                rows.append(("-", text))
    return rows


def check_all(
    inputs: List[Tuple[str, str]], target: Tuple[int, int],
    tolerance: float = DEFAULT_TOLERANCE, ffprobe: Optional[str] = None,
) -> Dict[str, Any]:
    """批量校验,返回结构化结果(含逐条明细与汇总)"""
    binary = ffprobe or shutil.which("ffprobe")
    items: List[Dict[str, Any]] = []
    for label, url in inputs:
        item: Dict[str, Any] = {"label": label, "video": url}
        if not binary:
            item.update({"ok": False, "note": "未找到 ffprobe(请安装 ffmpeg,或把 ffprobe 加入 PATH)"})
            items.append(item)
            continue
        size = probe_size(binary, url)
        if not size:
            item.update({"ok": False, "note": "读取分辨率失败(URL 不可达 / 非视频 / ffprobe 报错)"})
            items.append(item)
            continue
        item.update(judge(size[0], size[1], target, tolerance))
        items.append(item)

    passed = sum(1 for i in items if i.get("ok"))
    failed = sum(1 for i in items if not i.get("ok"))
    covered = {i["label"] for i in items if i.get("label") not in (None, "-")}
    return {
        "target": f"{target[0]}:{target[1]}",
        "tolerance_pct": tolerance,
        "total": len(items),
        "passed": passed,
        "failed": failed,
        "covered_entries": sorted(covered),
        "missing_entries": [e for e in EXPECTED_ENTRIES if e not in covered],
        "items": items,
    }


def _short(text: str, width: int = 52) -> str:
    """URL 过长时中间省略,保证表格对齐可读"""
    text = str(text or "")
    if len(text) <= width:
        return text
    keep = (width - 3) // 2
    return f"{text[:keep]}...{text[-keep:]}"


def render_table(result: Dict[str, Any]) -> str:
    """把结果渲染成等宽表格文本"""
    lines = []
    header = f"{'#':<3}{'标签':<12}{'分辨率':<14}{'宽高比':<12}{'方向':<6}{'偏差%':<8}{'结论'}"
    lines.append(f"目标画幅 {result['target']} · 容忍偏差 ±{result['tolerance_pct']}%")
    lines.append(header)
    lines.append("-" * 76)
    for idx, item in enumerate(result["items"], start=1):
        if item.get("width"):
            lines.append(
                f"{idx:<3}{item.get('label','-'):<12}"
                f"{str(item['width']) + 'x' + str(item['height']):<14}"
                f"{item.get('ratio','-'):<12}{item.get('orientation','-'):<6}"
                f"{item.get('deviation_pct','-'):<8}"
                f"{'通过' if item.get('ok') else '不通过'}"
            )
        else:
            lines.append(f"{idx:<3}{item.get('label','-'):<12}{'-':<14}{'-':<12}{'-':<6}{'-':<8}{item.get('note','')}")
        lines.append(f"    {_short(item.get('video',''))}")
    lines.append("-" * 76)
    lines.append(
        f"合计 {result['total']} 条:通过 {result['passed']} / 不通过 {result['failed']}"
    )
    if result["target"] == "9:16":
        dims = " 或 ".join(f"{w}x{h}" for w, h in COMMON_9_16)
        lines.append(f"9:16 常见目标分辨率: {dims}")
    if result["missing_entries"]:
        lines.append(f"未覆盖入口(建议补齐各跑一条): {', '.join(result['missing_entries'])}")
    return "\n".join(lines)


def main() -> int:
    # Windows 控制台常见 GBK 编码:遇到无法编码的字符会直接抛 UnicodeEncodeError,
    # 这里改成「无法编码则替换」,保证脚本在任意终端都能正常打印结果(不因输出编码崩掉)。
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass

    parser = argparse.ArgumentParser(description="成片画幅校验(默认判定竖版 9:16)")
    parser.add_argument("--video", action="append", default=[],
                        help="待校验的视频 URL 或本地文件(可重复)")
    parser.add_argument("--file", dest="list_file", default=None,
                        help="清单文件:每行 `URL` 或 `标签 | URL`(# 为注释)")
    parser.add_argument("--target", default=DEFAULT_TARGET,
                        help=f"目标画幅(默认 {DEFAULT_TARGET};可选 {'/'.join(SUPPORTED_TARGETS)})")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE,
                        help=f"相对偏差容忍阈值 %% (默认 {DEFAULT_TOLERANCE})")
    parser.add_argument("--json", action="store_true", help="输出 JSON(便于存档/CI 解析)")
    args = parser.parse_args()

    target = parse_ratio(args.target)
    if not target:
        print(f"目标画幅非法: {args.target}(应为 9:16 / 16:9 / 1:1 等)", file=sys.stderr)
        return 1

    inputs: List[Tuple[str, str]] = [("-", url) for url in args.video]
    if args.list_file:
        try:
            inputs.extend(parse_list_file(args.list_file))
        except OSError as exc:
            print(f"清单文件读取失败: {exc}", file=sys.stderr)
            return 1
    if not inputs:
        print("未提供待校验视频:请用 --video 或 --file 指定", file=sys.stderr)
        return 1

    result = check_all(inputs, target, args.tolerance)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_table(result))
    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
