# -*- coding: utf-8 -*-
'''
@文件    :schema_sync.py
@说明    :已部署库的结构追平(为已存在的表补新增列 / 补建后加的表)
@时间    :2026/09/22 18:40:00
@作者    :一源AI
@版本    :1.0

为什么需要这个模块:
  1. 本仓库未托管 aerich 迁移历史(`backend/migrations/models/` 为空),
     无法用 `python main.py upgrade` 把新增列同步到已部署的库;
  2. `OrmDB.startup()` 里的 `Tortoise.generate_schemas(safe=True)` **只建表不加列**,
     且仅在「库内表数 < 2」的全新库上执行。
  结果:模型里加了字段/新表,已部署库不会自动获得,对应接口在 SELECT 阶段直接报
  「column xxx does not exist」(HTTP 500)。

约定:本模块只做「增」——只 ADD COLUMN、只建缺失的表,不改列类型、不改约束、不删列,
先查 information_schema 判断缺口,因此可重复执行(幂等)。
新增模型字段/新表后,请把条目登记到 TABLE_COLUMNS / CREATE_TABLES,启动时会自动追平。
'''
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from tortoise import Tortoise

logger = logging.getLogger(__name__)

# 需要存在但可能缺失的列:表 -> 列 -> 各方言 DDL(JSON 类型 SQLite 不存在,统一回退 TEXT)
TABLE_COLUMNS: Dict[str, Dict[str, Dict[str, str]]] = {
    "tb_video_template": {
        # 画面构成三段式(person 主体 / shot 镜头 / setting 场景)
        "prompt_parts": {"mysql": "JSON NULL", "postgresql": "JSONB NULL", "sqlite": "TEXT NULL"},
    },
    "tb_digital_human": {
        # 主视图派生:派生视图以主图 image 为 reference
        "pose_variants": {"mysql": "JSON NULL", "postgresql": "JSONB NULL", "sqlite": "TEXT NULL"},
        # 口播生成所需字段(形象图 / 音色 / 模型 / 默认文案)
        "image": {"mysql": "VARCHAR(255) NULL", "postgresql": "VARCHAR(255) NULL", "sqlite": "TEXT NULL"},
        "voice": {"mysql": "VARCHAR(100) NULL", "postgresql": "VARCHAR(100) NULL", "sqlite": "TEXT NULL"},
        # 声纹复用(voice-casting):绑定到数字人的可复用声纹样本音频地址
        "voice_reference": {"mysql": "VARCHAR(512) NULL", "postgresql": "VARCHAR(512) NULL", "sqlite": "TEXT NULL"},
        "model": {"mysql": "VARCHAR(100) NULL", "postgresql": "VARCHAR(100) NULL", "sqlite": "TEXT NULL"},
        "default_text": {"mysql": "TEXT NULL", "postgresql": "TEXT NULL", "sqlite": "TEXT NULL"},
        # 专属数字人归属:用户自助上传形象生成的专属数字人绑定到对应用户,仅本人可用
        "user_id": {"mysql": "BIGINT NULL", "postgresql": "BIGINT NULL", "sqlite": "INTEGER NULL"},
        # 注:本块所有列都是数字人能力分批落地时新增的,aerich 的 init 迁移里没有它们
        # (init 早于这些字段)。全新部署与已部署库都靠 sync_schema() 在 backend 启动时
        # 幂等补齐,因此**不要再为这些列手写迁移**(会与此处追平重复执行而报错)。
    },
    # 生成中间产物缓存(P2 资产复用):表本身也是后加的,已部署库同样不会被自动补建
    "tb_gen_asset_cache": {},
    # 用户意见反馈表(后加表,已部署库需整体补建)
    "tb_feedback": {},
    # 分镜集 / 镜头表(后加表,把 worker 运行期分镜沉淀为实体,已部署库需整体补建)
    "tb_episode": {},
    "tb_shot": {},
    # 系统操作日志表(此前因 schema="logs" 指向不存在的独立库而从未建表,回归主库后需补建)
    "tb_system_log": {},
    # 用户工程模板表(参数模板化 / 一套结构百变体,后加表,已部署库需整体补建)
    "tb_gen_task_template": {},
}

# 需要存在、缺失时整体建表的表(列定义交给模型生成,不在此逐列枚举)
CREATE_TABLES = ("tb_gen_asset_cache", "tb_feedback", "tb_episode", "tb_shot", "tb_system_log", "tb_gen_task_template")

# 已存在列需要「改类型」的追平(本项目 schema_sync 默认只 ADD COLUMN,不 MODIFY 已有列类型)。
# 例:tb_generate_task.result_video 原本 VARCHAR(512),但视频模型直链(带签名)常 > 512,
# 回调落库会报 Data too long → backend 500 → worker notify 失败 → 任务永久卡 processing。
# 这里登记需要扩大的列,启动幂等执行(按当前列类型判断,已改为 TEXT 后不再重复 ALTER)。
TABLE_ALTERS: Dict[str, Dict[str, Dict[str, str]]] = {
    "tb_generate_task": {
        "result_video": {
            "mysql": "ALTER TABLE `tb_generate_task` MODIFY COLUMN `result_video` TEXT NULL",
            "postgresql": 'ALTER TABLE "tb_generate_task" ALTER COLUMN "result_video" TYPE TEXT',
            # SQLite 动态类型,列类型声明不影响存储,无需 ALTER
            "sqlite": "",
        },
    },
}


