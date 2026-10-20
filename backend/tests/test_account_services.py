"""账号服务真实 ORM 回归：只使用隔离内存库，不连接业务数据库或 Redis。"""
import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.exceptions import HTTPException
from tortoise import Tortoise, connections
from tortoise.exceptions import IntegrityError

from app.core.plugin import password, redis
from app.models.account import CreditLogModel, UserInvitationModel, UserModel
from app.models.asset_cache import GenAssetCacheModel
from app.models.system import SystemConfigModel
from app.schemas.account import RegisterSchema, EditSchema, SetPasswordSchema, ChangePasswordSchema, CodeLoginSchema
from app.schemas.credit import LogQuerySchema
from app.schemas.user_material import MaterialQuerySchema
from app.services.account import service as account_service
from app.services.credit import service as credit_service
from app.services.invitation import service as invitation_service
from app.services.user_material import register_material, verify_materials, list_materials, material_key, sync_materials


def run_database(scenario):
    """在同一个事件循环内创建、使用并关闭全新内存数据库。"""
    async def execute():
        """每例独立建表，测试异常时也确保连接关闭。"""
        await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["app.models"]})
        try:
            await Tortoise.generate_schemas()
            await scenario()
        finally:
            await Tortoise.close_connections()
    asyncio.run(execute())


def test_invitation_registration_atomic_and_once():
    """新注册双方各入账一次；无效邀请码不留账号，重复注册不多发奖励。"""
    async def scenario():
        """验证真实余额、关系唯一约束、统计和永久额度流水。"""
        inviter = await UserModel.create(account="inviter", password="", credits=7)
        identity = await invitation_service.identity(inviter.id)
        payload = RegisterSchema(account="new-user", password="secret-123", invite_code=identity.code.lower())
        created = await account_service.register(payload)
        await inviter.refresh_from_db()
        newcomer = await UserModel.get(id=created["id"])
        assert inviter.credits == 17
        assert newcomer.credits == 10
        assert await CreditLogModel.filter(type="grant").count() == 2
        with pytest.raises(HTTPException):
            await account_service.register(payload)
        assert await CreditLogModel.filter(type="grant").count() == 2
        with pytest.raises(HTTPException):
            await account_service.register(RegisterSchema(account="bad-user", password="secret-123", invite_code="INVALID0"))
        assert not await UserModel.filter(account="bad-user").exists()
        summary = await invitation_service.summary(inviter.id)
        assert summary == {"code": identity.code, "reward_amount": 10, "invited_count": 1, "earned_credits": 10}
        assert (await invitation_service.identity(inviter.id)).code == identity.code
        with pytest.raises(IntegrityError):
            await UserInvitationModel.create(user_id=newcomer.id, code="12345678", inviter_id=inviter.id)
    run_database(scenario)


def test_invitation_rolls_back_both_awards(monkeypatch):
    """第二笔奖励失败时，第一笔奖励、新账号和邀请关系必须一起回滚。"""
    async def scenario():
        """用真实首笔入账加第二笔故障验证事务边界。"""
        inviter = await UserModel.create(account="inviter", password="", credits=2)
        identity = await invitation_service.identity(inviter.id)
        original = credit_service.grant
        async def fail_second(user_id, amount, **kwargs):
            """保留邀请人的真实入账，再模拟新用户入账故障。"""
            if user_id != inviter.id:
                raise RuntimeError("模拟第二笔入账失败")
            await original(user_id, amount, **kwargs)
        monkeypatch.setattr(credit_service, "grant", fail_second)
        with pytest.raises(RuntimeError):
            await account_service.register(RegisterSchema(account="new-user", password="secret-123", invite_code=identity.code))
        await inviter.refresh_from_db()
        assert inviter.credits == 2
        assert not await UserModel.filter(account="new-user").exists()
        assert await CreditLogModel.all().count() == 0
        assert await UserInvitationModel.filter(inviter_id=inviter.id).count() == 0
    run_database(scenario)


