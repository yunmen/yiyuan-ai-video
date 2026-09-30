from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `tb_feedback` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `content` LONGTEXT NOT NULL COMMENT '反馈内容',
    `contact` VARCHAR(100) COMMENT '联系方式(选填)',
    `user_id` BIGINT COMMENT '提交用户Id(登录时记录,匿名留空)',
    `status` INT NOT NULL COMMENT '处理状态:0待处理 1已处理' DEFAULT 0
) CHARACTER SET utf8mb4 COMMENT='用户意见反馈表';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `result_video` LONGTEXT COMMENT '生成结果媒体地址(视频/图片/音频)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `result_video` VARCHAR(512) COMMENT '生成结果媒体地址(视频/图片/音频)';
        DROP TABLE IF EXISTS `tb_feedback`;"""
