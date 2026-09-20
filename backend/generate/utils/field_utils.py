# -*- coding: utf-8 -*-
'''
@文件    :field_utils.py
@说明    :
@时间    :2025/08/28 18:27:29
@作者    :睿
@版本    :1.0
'''
from typing import Union, List, Dict, Any
from tortoise.fields import Field


def get_field_type(field: Field):
    """
    BooleanField
    IntField 
    BigIntField
    DateField
    DatetimeField
    DecimalField
    FloatField
    JSONField
    SmallIntField
    TextField
    # 关系字段
    tortoise.fields.relational.ForeignKeyField
    tortoise.fields.relational.ManyToManyField
    tortoise.fields.relational.OneToOneField
    """
    if field.__class__.__name__ in ("CharField", "TextField"):
        type_string = "str"
    elif field.__class__.__name__ == "BooleanField":
        type_string = "bool"
    elif field.__class__.__name__ == "FloatField":
        type_string = "float"
    elif field.__class__.__name__ == "JSONField":
        type_string = "Union[List, Dict]"
    elif field.__class__.__name__ in ("IntField","SmallIntField","BigIntField"):
        type_string = "int"
    elif field.__class__.__name__ == "DateField":
        type_string = "date"
    elif field.__class__.__name__ == "DatetimeField":
        type_string = "datetime"
    elif field.__class__.__name__ == "DecimalField":
        type_string = "Decimal"
    else:
        type_string = "Any"
    if field.null:
        type_string = f"Union[{type_string}, None]"
    return type_string
    

def get_field_default(field: Field):
    if field.null:
        default = "None"
    else:
        default = "..."
    return default
