import time
import string
import random
import base64
import os
import hashlib
import xmltodict
from datetime import datetime
from Crypto.Cipher import AES
from typing import Dict





def generate_signature(Token: str, timestamp: str, nonce: str, encrypt: str = None):
    """
    生成签名   
    :params Token: 公众号配置的Token
    :params timestamp: 时间戳
    :params nonce: 随机字符串 
    :params encrypt: 加密消息
    :return signature: 签名
    """
    sortlist = [Token, timestamp, nonce]
    if encrypt:
        sortlist.append(encrypt)
    sortlist.sort()
    sha1 = hashlib.sha1()
    sha1.update("".join(sortlist).encode("utf8"))
    signature = sha1.hexdigest()
    return signature



def generate_random_string(length=10):
    """生成随机字符串"""
    characters = string.ascii_letters + string.digits  # 大小写字母 + 数字
    return ''.join(random.sample(characters, k=length))


def generate_timestamp():
    """生成时间戳"""
    return str(int(time.time()))



def xml_to_dict(xml):
    """
    @功能    :xml转换成dict  
    @参数    :msg字典  
    @返回值  :xml对象  
    @时间    :2022/04/28 16:17:19  
    @作者    :睿  
    @版本    :1.0  
    """
    data = xmltodict.parse(xml, dict_constructor=dict)
    return data.get("xml")


def dict_to_xml(kwargs: Dict):
    """
    @功能    :dict格式转xml格式  
    @参数    :msg字典  
    @返回值  :xml对象  
    @时间    :2022/04/28 16:17:19  
    @作者    :睿  
    @版本    :1.0  
    """
    data = {
        "xml":{}
    }
    data["xml"] = kwargs
    xmlobj = xmltodict.unparse(data, pretty=True)
    return xmlobj


def build_message(msgtype="text",  **kwargs):
    """
    @功能    :构建原始消息体
    @msgtype :消息类型，可选值："text"（文本）、"image"（图片）、"voice"（文件）
    @kwargs  :其他参数
    @返回值  :  
    @时间    :2025/04/28 23:53:48  
    @作者    :睿  
    @版本    :1.0  
    """
    timestamp = generate_timestamp()
    data = {
        "ToUserName": kwargs.get("FromUserName"),
        "FromUserName": kwargs.get("ToUserName"),
        "CreateTime": timestamp,
        "MsgType": msgtype
    }
    if msgtype == "text":
        data.update(Content=kwargs.get("Content"))
    if msgtype == "image":
        data.update(MediaId=kwargs.get("MediaId"))
    if msgtype == "voice":
        data.update(MediaId=kwargs.get("MediaId"))
    if msgtype == "video":
        data.update(
            MediaId=kwargs.get("MediaId"),
            Title=kwargs.get("Title"),
            Description=kwargs.get("Description")
        )
    if msgtype == "music":
        data.update(
            Title=kwargs.get("Title"),
            Description=kwargs.get("Description"),
            MusicURL=kwargs.get("MediaId"),
            HQMusicUrl=kwargs.get("HQMusicUrl"),
            ThumbMediaId=kwargs.get("ThumbMediaId")
        )
    if msgtype == "news":
        data.update(
            ArticleCount=kwargs.get("ArticleCount"),
            Articles=kwargs.get("Articles"),
            Title=kwargs.get("Title"),
            Description=kwargs.get("Description"),
            PicUrl=kwargs.get("PicUrl"),
            Url=kwargs.get("Url")
        )
    data = {k: v for k, v in data.items() if v is not None}
    return data


class WXMsgCrypt:
    def __init__(self, encoding_aes_key, appid):
        self.key = base64.b64decode(encoding_aes_key + "=")
        self.iv = self.key[:16]  # AES初始向量为key的前16字节
        self.appid = appid

    def encrypt(self, xml_content):
        """
        加密微信消息
        :param xml_content: 明文字符串格式的XML消息
        :return: 加密后的encrypt字符串
        """
        try:
            # 生成16字节随机字符串
            random_nonce =  os.urandom(16)
            # 构造明文数据包
            text = xml_content.encode()
            appid_bytes = self.appid.encode()
            msg_len = len(text).to_bytes(4, byteorder='big')
            plaintext = random_nonce + msg_len + text + appid_bytes
            # PKCS7填充
            padded = self._pad(plaintext)
            # 执行AES加密
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            ciphertext = cipher.encrypt(padded)
            # Base64编码加密结果
            return base64.b64encode(ciphertext).decode('utf-8')
        except Exception as e:
            raise ValueError(f"加密失败: {str(e)}")


    def decrypt(self, encrypted_msg):
        """
        解密微信消息
        :param encrypted_msg: 加密的消息字符串
        :return: 解密后的明文消息
        """
        try:
            # Base64解码加密消息
            ciphertext = base64.b64decode(encrypted_msg)
            # 初始化AES-CBC解密器
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            # 执行解密并去除PKCS#7填充
            decrypted_data = cipher.decrypt(ciphertext)
            # 检查数据长度是否为16的整数倍
            if len(decrypted_data) % AES.block_size != 0:
                raise ValueError("解密数据长度不符合块大小整数倍")
            plaintext = self._unpad(decrypted_data)
            # 解析解密后的数据
            # 格式: 16字节随机字符串 + msg_len(4字节网络字节序) + msg + appid
            if len(plaintext) < 16 + 4:
                raise ValueError("解密后数据长度异常")
            # 提取消息内容
            msg_len = int.from_bytes(plaintext[16:20], byteorder='big')
            appid_start = 20 + msg_len
            if appid_start > len(plaintext):
                raise ValueError("消息长度错误")
            
            xml_content = plaintext[20:appid_start].decode('utf-8')
            appid_received = plaintext[appid_start:].decode('utf-8')
            
            # 验证AppID
            if appid_received != self.appid:
                raise ValueError("AppID校验失败")
            
            return xml_content
        
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")

    def _unpad(self, s):
        """
        去除PKCS#7填充
        """
        # 检查数据长度是否为块大小的整数倍
        if len(s) % AES.block_size != 0:
            raise ValueError("解密后数据长度不符合块大小整数倍")
        pad = s[-1]
        if pad < 1 or pad > AES.block_size:
            # pad = 0
            raise ValueError("无效的填充值")
        # 验证所有填充字节是否相同
        if s[-pad:] != bytes([pad] * pad):
            raise ValueError("填充字节不一致")
        return s[:-pad]
    
    def _pad(self, s):
        """PKCS7填充"""
        pad = AES.block_size - (len(s) % AES.block_size)
        return s + bytes([pad] * pad)
    



