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
    `type` VARCHAR(20) NOT NULL COMMENT '类型:reset每日重置/consume消耗/recharge充值/grant赠送/refund失败返还',
    `task_id` BIGINT COMMENT '关联生成任务Id',
    `remark` VARCHAR(255) NOT NULL COMMENT '备注' DEFAULT '',
    KEY `idx_tb_credit_l_user_id_d1050c` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='C端用户额度流水表';
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
    `image` VARCHAR(255) COMMENT '形象图(口型驱动底图,留空回退 avatar)',
    `voice` VARCHAR(100) COMMENT '音色(TTS voice,留空用网关默认音色)',
    `model` VARCHAR(100) COMMENT '生成模型(留空用全局配置 gen.digital_model)',
    `default_text` LONGTEXT COMMENT '默认口播文案(用户未填写时使用)',
    `pose_variants` JSON NOT NULL COMMENT '派生视图[{name,image}]',
    `sort` INT NOT NULL COMMENT '排序' DEFAULT 0,
    `active` BOOL NOT NULL COMMENT '是否上架' DEFAULT 1
) CHARACTER SET utf8mb4 COMMENT='数字人表';
CREATE TABLE IF NOT EXISTS `tb_gen_asset_cache` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `cache_key` VARCHAR(64) NOT NULL UNIQUE COMMENT '缓存键(输入内容哈希)',
    `asset_type` VARCHAR(32) NOT NULL COMMENT '产物类型:tts_audio/optimized_prompt',
    `task_type` VARCHAR(32) NOT NULL COMMENT '任务类型,便于按类型清理' DEFAULT '',
    `content` LONGTEXT NOT NULL COMMENT '产物内容(URL 或文本)',
    `meta` JSON NOT NULL COMMENT '附加信息(模型/音色等,便于排查)',
    `hit_count` INT NOT NULL COMMENT '命中次数(用于验证降本效果)' DEFAULT 0,
    `expire_time` DATETIME(6) COMMENT '过期时间(为空表示不过期)',
    KEY `idx_tb_gen_asse_asset_t_078dc1` (`asset_type`)
) CHARACTER SET utf8mb4 COMMENT='生成中间产物缓存(P2 资产复用)';
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
) CHARACTER SET utf8mb4 COMMENT='充值套餐表';
CREATE TABLE IF NOT EXISTS `tb_system_config` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `key` VARCHAR(64) NOT NULL UNIQUE COMMENT '配置键,如 gen.video_model_i2v',
    `value` LONGTEXT COMMENT '配置值',
    `group` VARCHAR(32) NOT NULL COMMENT '配置分组' DEFAULT 'gen',
    `remark` VARCHAR(255) NOT NULL COMMENT '配置说明' DEFAULT '',
    `is_public` BOOL NOT NULL COMMENT '是否允许未登录读取(敏感配置置 False)' DEFAULT 1
) CHARACTER SET utf8mb4 COMMENT='系统业务配置表';
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
CREATE TABLE IF NOT EXISTS `tb_user` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `account` VARCHAR(20) NOT NULL UNIQUE COMMENT '账号(手机号)',
    `nickname` VARCHAR(30) NOT NULL COMMENT '昵称' DEFAULT '',
    `avatar` VARCHAR(255) COMMENT '头像',
    `password` VARCHAR(128) NOT NULL COMMENT '密码',
    `status` BOOL NOT NULL COMMENT '是否启用' DEFAULT 1,
    `free_credits` INT NOT NULL COMMENT '每日免费额度(跨天重置)' DEFAULT 3,
    `credits` INT NOT NULL COMMENT '付费额度(充值/赠送,永久有效)' DEFAULT 0,
    `last_reset_date` DATE COMMENT '免费额度最近重置日期'
) CHARACTER SET utf8mb4 COMMENT='C端用户表';
CREATE TABLE IF NOT EXISTS `tb_user_payment` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL COMMENT '下单用户Id',
    `order_no` VARCHAR(64) NOT NULL UNIQUE COMMENT '商户订单号',
    `transaction_id` VARCHAR(64) COMMENT '渠道交易号(微信)',
    `biz_type` INT NOT NULL COMMENT '业务类型:1视频生成',
    `package_name` VARCHAR(100) NOT NULL COMMENT '商品名称快照',
    `amount` DECIMAL(10,2) NOT NULL COMMENT '金额(元)',
    `status` INT NOT NULL COMMENT '状态:1待支付2已支付3已交付4已取消5退款中6已退款' DEFAULT 1,
    `gateway` VARCHAR(20) NOT NULL COMMENT '支付网关:wechat/mock' DEFAULT 'wechat',
    `pay_time` DATETIME(6) COMMENT '支付完成时间',
    `source` JSON COMMENT '下单业务快照(模板/素材/文案)',
    `request` JSON COMMENT '渠道下单响应快照',
    `response` JSON COMMENT '渠道回调报文快照',
    `remark` VARCHAR(255) NOT NULL COMMENT '备注(退款原因等)' DEFAULT ''
) CHARACTER SET utf8mb4 COMMENT='支付订单表';
CREATE TABLE IF NOT EXISTS `tb_user_sign` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL COMMENT '用户Id',
    `sign_date` DATE NOT NULL COMMENT '签到日期',
    `credits` INT NOT NULL COMMENT '本次获得额度' DEFAULT 1,
    `streak` INT NOT NULL COMMENT '连续签到天数(含本次)' DEFAULT 1,
    UNIQUE KEY `uid_tb_user_sig_user_id_21c8e8` (`user_id`, `sign_date`),
    KEY `idx_tb_user_sig_user_id_bb1043` (`user_id`)
) CHARACTER SET utf8mb4 COMMENT='C端用户签到表';
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
CREATE TABLE IF NOT EXISTS `tb_video_template` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `title` VARCHAR(100) NOT NULL COMMENT '模板标题',
    `category` VARCHAR(50) NOT NULL COMMENT '模板分类',
    `cover` VARCHAR(255) COMMENT '封面图',
    `video_url` VARCHAR(255) COMMENT '示例视频地址',
    `duration` INT NOT NULL COMMENT '视频时长(秒)' DEFAULT 10,
    `hot` INT NOT NULL COMMENT '热度值' DEFAULT 0,
    `use_count` INT NOT NULL COMMENT '使用次数' DEFAULT 0,
    `desc` LONGTEXT COMMENT '模板描述',
    `tags` JSON NOT NULL COMMENT '标签',
    `example_images` JSON NOT NULL COMMENT '示例图',
    `default_text` JSON NOT NULL COMMENT '默认文案(大标题/副标题/口播)',
    `prompt_parts` JSON NOT NULL COMMENT '画面构成(主体/镜头/场景)',
    `recommend` BOOL NOT NULL COMMENT '是否首页推荐' DEFAULT 0,
    `recommend_sort` INT NOT NULL COMMENT '推荐位排序(倒序)' DEFAULT 0,
    `sort` INT NOT NULL COMMENT '排序' DEFAULT 0,
    `active` BOOL NOT NULL COMMENT '是否上架' DEFAULT 1
) CHARACTER SET utf8mb4 COMMENT='视频模板表';
CREATE TABLE IF NOT EXISTS `tb_generate_task` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '主键Id',
    `deleted` BOOL NOT NULL COMMENT '软删除标记,True无效False有效' DEFAULT 0,
    `create_time` DATETIME(6) NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `update_time` DATETIME(6) NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `task_no` VARCHAR(32) NOT NULL UNIQUE COMMENT '任务编号',
    `type` VARCHAR(20) NOT NULL COMMENT '任务类型:video/image/audio/text/digital' DEFAULT 'video',
    `status` VARCHAR(20) NOT NULL COMMENT '任务状态' DEFAULT 'processing',
    `progress` INT NOT NULL COMMENT '进度百分比' DEFAULT 0,
    `materials` JSON NOT NULL COMMENT '用户上传素材',
    `params` JSON COMMENT '生成参数(用于重新生成)',
    `checkpoint` JSON COMMENT '断点续跑检查点(stage + 各阶段中间产物)',
    `remark` LONGTEXT COMMENT '备注',
    `result_video` VARCHAR(512) COMMENT '生成结果媒体地址(视频/图片/音频)',
    `result_text` LONGTEXT COMMENT '文本类结果',
    `fail_reason` VARCHAR(255) COMMENT '失败原因',
    `usage` JSON COMMENT '用量与消耗(计费,worker 回调回写)',
    `device` VARCHAR(20) NOT NULL COMMENT '设备类型' DEFAULT 'desktop',
    `user_id` BIGINT COMMENT '关联用户Id',
    `order_no` VARCHAR(64) COMMENT '关联支付订单号(付费任务)',
    `template_id` BIGINT COMMENT '模板',
    KEY `idx_tb_generate_order_n_7e656b` (`order_no`)
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
