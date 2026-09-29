# -*- coding: utf-8 -*-
'''
@文件    :oss.py
@说明    :OSS 转存工具 — 把远程资源(模型返回的临时直链)下载后转存到自有 OSS
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.0
@说明    :OSS 未启用或转存失败时,保留原始直链,不阻塞主流程。
'''
import asyncio
import os
import re
import tempfile
import time
import uuid
from typing import List, Optional, Tuple

import httpx

from app.core.plugin import oss, logger
from app.settings import config

# 常见媒体类型 → 扩展名映射
_EXT_MAP = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/bmp": ".bmp",
    "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm",
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/wav": ".wav",
    "audio/x-wav": ".wav", "application/pdf": ".pdf",
}
_URL_RE = re.compile(r"^https?://\S+$")

# 远程媒体下载参数。跨境链路实测:10MB 成片要走 250 秒,而 httpx 的 read 超时
# 只约束"两个数据包之间的间隔","挤牙膏"式慢连接每包都在间隔内缓慢到达,
# read 超时永远不触发,任务会挂十几分钟直到对端断连 —— 所以必须再加总时长兜底。
_DOWNLOAD_CONNECT_TIMEOUT = 15.0     # 建连超时(秒)
_DOWNLOAD_READ_TIMEOUT = 30.0       # 两个数据块之间的最大间隔(秒):停滞 30s 即断连重试
_DOWNLOAD_MAX_TOTAL = 900.0         # 单次下载全程总时长上限(秒),含建连与读取
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 流式读取块大小:1MB
_DOWNLOAD_RETRIES = 3               # 整文件下载重试次数(GET 幂等,跨境断流高发)

# 内网/本机/链路本地(云元数据)地址:worker 替用户下载素材时一律禁止访问,防止 SSRF
_PRIVATE_URL_RE = re.compile(
    r"^https?://("
    r"localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+"
    r"|169\.254\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+"
    r"|\[::1\]|::1"
    r")(?::\d+)?(/|$)"
)


def _is_private_url(url: str) -> bool:
    """是否内网/本机/云元数据地址:模型侧拉不到,且 worker 回源下载时禁止访问"""
    return bool(_PRIVATE_URL_RE.match((url or "").strip()))


def _accelerate_url(url: str) -> str:
    """把**自有 COS 桶**的下载地址换成全球加速域名(未开启加速/非本桶时原样返回)

    为什么需要这一步:SDK 的 Domain 加速只作用于 SDK 调用(上传),而回读走的是
    httpx 直连 _build_url() 生成的标准地域域名,跨境时享受不到加速 ——
    实测同一个桶、同样大小的成片:加速生效的取回约 1.5 分钟,未加速的要 13.5 分钟。
    只替换域名不改路径/签名,故只对命中本桶的地址生效,外部 URL 一律不碰(不引入 SSRF 面)。
    """
    if not config.OSS_SERVICE_Accelerate:
        return url
    bucket = (config.OSS_SERVICE_Bucket or "").strip()
    if not bucket:
        return url
    standard = f"https://{bucket}.cos.{config.OSS_SERVICE_Region}.myqcloud.com/"
    if not (url or "").startswith(standard):
        return url
    return f"https://{bucket}.cos.accelerate.myqcloud.com/" + url[len(standard):]


def _reject_private_redirect(response: "httpx.Response") -> None:
    """跟随重定向时,若下一跳指向内网/云元数据地址则中断,防止 SSRF 重定向绕过初始 URL 校验"""
    next_req = response.next_request
    if next_req is not None and _is_private_url(str(next_req.url)):
        raise httpx.HTTPError(f"拒绝跟随重定向到内网地址: {next_req.url}")


def _ext_from_content_type(content_type: str) -> str:
    return _EXT_MAP.get((content_type or "").split(";")[0].strip().lower(), ".bin")


def upload_bytes(data: bytes, key: str) -> Optional[str]:
    """把二进制数据上传到 OSS,返回 URL;OSS 未启用或失败返回 None"""
    if not oss:
        return None
    try:
        return oss.put_object(key, data)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"OSS 上传失败 key={key}: {exc}")
        return None


