# -*- coding: utf-8 -*-
"""补齐 tb_digital_human 的口播字段(数字人口播功能上线用)。

背景(为什么需要这个脚本):
  1. 本仓库未托管 aerich 迁移历史(`backend/migrations/models/` 为空),
     无法用 `python main.py upgrade` 把新增列同步到已部署的库;
  2. `backend/plugin/database/aioorm.py` 的 `OrmDB.startup()` 仅在
     「库内表数 < 2」的全新库上执行 `Tortoise.generate_schemas(safe=True)`,
     而该接口**只创建缺失的表,不会为已存在的表增加列**。
  因此已部署环境的 `tb_digital_human` 不会自动获得数字人口播所需的 4 个新列,
  未补列时数字人接口在 SELECT 阶段会报「列不存在」。

本脚本幂等:先查 information_schema 判断缺哪些列,只对缺失列执行 ADD COLUMN,
重复执行无副作用;表不存在时说明是全新库,交给启动时的 generate_schemas 建表即可。

用法:
  # 1) 不连库,只打印需要执行的 SQL(用于人工复核 / 交给 DBA)
  python backend/scripts/ensure_digital_columns.py --print-sql

  # 2) 连库检查缺失列(只读,不修改)
  python backend/scripts/ensure_digital_columns.py

  # 3) 连库并直接补列
  python backend/scripts/ensure_digital_columns.py --apply
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

TABLE = "tb_digital_human"

# 只增列,不改列、不删列;类型与 app/models/digital.py 保持一致
COLUMNS = [
    ("image", "VARCHAR(255) NULL"),
    ("voice", "VARCHAR(100) NULL"),
    ("model", "VARCHAR(100) NULL"),
    ("default_text", "TEXT NULL"),
]


def q(name: str, engine: str) -> str:
    """按方言引用标识符:MySQL 用反引号,PostgreSQL/SQLite 用双引号"""
    return f"`{name}`" if engine == "mysql" else f'"{name}"'


def build_alter_sql(engine: str, missing: list[str]) -> list[str]:
    return [
        f"ALTER TABLE {q(TABLE, engine)} ADD COLUMN {q(col, engine)} {ddl};"
        for col, ddl in COLUMNS
        if col in missing
    ]


async def _table_exists(conn, engine: str) -> bool:
    if engine == "mysql":
        sql = "SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s"
    elif engine == "postgresql":
        sql = "SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1"
    else:
        sql = "SELECT COUNT(*) AS c FROM sqlite_master WHERE type = 'table' AND name = ?"
    rows = await conn.execute_query_dict(sql, [TABLE])
    return int(rows[0]["c"]) > 0


async def _existing_columns(conn, engine: str) -> set[str]:
    if engine == "mysql":
        sql = "SELECT column_name AS name FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s"
        rows = await conn.execute_query_dict(sql, [TABLE])
    elif engine == "postgresql":
        sql = "SELECT column_name AS name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1"
        rows = await conn.execute_query_dict(sql, [TABLE])
    else:
        rows = await conn.execute_query_dict(f"PRAGMA table_info({q(TABLE, engine)})")
    return {str(r["name"]).lower() for r in rows}


async def run(apply: bool) -> int:
    from tortoise import Tortoise

    engine = (config.ORM_ENGINE or "mysql").lower()
    await Tortoise.init(config=config.ORM_CONFIG)
    try:
        conn = Tortoise.get_connection("default")

        if not await _table_exists(conn, engine):
            print(f"[提示] 表 {TABLE} 不存在(数据库: {engine})。")
            print("       属于全新库,启动 backend 时会由 generate_schemas 建表,无需手工补列。")
            return 0

        existing = await _existing_columns(conn, engine)
        missing = [col for col, _ in COLUMNS if col not in existing]

        if not missing:
            print(f"[OK] {TABLE} 口播字段齐全(image/voice/model/default_text),无需补列。")
            return 0

        print(f"[MISSING] {TABLE} 缺少列: {', '.join(missing)}")
        for stmt in build_alter_sql(engine, missing):
            print(f"         {stmt}")

        if not apply:
            print("\n[提示] 以上为待执行 SQL。确认无误后加 --apply 直接执行(或在库上人工执行)。")
            return 1

        for stmt in build_alter_sql(engine, missing):
            await conn.execute_query(stmt)
            print(f"[已执行] {stmt}")
        print(f"\n[完成] {TABLE} 已补齐 {len(missing)} 个列。")
        return 0
    finally:
        await Tortoise.close_connections()


def main() -> int:
    parser = argparse.ArgumentParser(description="补齐 tb_digital_human 的口播字段")
    parser.add_argument("--print-sql", action="store_true", help="不连库,只打印 SQL")
    parser.add_argument("--apply", action="store_true", help="连库并直接补列")
    args = parser.parse_args()

    engine = (config.ORM_ENGINE or "mysql").lower()
    if args.print_sql:
        cols = [c for c, _ in COLUMNS]
        print(f"-- 引擎: {engine} | 目标表: {TABLE}")
        for stmt in build_alter_sql(engine, cols):
            print(stmt)
        return 0

    try:
        return asyncio.run(run(args.apply))
    except Exception as exc:  # noqa: BLE001
        print(
            f"[错误] 连接数据库失败或执行失败: {exc}\n"
            f"       请在 backend 环境运行,并确认 ENVIRONMENT / {engine.upper()} 连接配置正确。",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
