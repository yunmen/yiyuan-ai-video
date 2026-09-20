from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `tb_video_category` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(50) NOT NULL UNIQUE COMMENT '分类名称',
    `cover` VARCHAR(255) COMMENT '分类图标/封面',
    `sort` INT NOT NULL COMMENT '排序(倒序,越大越靠前)' DEFAULT 0,
    `active` BOOL NOT NULL COMMENT '是否启用' DEFAULT 1,
    `remark` VARCHAR(255) NOT NULL COMMENT '备注' DEFAULT ''
) CHARACTER SET utf8mb4 COMMENT='视频模板分类表';
        ALTER TABLE `tb_video_template` ADD `default_text` JSON NOT NULL COMMENT '默认文案(大标题/副标题/口播)';
        ALTER TABLE `tb_video_template` ADD `recommend` BOOL NOT NULL COMMENT '是否首页推荐' DEFAULT 0;
        ALTER TABLE `tb_video_template` ADD `recommend_sort` INT NOT NULL COMMENT '推荐位排序(倒序)' DEFAULT 0;
        CREATE TABLE IF NOT EXISTS `tb_user_sign` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL COMMENT '用户Id',
    `sign_date` DATE NOT NULL COMMENT '签到日期',
    `credits` INT NOT NULL COMMENT '本次获得额度' DEFAULT 1,
    `streak` INT NOT NULL COMMENT '连续签到天数(含本次)' DEFAULT 1,
    KEY `idx_tb_user_sig_user_id_1a5f2e` (`user_id`),
    UNIQUE KEY `uid_tb_user_sign_user_id_sign` (`user_id`, `sign_date`)
) CHARACTER SET utf8mb4 COMMENT='C端用户签到表';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `tb_user_sign`;
        ALTER TABLE `tb_video_template` DROP COLUMN `recommend_sort`;
        ALTER TABLE `tb_video_template` DROP COLUMN `recommend`;
        ALTER TABLE `tb_video_template` DROP COLUMN `default_text`;
        DROP TABLE IF EXISTS `tb_video_category`;"""
