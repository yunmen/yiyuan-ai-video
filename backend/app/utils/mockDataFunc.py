# -*- coding: utf-8 -*-
'''
@文件    :common.py
@说明    :公共方法
@时间    :2025/09/09 00:12:27
@作者    :睿
@版本    :1.0
'''
import os
import random
import string
import datetime
import time




def generate_random_code(length=6):
    """生成code码"""
    random_str = ''.join(random.choices(string.ascii_uppercase, k=length))
    return random_str


def generate_order_no(prefix="PAY"):
    """生成订单号"""
    now = datetime.datetime.now()
    date_part = now.strftime("%y%m%d")  # 日期：231015（23年10月15日）
    time_part = now.strftime("%H%M%S")  # 时间：142305（14点23分05秒）
    timestamp = str(int(time.time() * 10))
    return f"{prefix}-{date_part}-{time_part}-{timestamp}"


def generate_random_string(length=10):
    """生成随机字符串"""
    characters = string.ascii_letters + string.digits  # 大小写字母 + 数字
    return ''.join(random.sample(characters, k=length))


def generate_timestamp():
    """生成时间戳"""
    return str(int(time.time()))


def generate_timestamp_format(fm="%Y-%m-%d %H:%M:%S"):
    """生成日期"""
    # 毫米时间戳获取
    now = datetime.datetime.now()
    # 格式化当前时间
    timestamp = now.strftime(fm)
    return timestamp
