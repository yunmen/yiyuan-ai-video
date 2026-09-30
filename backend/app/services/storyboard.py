# -*- coding: utf-8 -*-
'''
@文件    :storyboard.py
@说明    :分镜/镜头业务:分镜级状态查询、镜头编辑、Worker 回写持久化
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
from typing import Optional

from app.cruds.storyboard import episode_crud, shot_crud


class StoryboardService:
    """分镜/镜头查询与编辑;worker 成功回调时调用 persist_from_usage 把运行期分镜表沉淀为实体"""

    # ------------------------- 查询 -------------------------
    async def get_by_task(self, task_id: int, page_num: int = 1, page_size: int = 50):
        """按任务拉取分镜集与镜头列表(分镜级状态查询)"""
        episode = await episode_crud.get_by_task(task_id)
        total, shots = await shot_crud.list_by_task(task_id, page_num, page_size)
        shot_items = [self._to_shot(s) for s in shots]
        episode_item = self._to_episode(episode, shot_items) if episode else None
        return {"total": total, "episode": episode_item, "shots": shot_items}

    async def update_shot(
        self, task_id: int, index: int, prompt: Optional[str] = None,
        narration: Optional[str] = None,
        start_ms: Optional[int] = None, end_ms: Optional[int] = None,
    ):
        """编辑单个镜头(提示词/台词/时长),供局部重跑使用。按 task_id + index 定位。

        编辑会同时回写生成任务 usage.shot_prompts(权威提示词来源),使随后的局部重跑
        (regenerate_segment)能直接采用本次编辑后的复刻描述,无需前端额外透传。

        start_ms/end_ms 成对传入时同步重算 duration_ms —— 时长是派生的,
        不允许调用方单独传入,否则三者可能出现 start + duration ≠ end 的矛盾数据。
        """
        shot = await shot_crud.get_by_task_and_index(task_id, index)
        if not shot:
            return None
        data = {}
        if prompt is not None:
            data["prompt"] = prompt
        if narration is not None:
            data["narration"] = narration
        if start_ms is not None and end_ms is not None:
            data["start_ms"] = int(start_ms)
            data["end_ms"] = int(end_ms)
            data["duration_ms"] = int(end_ms) - int(start_ms)
        if data:
            await shot_crud.update(shot, data)
        # 回写任务 usage:让 regenerate_segment 能从 usage.shot_prompts 取到最新提示词
        if prompt is not None:
            try:
                from app.cruds.generate_task import crud as task_crud
                obj = await task_crud.get(task_id)
                if obj:
                    # usage 可能为空(首轮尚未回写):仍需写入 shot_prompts,
                    # 否则局部重跑取不到本次编辑后的提示词
                    usage = dict(obj.usage) if isinstance(obj.usage, dict) else {}
                    prompts = usage.get("shot_prompts") or []
                    hit = next((p for p in prompts if isinstance(p, dict) and p.get("index") == index), None)
                    if hit:
                        hit["prompt"] = prompt
                    else:
                        prompts.append({"index": index, "prompt": prompt})
                    usage["shot_prompts"] = prompts
                    obj.usage = usage
                    await obj.save(update_fields=["usage"])
            except Exception as exc:  # noqa: BLE001
                import logging
                logging.getLogger("storyboard").warning(f"镜头编辑回写 usage 失败 task={task_id}: {exc}")
        return self._to_shot(shot)

    # ------------------------- 持久化(worker 回调) -------------------------
    async def persist_from_usage(
        self, task_id: int, usage: Optional[dict], source: str = "multi_segment"
    ) -> None:
        """把 worker 回写的 usage.shots / shot_prompts / shot_qc 沉淀为 Episode+Shot 实体。

        防御式实现:任意字段缺失/异常都不影响主任务回调(分镜只是增强能力)。
        仅当 usage 含 shots 时才落库,单段任务自然跳过。

        source 由调用方按任务类型传入:
          · `replicate`     = 对标视频拆解(deconstruct)逆推出的分镜,用户可编辑后再出片;
          · `multi_segment` = 多段生成按镜头切分的成片结构记录。
        两者结构同源却语义不同,落库时区分开才能在前端做不同处理
        (拆解态允许大改重排,成片态只做核对)。
        """
        if not usage or not isinstance(usage, dict):
            return
        shots = usage.get("shots")
        if not shots or not isinstance(shots, list):
            return
        try:
            episode = await episode_crud.get_by_task(task_id)
            if not episode:
                episode = await episode_crud.create({
                    "task_id": task_id, "title": "", "source": source,
                    "shot_count": len(shots), "status": "success",
                })
            else:
                episode.shot_count = len(shots)
                episode.status = "success"
                await episode.save(update_fields=["shot_count", "status"])

            prompts = {item.get("index"): item.get("prompt") for item in (usage.get("shot_prompts") or []) if isinstance(item, dict)}
            qc_map = {item.get("index"): item for item in (usage.get("shot_qc") or []) if isinstance(item, dict)}

            for raw in shots:
                if not isinstance(raw, dict):
                    continue
                idx = int(raw.get("index", 0) or 0)
                start = float(raw.get("start") or 0)
                end = float(raw.get("end") or 0)
                dur = float(raw.get("duration") or (end - start))
                shot = await shot_crud.get_by_task_and_index(task_id, idx)
                fields = {
                    "episode_id": episode.id,
                    "index": idx,
                    "start_ms": int(start * 1000),
                    "end_ms": int(end * 1000),
                    "duration_ms": int(dur * 1000),
                    "narration": raw.get("text") or raw.get("narration") or None,
                    "prompt": prompts.get(idx),
                    "status": "success",
                }
                qc = qc_map.get(idx) or {}
                if qc:
                    fields["qc_score"] = qc.get("score")
                    fields["qc_low"] = bool(qc.get("low"))
                    fields["qc_note"] = qc.get("note")
                if shot:
                    await shot_crud.update(shot, fields)
                else:
                    await shot_crud.create({"task_id": task_id, **fields})
        except Exception as exc:  # noqa: BLE001
            # 分镜持久化失败绝不阻断主任务回调
            import logging
            logging.getLogger("storyboard").warning(f"分镜持久化失败 task={task_id}: {exc}")

    # ------------------------- 序列化 -------------------------
    @staticmethod
    def _to_shot(s):
        return {
            "id": s.id, "index": s.index, "start_ms": s.start_ms, "end_ms": s.end_ms,
            "duration_ms": s.duration_ms, "narration": s.narration, "prompt": s.prompt,
            "status": s.status, "result_url": s.result_url, "qc_score": s.qc_score,
            "qc_low": s.qc_low, "qc_note": s.qc_note,
        }

    @staticmethod
    def _to_episode(e, shots):
        return {
            "id": e.id, "task_id": e.task_id, "title": e.title, "source": e.source,
            "shot_count": e.shot_count, "status": e.status, "shots": shots,
        }


service = StoryboardService()