def test_sms_registration_award_and_existing_login(monkeypatch):
    """首次验证码注册发奖，老用户携带邀请码登录不会补发。"""
    async def scenario():
        """短信供应商与 Redis 仅在外部边界替身，账号和额度真实落库。"""
        from app.core import sms
        monkeypatch.setattr(sms, "verify_code", AsyncMock())
        monkeypatch.setattr(redis, "set", AsyncMock())
        inviter = await UserModel.create(account="inviter", password="")
        identity = await invitation_service.identity(inviter.id)
        payload = CodeLoginSchema(phone="13800138001", code="123456", invite_code=identity.code)
        first = await account_service.login_by_code(payload)
        second = await account_service.login_by_code(payload)
        assert first["is_new"] is True and second["is_new"] is False
        assert first["info"]["phone"] == payload.phone
        assert await CreditLogModel.filter(type="grant").count() == 2
    run_database(scenario)


def test_configured_reward_zero_and_concurrent_register():
    """并发注册同一用户名只有一份奖励；奖励可配置为零暂停发放。"""
    async def scenario():
        """SQLite 串行事务验证重复注册边界，生产行锁仍需目标库联调。"""
        inviter = await UserModel.create(account="inviter", password="")
        identity = await invitation_service.identity(inviter.id)
        payload = RegisterSchema(account="new-user", password="secret-123", invite_code=identity.code)
        results = await asyncio.gather(account_service.register(payload), account_service.register(payload), return_exceptions=True)
        assert sum(isinstance(item, dict) for item in results) == 1
        assert await CreditLogModel.filter(type="grant").count() == 2
        await SystemConfigModel.create(key="account.invite_reward_credits", value="0")
        await account_service.register(RegisterSchema(account="zero-user", password="secret-123", invite_code=identity.code))
        assert await CreditLogModel.filter(type="grant").count() == 2
    run_database(scenario)


def test_invitation_code_collision_retry(monkeypatch):
    """随机码撞码可重试，不能使注册事务进入数据库失败状态。"""
    async def scenario():
        """先制造一次唯一冲突，再验证重试后的双方奖励仍各一笔。"""
        import app.services.invitation as invitation_module
        inviter = await UserModel.create(account="inviter", password="")
        await UserInvitationModel.create(user_id=inviter.id, code="AABBCCDD")
        codes = iter(["aabbccdd", "11223344"])
        def next_code(_length):
            """按顺序返回冲突和不冲突的测试随机码。"""
            return next(codes)
        monkeypatch.setattr(invitation_module.secrets, "token_hex", next_code)
        newcomer = await account_service.register(RegisterSchema(account="new-user", password="secret-123", invite_code="AABBCCDD"))
        assert (await UserInvitationModel.get(user_id=newcomer["id"])).code == "11223344"
        assert await CreditLogModel.filter(type="grant").count() == 2
    run_database(scenario)


def test_profile_username_phone_and_password(monkeypatch):
    """用户名唯一、手机号保留、局部资料更新及密码校验使用真实 ORM。"""
    async def scenario():
        """头像和密码不会因只修改昵称而被清空；已有密码不能绕过原密码重设。"""
        monkeypatch.setattr(redis, "delete", AsyncMock())
        monkeypatch.setattr(redis, "set", AsyncMock())
        user = await UserModel.create(account="13800138001", phone="13800138001", nickname="旧昵称", avatar="/old.jpg", password=password.get_password_hash("secret-123"))
        await UserModel.create(account="occupied", password="")
        updated = await account_service.update_info(user.id, EditSchema(nickname="新昵称"))
        assert updated["avatar"] == "/old.jpg" and not updated["reauth_required"]
        with pytest.raises(HTTPException):
            await account_service.update_info(user.id, EditSchema(account="occupied"))
        changed = await account_service.update_info(user.id, EditSchema(account="new-name"))
        assert changed["phone"] == "13800138001" and changed["reauth_required"]
        logged = await account_service.login(type("Payload", (), {"account": "13800138001", "password": "secret-123"})())
        assert logged["info"]["id"] == user.id
        with pytest.raises(HTTPException):
            await account_service.set_password(user.id, SetPasswordSchema(password="replace-123"))
        with pytest.raises(HTTPException):
            await account_service.change_password(user.id, ChangePasswordSchema(old_password="wrong", new_password="replace-123"))
        await account_service.change_password(user.id, ChangePasswordSchema(old_password="secret-123", new_password="replace-123"))
        await user.refresh_from_db()
        assert password.verify_password("replace-123", user.password)
        assert "password" not in changed
    run_database(scenario)


