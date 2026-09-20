# -*- coding: utf-8 -*-
'''
@文件    :logger.py
@说明    :
@时间    :2025/09/05 23:36:06
@作者    :睿
@版本    :1.0
'''

import logging
from typing import Optional, Callable
from loguru import logger


class InterceptHandler(logging.Handler):
    """日志拦截器"""
    def emit(self, record):
        # 将标准 logging 的日志转发到 Loguru
        log = logger.opt(depth=6, exception=record.exc_info)
        log.log(record.levelno, record.getMessage())


class UniLogManager:
    """统一日志管理器"""
    def __init__(self, 
        sink: str,
        level: str = "DEBUG",
        format: Optional[str] = None,
        intercept: bool = True,
        **kwargs
    ):
        self.sink = sink
        self.level = level
        self.format = format or "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
        self.intercept = intercept
        self.kwargs = kwargs
        if self.intercept:
            for name in logging.root.manager.loggerDict:
                log = logging.getLogger(name)
                log.setLevel(logging.DEBUG)
                log.propagate = True
                log.handlers = []
            logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    def add(self, patcher: Optional[Callable] = None):
        logger.remove()
        handler = dict(sink=self.sink, level=self.level, format=self.format, **self.kwargs)
        self.handler_ids = logger.configure(handlers=[handler], patcher=patcher)
        
    def remove(self):
        for handler_id in self.handler_ids:
            logger.remove(handler_id)

    def debug(self, *args, **kwargs):
        logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        logger.critical(*args, **kwargs)
    
    def exception(self, *args, **kwargs):
        logger.exception(*args, **kwargs)
    
