from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tb_generate_task` ADD `checkpoint` JSON COMMENT '断点续跑检查点(stage+中间产物)';
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tb_generate_task` DROP COLUMN `checkpoint`;
        """
