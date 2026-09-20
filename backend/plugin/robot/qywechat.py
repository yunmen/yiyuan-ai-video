import httpx


class QYWeixinRobot:
    """企业微信机器人"""
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
    method = "post"
    def __init__(self, key: str):
        self.key = key
    
    def upload_file(self, file: bytes):
        """
        上传附件到企业微信中
        {"errcode":0,"errmsg":"ok","type":"file","media_id":"3e9n94LAUCtwasZp-m8WEQEtmJ4JhW8PpSFi5qB3MfmUhFoKyREhMzGpnSSX-xjsT","created_at":"1676710555"}
        """
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media"
        params = {
            "key":self.key,
            "type":"file"
        }
        data = {
            "media":file
        }
        r = httpx.request(self.method, url, params=params, files=data)
        return r.json()["media_id"]

    def send_text(self, content: str):
        params = {
            "key":self.key
        }
        data = {
            "msgtype": "text",
            "text": {
                    "content": content
                }
        }
        r = httpx.request(self.method, self.url, params=params, json=data)


    def send_markdown(self, content: str):
        params = {
            "key":self.key
        }
        data = {
            "msgtype": "markdown",
            "markdown":{
                "content": content
            }
        }
        r = httpx.request(self.method, self.url, params=params, json=data)

    def send_file(self, file: bytes):
        params = {
            "key":self.key
        }
        media_id = self.upload_file(file)
        data = {
            "msgtype": "file",
            "file": {
                "media_id": media_id
            }
        }
        r = httpx.request(self.method, self.url, params=params, json=data)