def test_materials_confirm_ownership_and_filters(monkeypatch):
    """素材归属、待确认不可见、直传对象校验和分页筛选都使用真实台账。"""
    async def scenario():
        """存储 HEAD 为外部替身，数据库列表不拦截、不伪造。"""
        from types import SimpleNamespace
        import app.core.oss as oss_module
        head = lambda **kwargs: {"Content-Length": 1024}
        monkeypatch.setattr(oss_module, "get_oss", lambda: SimpleNamespace(bucket="test", client=SimpleNamespace(head_object=head)))
        await register_material(1, "/image.jpg", "照片.jpg", 100)
        await register_material(2, "/other.jpg", "他人的.jpg", 100)
        await register_material(1, "/video.mp4", "片段.mp4", storage_key="video.mp4")
        total, rows = await list_materials(1, MaterialQuerySchema())
        assert total == 1 and rows[0]["url"] == "/image.jpg"
        with pytest.raises(HTTPException):
            await verify_materials(2, ["/video.mp4"])
        await verify_materials(1, ["/video.mp4"])
        await verify_materials(1, ["/video.mp4"])
        total, rows = await list_materials(1, MaterialQuerySchema(kind="video"))
        assert total == 1 and rows[0]["size"] == 1024
        total, rows = await list_materials(1, MaterialQuerySchema(kind="image"))
        assert total == 1 and rows[0]["filename"] == "照片.jpg"
        await GenAssetCacheModel.filter(cache_key=material_key("/image.jpg")).update(deleted=True)
        assert (await list_materials(1, MaterialQuerySchema(kind="image")))[0] == 0
        with pytest.raises(HTTPException):
            await verify_materials(1, ["https://unowned.example/image.jpg"])
    run_database(scenario)


def test_credit_logs_owner_and_refund():
    """扣款和失败退款可按类型读取，另一账号的流水不会出现。"""
    async def scenario():
        """稳定分页保持真实余额与中文类型展示。"""
        await CreditLogModel.create(user_id=1, change=-3, balance=7, type="consume", task_id=22)
        await CreditLogModel.create(user_id=1, change=3, balance=10, type="refund", task_id=22)
        await CreditLogModel.create(user_id=2, change=-9, balance=1, type="consume")
        total, rows = await credit_service.logs(1, LogQuerySchema(type="refund"))
        assert total == 1 and rows[0]["change"] == 3 and rows[0]["type_label"] == "失败返还"
        total, rows = await credit_service.logs(1, LogQuerySchema(pageSize=1))
        assert total == 2 and len(rows) == 1 and rows[0]["user_id"] == 1
    run_database(scenario)


def test_legacy_pending_material_recovery(monkeypatch):
    """找回历史只核验本人台账，文件不存在时给出未确认数量。"""
    async def scenario():
        """存储返回一次有效对象、一次缺失对象，验证结果与列表一致。"""
        from types import SimpleNamespace
        import app.core.oss as oss_module
        def head_object(**kwargs):
            """按对象键模拟存储元数据，缺失对象无法进入成功列表。"""
            if kwargs["Key"] == "missing":
                raise RuntimeError("测试对象不存在")
            return {"Content-Length": 2048}
        def get_test_oss():
            """提供只读对象存储边界，禁止真实网络访问。"""
            return SimpleNamespace(bucket="test", client=SimpleNamespace(head_object=head_object))
        monkeypatch.setattr(oss_module, "get_oss", get_test_oss)
        await register_material(1, "/exists.jpg", "已上传.jpg", storage_key="exists")
        await register_material(1, "/missing.jpg", "未完成.jpg", storage_key="missing")
        await register_material(2, "/other.jpg", "其他用户.jpg", storage_key="exists")
        result = await sync_materials(1, 0)
        assert result["confirmed"] == 1 and result["unavailable"] == 1 and not result["has_more"]
        assert (await list_materials(1, MaterialQuerySchema()))[0] == 1
        assert (await list_materials(2, MaterialQuerySchema()))[0] == 0
    run_database(scenario)


