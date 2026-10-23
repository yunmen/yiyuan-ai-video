"""账号服务迁移：Aerich 隔离模型差异生成，补充手机号与素材归属命名空间回填。"""
from tortoise import BaseDBAsyncClient

# 结构由 Aerich 0.9.1 对本次前后模型生成；支持项目实际使用的 PostgreSQL/MySQL。
SCHEMA_SQL = {
    "postgres": {
        "upgrade": """
CREATE TABLE IF NOT EXISTS "tb_user_invitation" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL UNIQUE,
    "code" VARCHAR(8) NOT NULL UNIQUE,
    "inviter_id" BIGINT,
    "reward_amount" INT NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS "idx_tb_user_inv_inviter_6a71d4" ON "tb_user_invitation" ("inviter_id");
COMMENT ON COLUMN "tb_user_invitation"."id" IS '主键Id';
COMMENT ON COLUMN "tb_user_invitation"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_user_invitation"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_user_invitation"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_user_invitation"."user_id" IS '邀请码所属用户Id';
COMMENT ON COLUMN "tb_user_invitation"."code" IS '随机邀请码';
COMMENT ON COLUMN "tb_user_invitation"."inviter_id" IS '注册时的邀请人Id';
COMMENT ON COLUMN "tb_user_invitation"."reward_amount" IS '注册时双方各获得的永久额度';
COMMENT ON TABLE "tb_user_invitation" IS '用户邀请码与注册奖励记录';
ALTER TABLE "tb_user" ADD "phone" VARCHAR(11);
CREATE UNIQUE INDEX IF NOT EXISTS "uid_tb_user_phone_43d442" ON "tb_user" ("phone");
""",
        "downgrade": """
DROP INDEX IF EXISTS "uid_tb_user_phone_43d442";
ALTER TABLE "tb_user" DROP COLUMN "phone";
DROP TABLE IF EXISTS "tb_user_invitation";
""",
    },
    "mysql": {
        "upgrade": """
CREATE TABLE IF NOT EXISTS `tb_user_invitation` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL UNIQUE COMMENT '邀请码所属用户Id',
    `code` VARCHAR(8) NOT NULL UNIQUE COMMENT '随机邀请码',
    `inviter_id` BIGINT COMMENT '注册时的邀请人Id',
    `reward_amount` INT NOT NULL COMMENT '注册时双方各获得的永久额度' DEFAULT 0,
    KEY `idx_tb_user_inv_inviter_6a71d4` (`inviter_id`)
) CHARACTER SET utf8mb4 COMMENT='用户邀请码与注册奖励记录';
ALTER TABLE `tb_user` ADD `phone` VARCHAR(11) COMMENT '绑定手机号';
ALTER TABLE `tb_user` ADD UNIQUE INDEX `phone` (`phone`);
""",
        "downgrade": """
ALTER TABLE `tb_user` DROP INDEX `phone`;
ALTER TABLE `tb_user` DROP COLUMN `phone`;
DROP TABLE IF EXISTS `tb_user_invitation`;
""",
    },
    "sqlite": {
        "upgrade": """
CREATE TABLE IF NOT EXISTS "tb_user_invitation" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* 主键Id */,
    "deleted" INT NOT NULL DEFAULT 0 /* 软删除标记,True无效False有效 */,
    "create_time" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "update_time" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 更新时间 */,
    "user_id" BIGINT NOT NULL UNIQUE /* 邀请码所属用户Id */,
    "code" VARCHAR(8) NOT NULL UNIQUE /* 随机邀请码 */,
    "inviter_id" BIGINT /* 注册时的邀请人Id */,
    "reward_amount" INT NOT NULL DEFAULT 0 /* 注册时双方各获得的永久额度 */
) /* 用户邀请码与注册奖励记录 */;
CREATE INDEX IF NOT EXISTS "idx_tb_user_inv_inviter_6a71d4" ON "tb_user_invitation" ("inviter_id");
ALTER TABLE "tb_user" ADD "phone" VARCHAR(11) /* 绑定手机号 */;
CREATE UNIQUE INDEX "uid_tb_user_phone_43d442" ON "tb_user" ("phone");
""",
        "downgrade": """
DROP INDEX IF EXISTS "uid_tb_user_phone_43d442";
ALTER TABLE "tb_user" DROP COLUMN "phone";
DROP TABLE IF EXISTS "tb_user_invitation";
""",
    },
}


