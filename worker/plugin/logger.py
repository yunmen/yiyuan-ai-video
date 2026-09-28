# -*- coding: utf-8 -*-
'''
@文件    :logger.py
@说明    :日志门面(基于 loguru 的轻量封装,统一各层日志出口)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
import os
import sys
from loguru import logger as _logger


class UniLogManager:
    def __init__(self, level: str = "DEBUG", sink=sys.stdout):
        _logger.remove()
        # 统一落盘:无论哪个 worker 实例、是否有控制台,诊断日志都汇总到同一个文件
        # (worker/logs/worker.log),避免多实例运行时日志分散、难以排查
        # (此前只有经 main.py 无头兜底重定向的那一个实例写 worker_stdout.log)。
        _log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
        )
        os.makedirs(_log_dir, exist_ok=True)
        _logger.add(
            os.path.join(_log_dir, "worker.log"),
            level=level,
            rotation="50 MB",
            retention=5,
            enqueue=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
                "[<level>{level: <8}</level>] "
                "<cyan>{name}</cyan> | <level>{message}</level>"
            ),
        )
        # 控制台出口(无头环境下 sys.stdout 可能为 None,由 main.py 兜底重定向;此处再次防御)
        if sink is not None:
            _logger.add(
                sink,
                level=level,
                format=(
                    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
                    "[<level>{level: <8}</level>] "
                    "<cyan>{name}</cyan> | <level>{message}</level>"
                ),
            )

    def debug(self, msg): _logger.debug(msg)
    def info(self, msg): _logger.info(msg)
    def warning(self, msg): _logger.warning(msg)
    def error(self, msg): _logger.error(msg)
    def exception(self, msg): _logger.exception(msg)


__all__ = ["UniLogManager"]
