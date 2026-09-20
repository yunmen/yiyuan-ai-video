# -*- coding: utf-8 -*-
'''
@文件    :jinja2_utils.py
@说明    :
@时间    :2025/08/28 15:30:00
@作者    :睿
@版本    :1.0
'''

from jinja2 import Environment, FileSystemLoader
from pathlib import Path


class Jinja2Utils:
    def __init__(self):
        template_path = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(searchpath=template_path),  # 模板存放路径
            trim_blocks=True,  # 去除模板中多余的空行
            lstrip_blocks=True
        )

    def generate(self, template_name: str, **kwargs):
        # 加载模板文件
        template = self.env.get_template(template_name)
        # 渲染模板（传入动态数据）
        content = template.render(**kwargs)
        return content
