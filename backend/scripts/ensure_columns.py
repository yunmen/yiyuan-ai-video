# -*- coding: utf-8 -*-
"""补齐演进路线的并行项新增列(三段式 prompt / 数字人派生视图)。

背景(为什么需要这个脚本):
  1. 本仓库未托管 aerich 迁移历史(`backend/migrations/models/` 为空),
     无法用 `python main.py upgrade` 把新增列同步到已部署的库;
  2. `backend/plugin/database/aioorm.py` 的 `OrmDB.startup()` 仅在「库内表数 < 2」
     的全新库上执行 `Tortoise.generate_schemas(safe=True)`,而该接口**只建表不加列**。
  因此已部署环境不会自动获得新列,未补列时对应接口在 SELECT 阶段会报「列不存在」。

本脚本幂等:先查 information_schema 判断缺哪些列,只对缺失列执行 ADD COLUMN,
重复执行无副作用;表不存在时说明是全新库,交给启动时的 generate_schemas 建表即可。

用法:
  python backend/scripts/ensure_columns.py --print-sql      # 不连库,只打印 SQL
  python backend/scripts/ensure_columns.py                  # 连库检查缺失列(只读)
  python backend/scripts/ensure_columns.py --apply          # 连库并直接补列
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

# 只增列,不改列、不删列;类型与 app/models 下保持一致(按方言给不同 DDL:
# JSON 类型在 SQLite 不存在,统一回退 TEXT)
TABLE_COLUMNS = {
    # 画面构成三段式(person/shot/setting)
    "tb_video_template": {
        "prompt_parts": {"mysql": "JSON NULL", "postgresql": "JSONB NULL", "sqlite": "TEXT NULL"},
    },
    # 主视图派生:派生视图以主图 image 为 reference
    "tb_digital_human": {
        "pose_variants": {"mysql": "JSON NULL", "postgresql": "JSONB NULL", "sqlite": "TEXT NULL"},
    },
}


def q(name: str, engine: str) -> str:
    """按方言引用标识符:MySQL 用反引号,PostgreSQL/SQLite 用双引号"""
    return f"`{name}`" if engine == "mysql" else f'"{name}"'


def build_alter_sql(engine: str, table: str, missing: list[str]) -> list[str]:
    cols = TABLE_COLUMNS.get(table, {})
    return [
        f"ALTER TABLE {q(table, engine)} ADD COLUMN {q(col, engine)} {cols[col].get(engine, 'TEXT NULL')};"
        for col in missing
        if col in cols
    ]


async def _table_exists(conn, engine: str, table: str) -> bool:
    if engine == "mysql":
        sql = "SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s"
    elif engine == "postgresql":
        sql = "SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1"
    else:
        sql = "SELECT COUNT(*) AS c FROM sqlite_master WHERE type = 'table' AND name = ?"
    rows = await conn.execute_query_dict(sql, [table])
    return int(rows[0]["c"]) > 0


async def _existing_columns(conn, engine: str, table: str) -> set[str]:
    if engine == "mysql":
        sql = "SELECT column_name AS name FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s"
        rows = await conn.execute_query_dict(sql, [table])
    elif engine == "postgresql":
        sql = "SELECT column_name AS name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1"
        rows = await conn.execute_query_dict(sql, [table])
    else:
        rows = await conn.execute_query_dict(f"PRAGMA table_info({q(table, engine)})")
    return {str(r["name"]).lower() for r in rows}


async def _handle_table(conn, engine: str, table: str, apply: bool) -> int:
    if not await _table_exists(conn, engine, table):
        print(f"[提示] 表 {table} 不存在(数据库: {engine})。")
        print("       属于全新库,启动 backend 时会由 generate_schemas 建表,无需手工补列。")
        return 0

    existing = await _existing_columns(conn, engine, table)
    missing = [col for col in TABLE_COLUMNS.get(table, {}) if col not in existing]
    if not missing:
        print(f"[OK] {table} 新字段齐全({', '.join(TABLE_COLUMNS[table])}),无需补列。")
        return 0

    print(f"[MISSING] {table} 缺少列: {', '.join(missing)}")
    statements = build_alter_sql(engine, table, missing)
    for stmt in statements:
        print(f"         {stmt}")

    if not apply:
        print("[提示] 以上为待执行 SQL。确认无误后加 --apply 直接执行(或在库上人工执行)。")
        return 1

    for stmt in statements:
        await conn.execute_query(stmt)
        print(f"[已执行] {stmt}")
    print(f"[完成] {table} 已补齐 {len(missing)} 个列。")
    return 0


async def run(apply: bool, table: str | None) -> int:
    from tortoise import Tortoise

    engine = (config.ORM_ENGINE or "mysql").lower()
    await Tortoise.init(config=config.ORM_CONFIG)
    try:
        conn = Tortoise.get_connection("default")
        tables = [table] if table else list(TABLE_COLUMNS)
        codes = [await _handle_table(conn, engine, t, apply) for t in tables]
        return 1 if any(codes) else 0
    finally:
        await Tortoise.close_connections()


def main() -> int:
    parser = argparse.ArgumentParser(description="补齐演进路线并行项的新增列")
    parser.add_argument("--print-sql", action="store_true", help="不连库,只打印 SQL")
    parser.add_argument("--apply", action="store_true", help="连库并直接补列")
    parser.add_argument("--table", help="只处理指定表(默认全部)")
    args = parser.parse_args()

    engine = (config.ORM_ENGINE or "mysql").lower()
    if args.print_sql:
        targets = [args.table] if args.table else list(TABLE_COLUMNS)
        print(f"-- 引擎: {engine}")
        for t in targets:
            for stmt in build_alter_sql(engine, t, list(TABLE_COLUMNS.get(t, {}))):
                print(stmt)
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
