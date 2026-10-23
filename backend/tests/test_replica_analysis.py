"""解析凭证的用户、视频、版本与过期校验，不连接真实 Redis。"""
import unittest
from unittest.mock import patch, AsyncMock

from fastapi.exceptions import HTTPException
from app.services import replica_analysis


class MemoryRedis:
    """仅供当前测试保存解析快照，不访问外部服务。"""

    def __init__(self):
        """初始化独立缓存，防止测试间共享状态。"""
        self.values = {}

    async def set(self, key, value, **kwargs):
        """记录快照及过期参数。"""
        self.values[key] = value
        assert kwargs["ex"] == replica_analysis.ANALYSIS_TTL

    async def get(self, key):
        """返回测试缓存中的快照，缺失模拟过期。"""
        return self.values.get(key)


class ReplicaAnalysisTest(unittest.IsolatedAsyncioTestCase):
    """校验凭证不能跨用户、跨原片或跨版本复用。"""

    async def test_snapshot_identity_and_expiration(self):
        """有效快照可读取，错误身份、视频、版本和过期均被拒绝。"""
        cache = MemoryRedis()
        with patch.object(replica_analysis, "get_cache", return_value=cache):
            result = await replica_analysis.save_analysis(1, "/uploads/ref.mp4", [{"id": "e0"}])
            analysis_id = result["analysis_id"]
            record = await replica_analysis.load_analysis(analysis_id, 1, 1, "/uploads/ref.mp4")
            self.assertEqual(record["elements"], [{"id": "e0"}])
            for version, user_id, video in [(1, 2, "/uploads/ref.mp4"), (1, 1, "other.mp4"), (2, 1, "/uploads/ref.mp4")]:
                with self.assertRaises(HTTPException):
                    await replica_analysis.load_analysis(analysis_id, version, user_id, video)
            cache.values.clear()
            with self.assertRaises(HTTPException):
                await replica_analysis.load_analysis(analysis_id, 1, 1, "/uploads/ref.mp4")

    async def test_manual_element_uses_verified_shot_and_new_snapshot(self):
        """补充元素生成新凭证且保留旧快照，镜头越界不能写入。"""
        from app.schemas.replica_analysis import UpdateAnalysisSchema
        cache = MemoryRedis()
        with patch.object(replica_analysis, "get_cache", return_value=cache), patch.object(
                replica_analysis, "get_verified_shots", AsyncMock(return_value=[{"start": 1, "end": 3}])):
            original = await replica_analysis.save_analysis(1, "ref.mp4", [])
            payload = UpdateAnalysisSchema(analysis_id=original["analysis_id"], analysis_version=1,
                reference_video="ref.mp4", deconstruct_id=1, shot_index=0, kind="product", label="原片杯子")
            updated = await replica_analysis.update_analysis(payload, 1)
            self.assertNotEqual(updated["analysis_id"], original["analysis_id"])
            self.assertEqual(updated["elements"][0]["observations"][0]["shot_end"], 3)
            old = await replica_analysis.load_analysis(original["analysis_id"], 1, 1, "ref.mp4")
            self.assertEqual(old["elements"], [])
            payload.shot_index = 2
            with self.assertRaises(HTTPException):
                await replica_analysis.update_analysis(payload, 1)


class ShotPlanTest(unittest.IsolatedAsyncioTestCase):
    """验证分镜快照、来源权限与最少操作兼容性。"""

    def test_snapshot_and_text_overrides(self):
        """覆盖仅改变独立快照的文字，不改变来源或时间轴。"""
        from app.schemas.generate_task import ShotOverrideSchema
        source = [{"index": 0, "start": 0, "end": 2, "description": "原描述", "narration": "原旁白"}]
        plan = replica_analysis.normalize_shot_plan(3, source, [ShotOverrideSchema(index=0, description="新描述", narration="新旁白")])
        self.assertEqual(plan["source_task_id"], 3)
        self.assertEqual(plan["shots"][0]["duration"], 2)
        self.assertEqual(plan["shots"][0]["narration"], "新旁白")
        source[0]["description"] = "后续修改"
        self.assertEqual(plan["shots"][0]["description"], "新描述")

    def test_reject_invalid_timeline_and_overrides(self):
        """拒绝空、倒序、重叠、非有限时间、非法序号与伪造时间覆盖。"""
        valid = [{"index": 0, "start": 0, "end": 2}]
        invalid = [[], [{"start": -1, "end": 2}], [{"start": 2, "end": 1}],
                   [{"start": 0, "end": float("inf")}], [{"index": 5, "start": 0, "end": 2}],
                   valid + [{"index": 1, "start": 1, "end": 3}]]
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(HTTPException):
                replica_analysis.normalize_shot_plan(1, source)
        for overrides in [[{"index": 1}], [{"index": 0, "start": 1}], [{"index": 0}, {"index": 0}]]:
            with self.subTest(overrides=overrides), self.assertRaises(HTTPException):
                replica_analysis.normalize_shot_plan(1, valid, overrides)

    def test_optional_schema_keeps_direct_generation(self):
        """直接生成不要求拆解；客户端不得伪造时间或重复覆盖。"""
        from pydantic import ValidationError
        from app.schemas.generate_task import CreateSchema
        self.assertIsNone(CreateSchema(materials=["ref.mp4"]).deconstruct_id)
        for fields in [{"shot_overrides": []},
                       {"deconstruct_id": 1, "shot_overrides": [{"index": 0, "start": 1}]},
                       {"deconstruct_id": 1, "shot_overrides": [{"index": 0}, {"index": 0}]}]:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                CreateSchema(materials=["ref.mp4"], **fields)

    async def test_verified_source_and_saved_prompt(self):
        """仅本人同原片成功任务可读取，并优先使用已保存描述。"""
        import json
        from types import SimpleNamespace
        import sys
        from app.cruds.generate_task import crud
        # 仅隔离地址补全依赖，避免单元测试加载应用日志、Redis 和环境配置。
        generate_task = SimpleNamespace(_abs_url=lambda value: value)
        task = SimpleNamespace(deleted=False, user_id=1, type="deconstruct", status="success",
            params={"reference_video": "ref.mp4"}, result_text=json.dumps({"shots": [{"index": 0, "start": 0, "end": 2, "description": "旧"}]}),
            usage={"shot_prompts": [{"index": 0, "prompt": "已保存"}]})
        with patch.object(crud, "get_by_id", AsyncMock(return_value=task)), patch.dict(sys.modules, {"app.services.generate_task": generate_task}):
            result = await replica_analysis.get_verified_shots(3, 1, "ref.mp4")
            self.assertEqual(result[0]["description"], "已保存")
            for user, video in [(2, "ref.mp4"), (1, "other.mp4")]:
                with self.assertRaises(HTTPException):
                    await replica_analysis.get_verified_shots(3, user, video)
            for field, value in [("deleted", True), ("status", "failed"), ("type", "video")]:
                old = getattr(task, field)
                setattr(task, field, value)
                with self.assertRaises(HTTPException):
                    await replica_analysis.get_verified_shots(3, 1, "ref.mp4")
                setattr(task, field, old)


if __name__ == "__main__":
    unittest.main()