def test_routes_require_auth_and_return_real_data():
    """经 HTTP 层验证新接口鉴权、响应包装及分页边界，数据库使用真实内存库。"""
    async def scenario():
        """应用不启动生产生命周期，只装载被测路由和请求记录上下文。"""
        import httpx
        from types import SimpleNamespace
        from fastapi import FastAPI
        from app.core.plugin import ctx
        from app.core.dependencies import DeepValidationUserToken
        from app.routes.user import account, common
        application = FastAPI()
        @application.middleware("http")
        async def prepare_context(request, call_next):
            """模拟项目真实中间件提供的记录上下文，不记录敏感请求。"""
            ctx.set("recorder", {})
            return await call_next(request)
        application.include_router(account.router, prefix="/v1/account")
        application.include_router(common.router, prefix="/v1/base/common")
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            for endpoint in ["/v1/account/invitation", "/v1/base/common/materials", "/v1/base/common/upload/confirm", "/v1/base/common/materials/sync", "/v1/account/credits/logs"]:
                response = await client.post(endpoint, json={})
                assert response.status_code == 401
            user = await UserModel.create(account="route-user", password="")
            async def current_user():
                """成功场景只替换外部登录会话校验，业务数据依然来自真实 ORM。"""
                return SimpleNamespace(id=user.id)
            application.dependency_overrides[DeepValidationUserToken] = current_user
            response = await client.post("/v1/account/invitation", json={})
            assert response.json()["code"] == 1 and len(response.json()["data"]["code"]) == 8
            await register_material(user.id, "/route-image.jpg", "接口图片.jpg", 32)
            response = await client.post("/v1/base/common/materials", json={"pageNum": 1, "pageSize": 20})
            assert response.json()["total"] == 1 and response.json()["data"][0]["filename"] == "接口图片.jpg"
            response = await client.post("/v1/base/common/materials", json={"pageNum": -1})
            assert response.status_code == 422
    run_database(scenario)


def test_account_services_migration_backfill():
    """在隔离旧结构执行实际 SQLite 迁移，验证手机号和历史素材回填。"""
    async def scenario():
        """仅修改内存库中的测试结构，不运行项目真实环境升级。"""
        path = Path(__file__).parents[1] / "migrations/models/2_20261020062500_account_services.py"
        spec = importlib.util.spec_from_file_location("account_services_migration", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        db = connections.get("default")
        # 明确定义旧表结构，避免把当前 ORM 的内联唯一约束误当作旧库结构。
        await db.execute_script('''DROP TABLE tb_user; DROP TABLE tb_user_invitation;
            CREATE TABLE tb_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT, deleted INT NOT NULL DEFAULT 0,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                account VARCHAR(20) NOT NULL UNIQUE, nickname VARCHAR(30) NOT NULL DEFAULT '',
                avatar VARCHAR(255), password VARCHAR(128) NOT NULL, status INT NOT NULL DEFAULT 1,
                free_credits INT NOT NULL DEFAULT 3, credits INT NOT NULL DEFAULT 0, last_reset_date DATE
            );''')
        await db.execute_script("INSERT INTO tb_user (account,nickname,password,status,free_credits,credits,deleted) VALUES ('13800138001','旧用户','',1,3,0,0);")
        await GenAssetCacheModel.create(cache_key=material_key("/old.jpg"), asset_type="uploaded_material", task_type="upload", content="/old.jpg", meta={"user_id": 1, "status": "ready", "filename": "旧图.jpg"})
        await db.execute_script(await module.upgrade(db))
        user = await UserModel.get(account="13800138001")
        assert user.phone == user.account
        total, rows = await list_materials(1, MaterialQuerySchema())
        assert total == 1 and rows[0]["filename"] == "旧图.jpg"
        await db.execute_script(await module.downgrade(db))
        columns = await db.execute_query_dict("PRAGMA table_info(tb_user)")
        assert "phone" not in {column["name"] for column in columns}
    run_database(scenario)
