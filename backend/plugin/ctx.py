# -*- coding: utf-8 -*-
'''
@文件    :ctx.py
@说明    :上下文管理器
@时间    :2025/07/12 00:56:35
@作者    :睿
@版本    :1.0
'''
from typing import List, Dict, Any, Union
from contextvars import ContextVar


class ContextVarManager:
    """上下文管理器"""

    def __init__(self, var_list: List[str] = []):
        """
        初始化一个空的字典来存储上下文变量
        """
        self.ctx: Dict = {var: ContextVar(var, default="") for var in var_list}

    def show(self):
        """
        展示上下文变量

        :return result: 上下文变量
        """
        return self.ctx

    def push(self, name: str, default: Any = ""):
        """
        新增上下文变量

        :param name: 变量名称
        :param default: 变量默认值
        """
        self.ctx[name] = ContextVar(name, default=default)
        return self.ctx[name]

    def pull(self, name: str) -> ContextVar:
        """
        获取上下文变量

        :param name: 变量名称
        :return result: 上下文变量
        """
        return self.ctx.get(name)

    def delete(self, name: str):
        """
        删除上下文变量

        :param name: 变量名称
        """
        self.ctx.pop(name, None) 


    def set(self, name: str, value: Any):
        """
        设置上下文变量的值

        :param value: 变量值
        """
        ctx = self.ctx.get(name)
        if ctx:
            ctx.set(value)

    def get(self, name: str, key: str = None) -> Union[Any, ContextVar]:
        """
        获取上下文变量的值

        :param name: 上下文名称
        :param key: 变量名
        :return result: 变量值, 如果上下文不存在则返回None
        """
        ctx = self.ctx.get(name)
        if not ctx:
            return None
        if key:
            var = ctx.get()
            if isinstance(var, Dict):
                return var.get(key, None)
            elif isinstance(var, object):
                return getattr(var, key, None)
            else:
                return var
        else:
            return ctx.get()



if __name__ == "__main__":


    ctx = ContextVarManager(["g","stack"])


    ctxs = ctx.show()
    print(ctxs)
    ctx.set("g",111)
    g = ctx.get("g")
    print(g)