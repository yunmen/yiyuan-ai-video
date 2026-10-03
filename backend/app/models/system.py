# -*- coding: utf-8 -*-
'''
@文件    :system.py
@说明    :系统管理
@时间    :2024/11/05 18:24:57
@作者    :睿
@版本    :1.0
'''

from tortoise import fields
from .base import BaseModel, TimestampMixin, DefaultFilterManager
from app.enums.base import LoginTypeEnum


class SystemMenuModel(BaseModel, TimestampMixin):
    title = fields.CharField(max_length=20, null=False, description="显示名称")
    parent_id = fields.IntField(default=0, max_length=10, description="父菜单ID")
    type = fields.CharField(max_length=100, null=False, description="菜单类型")
    name = fields.CharField(max_length=100, null=False, description="别名")
    icon = fields.CharField(max_length=100, null=False, description="菜单图标")
    path = fields.CharField(max_length=100, null=False, description="菜单路径")
    redirect = fields.CharField(max_length=100, null=True, description="重定向")
    active = fields.CharField(max_length=100, null=True, description="菜单高亮")
    component = fields.CharField(max_length=100, null=False, description="组件")
    color = fields.CharField(max_length=100, null=True, description="颜色")
    hidden = fields.BooleanField(default=False, null=True, description="隐藏菜单")
    hiddenBreadcrumb = fields.BooleanField(default=False, null=True, description="隐藏面包屑")
    fullpage = fields.BooleanField(default=False, null=True, description="整页路由")
    tag = fields.CharField(max_length=100, null=True, description="标签")
    order = fields.IntField(default=0, description="排序")
    apiList = fields.JSONField(default=[], null=True, description="接口权限")
    
    class Meta:
        table = "tb_system_menu"
        table_description = "系统菜单表"
        manager = DefaultFilterManager()


class SystemDeptModel(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, null=False, description="部门名称")
    path = fields.CharField(max_length=20, null=False, description="路径")
    desc = fields.CharField(max_length=500, null=True, description="备注")
    order = fields.IntField(default=0, null=False, description="排序")
    parent_id = fields.IntField(default=0, max_length=10, description="父部门ID")
    active = fields.BooleanField(default=False, description="是否激活")
    
    class Meta:
        table = "tb_system_dept"
        table_description = "系统部门表"
        manager = DefaultFilterManager()


class SystemRoleModel(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, null=False, description="角色名称")
    alias = fields.CharField(max_length=20, null=True, description="别名")
    desc = fields.CharField(max_length=500, null=True, description="角色描述")
    active = fields.BooleanField(default=False, null=False, description="是否激活")
    menus = fields.ManyToManyField("models.SystemMenuModel", through="tb_system_role_menu", forward_key="menu_id", backward_key="role_id",  description="角色菜单表")
    
    class Meta:
        table = "tb_system_role"
        table_description = "系统角色表"
        manager = DefaultFilterManager()


class SystemUserModel(BaseModel, TimestampMixin):
    account = fields.CharField(max_length=20, null=False, description="账号")
    realname = fields.CharField(max_length=30, null=False, description="姓名")
    nickname = fields.CharField(max_length=30, null=False, description="昵称")
    avatar = fields.CharField(max_length=255, null=True, description="头像")
    email = fields.CharField(max_length=255, null=True, description="邮箱")
    phone = fields.CharField(max_length=20, null=False, description="电话")
    password = fields.CharField(max_length=128, null=False, description="密码")
    superuser = fields.BooleanField(default=False, description="是否超级管理员")
    permission = fields.SmallIntField(null=True, description="数据权限")
    active = fields.BooleanField(default=False, description="是否激活")
    last_login_type = fields.IntEnumField(LoginTypeEnum, null=True, description="最后登录类型")
    last_login_time = fields.DatetimeField(null=True, description="最后登录时间")
    last_login_ip = fields.CharField(max_length=128, null=True, description="最后登录Ip")
    dept = fields.ForeignKeyField("models.SystemDeptModel", related_name="users", null=True, db_constraint=False, description="部门")
    roles = fields.ManyToManyField("models.SystemRoleModel", related_name="users", through="tb_system_user_role", forward_key="role_id", backward_key="user_id", description="用户角色表")
    
    class Meta:
        table = "tb_system_user"
        table_description = "系统用户表"
        manager = DefaultFilterManager()


