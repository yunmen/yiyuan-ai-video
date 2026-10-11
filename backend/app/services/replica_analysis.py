"""复刻解析快照：绑定用户与原片，建单后将快照固化到任务参数。"""
import json
import uuid

from fastapi.exceptions import HTTPException

def get_cache():
    """延迟获取公共 Redis，避免仅导入快照服务就加载应用环境。"""
    from app.core.plugin import redis
    return redis

# 解析草稿保留一天；已创建任务使用自身快照，不依赖缓存续期。
ANALYSIS_TTL = 86400
ANALYSIS_VERSION = 1


def analysis_key(analysis_id: str) -> str:
    """生成复刻解析业务缓存键，随机标识不包含素材地址。"""
    return f"grapefruit:replica:analysis:{analysis_id}"


async def save_analysis(user_id: int, reference_video: str, elements: list) -> dict:
    """保存当前用户的解析快照，返回可用于建单验证的版本凭证。"""
    analysis_id = uuid.uuid4().hex
    record = {"analysis_id": analysis_id, "analysis_version": ANALYSIS_VERSION,
              "user_id": user_id, "reference_video": reference_video, "elements": elements}
    await get_cache().set(analysis_key(analysis_id), json.dumps(record, ensure_ascii=False), ex=ANALYSIS_TTL)
    return {"analysis_id": analysis_id, "analysis_version": ANALYSIS_VERSION,
            "expires_in": ANALYSIS_TTL, "elements": elements}


async def load_analysis(analysis_id: str, version: int, user_id: int, reference_video: str) -> dict:
    """扣费前验证解析的用户、视频与版本；不接受客户端伪造元素表。"""
    raw = await get_cache().get(analysis_key(analysis_id))
    if not raw:
        raise HTTPException(status_code=200, detail="解析结果已过期，请重新解析原视频")
    record = json.loads(raw)
    if (record.get("user_id") != user_id or record.get("reference_video") != reference_video
            or record.get("analysis_version") != version or version != ANALYSIS_VERSION):
        raise HTTPException(status_code=200, detail="解析结果与当前账号或原视频不匹配，请重新解析")
    return record


async def get_verified_shots(task_id: int, user_id: int, reference_video: str) -> list:
    """仅从本人同原片的成功拆解任务读取镜头表，拒绝客户端虚构时间轴。"""
    from app.cruds.generate_task import crud
    from app.services.generate_task import _abs_url
    task = await crud.get_by_id(task_id)
    if (not task or task.deleted or task.user_id != user_id or task.type != "deconstruct"
            or task.status != "success" or _abs_url((task.params or {}).get("reference_video", "")) != _abs_url(reference_video)):
        raise HTTPException(status_code=200, detail="请先完成当前原视频的分镜拆解")
    try:
        data = json.loads(task.result_text or "{}")
        shots = data.get("shots", data.get("segments", [])) if isinstance(data, dict) else []
    except (ValueError, TypeError):
        shots = []
    if not shots:
        raise HTTPException(status_code=200, detail="原片分镜结果不可用，请重新拆解")
    return shots


async def update_analysis(payload, user_id: int) -> dict:
    """追加人工元素关联并生成新不可变快照，不影响已建单任务。"""
    from app.schemas.generate_task import ReferenceElementSchema
    record = await load_analysis(payload.analysis_id, payload.analysis_version, user_id, payload.reference_video)
    shots = await get_verified_shots(payload.deconstruct_id, user_id, payload.reference_video)
    if payload.shot_index >= len(shots):
        raise HTTPException(status_code=200, detail="选择的镜头不存在")
    shot = shots[payload.shot_index]
    start, end = float(shot.get("start", 0)), float(shot.get("end", 0))
    if end <= start:
        raise HTTPException(status_code=200, detail="镜头时间轴不完整，请重新拆解")
    elements = record["elements"]
    element = next((item for item in elements if item["id"] == payload.element_id), None)
    if payload.element_id and (not element or element["kind"] != payload.kind):
        raise HTTPException(status_code=200, detail="原片元素已失效，请重新选择")
    if element is None:
        if len(elements) >= 30:
            raise HTTPException(status_code=200, detail="最多支持三十个原片元素")
        element = {"id": f"manual_{uuid.uuid4().hex[:16]}", "kind": payload.kind,
                   "label": payload.label, "time": start, "observations": [], "source": "user_confirmed"}
        elements.append(element)
    observations = element.setdefault("observations", [])
    if not any(item.get("shot_index") == payload.shot_index for item in observations):
        if len(observations) >= 12:
            raise HTTPException(status_code=200, detail="单个元素最多关联十二处镜头")
        observations.append({"time": (start + end) / 2, "shot_index": payload.shot_index,
                             "shot_start": start, "shot_end": end})
    ReferenceElementSchema.model_validate(element)
    return await save_analysis(user_id, payload.reference_video, elements)
