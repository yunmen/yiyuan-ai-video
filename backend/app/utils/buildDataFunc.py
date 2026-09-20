# -*- coding: utf-8 -*-
'''
@文件    :buildDataFunc.py
@说明    :构建数据
@时间    :2025/02/15 18:40:56
@作者    :睿
@版本    :1.0
'''
from typing import List, Dict


def build_tree_data(data, parent_id=0) -> List[Dict]:
    """
    @功能    :处理数据库中的树结构数据
    @参数    :
    @返回值  :
    @时间    :2023/12/21 21:32:21
    @作者    :睿
    @版本    :1.0
    """
    tree = []
    for item in data:
        if item['parent_id'] == parent_id:
            children = build_tree_data(data, item['id'])
            if children:
                item['children'] = children
            tree.append(item)
    return tree




def build_mask_text(text, show_first=3, show_last=4):
    """
    通用文本掩码处理
    
    Args:
        text: 要处理的文本
        show_first: 开头保留位数
        show_last: 结尾保留位数
    
    Returns:
        掩码处理后的文本
    """
    if not text:
        return text
    
    text = str(text)
    
    # 如果文本长度小于等于要显示的总长度，直接返回
    if len(text) <= show_first + show_last:
        return text
    
    # 构建掩码结果
    first_part = text[:show_first]
    last_part = text[-show_last:]
    middle_stars = '*' * (len(text) - show_first - show_last)
    
    return first_part + middle_stars + last_part
