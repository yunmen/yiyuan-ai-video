from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `tb_system_dept` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL COMMENT '部门名称',
    `path` VARCHAR(20) NOT NULL COMMENT '路径',
    `desc` VARCHAR(500) COMMENT '备注',
    `order` INT NOT NULL COMMENT '排序' DEFAULT 0,
    `parent_id` INT NOT NULL COMMENT '父部门ID' DEFAULT 0,
    `active` BOOL NOT NULL COMMENT '是否激活' DEFAULT 0
) CHARACTER SET utf8mb4 COMMENT='系统部门表';
CREATE TABLE IF NOT EXISTS `tb_system_log` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `request_id` VARCHAR(50) NOT NULL COMMENT '请求Id',
    `summary` VARCHAR(255) NOT NULL COMMENT '接口说明',
    `url` VARCHAR(255) NOT NULL COMMENT '请求地址',
    `method` VARCHAR(20) COMMENT '请求类型',
    `client_ip` VARCHAR(64) COMMENT '客户端IP',
    `headers` LONGTEXT COMMENT '请求头',
    `payload` JSON COMMENT '请求参数',
    `result` JSON COMMENT '响应结果',
    `status_code` VARCHAR(20) COMMENT '响应码',
    `process_time` VARCHAR(20) COMMENT '响应时间',
    `error_log` LONGTEXT COMMENT '错误日志',
    `client_type` VARCHAR(50) COMMENT '客户端',
    `operator_account` VARCHAR(50) COMMENT '操作人账号',
    `operator_nickname` VARCHAR(50) COMMENT '操作人昵称'
) CHARACTER SET utf8mb4 COMMENT='系统日志表';
CREATE TABLE IF NOT EXISTS `tb_system_menu` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `title` VARCHAR(20) NOT NULL COMMENT '显示名称',
    `parent_id` INT NOT NULL COMMENT '父菜单ID' DEFAULT 0,
    `type` VARCHAR(100) NOT NULL COMMENT '菜单类型',
    `name` VARCHAR(100) NOT NULL COMMENT '别名',
    `icon` VARCHAR(100) NOT NULL COMMENT '菜单图标',
    `path` VARCHAR(100) NOT NULL COMMENT '菜单路径',
    `redirect` VARCHAR(100) COMMENT '重定向',
    `active` VARCHAR(100) COMMENT '菜单高亮',
    `component` VARCHAR(100) NOT NULL COMMENT '组件',
    `color` VARCHAR(100) COMMENT '颜色',
    `hidden` BOOL COMMENT '隐藏菜单' DEFAULT 0,
    `hiddenBreadcrumb` BOOL COMMENT '隐藏面包屑' DEFAULT 0,
    `fullpage` BOOL COMMENT '整页路由' DEFAULT 0,
    `tag` VARCHAR(100) COMMENT '标签',
    `order` INT NOT NULL COMMENT '排序' DEFAULT 0,
    `apiList` JSON COMMENT '接口权限'
) CHARACTER SET utf8mb4 COMMENT='系统菜单表';
CREATE TABLE IF NOT EXISTS `tb_system_role` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL COMMENT '角色名称',
    `alias` VARCHAR(20) COMMENT '别名',
    `desc` VARCHAR(500) COMMENT '角色描述',
    `active` BOOL NOT NULL COMMENT '是否激活' DEFAULT 0
) CHARACTER SET utf8mb4 COMMENT='系统角色表';
CREATE TABLE IF NOT EXISTS `tb_system_task` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(50) NOT NULL COMMENT '任务名称',
    `func` VARCHAR(50) NOT NULL COMMENT '执行方法',
    `args` JSON COMMENT '位置参数',
    `kwargs` JSON COMMENT '关键字参数',
    `trigger` VARCHAR(50) NOT NULL COMMENT '触发器',
    `executor` VARCHAR(50) NOT NULL COMMENT '执行器',
    `jobstore` VARCHAR(50) NOT NULL COMMENT '储存器',
    `start_date` DATETIME(6) COMMENT '开始时间',
    `end_date` DATETIME(6) COMMENT '结束时间',
    `trigger_args` VARCHAR(20) NOT NULL COMMENT 'trigger表达式',
    `active` BOOL NOT NULL COMMENT '是否激活' DEFAULT 0,
    `desc` VARCHAR(255) COMMENT '任务描述'
) CHARACTER SET utf8mb4 COMMENT='定时任务表';
CREATE TABLE IF NOT EXISTS `tb_system_tasklog` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(255) NOT NULL COMMENT '任务名称',
    `status` BOOL NOT NULL COMMENT '状态, True为成功,False为失败',
    `desc` LONGTEXT NOT NULL COMMENT '任务描述',
    `next_run_time` DATETIME(6) COMMENT '下次执行时间',
    `task_id` BIGINT NOT NULL COMMENT '任务'
) CHARACTER SET utf8mb4 COMMENT='任务日志表';
CREATE TABLE IF NOT EXISTS `tb_system_user` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `account` VARCHAR(20) NOT NULL COMMENT '账号',
    `realname` VARCHAR(30) NOT NULL COMMENT '姓名',
    `nickname` VARCHAR(30) NOT NULL COMMENT '昵称',
    `avatar` VARCHAR(255) COMMENT '头像',
    `email` VARCHAR(255) COMMENT '邮箱',
    `phone` VARCHAR(20) NOT NULL COMMENT '电话',
    `password` VARCHAR(128) NOT NULL COMMENT '密码',
    `superuser` BOOL NOT NULL COMMENT '是否超级管理员' DEFAULT 0,
    `permission` SMALLINT COMMENT '数据权限',
    `active` BOOL NOT NULL COMMENT '是否激活' DEFAULT 0,
    `last_login_type` SMALLINT COMMENT '最后登录类型',
    `last_login_time` DATETIME(6) COMMENT '最后登录时间',
    `last_login_ip` VARCHAR(128) COMMENT '最后登录Ip',
    `dept_id` BIGINT COMMENT '部门'
) CHARACTER SET utf8mb4 COMMENT='系统用户表';
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
) CHARACTER SET utf8mb4 COMMENT='爆款视频模板表';
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
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `tb_system_role_menu` (
    `role_id` BIGINT NOT NULL,
    `menu_id` BIGINT NOT NULL,
    FOREIGN KEY (`role_id`) REFERENCES `tb_system_role` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`menu_id`) REFERENCES `tb_system_menu` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_tb_system_r_role_id_7dc296` (`role_id`, `menu_id`)
) CHARACTER SET utf8mb4 COMMENT='角色菜单表';
CREATE TABLE IF NOT EXISTS `tb_system_user_role` (
    `user_id` BIGINT NOT NULL,
    `role_id` BIGINT NOT NULL,
    FOREIGN KEY (`user_id`) REFERENCES `tb_system_user` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`role_id`) REFERENCES `tb_system_role` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uidx_tb_system_u_user_id_14f52a` (`user_id`, `role_id`)
) CHARACTER SET utf8mb4 COMMENT='用户角色表';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
