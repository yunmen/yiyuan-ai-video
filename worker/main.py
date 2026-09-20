# -*- coding: utf-8 -*-
'''
@文件    :main.py
@说明    :worker 程序入口(Typer CLI)— 启动 ARQ worker / 环境自检 / 下发测试任务
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
import os
import typer
import asyncio
from arq import run_worker, create_pool
from arq.connections import RedisSettings


shell = typer.Typer()


@shell.command()
def run(env: str = typer.Option("dev", "--env", help="运行环境 (dev, test, prod)")):
    """启动 ARQ worker"""
    os.environ["ENVIRONMENT"] = env
    from app.core.worker import get_worker_settings
    from app.settings import config

    typer.echo(
        f"ARQ Worker 启动中... (env={env}, queue={config.ARQ_QUEUE_NAME}, "
        f"concurrency={config.ARQ_CONCURRENCY}, 任务数=4)"
    )
    try:
        run_worker(get_worker_settings())
    except KeyboardInterrupt:
        typer.echo("收到中断信号,worker 退出")


@shell.command()
def check(env: str = typer.Option("dev", "--env", help="运行环境")):
    """环境自检 — 校验配置与生成工具可正常导入"""
    os.environ["ENVIRONMENT"] = env
    from app.settings import config
    from app.core.plugin import logger
    from app.tools.video_tool import VideoGenTool
    from app.tools.text_tool import TextGenTool
    from app.tools.image_tool import ImageGenTool
    from app.tools.audio_tool import AudioGenTool

    logger.info("=== worker 环境检查 ===")
    logger.info(f"环境: {config.ENVIRONMENT}")
    logger.info(f"Redis: {config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB_NAME}")
    logger.info(f"队列: {config.ARQ_QUEUE_NAME}  并发: {config.ARQ_CONCURRENCY}  超时: {config.ARQ_JOB_TIMEOUT}s")
    logger.info(f"回调: {config.NOTIFY_URL}")
    logger.info(f"大模型: chat={config.CHAT_MODEL} image={config.IMAGE_MODEL} video={config.VIDEO_MODEL} audio={config.AUDIO_MODEL}")
    logger.info(
        f"已加载生成工具: "
        f"{[c.__name__ for c in (VideoGenTool, TextGenTool, ImageGenTool, AudioGenTool)]}"
    )
    logger.info("环境检查完成")


@shell.command()
def enqueue(
    env: str = typer.Option("dev", "--env", help="运行环境"),
    task_id: int = typer.Option(1, "--task-id", help="测试任务Id"),
    notify_url: str = typer.Option(None, "--notify-url", help="覆盖回调地址"),
    job: str = typer.Option("process_video", "--job", help="任务方法名"),
):
    """下发一个测试任务到 ARQ 队列(开发联调用)"""
    os.environ["ENVIRONMENT"] = env
    from app.settings import config

    async def _enq():
        pool = await create_pool(RedisSettings(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD or None,
            username=config.REDIS_USER or None,
            database=config.REDIS_DB_NAME,
            ssl=False,
        ), default_queue_name=config.ARQ_QUEUE_NAME)
        url = notify_url or config.NOTIFY_URL
        params = {
            "template_id": 1,
            "prompt": "一段展示美食门店的探店短视频,节奏轻快,突出菜品与环境",
            "materials": [],
            "duration": 5,
        }
        await pool.enqueue_job(job, task_id, url, params, _queue_name=config.ARQ_QUEUE_NAME)
        await pool.close()
        typer.echo(f"已下发 {job} task_id={task_id} -> {url}")

    asyncio.run(_enq())


if __name__ == "__main__":
    shell()
