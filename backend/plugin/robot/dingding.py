import httpx


class DingDingRobot:
    """钉钉机器人"""
    url = "https://oapi.dingtalk.com/robot/send"
    method = "post"
    def __init__(self, key: str):
        self.key = key

    def send_text(self, content: str):
        params = {
            "access_token":self.key
        }
        data = {
            "msgtype": "text",
            "text": {
                    "content": content
                }
        }
        r = httpx.request(self.method, self.url, params=params, json=data)


    def send_markdown(self, title: str, content: str):
        params = {
            "access_token":self.key
        }
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title":title,
                "text":content
            }
        }
        r = httpx.request(self.method, self.url, params=params, json=data)

