# -*- coding: utf-8 -*-
'''
@文件    :notice.py
@说明    :回调通知 — 通过 httpx 异步 POST 把生成进度/结果回传给 backend
@时间    :2026/09/18 15:00:00
@作者    :一源AI
@版本    :1.1
@说明    :带自动重试(退避),避免 network 抖动导致成功/失败终态回调丢失
          —— 终态回调一旦丢失,任务会被 backend 对账误判为失败。
'''
import asyncio
from typing import Optional

import httpx

from app.core.plugin import logger
from app.settings import config


async def notify(
    notify_url: str,
    payload: dict,
    token: Optional[str] = None,
) -> None:
    """向 backend 的 notify_url 回写任务状态;失败自动重试,重试耗尽仅记录日志,不阻断任务"""
    url = notify_url or config.NOTIFY_URL
    headers = {"Content-Type": "application/json"}
    secret = token if token is not None else config.NOTIFY_TOKEN
    if secret:
        headers["X-Worker-Token"] = secret

    attempts = max(1, int(config.NOTIFY_RETRY_ATTEMPTS))
    delay = max(1, int(config.NOTIFY_RETRY_DELAY))
    last_err = ""
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code < 400:
                logger.info(f"回调成功 status={payload.get('status')} task={payload.get('task_id')}")
                return
            last_err = f"status={resp.status_code} body={resp.text}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        if attempt < attempts:
            logger.warning(f"回调失败(第 {attempt}/{attempts} 次),{delay * attempt}s 后重试: {last_err}")
            await asyncio.sleep(delay * attempt)

    logger.error(f"回调最终失败 task={payload.get('task_id')} status={payload.get('status')}: {last_err}")


def _base_url(notify_url: Optional[str]) -> str:
    """由 callback 地址推导同域名下的其它内部接口地址(去掉 /callback 后缀)"""
    base = (notify_url or config.NOTIFY_URL or "").rstrip("/")
    return base.rsplit("/callback", 1)[0]


async def fetch_checkpoint(notify_url: str, task_id: int, token: Optional[str] = None) -> dict:
    """向 backend 拉取任务的断点检查点(供 worker 崩溃后续跑)。失败返回空检查点。"""
    url = f"{_base_url(notify_url)}/checkpoint"
    headers = {}
    secret = token if token is not None else config.NOTIFY_TOKEN
    if secret:
        headers["X-Worker-Token"] = secret
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"task_id": task_id}, headers=headers)
        if resp.status_code < 400:
            body = resp.json()
            data = (body or {}).get("data") or {}
            return {
                "checkpoint": data.get("checkpoint") or {},
                "progress": int(data.get("progress") or 0),
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"拉取断点失败 task={task_id}: {exc}")
    return {"checkpoint": {}, "progress": 0}


async def checkpoint_save(notify_url: str, payload: dict, token: Optional[str] = None) -> None:
    """向 backend 回写断点检查点;失败自动重试,重试耗尽仅记录日志,不阻断任务。"""
    url = f"{_base_url(notify_url)}/checkpoint"
    headers = {"Content-Type": "application/json"}
    secret = token if token is not None else config.NOTIFY_TOKEN
    if secret:
        headers["X-Worker-Token"] = secret

    attempts = max(1, int(config.NOTIFY_RETRY_ATTEMPTS))
    delay = max(1, int(config.NOTIFY_RETRY_DELAY))
    last_err = ""
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code < 400:
                logger.info(f"断点回写成功 task={payload.get('task_id')} stage={payload.get('stage')}")
                return
            last_err = f"status={resp.status_code} body={resp.text}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        if attempt < attempts:
            logger.warning(f"断点回写失败(第 {attempt}/{attempts} 次),{delay * attempt}s 后重试: {last_err}")
            await asyncio.sleep(delay * attempt)

    logger.error(f"断点回写最终失败 task={payload.get('task_id')} stage={payload.get('stage')}: {last_err}")
