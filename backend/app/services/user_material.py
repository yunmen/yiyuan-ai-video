"""上传归属台账：复用持久化资产表，不依赖 Redis TTL 或公开地址前缀。"""
import asyncio
import hashlib

from fastapi.exceptions import HTTPException


def material_key(url: str) -> str:
    """上传地址使用服务端原始形式生成独立业务键，禁止客户端认领任意地址。"""
    return hashlib.sha256(f"user_material:v1:{url}".encode()).hexdigest()


async def register_material(user_id: int, url: str, filename: str, size: int = 0, storage_key: str = "") -> None:
    """仅由成功代理上传或签名签发调用；签名上传待对象存在检查后才能建单。"""
    from app.models.asset_cache import GenAssetCacheModel
    await GenAssetCacheModel.create(cache_key=material_key(url), asset_type="uploaded_material",
        task_type=f"upload:{user_id}" if storage_key else f"material:{user_id}", content=url, expire_time=None,
        meta={"user_id": user_id, "filename": filename, "size": size,
              "status": "pending" if storage_key else "ready", "storage_key": storage_key})


def validate_owner(record, user_id: int, url: str) -> dict:
    """校验非删除台账的精确地址及账号，公开可访问不代表可认领。"""
    if (not record or record.deleted or (record.meta or {}).get("user_id") != user_id
            or record.content != url or record.asset_type != "uploaded_material"):
        raise HTTPException(status_code=200, detail="参考图不属于当前账号或上传记录已失效，请重新上传")
    return dict(record.meta)


async def verify_materials(user_id: int, urls: list) -> None:
    """扣费和模型调用前核验全部图片归属，历史无台账图片要求重新上传。"""
    from app.models.asset_cache import GenAssetCacheModel
    from app.core.oss import get_oss
    from app.core.upload import MAX_SIZE
    for url in set(urls):
        record = await GenAssetCacheModel.filter(cache_key=material_key(url), asset_type="uploaded_material", deleted=False).first()
        meta = validate_owner(record, user_id, url)
        if meta.get("status") == "pending":
            oss = get_oss()
            if not oss or not meta.get("storage_key"):
                raise HTTPException(status_code=200, detail="素材直传尚未完成，请重新上传")
            try:
                # 元数据核验不应继承大文件上传的长超时，及时返回可重试反馈。
                head = await asyncio.wait_for(
                    asyncio.to_thread(oss.client.head_object, Bucket=oss.bucket, Key=meta["storage_key"]),
                    timeout=8,
                )
                size = int(head.get("Content-Length", 0))
            except Exception as exc:
                raise HTTPException(status_code=200, detail="无法确认素材直传完成，请稍后重试") from exc
            if not 0 < size <= MAX_SIZE:
                raise HTTPException(status_code=200, detail="上传素材为空或超过大小限制")
            meta.update(status="ready", size=size)
            record.meta = meta
            record.task_type = f"material:{user_id}"
            await record.save(update_fields=["meta", "task_type", "update_time"])
        if meta.get("status") != "ready":
            raise HTTPException(status_code=200, detail="素材尚不可用，请重新上传")


async def list_materials(user_id: int, payload) -> tuple[int, list]:
    """只列本人已确认成功的上传台账，历史记录通过迁移补充用户命名空间。"""
    from tortoise.expressions import Q
    from app.models.asset_cache import GenAssetCacheModel
    # 归属和就绪状态编码到独立命名空间，避免全表读取 JSON 再在内存分页。
    query = GenAssetCacheModel.filter(
        asset_type="uploaded_material", task_type=f"material:{user_id}", deleted=False
    )
    video_extensions = {"mp4", "mov", "m4v", "webm"}
    video_filter = Q()
    for extension in video_extensions:
        video_filter |= Q(content__iendswith=f".{extension}")
    if payload.kind == "video":
        query = query.filter(video_filter)
    elif payload.kind == "image":
        query = query.exclude(video_filter)
    total = await query.count()
    rows = await query.order_by("-create_time", "-id").offset(
        (payload.pageNum - 1) * payload.pageSize
    ).limit(payload.pageSize)
    result = []
    for row in rows:
        meta = row.meta or {}
        # 再检查一次元数据，台账损坏时也不能暴露其他人的素材。
        validate_owner(row, user_id, row.content)
        result.append({
            "id": row.id, "url": row.content, "filename": meta.get("filename", "素材"),
            "size": meta.get("size", 0),
            "kind": "video" if row.content.rsplit(".", 1)[-1].lower() in video_extensions else "image",
            "create_time": row.format_create_time,
        })
    return total, result


async def sync_materials(user_id: int, cursor: int) -> dict:
    """分批找回早期直传文件；对象不存在或不可用时明确计数，不伪造上传成功。"""
    from app.models.asset_cache import GenAssetCacheModel
    from loguru import logger
    records = await GenAssetCacheModel.filter(
        asset_type="uploaded_material", task_type=f"upload:{user_id}", deleted=False, id__gt=cursor
    ).order_by("id").limit(21)
    # 四个并行核验控制对象存储压力，20 条最坏约 40 秒，前端为同步保留一分钟。
    limiter = asyncio.Semaphore(4)
    async def check(record) -> bool:
        """单条失败明确记录并计数，不影响同批其他有效素材的恢复。"""
        async with limiter:
            try:
                await verify_materials(user_id, [record.content])
                return True
            except HTTPException:
                logger.warning(f"历史素材暂无法确认，用户Id={user_id}，素材Id={record.id}")
                return False
    results = await asyncio.gather(*(check(record) for record in records[:20]))
    return {
        "confirmed": sum(results), "unavailable": len(results) - sum(results),
        "next_cursor": records[min(len(records), 20) - 1].id if records else cursor,
        "has_more": len(records) > 20,
    }
