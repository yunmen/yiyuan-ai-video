"""手机号旧库追平回归：仅连接独立 SQLite 内存库，不加载业务配置。"""
import importlib.util
import unittest
from pathlib import Path

from tortoise import Tortoise, connections
from tortoise.exceptions import IntegrityError

from plugin.database.schema_sync import build_alter_sql, sync_schema


class UserPhoneSchemaTests(unittest.IsolatedAsyncioTestCase):
    """覆盖缺列修复、重复启动以及启动追平与迁移的双向兼容。"""

    async def asyncSetUp(self):
        """创建不包含手机号字段的旧用户表与最小素材台账。"""
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": []})
        self.db = connections.get("default")
        await self.db.execute_script('''
            CREATE TABLE tb_user (id INTEGER PRIMARY KEY, account VARCHAR(20) UNIQUE, credits INT);
            INSERT INTO tb_user VALUES (1, '13800138001', 7), (2, 'normal-user', 9);
            CREATE TABLE tb_gen_asset_cache (asset_type TEXT, task_type TEXT, meta JSON);
        ''')
        path = Path(__file__).parents[1] / "migrations/models/2_20261020062500_account_services.py"
        spec = importlib.util.spec_from_file_location("account_phone_migration", path)
        self.migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.migration)

    async def asyncTearDown(self):
        """无论断言是否成功，都关闭隔离数据库。"""
        await Tortoise.close_connections()

    async def test_check_only_does_not_write(self):
        """检查模式报告缺列，但不得执行 DDL 或回填。"""
        result = await sync_schema(self.db, "sqlite", apply=False, only_table="tb_user")
        self.assertEqual(result["pending_columns"], {"tb_user": ["phone"]})
        self.assertEqual(result["executed"], [])
        columns = await self.db.execute_query_dict("PRAGMA table_info(tb_user)")
        self.assertNotIn("phone", {column["name"] for column in columns})

    async def test_startup_repairs_and_repeats(self):
        """旧库补列、回填、保护唯一性，重复启动保持余额及已有绑定不变。"""
        await sync_schema(self.db, "sqlite", only_table="tb_user")
        rows = await self.db.execute_query_dict("SELECT phone, credits FROM tb_user ORDER BY id")
        self.assertEqual(rows, [{"phone": "13800138001", "credits": 7}, {"phone": None, "credits": 9}])
        await self.db.execute_query("UPDATE tb_user SET phone='13900139001' WHERE id=1")
        result = await sync_schema(self.db, "sqlite", only_table="tb_user")
        self.assertEqual(result["pending_columns"], {})
        rows = await self.db.execute_query_dict("SELECT phone FROM tb_user WHERE id=1")
        self.assertEqual(rows[0]["phone"], "13900139001")
        with self.assertRaises(IntegrityError):
            await self.db.execute_query("UPDATE tb_user SET phone='13900139001' WHERE id=2")

    async def test_startup_then_migration(self):
        """先启动追平后迁移不重复加列，邀请表仍正常创建。"""
        await sync_schema(self.db, "sqlite", only_table="tb_user")
        await self.db.execute_script(await self.migration.upgrade(self.db))
        await self.db.execute_query_dict("SELECT * FROM tb_user_invitation")
        rows = await self.db.execute_query_dict("SELECT phone FROM tb_user WHERE id=1")
        self.assertEqual(rows[0]["phone"], "13800138001")

    async def test_migration_then_startup(self):
        """直接迁移旧库后再启动追平，两条升级路径均能读取手机号。"""
        await self.db.execute_script(await self.migration.upgrade(self.db))
        result = await sync_schema(self.db, "sqlite", only_table="tb_user")
        self.assertEqual(result["pending_columns"], {})
        rows = await self.db.execute_query_dict("SELECT phone, credits FROM tb_user WHERE id=1")
        self.assertEqual(rows[0], {"phone": "13800138001", "credits": 7})

    def test_postgresql_column_sql(self):
        """线上 PostgreSQL 补列使用与模型一致的可空手机号类型。"""
        self.assertEqual(build_alter_sql("postgresql", "tb_user", ["phone"]), [
            'ALTER TABLE "tb_user" ADD COLUMN "phone" VARCHAR(11) NULL;'
        ])


if __name__ == "__main__":
    unittest.main()
