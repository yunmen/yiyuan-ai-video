# -*- coding: utf-8 -*-
'''
@文件    :common.py
@说明    :公共方法
@时间    :2025/09/09 00:12:27
@作者    :睿
@版本    :1.0
'''
import psutil
import socket


def get_network_interfaces() -> dict:
    """获取所有网络接口及其IP"""
    interfaces = {}
    for interface, addrs in psutil.net_if_addrs().items():
        ips = []
        for addr in addrs:
            if addr.family == socket.AF_INET:  # IPv4
                ips.append(addr.address)
        if ips:
            interfaces[interface] = ips
    return interfaces

def bytes2human(n: int, format_str: str = '%(value).1f%(symbol)s') -> str:
    """
    字节数转人类可读格式
    :param n: 字节数
    :param format_str: 格式化字符串
    :return: 可读的字节字符串,如 '1.5MB'
    """
    symbols = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    prefix = {s: 1 << (i + 1) * 10 for i, s in enumerate(symbols[1:])}
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format_str % locals()
    return format_str % dict(symbol=symbols[0], value=n)

