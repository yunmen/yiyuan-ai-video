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
from tortoise import Tortoise
from tortoise.transactions import in_transaction


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

    async def shutdown(self):
        await Tortoise.close_connections()

