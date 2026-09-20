from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tb_video_template` DROP INDEX `idx_tb_video_te_categor_aa076a`;
        ALTER TABLE `tb_video_template` DROP INDEX `idx_tb_video_te_title_85daf5`;
        ALTER TABLE `tb_generate_task` DROP INDEX `idx_tb_generate_status_b85723`;
        CREATE TABLE IF NOT EXISTS `tb_digital_human` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(50) NOT NULL COMMENT '数字人名称',
    `avatar` VARCHAR(255) COMMENT '头像',
    `gender` VARCHAR(10) NOT NULL COMMENT '性别' DEFAULT '女',
    `style` VARCHAR(50) COMMENT '风格',
    `desc` LONGTEXT COMMENT '简介',
    `tags` JSON NOT NULL COMMENT '标签',
    `preview_video` VARCHAR(255) COMMENT '预览视频',
    `sort` INT NOT NULL COMMENT '排序' DEFAULT 0,
    `active` BOOL NOT NULL COMMENT '是否上架' DEFAULT 1
) CHARACTER SET utf8mb4 COMMENT='数字人表';
        ALTER TABLE `tb_generate_task` ADD `params` JSON COMMENT '生成参数(用于重新生成)';
        ALTER TABLE `tb_generate_task` ADD `user_id` BIGINT COMMENT '关联用户Id';
        ALTER TABLE `tb_generate_task` ADD `usage` JSON COMMENT '用量与消耗(计费,worker 回调回写)';
        ALTER TABLE `tb_generate_task` ADD `result_text` LONGTEXT COMMENT '文本类结果';
        ALTER TABLE `tb_generate_task` ADD `type` VARCHAR(20) NOT NULL COMMENT '任务类型:video/image/audio/text' DEFAULT 'video';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `device` VARCHAR(20) NOT NULL COMMENT '设备类型' DEFAULT 'desktop';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `result_video` VARCHAR(512) COMMENT '生成结果媒体地址(视频/图片/音频)';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `result_video` VARCHAR(512) COMMENT '生成结果媒体地址(视频/图片/音频)';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `progress` INT NOT NULL COMMENT '进度百分比' DEFAULT 0;
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `materials` JSON NOT NULL COMMENT '用户上传素材';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `remark` LONGTEXT COMMENT '备注';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `remark` LONGTEXT COMMENT '备注';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `fail_reason` VARCHAR(255) COMMENT '失败原因';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `status` VARCHAR(20) NOT NULL COMMENT '任务状态' DEFAULT 'processing';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `template_id` BIGINT COMMENT '模板';
        CREATE TABLE IF NOT EXISTS `tb_user` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `account` VARCHAR(20) NOT NULL UNIQUE COMMENT '账号(手机号)',
    `nickname` VARCHAR(30) NOT NULL COMMENT '昵称' DEFAULT '',
    `avatar` VARCHAR(255) COMMENT '头像',
    `password` VARCHAR(128) NOT NULL COMMENT '密码',
    `status` BOOL NOT NULL COMMENT '是否启用' DEFAULT 1
) CHARACTER SET utf8mb4 COMMENT='C端用户表';
        ALTER TABLE `tb_video_template` ALTER COLUMN `duration` SET DEFAULT 10;
        ALTER TABLE `tb_video_template` MODIFY COLUMN `cover` VARCHAR(255) COMMENT '封面图';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `cover` VARCHAR(255) COMMENT '封面图';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `desc` LONGTEXT COMMENT '模板描述';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `video_url` VARCHAR(255) COMMENT '示例视频地址';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `video_url` VARCHAR(255) COMMENT '示例视频地址';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `tags` JSON NOT NULL COMMENT '标签';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `category` VARCHAR(50) NOT NULL COMMENT '模板分类';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `sort` INT NOT NULL COMMENT '排序' DEFAULT 0;
        ALTER TABLE `tb_video_template` MODIFY COLUMN `example_images` JSON NOT NULL COMMENT '示例图';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `tb_generate_task` DROP COLUMN `params`;
        ALTER TABLE `tb_generate_task` DROP COLUMN `user_id`;
        ALTER TABLE `tb_generate_task` DROP COLUMN `usage`;
        ALTER TABLE `tb_generate_task` DROP COLUMN `result_text`;
        ALTER TABLE `tb_generate_task` DROP COLUMN `type`;
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `device` VARCHAR(20) NOT NULL COMMENT '来源设备(desktop/mobile)' DEFAULT 'desktop';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `result_video` VARCHAR(500) COMMENT '生成结果视频URL';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `result_video` VARCHAR(500) COMMENT '生成结果视频URL';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `progress` INT NOT NULL COMMENT '生成进度(0-100)' DEFAULT 0;
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `materials` JSON NOT NULL COMMENT '上传素材URL列表';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `remark` VARCHAR(500) COMMENT '补充信息(可选)';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `remark` VARCHAR(500) COMMENT '补充信息(可选)';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `fail_reason` VARCHAR(500) COMMENT '失败原因';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `status` VARCHAR(20) NOT NULL COMMENT '任务状态(processing/success/failed)' DEFAULT 'processing';
        ALTER TABLE `tb_generate_task` MODIFY COLUMN `template_id` BIGINT COMMENT '关联模板';
        ALTER TABLE `tb_video_template` ALTER COLUMN `duration` SET DEFAULT 0;
        ALTER TABLE `tb_video_template` MODIFY COLUMN `cover` VARCHAR(500) COMMENT '封面图URL';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `cover` VARCHAR(500) COMMENT '封面图URL';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `desc` LONGTEXT COMMENT '模板说明';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `video_url` VARCHAR(500) COMMENT '模板示例视频URL';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `video_url` VARCHAR(500) COMMENT '模板示例视频URL';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `tags` JSON NOT NULL COMMENT '标签列表';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `category` VARCHAR(50) NOT NULL COMMENT '模板分类(美食/零售/美妆/教育等)';
        ALTER TABLE `tb_video_template` MODIFY COLUMN `sort` INT NOT NULL COMMENT '排序权重(越大越靠前)' DEFAULT 0;
        ALTER TABLE `tb_video_template` MODIFY COLUMN `example_images` JSON NOT NULL COMMENT '效果示例图列表';
        DROP TABLE IF EXISTS `tb_user`;
        DROP TABLE IF EXISTS `tb_digital_human`;
        ALTER TABLE `tb_generate_task` ADD INDEX `idx_tb_generate_status_b85723` (`status`);
        ALTER TABLE `tb_video_template` ADD INDEX `idx_tb_video_te_title_85daf5` (`title`);
        ALTER TABLE `tb_video_template` ADD INDEX `idx_tb_video_te_categor_aa076a` (`category`);"""
