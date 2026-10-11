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
        task_type="upload", content=url, expire_time=None,
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
                head = await asyncio.to_thread(oss.client.head_object, Bucket=oss.bucket, Key=meta["storage_key"])
                size = int(head.get("Content-Length", 0))
            except Exception as exc:
                raise HTTPException(status_code=200, detail="无法确认素材直传完成，请稍后重试") from exc
            if not 0 < size <= MAX_SIZE:
                raise HTTPException(status_code=200, detail="上传素材为空或超过大小限制")
            meta.update(status="ready", size=size)
            record.meta = meta
            await record.save(update_fields=["meta", "update_time"])
        if meta.get("status") != "ready":
            raise HTTPException(status_code=200, detail="素材尚不可用，请重新上传")
