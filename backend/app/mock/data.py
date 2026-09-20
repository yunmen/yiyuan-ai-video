# -*- coding: utf-8 -*-
'''
@文件    :data.py
@说明    :系统初始化mock数据(仅在对应表为空时写入,用于全新环境自举)
          - menus : 管理后台左侧菜单 / 权限点
          - roles : 角色(超级管理员默认授予全部菜单)
          - users : 超管账号(首次部署默认 admin / admin123456,务必上线前修改)
          - depts : 部门(留空,由 init_dept_data 处理)
@时间    :2026/09/20 21:00:00
@作者    :一源AI
@版本    :1.0
'''

# 菜单类型: menu=菜单目录/页面, button=接口权限点
menus = [
    # ===== 业务管理 =====
    {"id": 1, "parent_id": 0, "type": "menu", "name": "business", "title": "业务管理",
     "icon": "el-icon-goods", "path": "/business", "component": "", "order": 100},
    {"id": 11, "parent_id": 1, "type": "menu", "name": "videoTemplate", "title": "视频模板",
     "icon": "el-icon-video-camera", "path": "/video/template", "component": "video/template/index", "order": 101,
     "apiList": ["video:template:list", "video:template:save", "video:template:delete"]},
    {"id": 12, "parent_id": 1, "type": "menu", "name": "videoCategory", "title": "模板分类",
     "icon": "el-icon-collection", "path": "/video/category", "component": "video/category/index", "order": 102,
     "apiList": ["video:category:list", "video:category:save", "video:category:delete"]},
    {"id": 13, "parent_id": 1, "type": "menu", "name": "videoTask", "title": "生成任务",
     "icon": "el-icon-loading", "path": "/video/task", "component": "video/task/index", "order": 103,
     "apiList": ["video:task:list", "video:task:detail"]},
    {"id": 14, "parent_id": 1, "type": "menu", "name": "digital", "title": "数字人",
     "icon": "el-icon-user", "path": "/digital", "component": "digital/index", "order": 104,
     "apiList": ["video:digital:list", "video:digital:save", "video:digital:delete"]},
    {"id": 15, "parent_id": 1, "type": "menu", "name": "paymentPackage", "title": "充值套餐",
     "icon": "el-icon-goods", "path": "/payment/package", "component": "payment/package/index", "order": 105,
     "apiList": ["payment:package:list", "payment:package:save", "payment:package:delete"]},
    {"id": 16, "parent_id": 1, "type": "menu", "name": "paymentOrder", "title": "支付订单",
     "icon": "el-icon-tickets", "path": "/payment/order", "component": "payment/order/index", "order": 106,
     "apiList": ["payment:order:list", "payment:order:detail", "payment:order:refund"]},
    {"id": 17, "parent_id": 1, "type": "menu", "name": "creditUser", "title": "用户额度",
     "icon": "el-icon-coin", "path": "/credit/user", "component": "credit/user/index", "order": 107,
     "apiList": ["credit:user:list", "credit:user:grant"]},
    {"id": 18, "parent_id": 1, "type": "menu", "name": "systemConfig", "title": "业务配置",
     "icon": "el-icon-set-up", "path": "/setting/system", "component": "setting/system/index", "order": 108,
     "apiList": ["system:config:list", "system:config:save"]},

    # ===== 系统管理 =====
    {"id": 2, "parent_id": 0, "type": "menu", "name": "system", "title": "系统管理",
     "icon": "el-icon-setting", "path": "/system", "component": "", "order": 200},
    {"id": 21, "parent_id": 2, "type": "menu", "name": "menu", "title": "菜单管理",
     "icon": "el-icon-menu", "path": "/setting/menu", "component": "setting/menu/index", "order": 201,
     "apiList": ["system:menu:list", "system:menu:create", "system:menu:update", "system:menu:delete"]},
    {"id": 22, "parent_id": 2, "type": "menu", "name": "role", "title": "角色管理",
     "icon": "el-icon-unlock", "path": "/setting/role", "component": "setting/role/index", "order": 202,
     "apiList": ["system:role:list", "system:role:create", "system:role:update", "system:role:delete"]},
    {"id": 23, "parent_id": 2, "type": "menu", "name": "user", "title": "用户管理",
     "icon": "el-icon-user", "path": "/setting/user", "component": "setting/user/index", "order": 203,
     "apiList": ["system:user:list", "system:user:create", "system:user:update", "system:user:delete"]},
    {"id": 24, "parent_id": 2, "type": "menu", "name": "dept", "title": "部门管理",
     "icon": "el-icon-office-building", "path": "/setting/dept", "component": "setting/dept/index", "order": 204,
     "apiList": ["system:dept:list", "system:dept:create", "system:dept:update", "system:dept:delete"]},
    {"id": 25, "parent_id": 2, "type": "menu", "name": "dic", "title": "字典管理",
     "icon": "el-icon-notebook", "path": "/setting/dic", "component": "setting/dic/index", "order": 205,
     "apiList": ["system:dic:list", "system:dic:create", "system:dic:update", "system:dic:delete"]},
    {"id": 26, "parent_id": 2, "type": "menu", "name": "log", "title": "日志管理",
     "icon": "el-icon-document", "path": "/setting/log", "component": "setting/log/index", "order": 206,
     "apiList": ["system:log:list", "system:log:delete"]},
    {"id": 27, "parent_id": 2, "type": "menu", "name": "task", "title": "任务管理",
     "icon": "el-icon-alarm-clock", "path": "/setting/task", "component": "setting/task/index", "order": 207,
     "apiList": ["system:task:list", "system:task:create", "system:task:update"]},
    {"id": 28, "parent_id": 2, "type": "menu", "name": "monitor", "title": "系统监控",
     "icon": "el-icon-monitor", "path": "/system/monitor", "component": "system/monitor/index", "order": 208},
    {"id": 29, "parent_id": 2, "type": "menu", "name": "cache", "title": "缓存管理",
     "icon": "el-icon-cpu", "path": "/system/cache", "component": "system/cache/index", "order": 209},
]

roles = [
    {"id": 1, "name": "超级管理员", "alias": "SA", "desc": "系统超级管理员,拥有全部菜单与接口权限", "active": True},
    {"id": 2, "name": "运营", "alias": "OP", "desc": "运营人员,可管理业务模块数据", "active": True},
]

# 首次部署默认超管账号;上线前务必在管理后台修改密码
users = [
    {
        "id": 1,
        "account": "admin",
        "realname": "超级管理员",
        "nickname": "超级管理员",
        "phone": "13800000000",
        "avatar": "",
        "email": "",
        "password": "admin123456",
        "superuser": True,
        "active": True,
        "roles": [1],
    }
]

depts = []