async def upgrade(db: BaseDBAsyncClient) -> str:
    """创建邀请关系并保留旧手机号登录；仅回填已有上传归属台账。"""
    dialect = db.capabilities.dialect
    if dialect == "postgres":
        phone_sql = "UPDATE tb_user SET phone=account WHERE phone IS NULL AND account ~ '^1[3-9][0-9]{9}$';"
        owner = "meta->>'user_id'"
        status = "meta->>'status'"
        namespace = f"(CASE WHEN {status}='ready' THEN 'material:' ELSE 'upload:' END) || ({owner})"
    elif dialect == "mysql":
        phone_sql = "UPDATE tb_user SET phone=account WHERE phone IS NULL AND account REGEXP '^1[3-9][0-9]{9}$';"
        owner = "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.user_id'))"
        status = "JSON_UNQUOTE(JSON_EXTRACT(meta, '$.status'))"
        namespace = f"CONCAT(CASE WHEN {status}='ready' THEN 'material:' ELSE 'upload:' END, {owner})"
    elif dialect == "sqlite":
        phone_sql = "UPDATE tb_user SET phone=account WHERE phone IS NULL AND length(account)=11 AND substr(account,1,1)='1' AND substr(account,2,1) BETWEEN '3' AND '9' AND account NOT GLOB '*[^0-9]*';"
        owner = "json_extract(meta, '$.user_id')"
        status = "json_extract(meta, '$.status')"
        namespace = f"(CASE WHEN {status}='ready' THEN 'material:' ELSE 'upload:' END) || ({owner})"
    else:
        raise ValueError("账号服务迁移不支持当前数据库")
    material_sql = f"UPDATE tb_gen_asset_cache SET task_type={namespace} WHERE asset_type='uploaded_material' AND task_type='upload' AND {owner} IS NOT NULL;"
    # 启动追平可能已新增手机号，迁移仍需执行邀请表及素材归属变更。
    from plugin.database.schema_sync import _existing_columns

    engine = "postgresql" if dialect == "postgres" else dialect
    schema_sql = SCHEMA_SQL[dialect]["upgrade"]
    if "phone" in await _existing_columns(db, engine, "tb_user"):
        schema_sql = "\n".join(
            line for line in schema_sql.splitlines()
            if not (line.startswith("ALTER TABLE") and " ADD " in line and ("\"phone\"" in line or "`phone`" in line) and "INDEX" not in line)
        )
    if dialect == "mysql":
        indexes = await db.execute_query_dict("SHOW INDEX FROM `tb_user`")
        if any(row["Column_name"] == "phone" and not row["Non_unique"] for row in indexes):
            schema_sql = schema_sql.replace("ALTER TABLE `tb_user` ADD UNIQUE INDEX `phone` (`phone`);", "")
    elif dialect == "sqlite":
        schema_sql = schema_sql.replace("CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ")
    return schema_sql + "\n" + phone_sql + material_sql


async def downgrade(db: BaseDBAsyncClient) -> str:
    """回退结构与素材命名空间；回退会移除邀请码关系，请先备份业务数据。"""
    dialect = db.capabilities.dialect
    material_sql = "UPDATE tb_gen_asset_cache SET task_type='upload' WHERE asset_type='uploaded_material' AND (task_type LIKE 'material:%' OR task_type LIKE 'upload:%');"
    return material_sql + SCHEMA_SQL[dialect]["downgrade"]
