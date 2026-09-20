# -*- coding: utf-8 -*-
"""pytest 公共配置:把 backend 目录加入 sys.path 并切换到该目录(settings 按相对路径读取 env 文件)

用法:在 backend 目录执行 `python -m pytest`(或 `pytest`)。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("ENVIRONMENT", "dev")
