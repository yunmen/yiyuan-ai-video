# -*- coding: utf-8 -*-
'''
@文件    :jwt.py
@说明    :jwt相关方法
@时间    :2024/10/25 16:10:31
@作者    :睿
@版本    :1.0
'''
import jwt
from typing import Dict, Union
from types import SimpleNamespace


class JWT:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        

    def generate_token(self, payload: Dict) -> str:
        """"
        生成加密后的token
        """
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token


    def decrypt_token(self, token: str, space: bool = False) -> Union[Dict, object]:
        """
        对token进行解密
        """
        data = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        if space:
            data = SimpleNamespace(**data)
        return data