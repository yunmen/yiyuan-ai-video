from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `tb_credit_log` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL COMMENT '用户Id',
    `change` INT NOT NULL COMMENT '变动值(正增负减)',
    `balance` INT NOT NULL COMMENT '变动后余额(免费+付费)',
    `type` VARCHAR(20) NOT NULL COMMENT '类型:reset每日重置/consume消耗/recharge充值/grant赠送',
    `task_id` BIGINT COMMENT '关联生成任务Id',
    `remark` VARCHAR(255) NOT NULL COMMENT '备注' DEFAULT '',
    KEY `idx_tb_credit_l_user_id_d1050c` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='C端用户额度流水表';
        ALTER TABLE `tb_user` ADD `last_reset_date` DATE COMMENT '免费额度最近重置日期';
        ALTER TABLE `tb_user` ADD `credits` INT NOT NULL COMMENT '付费额度(充值/赠送,永久有效)' DEFAULT 0;
        ALTER TABLE `tb_user` ADD `free_credits` INT NOT NULL COMMENT '每日免费额度(跨天重置)' DEFAULT 3;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tb_user` DROP COLUMN `last_reset_date`;
        ALTER TABLE `tb_user` DROP COLUMN `credits`;
        ALTER TABLE `tb_user` DROP COLUMN `free_credits`;
        DROP TABLE IF EXISTS `tb_credit_log`;"""