def quote(name: str, engine: str) -> str:
    """按方言引用标识符:MySQL 用反引号,PostgreSQL / SQLite 用双引号"""
    return f"`{name}`" if engine == "mysql" else f'"{name}"'


def build_alter_sql(engine: str, table: str, missing: List[str]) -> List[str]:
    """按缺失列生成 ADD COLUMN 语句(SQLite 不支持的 JSON 类型统一用 TEXT 兜底)"""
    cols = TABLE_COLUMNS.get(table, {})
    return [
        f"ALTER TABLE {quote(table, engine)} ADD COLUMN {quote(col, engine)} "
        f"{cols[col].get(engine, 'TEXT NULL')};"
        for col in missing
        if col in cols
    ]


async def table_exists(conn, engine: str, table: str) -> bool:
    """判断表是否存在,兼容 MySQL / PostgreSQL / SQLite 三种方言"""
    if engine == "mysql":
        sql = "SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s"
    elif engine == "postgresql":
        sql = "SELECT COUNT(*) AS c FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1"
    else:
        sql = "SELECT COUNT(*) AS c FROM sqlite_master WHERE type = 'table' AND name = ?"
    rows = await conn.execute_query_dict(sql, [table])
    return int(rows[0]["c"]) > 0


async def _existing_columns(conn, engine: str, table: str) -> Set[str]:
    """取表内已有列名(统一小写比较,避免方言大小写差异导致误判)"""
    if engine == "mysql":
        sql = "SELECT column_name AS name FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s"
        rows = await conn.execute_query_dict(sql, [table])
    elif engine == "postgresql":
        sql = "SELECT column_name AS name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1"
        rows = await conn.execute_query_dict(sql, [table])
    else:
        rows = await conn.execute_query_dict(f"PRAGMA table_info({quote(table, engine)})")
    return {str(r["name"]).lower() for r in rows}


async def _apply_type_alters(conn, engine: str, apply: bool) -> List[str]:
    """追平已存在列的类型变更(只扩大长度,不改语义),启动幂等。

    按当前列类型判断是否需要 ALTER:已是目标类型则跳过,避免每次启动都跑 ALTER 锁表。
    """
    executed: List[str] = []
    if engine == "sqlite":
        return executed  # 动态类型,无需改列类型
    for table, cols in TABLE_ALTERS.items():
        for col, stmts in cols.items():
            stmt = stmts.get(engine, "")
            if not stmt:
                continue
            if engine == "mysql":
                sql = (
                    "SELECT DATA_TYPE FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s"
                )
            else:  # postgresql
                sql = (
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = %s AND column_name = %s"
                )
            try:
                rows = await conn.execute_query_dict(sql, [table, col])
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[结构追平] 查询列类型失败 {table}.{col}: {exc}")
                continue
            if not rows:
                continue
            dtype = (rows[0].get("DATA_TYPE") or rows[0].get("data_type") or "").lower()
            # 已是 text 系则无需再改
            if dtype in ("text", "mediumtext", "longtext"):
                continue
            if apply:
                await conn.execute_query(stmt)
            executed.append(stmt)
    return executed


async def sync_schema(
    conn,
    engine: str,
    apply: bool = True,
    only_table: Optional[str] = None,
) -> Dict[str, Any]:
    """追平已部署库的结构缺口。

    参数:
      conn: 已初始化的 Tortoise 连接。
      engine: 方言名(mysql / postgresql / sqlite)。
      apply: False 时只检查不执行(供人工复核待执行 SQL)。
      only_table: 只处理指定表,默认处理 TABLE_COLUMNS 全部表。

    返回:
      {
        "pending_columns": {表: [缺失列]},  # apply=False 时为待补清单;True 时为执行前的缺口
        "pending_tables": [仍缺失的表],      # apply=True 且建表成功后为空
        "executed": [已执行的语句/动作],      # apply=False 时恒为空
      }
    """
    tables = [only_table] if only_table else list(TABLE_COLUMNS)
    result: Dict[str, Any] = {"pending_columns": {}, "pending_tables": [], "executed": []}

    for table in tables:
        if not await table_exists(conn, engine, table):
            # 表不存在:只登记其中的「后加表」,全新库交由启动时的 generate_schemas 建表
            if table in CREATE_TABLES:
                result["pending_tables"].append(table)
            continue

        existing = await _existing_columns(conn, engine, table)
        missing = [col for col in TABLE_COLUMNS.get(table, {}) if col not in existing]
        if not missing:
            continue

        result["pending_columns"][table] = missing
        if not apply:
            continue
        for stmt in build_alter_sql(engine, table, missing):
            await conn.execute_query(stmt)
            result["executed"].append(stmt)

    if apply and result["pending_tables"]:
        # safe=True:只创建不存在的表,不会改动已有表结构
        await Tortoise.generate_schemas(safe=True)
        still_missing = [
            t for t in result["pending_tables"] if not await table_exists(conn, engine, t)
        ]
        for t in result["pending_tables"]:
            if t not in still_missing:
                result["executed"].append(f"CREATE TABLE {t}")
        result["pending_tables"] = still_missing

    # 已存在列的类型追平(扩大长度等):tb_generate_task.result_video VARCHAR(512) → TEXT
    alters = await _apply_type_alters(conn, engine, apply)
    if alters:
        result["executed"].extend(alters)

    return result