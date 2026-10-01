# -*- coding: utf-8 -*-
'''
@文件    :seed_digital.py
@说明    :数字人种子数据脚本(幂等,重复执行不会重复写入)
@时间    :2026/09/30 10:00:00
@作者    :一源AI
@版本    :1.0

数字人种子数据。

背景:
  tb_digital_human 为空时,用户端「数字人」市场页没有任何可选形象(显示"数字人整理中,敬请期待")。
  本脚本一次性铺一批可直接上架的数字人,头像/形象图/预览视频由运营在后台上传替换
  (脚本默认不写死任何外部地址,避免生产环境出现一堆裂图)。

  ⚠️ 真实出片前置:数字人口播依赖数字人模型与网关。二选一即可让任务建单后打到 worker 验证全链路:
    ① 在管理端「业务配置」填写 gen.digital_model(全局数字人模型名);
    ② 或给数字人记录填 model 字段(本脚本已填占位值,部署时替换为真实模型名)。
  未配置时 backend 会在扣额度前以明确原因拦截(设计如此,避免白扣额度)。

用法(需在 backend 容器内执行,容器才能解析数据库主机):
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_digital.py --dry-run
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_digital.py
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_digital.py --update
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_digital.py --placeholder-url https://<占位地址>

参数说明:
  --env             目标环境,决定读取 backend/env/.env.<env>(默认取环境变量 ENVIRONMENT,再回退 prod)
  --dry-run         只打印将要写入的数据,不写库
  --update          已存在同名数字人时更新(不覆盖头像/形象图/预览视频)
  --placeholder-url 头像/形象图/预览视频的占位地址;留空则不写地址,由运营在后台上传
'''
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# 让脚本能从 backend 根目录直接运行
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    """解析命令行参数(ENVIRONMENT 必须在导入 app.settings 之前确定)"""
    parser = argparse.ArgumentParser(description="初始化数字人种子数据(幂等)")
    parser.add_argument(
        "--env", default=os.getenv("ENVIRONMENT") or "prod",
        help="目标环境:决定读取 backend/env/.env.<env>(dev/test/prod)",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印计划写入的数据,不写库")
    parser.add_argument(
        "--update", action="store_true",
        help="已存在同名数字人时更新文案与风格(不覆盖头像/形象图/预览视频)",
    )
    parser.add_argument(
        "--placeholder-url", default="",
        help="头像/形象图/预览视频的占位地址;留空则不写地址,由运营在后台上传",
    )
    return parser.parse_args()


# 模块级解析:app.settings 在导入时即按 ENVIRONMENT 读取对应环境文件
ARGS = parse_args()
os.environ["ENVIRONMENT"] = ARGS.env

from tortoise import Tortoise  # noqa: E402
from tortoise.transactions import in_transaction  # noqa: E402
from app.settings import config  # noqa: E402
from app.models.digital import DigitalHumanModel  # noqa: E402


# 数字人种子。model 为占位模型名:部署时替换为真实数字人模型(或留空、改由 gen.digital_model 提供)。
# 头像/形象图/预览视频默认空,由运营在后台上传;传 --placeholder-url 时才填占位地址。
# default_text 为未填口播文案时的默认台词;pose_variants 为主视图派生(换姿势不换人)。
DIGITAL_HUMANS: List[Dict[str, Any]] = [
    {
        "name": "知性女主播 小鹿",
        "gender": "女", "style": "知性主播", "sort": 100, "active": True,
        "tags": ["带货", "口播", "知性"],
        "desc": "适合美妆、家居、知识类口播:正面半身、眼神看镜头,留右侧手势空间",
        "voice": "female-qingxin",
        "model": "doubao-seedance-digital-1.0",
        "default_text": "今天给大家分享一个我一直在用的好物,真的省心又好用,链接就放在视频下方。",
        "pose_variants": [
            {"name": "挥手致意", "image": ""},
            {"name": "侧身讲解", "image": ""},
        ],
    },
    {
        "name": "活力男讲师 阿杰",
        "gender": "男", "style": "活力讲师", "sort": 90, "active": True,
        "tags": ["课程", "讲解", "科技"],
        "desc": "适合课程预告、科技产品讲解:略偏右构图,左侧留给图表与字幕",
        "voice": "male-huoyue",
        "model": "doubao-seedance-digital-1.0",
        "default_text": "这门课我们只讲能上手的部分,从原理到实操一共八节,下周开讲,名额有限。",
        "pose_variants": [
            {"name": "指画面", "image": ""},
        ],
    },
    {
        "name": "专业女播报 安然",
        "gender": "女", "style": "新闻播报", "sort": 80, "active": True,
        "tags": ["播报", "资讯", "企业"],
        "desc": "适合资讯播报与品牌口播:虚拟演播室风格,画面稳定、适合批量产出",
        "voice": "female-zhuanzhu",
        "model": "doubao-seedance-digital-1.0",
        "default_text": "今天这条消息值得关注,政策已经落地,影响范围覆盖多数从业者,一分钟给你讲明白。",
        "pose_variants": [],
    },
]


# --update 时允许覆盖的字段:不含头像/形象图/预览视频,避免把运营已上传的素材冲掉
UPDATABLE_FIELDS = ("gender", "style", "desc", "tags", "voice", "model", "default_text", "pose_variants")


def build_payload(item: Dict[str, Any], placeholder_url: str) -> Dict[str, Any]:
    """把种子条目补齐为完整建库字段(占位地址为空时不写头像/形象图/预览视频)"""
    data: Dict[str, Any] = dict(item)
    data.setdefault("tags", [])
    data.setdefault("pose_variants", [])
    data.setdefault("active", True)
    if placeholder_url:
        data.setdefault("avatar", placeholder_url)
        data.setdefault("image", placeholder_url)
        data.setdefault("preview_video", placeholder_url)
    return data


async def ensure_digital(dry_run: bool, update: bool, placeholder_url: str) -> Dict[str, int]:
    """写入数字人种子:同名(名称)视为同一条,默认跳过,--update 时更新文案与风格"""
    stat = {"created": 0, "updated": 0, "skipped": 0}
    for item in DIGITAL_HUMANS:
        data = build_payload(item, placeholder_url)
        exist = await DigitalHumanModel.get_or_none(name=data["name"])
        if not exist:
            if dry_run:
                stat["created"] += 1
                print(f"[数字人·待新增] {data['name']}({data['gender']} / {data['style']})")
                continue
            await DigitalHumanModel.create(**data)
            stat["created"] += 1
            print(f"[数字人·新增] {data['name']}({data['gender']} / {data['style']})")
            continue
        if not update:
            stat["skipped"] += 1
            continue
        if dry_run:
            stat["updated"] += 1
            print(f"[数字人·待更新] {data['name']}")
            continue
        for field in UPDATABLE_FIELDS:
            setattr(exist, field, data[field])
        await exist.save(update_fields=list(UPDATABLE_FIELDS))
        stat["updated"] += 1
        print(f"[数字人·更新] {data['name']}")
    return stat


async def run(dry_run: bool, update: bool, placeholder_url: str) -> int:
    """连接数据库并执行种子写入(整体放在一个事务里,失败则全部回滚)"""
    await Tortoise.init(config=config.ORM_CONFIG)
    try:
        print(f"目标环境: {ARGS.env} | 模式: {'预演(不写库)' if dry_run else '写入'}"
              f" | 数字人总数: {len(DIGITAL_HUMANS)}")
        if dry_run:
            stat = await ensure_digital(dry_run=True, update=update, placeholder_url=placeholder_url)
        else:
            async with in_transaction():
                stat = await ensure_digital(dry_run=False, update=update, placeholder_url=placeholder_url)
        print("-" * 56)
        print(f"数字人:新增 {stat['created']} 个,更新 {stat['updated']} 个,已存在跳过 {stat['skipped']} 个")
        if not dry_run and not placeholder_url:
            print("提示:头像/形象图/预览视频未写入地址,请在管理端「数字人」中上传后上架;")
            print("      真实出片还需在管理端「业务配置」填写 gen.digital_model 或给数字人填 model。")
        return 0
    finally:
        await Tortoise.close_connections()


def main() -> int:
    """脚本入口"""
    try:
        return asyncio.run(run(ARGS.dry_run, ARGS.update, ARGS.placeholder_url.strip()))
    except Exception as exc:  # noqa: BLE001
        # 保留完整错误信息用于定位(多为环境文件或数据库不可达)
        print(f"[错误] 数字人种子数据初始化失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
