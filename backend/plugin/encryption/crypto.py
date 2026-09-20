# -*- coding: utf-8 -*-
'''
@文件    :crypto.py
@说明    :
@时间    :2026/01/24 11:34:23
@作者    :睿
@版本    :1.0
'''
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64


class AES256GCM:
    """AES-256-GCM 对称加密"""
    def __init__(self, encryption_password: str):
        if len(encryption_password) < 12:
            raise ValueError("加密密码至少需要12个字符")
        self.encryption_password = encryption_password.encode()
        
    def _derive_key(self, salt: bytes) -> bytes:
        """从密码派生密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.encryption_password))
    
    def encrypt_private_key(self, private_key: bytes) -> tuple:
        """加密私钥"""
        salt = os.urandom(16)
        key = self._derive_key(salt)
        fernet = Fernet(key)
        
        encrypted_key = fernet.encrypt(private_key)
        return salt, encrypted_key
    
    def decrypt_private_key(self, salt: bytes, encrypted_key: bytes) -> bytes:
        """解密私钥"""
        key = self._derive_key(salt)
        fernet = Fernet(key)
        
        return fernet.decrypt(encrypted_key)
    


if __name__ == "__main__":
    # 使用示例
    key_store = AES256GCM("your_secure_password")

    secret = "待加密的私钥"

    # 加密存储
    salt, encrypted_secret = key_store.encrypt_private_key(bytes(secret))

    print("Salt:", base64.b64encode(salt).decode())
    print("Encrypted:", base64.b64encode(encrypted_secret).decode())

