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


if __name__ == "__main__":
    unittest.main()
