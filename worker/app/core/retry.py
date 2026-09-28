# -*- coding: utf-8 -*-
'''瞬时错误退避重试:方舟 429 限流 / 5xx 内部错误 / 网络抖动应重试而非直接判失败。

为什么需要:
  实测 seedream 图片生成会返回 429(RPM 限流)、seedance 视频生成会偶发 500(方舟内部错误),
  这些都是**瞬时**错误,重试通常可恢复;但旧实现把这些错误和"参数错误/无权限"一视同仁,
  直接抛给上层 → 整条生成任务失败(视频还会触发 ARQ 整任务重跑,重复扣费)。

用法:把"一次真实网关请求"包成无参异步工厂交给 with_transient_retry,
  非瞬时错误(400/401/403 参数或鉴权问题)立即抛出,不浪费重试。
'''
import asyncio
from typing import Any, Awaitable, Callable, Optional

import httpx

from app.core.plugin import logger

# 瞬时 HTTP 状态码:限流与方舟侧内部错误,重试通常可恢复
_TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})


def is_transient_error(exc: BaseException) -> bool:
    """判断异常是否属瞬时错误(应退避重试)"""
    # 网络抖动:超时 / 传输层错误,重试安全
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    # httpx 显式状态码错误(raise_for_status 抛出)
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_STATUS
    # OpenAI SDK 等把状态码挂在 .status_code 上的响应错误
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status in _TRANSIENT_STATUS:
        return True
    # 方舟把 4xx/5xx 包成 RuntimeError("方舟返回 {code}: ..."),从中解析状态码
    msg = str(exc)
    if msg.startswith("方舟返回 "):
        try:
            code = int(msg[len("方舟返回 "):].split(":", 1)[0].strip())
        except (ValueError, IndexError):
            return False
        return code in _TRANSIENT_STATUS
    return False


async def with_transient_retry(
    factory: Callable[[], Awaitable[Any]],
    *,
    retries: Optional[int] = None,
    backoff: Optional[float] = None,
    label: str = "",
) -> Any:
    """对瞬时错误做指数退避重试;非瞬时错误立即抛出,避免无谓重试。

    factory 为无参异步工厂(每次重试都重新发起调用,不使用缓存结果)。
    retries/backoff 缺省取 settings(GEN_TRANSIENT_RETRIES / GEN_TRANSIENT_BACKOFF);
    首次等待 backoff,其后翻倍(backoff、2*backoff、4*backoff...)。
    """
    from app.settings import config

    # retries 为「额外重试次数」,总尝试 = 1(首次) + retries;默认值 3 即「含首次共 4 次」。
    # 与 settings 注释「GEN_TRANSIENT_RETRIES: 3(含首次共 1+3 次)」保持一致。
    retries_n = int(retries if retries is not None else getattr(config, "GEN_TRANSIENT_RETRIES", 3) or 3)
    total = retries_n + 1
    base = float(backoff if backoff is not None else getattr(config, "GEN_TRANSIENT_BACKOFF", 2.0) or 2.0)
    last: Optional[BaseException] = None
    for attempt in range(1, total + 1):
        try:
            return await factory()
        except Exception as exc:  # noqa: BLE001
            if not is_transient_error(exc):
                raise
            last = exc
            if attempt >= total:
                logger.warning(f"[retry] {label} 瞬时错误重试 {retries_n} 次仍失败: {exc}")
                raise
            wait = base * (2 ** (attempt - 1))
            logger.warning(
                f"[retry] {label} 命中瞬时错误(第 {attempt}/{total} 次),{wait:.1f}s 后重试: {exc}"
            )
            await asyncio.sleep(wait)
    # 理论上不会到这(retries>=1),仅兜底
    assert last is not None
    raise last
