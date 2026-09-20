# -*- coding: utf-8 -*-
'''
@文件    :logger.py
@说明    :日志门面(基于 loguru 的轻量封装,统一各层日志出口)
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
'''
import sys
from loguru import logger as _logger


class UniLogManager:
    def __init__(self, level: str = "DEBUG", sink=sys.stdout):
        _logger.remove()
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
