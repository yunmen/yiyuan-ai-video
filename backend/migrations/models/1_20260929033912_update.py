from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "tb_generate_task" ALTER COLUMN "result_video" TYPE TEXT USING "result_video"::TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "tb_generate_task" ALTER COLUMN "result_video" TYPE VARCHAR(512) USING "result_video"::VARCHAR(512);"""
