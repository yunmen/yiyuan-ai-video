短信服务(short message service)使用指南
## 腾讯云
- 1、安装依赖
```sh
pip install -U tencentcloud-sdk-python
```
- 2、配置
有3种方式配置,直接修改config.py的内容,或者在代码中直接覆盖其参数, 或者实例化后调用configure方法.
第一种方式:
```py
from sms import config
config.SecretId = "你的密钥ID"
config.SecretKey = "你的密钥KEY"
```
第二种方式
```py
from sms import TencentSMS
sms = TencentSMS()
sms.configure(SecretId="你的密钥ID", SecretKey="你的密钥KEY")
```

使用工厂类
```py
from sms import SMSFactory

# 实例化工厂（会自动初始化所有服务）
sms = SMSFactory()

# 使用阿里云发送短信
sms.aliyun.send_template(phone="13800138000", template="SMS_123456", vars={"code": "123456"})

# 使用腾讯云发送短信
sms.tencent.send_template(phone="13800138000", template="123456", vars={"code": "123456"})

# 使用赛邮云发送短信
sms.submail.send_template(phone="13800138000", template="PROJECT_ID", vars={"code": "123456"})

# 重新配置某个服务的参数
sms.configure("aliyun", SecretId="new_key", SecretKey="new_secret")

```
