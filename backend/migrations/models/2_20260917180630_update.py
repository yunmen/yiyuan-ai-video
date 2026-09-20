from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `tb_generate_task` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `task_no` VARCHAR(32) NOT NULL UNIQUE COMMENT '任务编号',
    `status` VARCHAR(20) NOT NULL COMMENT '任务状态(processing/success/failed)' DEFAULT 'processing',
    `progress` INT NOT NULL COMMENT '生成进度(0-100)' DEFAULT 0,
    `materials` JSON NOT NULL COMMENT '上传素材URL列表',
    `remark` VARCHAR(500) COMMENT '补充信息(可选)',
    `result_video` VARCHAR(500) COMMENT '生成结果视频URL',
    `fail_reason` VARCHAR(500) COMMENT '失败原因',
    `device` VARCHAR(20) NOT NULL COMMENT '来源设备(desktop/mobile)' DEFAULT 'desktop',
    `template_id` BIGINT COMMENT '关联模板',
    KEY `idx_tb_generate_task_no_5026b2` (`task_no`),
    KEY `idx_tb_generate_status_b85723` (`status`)
) CHARACTER SET utf8mb4 COMMENT='视频生成任务表';
        CREATE TABLE IF NOT EXISTS `tb_video_template` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `title` VARCHAR(100) NOT NULL COMMENT '模板标题',
    `category` VARCHAR(50) NOT NULL COMMENT '模板分类(美食/零售/美妆/教育等)',
    `cover` VARCHAR(500) COMMENT '封面图URL',
    `video_url` VARCHAR(500) COMMENT '模板示例视频URL',
    `duration` INT NOT NULL COMMENT '视频时长(秒)' DEFAULT 0,
    `hot` INT NOT NULL COMMENT '热度值' DEFAULT 0,
    `use_count` INT NOT NULL COMMENT '使用次数' DEFAULT 0,
    `desc` LONGTEXT COMMENT '模板说明',
    `tags` JSON NOT NULL COMMENT '标签列表',
    `example_images` JSON NOT NULL COMMENT '效果示例图列表',
    `sort` INT NOT NULL COMMENT '排序权重(越大越靠前)' DEFAULT 0,
    `active` BOOL NOT NULL COMMENT '是否上架' DEFAULT 1,
    KEY `idx_tb_video_te_title_85daf5` (`title`),
    KEY `idx_tb_video_te_categor_aa076a` (`category`)
) CHARACTER SET utf8mb4 COMMENT='爆款视频模板表';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `tb_video_template`;
        DROP TABLE IF EXISTS `tb_generate_task`;"""
