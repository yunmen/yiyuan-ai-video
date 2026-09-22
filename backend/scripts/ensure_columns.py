# -*- coding: utf-8 -*-
"""人工核查 / 补执行已部署库的结构缺口(新增列 / 新增表)。

背景:
  本仓库未托管 aerich 迁移历史(`backend/migrations/models/` 为空),而启动时的
  `Tortoise.generate_schemas(safe=True)` 只在全新库建表、且不给已存在的表加列,
  所以模型里新加的字段/表在已部署库上会缺,对应接口 SELECT 时报「列不存在」。

  这类缺口现在会在 backend 启动时由 `plugin/database/schema_sync.sync_schema()`
  自动追平(幂等,只增不改)。本脚本保留用于:核查某个库是否已对齐、以及在不方便
  重启服务时手工补执行。需要追平的列/表统一登记在 `plugin/database/schema_sync.py`,
  本脚本不再重复维护清单。

用法:
  python backend/scripts/ensure_columns.py --print-sql      # 不连库,只打印 SQL
  python backend/scripts/ensure_columns.py                  # 连库检查缺失项(只读)
  python backend/scripts/ensure_columns.py --apply          # 连库并直接补列/补表
  python backend/scripts/ensure_columns.py --table tb_video_template --apply
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "dev")

from app.settings import config  # noqa: E402
from plugin.database.schema_sync import (  # noqa: E402
    CREATE_TABLES,
    TABLE_COLUMNS,
    build_alter_sql,
    sync_schema,
)


async def run(apply: bool, table: str | None) -> int:
    """连库执行:默认只检查缺口,apply=True 时直接补列 / 补表"""
    from tortoise import Tortoise

    engine = (config.ORM_ENGINE or "mysql").lower()
    await Tortoise.init(config=config.ORM_CONFIG)
    try:
        conn = Tortoise.get_connection("default")
        result = await sync_schema(conn, engine, apply=apply, only_table=table)

        for target, cols in result["pending_columns"].items():
            print(f"[MISSING] {target} 缺少列: {', '.join(cols)}")
            for stmt in build_alter_sql(engine, target, cols):
                print(f"         {stmt}")
        if result["pending_tables"]:
            print(f"[缺表] {', '.join(result['pending_tables'])} 不存在。")
            if apply:
                print("       已尝试由 generate_schemas(safe=True) 建表,但建表后仍缺失。")
            else:
                print("       加 --apply 后由 generate_schemas(safe=True) 建表(只建缺失表,不改已有表)。")
        for action in result["executed"]:
            print(f"[已执行] {action}")

        if result["pending_columns"] or result["pending_tables"]:
            if apply:
                return 0
            print("[提示] 以上为待执行项。确认无误后加 --apply 直接执行(或在库上人工执行)。")
            return 1

        print(f"[OK] 结构已对齐(检查范围: {table or '、'.join(TABLE_COLUMNS)})。")
        return 0
    finally:
        await Tortoise.close_connections()


def main() -> int:
    parser = argparse.ArgumentParser(description="补齐已部署库缺失的列与表")
    parser.add_argument("--print-sql", action="store_true", help="不连库,只打印 SQL")
    parser.add_argument("--apply", action="store_true", help="连库并直接补列/补表")
    parser.add_argument("--table", help="只处理指定表(默认全部)")
    args = parser.parse_args()

    engine = (config.ORM_ENGINE or "mysql").lower()
    if args.print_sql:
        targets = [args.table] if args.table else list(TABLE_COLUMNS)
        print(f"-- 引擎: {engine}")
        for target in targets:
            for stmt in build_alter_sql(engine, target, list(TABLE_COLUMNS.get(target, {}))):
                print(stmt)
            if target in CREATE_TABLES:
                print(f"-- 缺表时执行: CREATE TABLE {target}(列定义由 Tortoise 模型生成,启动时 generate_schemas(safe=True))")
        return 0

    try:
        return asyncio.run(run(args.apply, args.table))
    except Exception as exc:  # noqa: BLE001
        print(
            f"[错误] 连接数据库失败或执行失败: {exc}\n"
            f"       请在 backend 环境运行,并确认 ENVIRONMENT / {engine.upper()} 连接配置正确。",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())