# -*- coding: utf-8 -*-
'''
@文件    :password.py
@说明    :密码工具
@时间    :2024/10/26 17:02:08
@作者    :睿
@版本    :1.0
'''
from typing import Optional
from passlib import pwd
from passlib.context import CryptContext


class Password:
    def __init__(self, hash: str = "argon2"):
        """初始化密码哈希算法 argon2/bcrypt"""
        self.pwd_context = CryptContext(schemes=[hash], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """获取密码哈希值"""
        return self.pwd_context.hash(password)

    @staticmethod
    def generate_password(length: int = 12) -> str:
        """生成随机密码"""
        return pwd.genword(length=length)

    def check_password_strength(cls, password: str) -> Optional[str]:
        """检查密码强度"""
        if len(password) < 6:
            return "密码长度至少6位"
        if not any(c.isupper() for c in password):
            return "密码需要包含大写字母"
        if not any(c.islower() for c in password):
            return "密码需要包含小写字母" 
        if not any(c.isdigit() for c in password):
            return "密码需要包含数字"
        return None