class SystemLogModel(BaseModel, TimestampMixin):
    request_id = fields.CharField(max_length=50, null=False, description="请求Id")
    summary = fields.CharField(max_length=255, null=False, description="接口说明")
    url = fields.CharField(max_length=255, null=False, description="请求地址")
    method = fields.CharField(max_length=20, null=True, description="请求类型")
    client_ip = fields.CharField(max_length=64, null=True, description="客户端IP")
    headers = fields.TextField(null=True, description="请求头")
    payload = fields.JSONField(null=True, description="请求参数")
    result = fields.JSONField( null=True, description="响应结果")
    status_code = fields.CharField(max_length=20, null=True, description="响应码")
    process_time = fields.CharField(max_length=20, null=True, description="响应时间")
    error_log = fields.TextField(null=True, description="错误日志")
    client_type = fields.CharField(max_length=50, null=True, description="客户端")
    operator_account = fields.CharField(max_length=50, null=True, description="操作人账号")
    operator_nickname = fields.CharField(max_length=50, null=True, description="操作人昵称")
    class Meta:
        table = "tb_system_log"
        # 操作日志表与业务表同库(本仓库单库约定, schema_sync 也只针对当前库),
        # 此前误配 schema="logs" 指向不存在的独立库,导致 list 查询 500。
        table_description = "系统日志表"
        manager = DefaultFilterManager()


class SystemTaskModel(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=50, null=False, description="任务名称")
    func = fields.CharField(max_length=50, null=False, description="执行方法")
    args = fields.JSONField(null=True, description="位置参数")
    kwargs = fields.JSONField(null=True, description="关键字参数")
    trigger = fields.CharField(max_length=50, null=False, description="触发器")
    executor = fields.CharField(max_length=50, null=False, description="执行器")
    jobstore = fields.CharField(max_length=50, null=False, description="储存器")
    start_date = fields.DatetimeField(null=True, description="开始时间")
    end_date = fields.DatetimeField(null=True, description="结束时间")
    trigger_args = fields.CharField(max_length=20, null=False, description="trigger表达式")
    active = fields.BooleanField(default=False, description="是否激活")
    desc = fields.CharField(max_length=255, null=True, description="任务描述")
    @property
    def format_args(self) -> str:
        return ",".join(self.args)

    @property
    def format_kwargs(self) -> str:
        return "&".join([f"{k}={v}" for k, v in self.kwargs.items()])

    class Meta:
        table = "tb_system_task"
        table_description = "定时任务表"
        manager = DefaultFilterManager()


class SystemTasklogModel(BaseModel, TimestampMixin):
    task = fields.ForeignKeyField("models.SystemTaskModel", related_name="logs", db_constraint=False, description="任务")
    name = fields.CharField(max_length=255, null=False, description="任务名称")
    status = fields.BooleanField(null=False, description="状态, True为成功,False为失败")
    desc = fields.TextField(max_length=255, null=False, description="任务描述")
    next_run_time = fields.DatetimeField(null=True, description="下次执行时间")

    class Meta:
        table = "tb_system_tasklog"
        table_description = "任务日志表"
        manager = DefaultFilterManager()


class SystemConfigModel(BaseModel, TimestampMixin):
    """系统业务配置表(key-value,供 worker/前端动态读取,替代硬编码 env)"""
    key = fields.CharField(max_length=64, unique=True, description="配置键,如 gen.video_model_i2v")
    value = fields.TextField(null=True, description="配置值")
    group = fields.CharField(max_length=32, default="gen", description="配置分组")
    remark = fields.CharField(max_length=255, default="", description="配置说明")
    is_public = fields.BooleanField(default=True, description="是否允许未登录读取(敏感配置置 False)")

    class Meta:
        table = "tb_system_config"
        table_description = "系统业务配置表"