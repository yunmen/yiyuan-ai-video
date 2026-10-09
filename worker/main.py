# -*- coding: utf-8 -*-
'''
@文件    :main.py
@说明    :worker 程序入口(Typer CLI)— 启动 ARQ worker / 环境自检 / 下发测试任务
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
import os
import sys
import typer
import asyncio
from arq import run_worker, create_pool
from arq.connections import RedisSettings


# 无控制台环境(Windows 无头启动 / pythonw)下 sys.stdout/stderr 为 None,
# 日志组件与 print/typer.echo 会直接崩溃,导致 worker 无法启动。
# 此处将其重定向到日志文件,保证 worker 在无头环境下也能正常拉起并留痕。
if sys.stdout is None or sys.stderr is None:
    _log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _log_file = os.path.join(_log_dir, "worker_stdout.log")
    _fh = open(_log_file, "a", buffering=1, encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _fh
    if sys.stderr is None:
        sys.stderr = _fh

# Windows 控制台默认 GBK 编码,日志里出现 emoji 或生僻字符(如 "💡 提示")会抛
# UnicodeEncodeError,并让**整条日志直接丢失**(实测启动阶段就丢过一次)。
# 此处统一把标准流重配为 UTF-8,并对无法编码的字符降级替换,保证日志不因编码问题中断。
# 无头环境的分支上面已把标准流替换为 UTF-8 文件流,reconfigure 同样适用。
for _stream in (sys.stdout, sys.stderr):
    try:
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        # 个别包装流不支持重配,失败不阻断启动
        pass


shell = typer.Typer()


@shell.command()
def run(env: str = typer.Option("dev", "--env", help="运行环境 (dev, test, prod)")):
    """启动 ARQ worker"""
    os.environ["ENVIRONMENT"] = env
    from app.core.worker import get_worker_settings
    from app.settings import config

    typer.echo(
        f"ARQ Worker 启动中... (env={env}, queue={config.ARQ_QUEUE_NAME}, "
        f"concurrency={config.ARQ_CONCURRENCY}, 任务数=5)"
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
    from app.tools.digital_tool import DigitalHumanTool

    logger.info("=== worker 环境检查 ===")
    logger.info(f"环境: {config.ENVIRONMENT}")
    logger.info(f"Redis: {config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB_NAME}")
    logger.info(f"队列: {config.ARQ_QUEUE_NAME}  并发: {config.ARQ_CONCURRENCY}  超时: {config.ARQ_JOB_TIMEOUT}s")
    logger.info(f"回调: {config.NOTIFY_URL}")
    logger.info(f"大模型: chat={config.CHAT_MODEL} image={config.IMAGE_MODEL} video={config.VIDEO_MODEL} audio={config.AUDIO_MODEL}")
    logger.info(f"数字人口播模型: {config.DIGITAL_MODEL or '(未配置,数字人任务将失败)'}")
    logger.info(
        f"已加载生成工具: "
        f"{[c.__name__ for c in (VideoGenTool, TextGenTool, ImageGenTool, AudioGenTool, DigitalHumanTool)]}"
    )
    # 业务配置热更新目标:容器内必须指向 backend 服务名,否则管理端改模型/网关不会生效
    logger.info(
        f"配置热更新: {config.BACKEND_PUBLIC_URL} (间隔 {config.CONFIG_REFRESH_INTERVAL}s)"
    )
    if "127.0.0.1" in config.BACKEND_PUBLIC_URL or "localhost" in config.BACKEND_PUBLIC_URL:
        logger.warning(
            "BACKEND_PUBLIC_URL 指向本机:若 worker 运行在容器中,配置热更新会失败,"
            "管理端修改的模型/网关不会生效。请改为 backend 服务名(如 http://backend:8801)。"
        )
    logger.info(f"OSS 转存: {'已启用' if config.OSS_ENABLED else '未启用(生成结果保留模型原始直链,可能过期)'}")
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
