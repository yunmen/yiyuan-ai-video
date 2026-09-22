# -*- coding: utf-8 -*-
'''
@文件    :orm.py
@说明    :
@时间    :2025/08/26 14:49:16
@作者    :睿
@版本    :1.0
'''

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from loguru import logger
from tortoise import Tortoise
from tortoise.transactions import in_transaction
from plugin.database.schema_sync import sync_schema


class OrmDB:
    def __init__(self, config: Dict, engine: str = "mysql"):
        self.config = config
        self.engine = engine
    
    async def query(self, sql: str, args: List = []) -> List[Dict]:
        """返回字典格式的结果列表"""
        async with in_transaction("default") as conn:
            return await conn.execute_query_dict(sql, args)

    async def execute(self, sql: str, args: List = []) -> Tuple[int, List]:
        """
        返回受影响的行数以及查询结果
        """
        async with in_transaction("default") as conn:
            return await conn.execute_query(sql, args)

    async def insert(self, sql: str, args: List = []) -> int:
        """
        返回新增的主键Id
        """
        async with in_transaction("default") as conn:
            return await conn.execute_insert(sql, args)

    async def _init_log_partitions(self):
        """初始化系统日志分区表（仅 PostgreSQL）"""
        now = datetime.now()
        start_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_next = (start_of_current.replace(day=28) + timedelta(days=4)).replace(day=1)
        start_of_after_next = (start_of_next.replace(day=28) + timedelta(days=4)).replace(day=1)

        current_month = start_of_current.strftime("%Y%m")
        next_month = start_of_next.strftime("%Y%m")

        await self.execute("CREATE SCHEMA IF NOT EXISTS logs")

        await self.execute("""
            CREATE TABLE IF NOT EXISTS logs.tb_system_log (
                id BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
                deleted BOOLEAN NOT NULL DEFAULT FALSE,
                create_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                update_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                request_id VARCHAR(50) NOT NULL,
                summary VARCHAR(255) NOT NULL,
                url VARCHAR(255) NOT NULL,
                method VARCHAR(20),
                client_ip VARCHAR(64),
                headers TEXT,
                payload JSONB,
                result JSONB,
                status_code VARCHAR(20),
                process_time VARCHAR(20),
                error_log TEXT,
                client_type VARCHAR(50),
                operator_account VARCHAR(50),
                operator_nickname VARCHAR(50)
            ) PARTITION BY RANGE (create_time)
        """)

        await self.execute(f"""
            CREATE TABLE IF NOT EXISTS logs.tb_system_log_{current_month}
            PARTITION OF logs.tb_system_log
            FOR VALUES FROM ('{start_of_current.strftime("%Y-%m-%d")}') TO ('{start_of_next.strftime("%Y-%m-%d")}')
        """)

        await self.execute(f"""
            CREATE TABLE IF NOT EXISTS logs.tb_system_log_{next_month}
            PARTITION OF logs.tb_system_log
            FOR VALUES FROM ('{start_of_next.strftime("%Y-%m-%d")}') TO ('{start_of_after_next.strftime("%Y-%m-%d")}')
        """)

    async def _sync_schema(self):
        """启动时追平模型新增列 / 新增表(幂等)。

        上面的 generate_schemas 只建表不加列,且仅对全新库生效,已部署库需要这一步
        才能拿到后加的字段;失败只记错误日志,不阻断服务启动。
        """
        try:
            conn = Tortoise.get_connection("default")
            result = await sync_schema(conn, self.engine, apply=True)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[数据库结构追平] 执行失败,依赖新增字段的接口可能报「列不存在」: {exc}")
            return

        for action in result["executed"]:
            logger.info(f"[数据库结构追平] 已执行: {action}")
        if result["pending_columns"] or result["pending_tables"]:
            logger.error(
                f"[数据库结构追平] 仍有缺口(缺列: {result['pending_columns']}, 缺表: {result['pending_tables']}),"
                f"请检查数据库权限或手工执行 backend/scripts/ensure_columns.py --apply"
            )

    async def startup(self):
        await Tortoise.init(config=self.config)
        if self.engine == "postgresql":
            await self._init_log_partitions()
            sql = "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema = 'public';"
        elif self.engine == "mysql":
            sql = "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema = DATABASE();"
        else:
            sql = "SELECT COUNT(*) as count FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
        result = await self.query(sql)
        if result[0]['count'] < 2: # 兼容日志表
            await Tortoise.generate_schemas(safe=True)
        # 已部署库的结构追平:任何启动方式(compose / 脚本 / 手工重启)都会执行,避免新增字段后 500
        await self._sync_schema()

    async def shutdown(self):
        await Tortoise.close_connections()

