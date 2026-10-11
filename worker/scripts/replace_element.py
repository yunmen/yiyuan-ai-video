# -*- coding: utf-8 -*-
'''
@文件    :replace_element.py
@说明    :视频元素替换直测脚本 — 参考视频 + 参考图直接走 worker 的 v2v 视频编辑链路,
          验证「把视频里的产品/人物/场景换成参考图内容,其余保持原样」的实际成片效果
@用法    :python scripts/replace_element.py --video <参考视频路径或URL> --image <参考图路径或URL> [--intent person]
'''
import argparse
import asyncio
import base64
import os
import sys
from typing import Dict, List
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENVIRONMENT", "dev")

# 各意图的「替换」指令文案,与 backend/app/services/prompt_builder.build_replace_requirement 保持一致
# (worker 是独立进程,不 import backend,文案在此镜像维护;改动时两边同步)
_REPLACE_TEXTS: Dict[str, tuple] = {
    "product": ("商品与品牌标识", "视频中的商品与品牌标识必须替换为用户上传的商品图内容,不得沿用原商品"),
    "person": ("出镜人物", "视频中的出镜人物必须替换为用户上传的人物参考图,保持该人物外观一致,不得沿用原人物"),
    "scene": ("场景与背景", "视频中的场景与背景必须替换为用户上传/指定的场景,保留主体与运镜节奏"),
}
# 全部意图维度(用于反向生成「未被替换元素保持原样」条款)
_ALL_DIMS = ("商品与品牌标识", "出镜人物", "场景与背景")


def _to_url(path_or_url: str, kind: str) -> str:
    """把素材统一转成模型可访问的形式

    http(s)/data URI 直接返回;本地文件上传 OSS 得公网 URL。
    OSS 未启用时的回退:图片转 base64 data URI(模型可直接拉取);
    视频体积大,base64 不可行,直接报错提示需启用 OSS。
    """
    s = str(path_or_url or "").strip()
    if s.startswith(("http://", "https://", "data:")):
        return s
    if not os.path.exists(s):
        raise RuntimeError(f"素材文件不存在: {s}")
    with open(s, "rb") as fp:
        data = fp.read()
    ext = os.path.splitext(s)[1].lower().lstrip(".") or ("jpg" if kind == "image" else "mp4")
    try:
        from app.utils.oss import upload_bytes
        url = upload_bytes(data, f"generate/material/{uuid4().hex}.{ext}")
        if url:
            return url
    except Exception as exc:  # noqa: BLE001
        if kind == "video":
            raise RuntimeError(f"参考视频上传 OSS 失败,无法继续(视频无法回退 base64,请启用 OSS): {exc}") from exc
    if kind == "video":
        raise RuntimeError("参考视频必须转成公网 URL 才能被模型拉取,请启用 OSS 后重试")
    return f"data:image/{ext};base64," + base64.b64encode(data).decode()


def build_replace_rules(intents: List[str]) -> str:
    """按意图组装替换指令:选中维度替换 + 未选中维度保持原样 + 非首帧护栏

    与 backend 的 build_replace_requirement 同构:只说"换什么"模型会把上传图
    当首帧重画整片,必须点名"不许动什么"。
    """
    rules: List[str] = []
    keeps: List[str] = []
    for dim, (label, text) in _REPLACE_TEXTS.items():
        if dim in intents:
            rules.append(text)
        else:
            keeps.append(label)
    if not rules:
        # 意图未命中任何维度时,退回 blanket 指令(与后端默认行为一致)
        return (
            "视频中的商品与出镜主体必须替换为用户上传的商品图内容,"
            "不得保留参考视频中的原有商品、人物与品牌标识"
        )
    if keeps:
        rules.append(f"参考视频中的{'、'.join(keeps)}必须保持原样,不得改动或重新生成")
    rules.append(
        "用户上传的图片仅作为被替换元素的参考,不是视频首帧;"
        "除被替换的元素外,严格保持参考视频的场景、背景、运镜、节奏与镜头语言"
    )
    return "；".join(rules)


def build_context(intents: List[str], duration: int, ratio: str, script: str) -> str:
    """按项目格式组装 [模板结构]/[商家信息]/[生成模式]/[补充要求] 上下文"""
    head = "\n".join([
        "[模板结构]",
        "模板:参考视频元素替换(直测)",
        f"时长:{duration} 秒 | 画幅:{ratio}",
    ])
    merchant = "[商家信息]\n口播文案:" + script if script else ""
    mode = "\n".join([
        "[生成模式]",
        "视频编辑(v2v)",
        "1 段参考视频(复刻其场景、构图、运镜、节奏与转场,产出同款新片);"
        "1 张替换参考图(仅用于按所选意图替换参考视频中的对应元素,"
        "不是视频首帧,不得以它们为起点重新生成场景)",
    ])
    extra = "[补充要求]\n" + build_replace_rules(intents)
    parts = [head] + ([merchant] if merchant else []) + [mode, extra]
    return "\n\n".join(parts)


async def replace_element(video: str, image: str, intents: List[str], out: str,
                          duration: int, ratio: str, script: str) -> str:
    """走 worker v2v 视频编辑链路做元素替换,返回成片本地路径"""
    from app.tools.video_tool import VideoGenTool
    from app.core.plugin import logger

    ref_video = _to_url(video, "video")
    ref_image = _to_url(image, "image")
    logger.info(f"[replace] 参考视频: {ref_video}")
    logger.info(f"[replace] 替换参考图: {ref_image}")
    params = {
        "prompt_context": build_context(intents, duration, ratio, script),
        # materials 只放图片(替换参考图);参考视频必须走独立字段,generate 才会进视频编辑分支
        "materials": [ref_image],
        "reference_video": ref_video,
        "gen_mode": "v2v",
        "gen_duration": duration,
        "ratio": ratio,
        "resolution": "1080P",
    }
    result = await VideoGenTool().generate(params)
    if not result.metadata.get("success", True):
        raise RuntimeError(result.metadata.get("error") or result.content)
    url = result.content
    logger.info(f"[replace] 生成完成: {url}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"replaced_{'_'.join(intents) or 'blanket'}.mp4")
    import httpx
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as cli:
        resp = await cli.get(url)
        resp.raise_for_status()
        with open(path, "wb") as fp:
            fp.write(resp.content)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="参考视频元素替换直测(视频编辑 v2v)")
    ap.add_argument("--video", required=True, help="参考视频(本地路径或公网 URL)")
    ap.add_argument("--image", required=True, help="替换参考图(本地路径或公网 URL)")
    ap.add_argument("--intent", action="append", default=[],
                    choices=["person", "product", "scene"],
                    help="替换意图,可多次传入(如 --intent person);不传则退回 blanket 指令")
    ap.add_argument("--out", default="output", help="成片输出目录")
    ap.add_argument("--script", default="", help="口播文案(可选;不填沿用原片声音)")
    ap.add_argument("--duration", type=int, default=10, help="成片时长(秒,模型单段上限约 15)")
    ap.add_argument("--ratio", default="9:16", help="画幅,如 9:16 / 16:9")
    args = ap.parse_args()
    path = asyncio.run(replace_element(
        args.video, args.image, args.intent, args.out, args.duration, args.ratio, args.script,
    ))
    print(f"成片已保存: {path}")


if __name__ == "__main__":
    main()
