"""复刻解析快照：绑定用户与原片，建单后将快照固化到任务参数。"""
import json
import math
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
    """验证本人同原片的成功任务，读取原始时间轴并合并已保存的镜头描述。"""
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
    # 独立复制结果，建单后来源任务的编辑不会改变已经固化的快照。
    usage = task.usage if isinstance(getattr(task, "usage", None), dict) else {}
    prompts = {item.get("index"): item.get("prompt") for item in (usage.get("shot_prompts") or [])
               if isinstance(item, dict)}
    if not isinstance(shots, list) or any(not isinstance(shot, dict) for shot in shots):
        raise HTTPException(status_code=200, detail="原片分镜格式不可用，请重新拆解")
    return [{**shot, "description": prompts.get(shot.get("index", index), shot.get("description", ""))}
            for index, shot in enumerate(shots)]


def normalize_shot_plan(task_id: int, source_shots: list, overrides=None) -> dict:
    """将可信来源及可选文字覆盖固化为版本化快照，拒绝无效时间轴与越界覆盖。"""
    if not isinstance(source_shots, list) or not 1 <= len(source_shots) <= 300:
        raise HTTPException(status_code=200, detail="原片分镜数量不可用，请重新拆解")
    normalized = []
    previous_end = 0.0
    try:
        for index, shot in enumerate(source_shots):
            if not isinstance(shot, dict) or shot.get("index", index) != index:
                raise ValueError("镜头序号不连续")
            start, end = float(shot["start"]), float(shot["end"])
            if not all(math.isfinite(value) for value in (start, end)) or start < previous_end or end <= start:
                raise ValueError("镜头时间轴不合法")
            description = str(shot.get("description") or "")
            narration = str(shot.get("narration") or "")
            if len(description) > 4000 or len(narration) > 2000:
                raise ValueError("镜头文字超长")
            normalized.append({"index": index, "start": start, "end": end, "duration": end - start,
                               "description": description, "narration": narration})
            previous_end = end
        seen = set()
        for override in overrides or []:
            data = override.model_dump(exclude_none=True) if hasattr(override, "model_dump") else dict(override)
            index = data.pop("index")
            if not isinstance(index, int) or index < 0 or index >= len(normalized) or index in seen:
                raise ValueError("覆盖镜头不存在或重复")
            seen.add(index)
            for key, value in data.items():
                limit = {"description": 4000, "narration": 2000}.get(key)
                if limit is None or not isinstance(value, str) or len(value) > limit:
                    raise ValueError("只能覆盖有效镜头文字")
                normalized[index][key] = value
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(status_code=200, detail="原片分镜或修改内容无效，请重新拆解或确认镜头") from exc
    return {"version": 1, "source_task_id": task_id, "shots": normalized}


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
