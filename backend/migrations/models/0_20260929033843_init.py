from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "tb_credit_log" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL,
    "change" INT NOT NULL,
    "balance" INT NOT NULL,
    "type" VARCHAR(20) NOT NULL,
    "task_id" BIGINT,
    "remark" VARCHAR(255) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS "idx_tb_credit_l_user_id_d1050c" ON "tb_credit_log" ("user_id");
COMMENT ON COLUMN "tb_credit_log"."id" IS '主键Id';
COMMENT ON COLUMN "tb_credit_log"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_credit_log"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_credit_log"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_credit_log"."user_id" IS '用户Id';
COMMENT ON COLUMN "tb_credit_log"."change" IS '变动值(正增负减)';
COMMENT ON COLUMN "tb_credit_log"."balance" IS '变动后余额(免费+付费)';
COMMENT ON COLUMN "tb_credit_log"."type" IS '类型:reset每日重置/consume消耗/recharge充值/grant赠送/refund失败返还';
COMMENT ON COLUMN "tb_credit_log"."task_id" IS '关联生成任务Id';
COMMENT ON COLUMN "tb_credit_log"."remark" IS '备注';
COMMENT ON TABLE "tb_credit_log" IS 'C端用户额度流水表';
CREATE TABLE IF NOT EXISTS "tb_digital_human" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(50) NOT NULL,
    "avatar" VARCHAR(255),
    "gender" VARCHAR(10) NOT NULL DEFAULT '女',
    "style" VARCHAR(50),
    "desc" TEXT,
    "tags" JSONB NOT NULL,
    "preview_video" VARCHAR(255),
    "image" VARCHAR(255),
    "voice" VARCHAR(100),
    "model" VARCHAR(100),
    "default_text" TEXT,
    "pose_variants" JSONB NOT NULL,
    "sort" INT NOT NULL DEFAULT 0,
    "active" BOOL NOT NULL DEFAULT True
);
COMMENT ON COLUMN "tb_digital_human"."id" IS '主键Id';
COMMENT ON COLUMN "tb_digital_human"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_digital_human"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_digital_human"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_digital_human"."name" IS '数字人名称';
COMMENT ON COLUMN "tb_digital_human"."avatar" IS '头像';
COMMENT ON COLUMN "tb_digital_human"."gender" IS '性别';
COMMENT ON COLUMN "tb_digital_human"."style" IS '风格';
COMMENT ON COLUMN "tb_digital_human"."desc" IS '简介';
COMMENT ON COLUMN "tb_digital_human"."tags" IS '标签';
COMMENT ON COLUMN "tb_digital_human"."preview_video" IS '预览视频';
COMMENT ON COLUMN "tb_digital_human"."image" IS '形象图(口型驱动底图,留空回退 avatar)';
COMMENT ON COLUMN "tb_digital_human"."voice" IS '音色(TTS voice,留空用网关默认音色)';
COMMENT ON COLUMN "tb_digital_human"."model" IS '生成模型(留空用全局配置 gen.digital_model)';
COMMENT ON COLUMN "tb_digital_human"."default_text" IS '默认口播文案(用户未填写时使用)';
COMMENT ON COLUMN "tb_digital_human"."pose_variants" IS '派生视图[{name,image}]';
COMMENT ON COLUMN "tb_digital_human"."sort" IS '排序';
COMMENT ON COLUMN "tb_digital_human"."active" IS '是否上架';
COMMENT ON TABLE "tb_digital_human" IS '数字人表';
CREATE TABLE IF NOT EXISTS "tb_gen_asset_cache" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "cache_key" VARCHAR(64) NOT NULL UNIQUE,
    "asset_type" VARCHAR(32) NOT NULL,
    "task_type" VARCHAR(32) NOT NULL DEFAULT '',
    "content" TEXT NOT NULL,
    "meta" JSONB NOT NULL,
    "hit_count" INT NOT NULL DEFAULT 0,
    "expire_time" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_tb_gen_asse_asset_t_078dc1" ON "tb_gen_asset_cache" ("asset_type");
