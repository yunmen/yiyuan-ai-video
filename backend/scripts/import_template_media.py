# -*- coding: utf-8 -*-
'''
@文件    :import_template_media.py
@说明    :模板示例视频/封面素材导入脚本(上传对象存储并回填模板,幂等)
@时间    :2026/09/29 11:00:00

用途:
  模板的示例视频与封面由外部生成/剪辑好后,用本脚本上传到对象存储并回填到
  tb_video_template,用户端列表即可展示视频首帧预览与封面图。
  同一模板重复执行会覆盖地址(以最后一次为准),不会新增记录。

用法(需在 backend 容器内执行,凭据与对象存储配置来自 backend/env/.env.<env>):
  docker exec -e ENVIRONMENT=prod backend python scripts/import_template_media.py \
    --title "深夜烟火大排档" --video /tmp/demo.mp4 --cover /tmp/demo.jpg
  docker exec -e ENVIRONMENT=prod backend python scripts/import_template_media.py \
    --title "深夜烟火大排档" --video /tmp/demo.mp4 --dry-run

参数说明:
  --title     模板标题(用于定位模板,必填)
  --category  模板分类(同名标题存在多条时用于消歧,可选)
  --video     本地示例视频路径(mp4/mov/m4v/webm)
  --cover     本地封面图路径(jpg/png/webp,可选)
  --clear     清空该模板的示例视频与封面(连同对象存储上的文件一并删除),
              用于素材授权不符或内容与模板不匹配时回退到文字兜底展示
  --env       目标环境(默认取环境变量 ENVIRONMENT,再回退 prod)
  --dry-run   只打印将要上传与回填的内容,不真正执行
'''
import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# 让脚本能从 backend 根目录直接运行
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    """解析命令行参数(ENVIRONMENT 必须在导入 app.settings 之前确定)"""
    parser = argparse.ArgumentParser(description="上传模板示例视频/封面并回填模板")
    parser.add_argument("--title", required=True, help="模板标题(用于定位模板)")
    parser.add_argument("--category", default="", help="模板分类(同名标题多条时用于消歧)")
    parser.add_argument("--video", default="", help="本地示例视频路径")
    parser.add_argument("--cover", default="", help="本地封面图路径")
    parser.add_argument(
        "--clear", action="store_true",
        help="清空模板的示例视频与封面(含对象存储文件)",
    )
    parser.add_argument(
        "--env", default=os.getenv("ENVIRONMENT") or "prod",
        help="目标环境:决定读取 backend/env/.env.<env>",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印计划,不上传不写库")
    return parser.parse_args()


# 模块级解析:app.settings 在导入时即按 ENVIRONMENT 读取对应环境文件
ARGS = parse_args()
os.environ["ENVIRONMENT"] = ARGS.env

from tortoise import Tortoise  # noqa: E402
from app.settings import config  # noqa: E402
from app.core.oss import get_oss  # noqa: E402
from app.models.video import VideoTemplateModel  # noqa: E402


# 允许导入的媒体扩展名(与 app/core/upload.py 的上传白名单保持一致)
ALLOWED_VIDEO = {"mp4", "mov", "m4v", "webm"}
ALLOWED_IMAGE = {"jpg", "jpeg", "png", "webp"}


def read_media(path: str, allowed: set) -> tuple[bytes, str]:
    """读取本地媒体文件并返回(字节内容, 扩展名);路径不存在或类型不支持时抛出中文错误"""
    file = Path(path)
    if not file.is_file():
        raise ValueError(f"文件不存在: {path}")
    ext = file.suffix.lstrip(".").lower()
    if ext not in allowed:
        raise ValueError(f"不支持的文件类型:.{ext}(允许 {', '.join(sorted(allowed))})")
    return file.read_bytes(), ext


def build_key(kind: str, ext: str) -> str:
    """按 用途/日期/随机名 组织对象存储路径,避免与用户上传目录混淆"""
    day = datetime.now().strftime("%Y%m%d")
    return f"templates/{kind}/{day}/{uuid.uuid4().hex}.{ext}"


async def upload(oss, kind: str, path: str, allowed: set) -> Optional[str]:
    """上传单个媒体文件到对象存储,返回公网访问地址"""
    content, ext = read_media(path, allowed)
    key = build_key(kind, ext)
    if ARGS.dry_run:
        print(f"[待上传] {kind}: {path} -> {key}({len(content)} 字节)")
        return oss.public_url(key) if oss else f"https://<bucket>.cos.<region>.myqcloud.com/{key}"
    return await asyncio.to_thread(oss.put_object, key, content)


def media_key(url: str, oss) -> str:
    """从公网访问地址反解对象存储 key;非本桶地址返回空串"""
    prefix = f"https://{oss.bucket}.cos.{oss.region}.myqcloud.com/"
    return url[len(prefix):] if url.startswith(prefix) else ""


async def clear_media(oss, template) -> int:
    """清空模板的示例视频与封面,并删除对象存储上的对应文件"""
    cleared = []
    for field, label in (("video_url", "示例视频"), ("cover", "封面图")):
        url = getattr(template, field)
        if not url:
            continue
        key = media_key(url, oss)
        if key:
            if ARGS.dry_run:
                print(f"[待删除] {label}: {key}")
            else:
                await asyncio.to_thread(oss.delete_object, key)
        setattr(template, field, "")
        cleared.append(field)

    if not ARGS.dry_run and cleared:
        await template.save(update_fields=cleared)

    print("-" * 56)
    print(f"模板: {template.category} / {template.title}(id={template.id})")
    print(f"清理字段: {', '.join(cleared) if cleared else '无(本来就没有素材)'}")
    print("模式: 预演(未删除未写库)" if ARGS.dry_run else "模式: 已删除素材并清空地址")
    return 0


async def run() -> int:
    """定位模板 → 上传素材或清理素材"""
    if ARGS.clear and (ARGS.video or ARGS.cover):
        print("[错误] --clear 不能与 --video/--cover 同时使用", file=sys.stderr)
        return 2
    if not ARGS.clear and not ARGS.video and not ARGS.cover:
        print("[错误] 至少需要提供 --video 或 --cover 中的一个", file=sys.stderr)
        return 2

    oss = get_oss()
    if oss is None:
        print("[错误] 对象存储未启用或配置不完整,无法上传素材", file=sys.stderr)
        return 1

    await Tortoise.init(config=config.ORM_CONFIG)
    try:
        query = {"title": ARGS.title}
        if ARGS.category:
            query["category"] = ARGS.category
        template = await VideoTemplateModel.get_or_none(**query)
        if template is None:
            print(f"[错误] 未找到模板: {ARGS.title}{' / ' + ARGS.category if ARGS.category else ''}", file=sys.stderr)
            return 1

        if ARGS.clear:
            return await clear_media(oss, template)

        update_fields = []
        if ARGS.video:
            template.video_url = await upload(oss, "video", ARGS.video, ALLOWED_VIDEO)
            update_fields.append("video_url")
        if ARGS.cover:
            template.cover = await upload(oss, "cover", ARGS.cover, ALLOWED_IMAGE)
            update_fields.append("cover")

        if not ARGS.dry_run and update_fields:
            await template.save(update_fields=update_fields)

        print("-" * 56)
        print(f"模板: {template.category} / {template.title}(id={template.id})")
        print(f"示例视频: {template.video_url or '未设置'}")
        print(f"封面图: {template.cover or '未设置'}")
        print("模式: 预演(未上传未写库)" if ARGS.dry_run else "模式: 已上传并回填")
        return 0
    finally:
        await Tortoise.close_connections()


def main() -> int:
    """脚本入口"""
    try:
        return asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 素材导入失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
