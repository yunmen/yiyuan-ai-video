from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `tb_payment_package` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(50) NOT NULL COMMENT '套餐名称',
    `sub_title` VARCHAR(100) COMMENT '套餐副标题',
    `credits` INT NOT NULL COMMENT '到账额度(次)',
    `price` DECIMAL(10,2) NOT NULL COMMENT '售价(元)',
    `tag` VARCHAR(20) COMMENT '角标文案(如推荐/热卖)',
    `sort` INT NOT NULL COMMENT '排序(倒序,越大越靠前)' DEFAULT 0,
    `active` BOOL NOT NULL COMMENT '是否上架' DEFAULT 1
) CHARACTER SET utf8mb4 COMMENT='充值套餐表';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `tb_payment_package`;"""