def _download_media(url: str) -> Tuple[str, str]:
    """流式下载远程媒体到临时文件,返回 (临时文件路径, Content-Type)

    相比 ``client.get().content`` 一次性读入内存,这里:
      1. 边收边写盘,避免整片视频驻留内存;
      2. 手工做总时长计时 —— 跨境"挤牙膏"连接每个数据包都在 read 超时内缓慢到达,
         httpx 自身的 read timeout 拦不住,实测会空挂十几分钟等对端断连;
      3. 整文件失败(超时/断流/非 2xx)从头重试,最多 ``_DOWNLOAD_RETRIES`` 次,
         GET 为幂等请求,重试安全。

    三次均失败时抛出最后一次异常,由 ``_persist_single`` 兜底。
    调用方负责删除返回的临时文件。
    """
    last_exc: Optional[Exception] = None
    # 自有 COS 对象改走全球加速域名(与上传路径一致),跨境回读才享受加速
    url = _accelerate_url(url)
    for attempt in range(1, _DOWNLOAD_RETRIES + 1):
        fd, tmp_path = tempfile.mkstemp(suffix=".download")
        os.close(fd)
        start = time.monotonic()
        try:
            # event_hooks 只能挂在 Client 上(httpx.get()/stream 快捷方法不接受),
            # 重定向到内网地址时在响应钩子里中断,防 SSRF 绕过初始 URL 校验。
            with httpx.Client(
                timeout=httpx.Timeout(
                    _DOWNLOAD_READ_TIMEOUT,
                    connect=_DOWNLOAD_CONNECT_TIMEOUT,
                    write=_DOWNLOAD_READ_TIMEOUT,
                    pool=_DOWNLOAD_CONNECT_TIMEOUT,
                ),
                follow_redirects=True,
                event_hooks={"response": [_reject_private_redirect]},
            ) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "")
                    with open(tmp_path, "wb") as f:
                        for chunk in resp.iter_bytes(_DOWNLOAD_CHUNK_SIZE):
                            # 总时长兜底:read 超时只管块间隔,这里管整次下载的生死
                            if time.monotonic() - start > _DOWNLOAD_MAX_TOTAL:
                                raise httpx.TimeoutException(
                                    f"下载总时长超过 {int(_DOWNLOAD_MAX_TOTAL)} 秒"
                                    "(跨境链路过慢或已断流)"
                                )
                            if chunk:
                                f.write(chunk)
            return tmp_path, content_type
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            if attempt < _DOWNLOAD_RETRIES:
                logger.warning(
                    f"资源第 {attempt}/{_DOWNLOAD_RETRIES} 次下载失败,准备整文件重试: "
                    f"{url} ({exc})"
                )
    assert last_exc is not None  # 三次循环均失败时必有异常记录
    raise last_exc


def _upload_remote(url: str, prefix: str) -> Optional[str]:
    """下载远程资源并转存 OSS,返回 OSS URL;失败抛出异常由调用方兜底"""
    # SSRF 防护:禁止直接拉取内网/云元数据地址(素材 URL 可能来自用户传入)
    if _is_private_url(url):
        raise ValueError(f"拒绝下载内网地址: {url}")
    tmp_path: Optional[str] = None
    try:
        tmp_path, content_type = _download_media(url)
        with open(tmp_path, "rb") as f:
            data = f.read()
        original = url.split("/")[-1].split("?")[0]
        _, ext = os.path.splitext(original)
        if not ext:
            ext = _ext_from_content_type(content_type)
        key = f"generate/result/{prefix}_{uuid.uuid4().hex[:8]}{ext}"
        return upload_bytes(data, key)
    finally:
        # 无论转存成功与否都清掉临时文件,失败重试产生的残件已在 _download_media 内清理
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _persist_single(url: str, prefix: str) -> str:
    """单条转存:非 URL / OSS 未启用时原样返回;转存失败保留原直链"""
    if not oss or not _URL_RE.match(url or ""):
        return url
    try:
        return _upload_remote(url, prefix) or url
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"资源转存 OSS 失败,保留原链: {url} ({exc})")
        return url


async def persist_url_list(urls: List[str], prefix: Optional[str] = None) -> List[str]:
    """批量把在线资源转存到 OSS,返回持久化 URL 列表(长度与入参一致)"""
    if not urls:
        return []
    if not oss:
        return list(urls)
    task_prefix = prefix or uuid.uuid4().hex
    results = await asyncio.gather(
        *(asyncio.to_thread(_persist_single, u, task_prefix) for u in urls)
    )
    return list(results)


def download_to_local(url: str, suffix: str = ".mp4") -> Optional[str]:
    """下载远程资源到本地临时文件,返回路径;失败返回 None

    链路上的视频一直是 URL(转存 OSS 后回写),但 ffmpeg 只能处理本地文件 ——
    这里补上「URL → 本地」这一环。调用方负责用完删除(避免临时文件堆积)。

    复用 _download_media 的流式写盘 + 总时长兜底 + 整文件重试:
    此前这里是一次性读内存且只靠固定的 read 超时,跨境"挤牙膏"连接每包都在超时内
    缓慢到达,read 超时永远不触发 —— 实测表现就是任务 26 的段成片回读挂死十余分钟
    (任务 22 的「多段生成段成片下载失败」也出自同一处)。
    """
    if not _URL_RE.match(url or ""):
        return None
    # SSRF 防护:拒绝下载内网/云元数据地址(参考视频等 URL 可由匿名用户传入)
    if _is_private_url(url):
        logger.warning(f"拒绝下载内网地址: {url}")
        return None
    try:
        tmp_path, _content_type = _download_media(url)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"下载资源失败: {url} ({exc})")
        return None
    # _download_media 统一用 .download 后缀落盘,这里换成调用方期望的后缀,
    # 否则 ffmpeg 无法按扩展名识别容器格式(如 -f 推断失败)。
    if suffix and suffix != ".download":
        try:
            fd, target = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            os.replace(tmp_path, target)
            return target
        except OSError as exc:  # noqa: BLE001
            logger.warning(f"资源临时文件改名失败,沿用原路径: {url} ({exc})")
    return tmp_path


def upload_local_file(path: str, key: str) -> Optional[str]:
    """上传本地文件到 OSS,返回 URL;失败返回 None(ffmpeg 产物的回传入口)"""
    try:
        with open(path, "rb") as f:
            return upload_bytes(f.read(), key)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"本地文件上传失败 key={key}: {exc}")
        return None
