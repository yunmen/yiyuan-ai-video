# -*- coding: utf-8 -*-
'''
@文件    :database.py
@说明    :数据库初始化操作
@时间    :2025/08/26 15:47:14
@作者    :睿
@版本    :1.0
'''
from app.core.plugin import database
from app.services.system.user import service as user_service
from app.services.system.menu import service as menu_service
from app.services.system.dept import service as dept_service
from app.services.system.role import service as role_service
from app.core.logger import logger


async def init_database_data():
    """初始化数据库数据"""
    await database.startup()
    await menu_service.init_menu_data()
    await dept_service.init_dept_data()
    await role_service.init_role_data()
    await user_service.init_user_data()
    from app.services.system_config import service as config_service
    await config_service.init_config_data()  # 播种业务配置(模型/画幅/定价)
    from app.services.payment_package import service as package_service
    await package_service.init_package_data()  # 播种默认充值套餐
    from app.services.video_category import service as category_service
    await category_service.init_category_data()  # 播种默认模板分类
    logger.info("初始化database缓存数据")


async def close_database_data():
    """关闭数据库"""
    await database.shutdown()
    logger.info("关闭database缓存数据")
