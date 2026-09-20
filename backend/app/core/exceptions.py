from typing import Optional, Any



class BizException(Exception):
    """
    业务异常（类似 ValueError）
    """
    def __init__(self, message: str = "失败", data: Optional[Any] = None):
        self.message = message
        self.data = data
        super().__init__(message)