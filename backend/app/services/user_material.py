"""上传归属台账：复用持久化资产表，不依赖 Redis TTL 或公开地址前缀。"""
import asyncio
import hashlib
from pathlib import PurePosixPath
from urllib.parse import urlsplit


IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "m4v", "webm"}


def material_classification(url: str, meta: dict) -> dict:
    def suffix_kind(value):
        extension = PurePosixPath(urlsplit(value or "").path).suffix.lower().lstrip(".")
        return "image" if extension in IMAGE_EXTENSIONS else "video" if extension in VIDEO_EXTENSIONS else None

    url_kind = suffix_kind(url)
    filename_kind = suffix_kind(meta.get("filename", ""))
    conflict = bool(url_kind and filename_kind and url_kind != filename_kind)
    unknown = not url_kind or (bool(meta.get("filename")) and not filename_kind)
    user_kind = meta.get("user_kind") if meta.get("user_kind") in {"image", "video"} else None
    needs_confirmation = (conflict or unknown) and not user_kind
    kind = user_kind if conflict or unknown else url_kind
    return {"kind": kind, "user_kind": user_kind, "needs_confirmation": needs_confirmation,
            "classification_source": "user" if (conflict or unknown) and user_kind else "pending" if needs_confirmation else "suffix",
            "classification_reason": "conflict" if conflict else "unknown" if unknown else None}


async def material_info(user_id: int, url: str) -> dict:
    from app.models.asset_cache import GenAssetCacheModel
    record = await GenAssetCacheModel.filter(cache_key=material_key(url), asset_type="uploaded_material", deleted=False).first()
    meta = validate_owner(record, user_id, url)
    return {"url": url, **material_classification(url, meta)}

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


async def mark_material_type(user_id: int, url: str, kind: str) -> dict:
    from app.models.asset_cache import GenAssetCacheModel
    record = await GenAssetCacheModel.filter(
        cache_key=material_key(url), asset_type="uploaded_material", deleted=False
    ).first()
    meta = validate_owner(record, user_id, url)
    if meta.get("status") != "ready":
        raise HTTPException(status_code=200, detail="素材尚未上传完成，请稍后重试")
    classification = material_classification(url, meta)
    if kind not in {"image", "video"}:
        raise HTTPException(status_code=200, detail="素材标识只能是图片或视频")
    if classification["classification_reason"] is None and kind != classification["kind"]:
        raise HTTPException(status_code=200, detail="该素材后缀类型明确，无需修改标识")
    meta["user_kind"] = kind
    record.meta = meta
    await record.save(update_fields=["meta", "update_time"])
    return {"url": url, **material_classification(url, meta)}


async def mark_material_role(user_id: int, url: str, role: str | None) -> dict:
    from app.models.asset_cache import GenAssetCacheModel
    record = await GenAssetCacheModel.filter(
        cache_key=material_key(url), asset_type="uploaded_material", deleted=False
    ).first()
    meta = validate_owner(record, user_id, url)
    if meta.get("status") != "ready":
        raise HTTPException(status_code=200, detail="素材尚未上传完成，请稍后重试")
    if role not in {None, "person", "scene", "product"}:
        raise HTTPException(status_code=200, detail="素材用途只能是人物、场景或商品")
    meta["role"] = role
    record.meta = meta
    await record.save(update_fields=["meta", "update_time"])
    return {"url": url, "role": role, **material_classification(url, meta)}


async def list_materials(user_id: int, payload) -> tuple[int, list]:
    """只列本人已确认成功的上传台账，历史记录通过迁移补充用户命名空间。"""
    from app.models.asset_cache import GenAssetCacheModel
    query = GenAssetCacheModel.filter(
        asset_type="uploaded_material", task_type=f"material:{user_id}", deleted=False
    ).order_by("-create_time", "-id")
    start = (payload.pageNum - 1) * payload.pageSize
    total, offset, result = 0, 0, []
    # 历史台账没有分类列，分批计算有效分类后计数分页，避免整库加载及分页后过滤。
    while True:
        rows = await query.offset(offset).limit(200)
        for row in rows:
            meta = validate_owner(row, user_id, row.content)
            classification = material_classification(row.content, meta)
            match = (payload.kind == "all" or payload.kind == classification["kind"]
                     or (payload.kind == "pending" and classification["needs_confirmation"]))
            if not match:
                continue
            if start <= total < start + payload.pageSize:
                result.append({
                    "id": row.id, "url": row.content, "filename": meta.get("filename", "素材"),
                    "size": meta.get("size", 0), "role": meta.get("role"), **classification,
                    "create_time": row.format_create_time,
                })
            total += 1
        if len(rows) < 200:
            break
        offset += len(rows)
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
