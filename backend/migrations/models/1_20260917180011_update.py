from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `tb_generate_task`;
        DROP TABLE IF EXISTS `tb_video_template`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
