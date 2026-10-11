# -*- coding: utf-8 -*-
'''
@文件    :main.py
@说明    :程序入口
@时间    :2025/07/18 01:01:37
@作者    :睿
@版本    :1.0
'''

import os
import sys
import uvicorn
import typer
import asyncio
from app.enums.base import EnvironmentEnum
from generate.service.gen_code_service import GenCodeService
import aerich
from loguru import logger


# Windows 控制台默认 GBK 编码,提示与日志里出现 emoji 或生僻字符(如 "💡 提示")会抛
# UnicodeEncodeError,并让整条日志直接丢失(实测启动阶段就丢过一次)。
# 此处统一把标准流重配为 UTF-8,无法编码的字符降级替换,
# 保证 typer 提示与日志不因编码问题中断(不重配则表现为"日志少一条",很难排查)。
for _stream in (sys.stdout, sys.stderr):
    try:
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        # 个别包装流不支持重配,失败不阻断启动
        pass


shell = typer.Typer()


@shell.command()
def run(env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, test, prod)")):
    typer.echo("项目启动中...")
    # 设置环境变量
    os.environ["ENVIRONMENT"] = env.value
    
    from app.settings import config
    
    # 启动uvicorn服务
    uvicorn.run(
        app='app:create_app',
        **config.UVICORN_CONFIG
    )


@shell.command()
def migrate(env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, test, prod)")):
    """
    生成新的 Aerich 迁移脚本。
    """
    os.environ["ENVIRONMENT"] = env.value

    from app.settings import config

    async def aerich_migrate():
        typer.echo("开始生成迁移变更文件...")
        command = aerich.Command(tortoise_config=config.ORM_CONFIG)
        await command.init()    # 初始化数据库配置
        try:
            await command.migrate() # 生成迁移变更文件
        except Exception as exc:
            logger.error(f"生成迁移失败,尝试初始化数据库: {exc}")
            await command.init_db(safe=True)  # 如果是第一次,则直接初始化数据库
        typer.echo("迁移变更文件生成完成...")
    asyncio.run(aerich_migrate())
    

@shell.command()
def upgrade(env: EnvironmentEnum = typer.Option(EnvironmentEnum.DEV, "--env", help="运行环境 (dev, test, prod)")):
    """
    生成新的 Aerich 迁移脚本。
    """
    os.environ["ENVIRONMENT"] = env.value

    from app.settings import config

    async def aerich_upgrade():
        typer.echo("开始执行迁移变更文件...")
        command = aerich.Command(tortoise_config=config.ORM_CONFIG)
        await command.init()    # 初始化数据库配置
        await command.upgrade(run_in_transaction=True) # 升级到最新版本
        typer.echo("迁移变更文件执行完成...")
    asyncio.run(aerich_upgrade())


@shell.command()
def generate(model_name: str):
    """
    生成Crud相关代码。
    """
    typer.echo("开始生成crud相关代码...")
    service = GenCodeService(model_name, output=True, overwrite=True)
    service.generate_code()
    typer.echo("crud相关代码生成完成...")


if __name__ == '__main__':
    # 启动服务
    # python3 main.py run --env=dev(不加默认为dev)
    # 生成迁移
    # python3 main.py migrate --env=dev(不加默认为dev)
    # 应用迁移
    # python3 main.py upgrade --env=dev(不加默认为dev)
    # 代码生成
    # python3 main.py generate 模型名称
    
    shell()