COMMENT ON COLUMN "tb_gen_asset_cache"."id" IS '主键Id';
COMMENT ON COLUMN "tb_gen_asset_cache"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_gen_asset_cache"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_gen_asset_cache"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_gen_asset_cache"."cache_key" IS '缓存键(输入内容哈希)';
COMMENT ON COLUMN "tb_gen_asset_cache"."asset_type" IS '产物类型:tts_audio/optimized_prompt';
COMMENT ON COLUMN "tb_gen_asset_cache"."task_type" IS '任务类型,便于按类型清理';
COMMENT ON COLUMN "tb_gen_asset_cache"."content" IS '产物内容(URL 或文本)';
COMMENT ON COLUMN "tb_gen_asset_cache"."meta" IS '附加信息(模型/音色等,便于排查)';
COMMENT ON COLUMN "tb_gen_asset_cache"."hit_count" IS '命中次数(用于验证降本效果)';
COMMENT ON COLUMN "tb_gen_asset_cache"."expire_time" IS '过期时间(为空表示不过期)';
COMMENT ON TABLE "tb_gen_asset_cache" IS '生成中间产物缓存(P2 资产复用)';
CREATE TABLE IF NOT EXISTS "tb_payment_package" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(50) NOT NULL,
    "sub_title" VARCHAR(100),
    "credits" INT NOT NULL,
    "price" DECIMAL(10,2) NOT NULL,
    "tag" VARCHAR(20),
    "sort" INT NOT NULL DEFAULT 0,
    "active" BOOL NOT NULL DEFAULT True
);
COMMENT ON COLUMN "tb_payment_package"."id" IS '主键Id';
COMMENT ON COLUMN "tb_payment_package"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_payment_package"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_payment_package"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_payment_package"."name" IS '套餐名称';
COMMENT ON COLUMN "tb_payment_package"."sub_title" IS '套餐副标题';
COMMENT ON COLUMN "tb_payment_package"."credits" IS '到账额度(次)';
COMMENT ON COLUMN "tb_payment_package"."price" IS '售价(元)';
COMMENT ON COLUMN "tb_payment_package"."tag" IS '角标文案(如推荐/热卖)';
COMMENT ON COLUMN "tb_payment_package"."sort" IS '排序(倒序,越大越靠前)';
COMMENT ON COLUMN "tb_payment_package"."active" IS '是否上架';
COMMENT ON TABLE "tb_payment_package" IS '充值套餐表';
CREATE TABLE IF NOT EXISTS "tb_system_config" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "key" VARCHAR(64) NOT NULL UNIQUE,
    "value" TEXT,
    "group" VARCHAR(32) NOT NULL DEFAULT 'gen',
    "remark" VARCHAR(255) NOT NULL DEFAULT '',
    "is_public" BOOL NOT NULL DEFAULT True
);
COMMENT ON COLUMN "tb_system_config"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_config"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_config"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_config"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_config"."key" IS '配置键,如 gen.video_model_i2v';
COMMENT ON COLUMN "tb_system_config"."value" IS '配置值';
COMMENT ON COLUMN "tb_system_config"."group" IS '配置分组';
COMMENT ON COLUMN "tb_system_config"."remark" IS '配置说明';
COMMENT ON COLUMN "tb_system_config"."is_public" IS '是否允许未登录读取(敏感配置置 False)';
COMMENT ON TABLE "tb_system_config" IS '系统业务配置表';
CREATE TABLE IF NOT EXISTS "tb_system_dept" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL,
    "path" VARCHAR(20) NOT NULL,
    "desc" VARCHAR(500),
    "order" INT NOT NULL DEFAULT 0,
    "parent_id" INT NOT NULL DEFAULT 0,
    "active" BOOL NOT NULL DEFAULT False
);
COMMENT ON COLUMN "tb_system_dept"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_dept"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_dept"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_dept"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_dept"."name" IS '部门名称';
COMMENT ON COLUMN "tb_system_dept"."path" IS '路径';
COMMENT ON COLUMN "tb_system_dept"."desc" IS '备注';
COMMENT ON COLUMN "tb_system_dept"."order" IS '排序';
COMMENT ON COLUMN "tb_system_dept"."parent_id" IS '父部门ID';
COMMENT ON COLUMN "tb_system_dept"."active" IS '是否激活';
COMMENT ON TABLE "tb_system_dept" IS '系统部门表';
CREATE TABLE IF NOT EXISTS "tb_system_log" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "request_id" VARCHAR(50) NOT NULL,
    "summary" VARCHAR(255) NOT NULL,
    "url" VARCHAR(255) NOT NULL,
    "method" VARCHAR(20),
    "client_ip" VARCHAR(64),
    "headers" TEXT,
    "payload" JSONB,
    "result" JSONB,
    "status_code" VARCHAR(20),
    "process_time" VARCHAR(20),
    "error_log" TEXT,
    "client_type" VARCHAR(50),
    "operator_account" VARCHAR(50),
    "operator_nickname" VARCHAR(50)
);
COMMENT ON COLUMN "tb_system_log"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_log"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_log"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_log"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_log"."request_id" IS '请求Id';
COMMENT ON COLUMN "tb_system_log"."summary" IS '接口说明';
COMMENT ON COLUMN "tb_system_log"."url" IS '请求地址';
COMMENT ON COLUMN "tb_system_log"."method" IS '请求类型';
COMMENT ON COLUMN "tb_system_log"."client_ip" IS '客户端IP';
COMMENT ON COLUMN "tb_system_log"."headers" IS '请求头';
COMMENT ON COLUMN "tb_system_log"."payload" IS '请求参数';
COMMENT ON COLUMN "tb_system_log"."result" IS '响应结果';
COMMENT ON COLUMN "tb_system_log"."status_code" IS '响应码';
COMMENT ON COLUMN "tb_system_log"."process_time" IS '响应时间';
COMMENT ON COLUMN "tb_system_log"."error_log" IS '错误日志';
COMMENT ON COLUMN "tb_system_log"."client_type" IS '客户端';
COMMENT ON COLUMN "tb_system_log"."operator_account" IS '操作人账号';
COMMENT ON COLUMN "tb_system_log"."operator_nickname" IS '操作人昵称';
COMMENT ON TABLE "tb_system_log" IS '系统日志表';
CREATE TABLE IF NOT EXISTS "tb_system_menu" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "title" VARCHAR(20) NOT NULL,
    "parent_id" INT NOT NULL DEFAULT 0,
    "type" VARCHAR(100) NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "icon" VARCHAR(100) NOT NULL,
    "path" VARCHAR(100) NOT NULL,
    "redirect" VARCHAR(100),
    "active" VARCHAR(100),
    "component" VARCHAR(100) NOT NULL,
    "color" VARCHAR(100),
    "hidden" BOOL DEFAULT False,
    "hiddenBreadcrumb" BOOL DEFAULT False,
    "fullpage" BOOL DEFAULT False,
    "tag" VARCHAR(100),
    "order" INT NOT NULL DEFAULT 0,
    "apiList" JSONB
);
COMMENT ON COLUMN "tb_system_menu"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_menu"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_menu"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_menu"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_menu"."title" IS '显示名称';
COMMENT ON COLUMN "tb_system_menu"."parent_id" IS '父菜单ID';
COMMENT ON COLUMN "tb_system_menu"."type" IS '菜单类型';
COMMENT ON COLUMN "tb_system_menu"."name" IS '别名';
COMMENT ON COLUMN "tb_system_menu"."icon" IS '菜单图标';
COMMENT ON COLUMN "tb_system_menu"."path" IS '菜单路径';
COMMENT ON COLUMN "tb_system_menu"."redirect" IS '重定向';
COMMENT ON COLUMN "tb_system_menu"."active" IS '菜单高亮';
COMMENT ON COLUMN "tb_system_menu"."component" IS '组件';
COMMENT ON COLUMN "tb_system_menu"."color" IS '颜色';
COMMENT ON COLUMN "tb_system_menu"."hidden" IS '隐藏菜单';
COMMENT ON COLUMN "tb_system_menu"."hiddenBreadcrumb" IS '隐藏面包屑';
COMMENT ON COLUMN "tb_system_menu"."fullpage" IS '整页路由';
COMMENT ON COLUMN "tb_system_menu"."tag" IS '标签';
COMMENT ON COLUMN "tb_system_menu"."order" IS '排序';
COMMENT ON COLUMN "tb_system_menu"."apiList" IS '接口权限';
COMMENT ON TABLE "tb_system_menu" IS '系统菜单表';
CREATE TABLE IF NOT EXISTS "tb_system_role" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL,
    "alias" VARCHAR(20),
    "desc" VARCHAR(500),
    "active" BOOL NOT NULL DEFAULT False
);
COMMENT ON COLUMN "tb_system_role"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_role"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_role"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_role"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_role"."name" IS '角色名称';
COMMENT ON COLUMN "tb_system_role"."alias" IS '别名';
COMMENT ON COLUMN "tb_system_role"."desc" IS '角色描述';
COMMENT ON COLUMN "tb_system_role"."active" IS '是否激活';
COMMENT ON TABLE "tb_system_role" IS '系统角色表';
CREATE TABLE IF NOT EXISTS "tb_system_task" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(50) NOT NULL,
    "func" VARCHAR(50) NOT NULL,
    "args" JSONB,
    "kwargs" JSONB,
    "trigger" VARCHAR(50) NOT NULL,
    "executor" VARCHAR(50) NOT NULL,
    "jobstore" VARCHAR(50) NOT NULL,
    "start_date" TIMESTAMPTZ,
    "end_date" TIMESTAMPTZ,
    "trigger_args" VARCHAR(20) NOT NULL,
    "active" BOOL NOT NULL DEFAULT False,
    "desc" VARCHAR(255)
);
COMMENT ON COLUMN "tb_system_task"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_task"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_task"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_task"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_task"."name" IS '任务名称';
COMMENT ON COLUMN "tb_system_task"."func" IS '执行方法';
COMMENT ON COLUMN "tb_system_task"."args" IS '位置参数';
COMMENT ON COLUMN "tb_system_task"."kwargs" IS '关键字参数';
COMMENT ON COLUMN "tb_system_task"."trigger" IS '触发器';
COMMENT ON COLUMN "tb_system_task"."executor" IS '执行器';
COMMENT ON COLUMN "tb_system_task"."jobstore" IS '储存器';
COMMENT ON COLUMN "tb_system_task"."start_date" IS '开始时间';
COMMENT ON COLUMN "tb_system_task"."end_date" IS '结束时间';
COMMENT ON COLUMN "tb_system_task"."trigger_args" IS 'trigger表达式';
COMMENT ON COLUMN "tb_system_task"."active" IS '是否激活';
COMMENT ON COLUMN "tb_system_task"."desc" IS '任务描述';
COMMENT ON TABLE "tb_system_task" IS '定时任务表';
CREATE TABLE IF NOT EXISTS "tb_system_tasklog" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(255) NOT NULL,
    "status" BOOL NOT NULL,
    "desc" TEXT NOT NULL,
    "next_run_time" TIMESTAMPTZ,
    "task_id" BIGINT NOT NULL
);
COMMENT ON COLUMN "tb_system_tasklog"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_tasklog"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_tasklog"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_tasklog"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_tasklog"."name" IS '任务名称';
COMMENT ON COLUMN "tb_system_tasklog"."status" IS '状态, True为成功,False为失败';
COMMENT ON COLUMN "tb_system_tasklog"."desc" IS '任务描述';
COMMENT ON COLUMN "tb_system_tasklog"."next_run_time" IS '下次执行时间';
COMMENT ON COLUMN "tb_system_tasklog"."task_id" IS '任务';
COMMENT ON TABLE "tb_system_tasklog" IS '任务日志表';
CREATE TABLE IF NOT EXISTS "tb_system_user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "account" VARCHAR(20) NOT NULL,
    "realname" VARCHAR(30) NOT NULL,
    "nickname" VARCHAR(30) NOT NULL,
    "avatar" VARCHAR(255),
    "email" VARCHAR(255),
    "phone" VARCHAR(20) NOT NULL,
    "password" VARCHAR(128) NOT NULL,
    "superuser" BOOL NOT NULL DEFAULT False,
    "permission" SMALLINT,
    "active" BOOL NOT NULL DEFAULT False,
    "last_login_type" SMALLINT,
    "last_login_time" TIMESTAMPTZ,
    "last_login_ip" VARCHAR(128),
    "dept_id" BIGINT
);
COMMENT ON COLUMN "tb_system_user"."id" IS '主键Id';
COMMENT ON COLUMN "tb_system_user"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_system_user"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_system_user"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_system_user"."account" IS '账号';
COMMENT ON COLUMN "tb_system_user"."realname" IS '姓名';
COMMENT ON COLUMN "tb_system_user"."nickname" IS '昵称';
COMMENT ON COLUMN "tb_system_user"."avatar" IS '头像';
COMMENT ON COLUMN "tb_system_user"."email" IS '邮箱';
COMMENT ON COLUMN "tb_system_user"."phone" IS '电话';
COMMENT ON COLUMN "tb_system_user"."password" IS '密码';
COMMENT ON COLUMN "tb_system_user"."superuser" IS '是否超级管理员';
COMMENT ON COLUMN "tb_system_user"."permission" IS '数据权限';
COMMENT ON COLUMN "tb_system_user"."active" IS '是否激活';
COMMENT ON COLUMN "tb_system_user"."last_login_type" IS '最后登录类型';
COMMENT ON COLUMN "tb_system_user"."last_login_time" IS '最后登录时间';
COMMENT ON COLUMN "tb_system_user"."last_login_ip" IS '最后登录Ip';
COMMENT ON COLUMN "tb_system_user"."dept_id" IS '部门';
COMMENT ON TABLE "tb_system_user" IS '系统用户表';
CREATE TABLE IF NOT EXISTS "tb_user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "account" VARCHAR(20) NOT NULL UNIQUE,
    "nickname" VARCHAR(30) NOT NULL DEFAULT '',
    "avatar" VARCHAR(255),
    "password" VARCHAR(128) NOT NULL,
    "status" BOOL NOT NULL DEFAULT True,
    "free_credits" INT NOT NULL DEFAULT 3,
    "credits" INT NOT NULL DEFAULT 0,
    "last_reset_date" DATE
);
COMMENT ON COLUMN "tb_user"."id" IS '主键Id';
COMMENT ON COLUMN "tb_user"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_user"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_user"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_user"."account" IS '账号(手机号)';
COMMENT ON COLUMN "tb_user"."nickname" IS '昵称';
COMMENT ON COLUMN "tb_user"."avatar" IS '头像';
COMMENT ON COLUMN "tb_user"."password" IS '密码';
COMMENT ON COLUMN "tb_user"."status" IS '是否启用';
COMMENT ON COLUMN "tb_user"."free_credits" IS '每日免费额度(跨天重置)';
COMMENT ON COLUMN "tb_user"."credits" IS '付费额度(充值/赠送,永久有效)';
COMMENT ON COLUMN "tb_user"."last_reset_date" IS '免费额度最近重置日期';
COMMENT ON TABLE "tb_user" IS 'C端用户表';
CREATE TABLE IF NOT EXISTS "tb_user_payment" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL,
    "order_no" VARCHAR(64) NOT NULL UNIQUE,
    "transaction_id" VARCHAR(64),
    "biz_type" INT NOT NULL,
    "package_name" VARCHAR(100) NOT NULL,
    "amount" DECIMAL(10,2) NOT NULL,
    "status" INT NOT NULL DEFAULT 1,
    "gateway" VARCHAR(20) NOT NULL DEFAULT 'wechat',
    "pay_time" TIMESTAMPTZ,
    "source" JSONB,
    "request" JSONB,
    "response" JSONB,
    "remark" VARCHAR(255) NOT NULL DEFAULT ''
);
COMMENT ON COLUMN "tb_user_payment"."id" IS '主键Id';
COMMENT ON COLUMN "tb_user_payment"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_user_payment"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_user_payment"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_user_payment"."user_id" IS '下单用户Id';
COMMENT ON COLUMN "tb_user_payment"."order_no" IS '商户订单号';
COMMENT ON COLUMN "tb_user_payment"."transaction_id" IS '渠道交易号(微信)';
COMMENT ON COLUMN "tb_user_payment"."biz_type" IS '业务类型:1视频生成';
COMMENT ON COLUMN "tb_user_payment"."package_name" IS '商品名称快照';
COMMENT ON COLUMN "tb_user_payment"."amount" IS '金额(元)';
COMMENT ON COLUMN "tb_user_payment"."status" IS '状态:1待支付2已支付3已交付4已取消5退款中6已退款';
COMMENT ON COLUMN "tb_user_payment"."gateway" IS '支付网关:wechat/mock';
COMMENT ON COLUMN "tb_user_payment"."pay_time" IS '支付完成时间';
COMMENT ON COLUMN "tb_user_payment"."source" IS '下单业务快照(模板/素材/文案)';
COMMENT ON COLUMN "tb_user_payment"."request" IS '渠道下单响应快照';
COMMENT ON COLUMN "tb_user_payment"."response" IS '渠道回调报文快照';
COMMENT ON COLUMN "tb_user_payment"."remark" IS '备注(退款原因等)';
COMMENT ON TABLE "tb_user_payment" IS '支付订单表';
CREATE TABLE IF NOT EXISTS "tb_user_sign" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" BIGINT NOT NULL,
    "sign_date" DATE NOT NULL,
    "credits" INT NOT NULL DEFAULT 1,
    "streak" INT NOT NULL DEFAULT 1,
    CONSTRAINT "uid_tb_user_sig_user_id_21c8e8" UNIQUE ("user_id", "sign_date")
);
CREATE INDEX IF NOT EXISTS "idx_tb_user_sig_user_id_bb1043" ON "tb_user_sign" ("user_id");
COMMENT ON COLUMN "tb_user_sign"."id" IS '主键Id';
COMMENT ON COLUMN "tb_user_sign"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_user_sign"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_user_sign"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_user_sign"."user_id" IS '用户Id';
COMMENT ON COLUMN "tb_user_sign"."sign_date" IS '签到日期';
COMMENT ON COLUMN "tb_user_sign"."credits" IS '本次获得额度';
COMMENT ON COLUMN "tb_user_sign"."streak" IS '连续签到天数(含本次)';
COMMENT ON TABLE "tb_user_sign" IS 'C端用户签到表';
CREATE TABLE IF NOT EXISTS "tb_video_category" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(50) NOT NULL UNIQUE,
    "cover" VARCHAR(255),
    "sort" INT NOT NULL DEFAULT 0,
    "active" BOOL NOT NULL DEFAULT True,
    "remark" VARCHAR(255) NOT NULL DEFAULT ''
);
COMMENT ON COLUMN "tb_video_category"."id" IS '主键Id';
COMMENT ON COLUMN "tb_video_category"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_video_category"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_video_category"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_video_category"."name" IS '分类名称';
COMMENT ON COLUMN "tb_video_category"."cover" IS '分类图标/封面';
COMMENT ON COLUMN "tb_video_category"."sort" IS '排序(倒序,越大越靠前)';
COMMENT ON COLUMN "tb_video_category"."active" IS '是否启用';
COMMENT ON COLUMN "tb_video_category"."remark" IS '备注';
COMMENT ON TABLE "tb_video_category" IS '视频模板分类表';
CREATE TABLE IF NOT EXISTS "tb_video_template" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "title" VARCHAR(100) NOT NULL,
    "category" VARCHAR(50) NOT NULL,
    "cover" VARCHAR(255),
    "video_url" VARCHAR(255),
    "duration" INT NOT NULL DEFAULT 10,
    "hot" INT NOT NULL DEFAULT 0,
    "use_count" INT NOT NULL DEFAULT 0,
    "desc" TEXT,
    "tags" JSONB NOT NULL,
    "example_images" JSONB NOT NULL,
    "default_text" JSONB NOT NULL,
    "prompt_parts" JSONB NOT NULL,
    "recommend" BOOL NOT NULL DEFAULT False,
    "recommend_sort" INT NOT NULL DEFAULT 0,
    "sort" INT NOT NULL DEFAULT 0,
    "active" BOOL NOT NULL DEFAULT True
);
COMMENT ON COLUMN "tb_video_template"."id" IS '主键Id';
COMMENT ON COLUMN "tb_video_template"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_video_template"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_video_template"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_video_template"."title" IS '模板标题';
COMMENT ON COLUMN "tb_video_template"."category" IS '模板分类';
COMMENT ON COLUMN "tb_video_template"."cover" IS '封面图';
COMMENT ON COLUMN "tb_video_template"."video_url" IS '示例视频地址';
COMMENT ON COLUMN "tb_video_template"."duration" IS '视频时长(秒)';
COMMENT ON COLUMN "tb_video_template"."hot" IS '热度值';
COMMENT ON COLUMN "tb_video_template"."use_count" IS '使用次数';
COMMENT ON COLUMN "tb_video_template"."desc" IS '模板描述';
COMMENT ON COLUMN "tb_video_template"."tags" IS '标签';
COMMENT ON COLUMN "tb_video_template"."example_images" IS '示例图';
COMMENT ON COLUMN "tb_video_template"."default_text" IS '默认文案(大标题/副标题/口播)';
COMMENT ON COLUMN "tb_video_template"."prompt_parts" IS '画面构成(主体/镜头/场景)';
COMMENT ON COLUMN "tb_video_template"."recommend" IS '是否首页推荐';
COMMENT ON COLUMN "tb_video_template"."recommend_sort" IS '推荐位排序(倒序)';
COMMENT ON COLUMN "tb_video_template"."sort" IS '排序';
COMMENT ON COLUMN "tb_video_template"."active" IS '是否上架';
COMMENT ON TABLE "tb_video_template" IS '视频模板表';
CREATE TABLE IF NOT EXISTS "tb_generate_task" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "task_no" VARCHAR(32) NOT NULL UNIQUE,
    "type" VARCHAR(20) NOT NULL DEFAULT 'video',
    "status" VARCHAR(20) NOT NULL DEFAULT 'processing',
    "progress" INT NOT NULL DEFAULT 0,
    "materials" JSONB NOT NULL,
    "params" JSONB,
    "checkpoint" JSONB,
    "remark" TEXT,
    "result_video" VARCHAR(512),
    "result_text" TEXT,
    "fail_reason" VARCHAR(255),
    "usage" JSONB,
    "device" VARCHAR(20) NOT NULL DEFAULT 'desktop',
    "user_id" BIGINT,
    "order_no" VARCHAR(64),
    "template_id" BIGINT
);
CREATE INDEX IF NOT EXISTS "idx_tb_generate_order_n_7e656b" ON "tb_generate_task" ("order_no");
COMMENT ON COLUMN "tb_generate_task"."id" IS '主键Id';
COMMENT ON COLUMN "tb_generate_task"."deleted" IS '软删除标记,True无效False有效';
COMMENT ON COLUMN "tb_generate_task"."create_time" IS '创建时间';
COMMENT ON COLUMN "tb_generate_task"."update_time" IS '更新时间';
COMMENT ON COLUMN "tb_generate_task"."task_no" IS '任务编号';
COMMENT ON COLUMN "tb_generate_task"."type" IS '任务类型:video/image/audio/text/digital';
COMMENT ON COLUMN "tb_generate_task"."status" IS '任务状态';
COMMENT ON COLUMN "tb_generate_task"."progress" IS '进度百分比';
COMMENT ON COLUMN "tb_generate_task"."materials" IS '用户上传素材';
COMMENT ON COLUMN "tb_generate_task"."params" IS '生成参数(用于重新生成)';
COMMENT ON COLUMN "tb_generate_task"."checkpoint" IS '断点续跑检查点(stage + 各阶段中间产物)';
COMMENT ON COLUMN "tb_generate_task"."remark" IS '备注';
COMMENT ON COLUMN "tb_generate_task"."result_video" IS '生成结果媒体地址(视频/图片/音频)';
COMMENT ON COLUMN "tb_generate_task"."result_text" IS '文本类结果';
COMMENT ON COLUMN "tb_generate_task"."fail_reason" IS '失败原因';
COMMENT ON COLUMN "tb_generate_task"."usage" IS '用量与消耗(计费,worker 回调回写)';
COMMENT ON COLUMN "tb_generate_task"."device" IS '设备类型';
COMMENT ON COLUMN "tb_generate_task"."user_id" IS '关联用户Id';
COMMENT ON COLUMN "tb_generate_task"."order_no" IS '关联支付订单号(付费任务)';
COMMENT ON COLUMN "tb_generate_task"."template_id" IS '模板';
COMMENT ON TABLE "tb_generate_task" IS '视频生成任务表';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "tb_system_role_menu" (
    "role_id" BIGINT NOT NULL REFERENCES "tb_system_role" ("id") ON DELETE CASCADE,
    "menu_id" BIGINT NOT NULL REFERENCES "tb_system_menu" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "tb_system_role_menu" IS '角色菜单表';
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_tb_system_r_role_id_7dc296" ON "tb_system_role_menu" ("role_id", "menu_id");
CREATE TABLE IF NOT EXISTS "tb_system_user_role" (
    "user_id" BIGINT NOT NULL REFERENCES "tb_system_user" ("id") ON DELETE CASCADE,
    "role_id" BIGINT NOT NULL REFERENCES "tb_system_role" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "tb_system_user_role" IS '用户角色表';
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_tb_system_u_user_id_14f52a" ON "tb_system_user_role" ("user_id", "role_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
