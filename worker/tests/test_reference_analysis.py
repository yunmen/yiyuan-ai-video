# -*- coding: utf-8 -*-
"""共享参考分析的权限隔离、并发去重、预算与不可信输出回归。"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services import reference_analysis as module


class MemoryRedis:
    """仅模拟本测试所需原子操作，不冒充真实Redis验收。"""

    def __init__(self):
        """保存独立测试键值，避免跨用例共享。"""
        self.data = {}

    async def get(self, key):
        """读取测试键。"""
        return self.data.get(key)

    async def set(self, key, value, nx=False, ex=None):
        """模拟单事件循环下原子SET NX。"""
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    async def eval(self, script, count, *args):
        """模拟令牌校验发布/释放及预算计数语义。"""
        if script == module.RESERVE:
            self.data[args[0]] = self.data.get(args[0], 0) + 1
            return self.data[args[0]]
        if script == module.RELEASE:
            if self.data.get(args[0]) == args[1]:
                self.data.pop(args[0])
                return 1
            return 0
        lock, key, token, value, ttl = args
        if self.data.get(lock) != token:
            return 0
        self.data[key] = value
        return 1


class ReferenceAnalysisTests(unittest.IsolatedAsyncioTestCase):
    """通过独立事件循环验证共享分析，不发起真实模型请求。"""

    async def asyncSetUp(self):
        """准备内容相同的本地素材和固定视觉路由。"""
        self.directory = tempfile.TemporaryDirectory()
        self.local = str(Path(self.directory.name) / "ref.mp4")
        Path(self.local).write_bytes(b"test-video")
        self.rows = [{"index": 0, "start": 0, "end": 4}]
        self.redis = MemoryRedis()
        self.route = patch.object(module.gateway, "resolve", return_value={"url": "https://vision.invalid", "key": "test"})
        self.model = patch.object(module.config, "VISION_MODEL", "vision-test")
        self.enabled = patch.object(module.config, "REFERENCE_ANALYSIS_ENABLED", True)
        self.route.start()
        self.model.start()
        self.enabled.start()

    async def asyncTearDown(self):
        """恢复全局路由与临时文件。"""
        self.route.stop()
        self.model.stop()
        self.enabled.stop()
        self.directory.cleanup()

    async def test_same_account_singleflight_and_cache(self):
        """同账号并发只生产一次，后续任务命中同内容缓存。"""
        async def produce(*args):
            """短暂让出执行权以覆盖并发等待。"""
            await asyncio.sleep(0.02)
            return module.build_reference_dna(self.rows), "analyzed"
        mock = AsyncMock(side_effect=produce)
        with patch.object(module.ReferenceAnalyzer, "_produce", mock):
            a = module.ReferenceAnalyzer(self.redis, "user-a", "task-a")
            b = module.ReferenceAnalyzer(self.redis, "user-a", "task-b")
            results = await asyncio.gather(a.analyze(self.local, self.rows, 4), b.analyze(self.local, self.rows, 4))
            self.assertEqual(mock.await_count, 1)
            self.assertEqual({item["state"] for item in results}, {"analyzed", "cache_hit"})

    async def test_accounts_are_isolated(self):
        """同素材不同账号不能命中对方缓存。"""
        mock = AsyncMock(return_value=(module.build_reference_dna(self.rows), "analyzed"))
        with patch.object(module.ReferenceAnalyzer, "_produce", mock):
            for owner in ("user-a", "user-b"):
                await module.ReferenceAnalyzer(self.redis, owner, "task").analyze(self.local, self.rows, 4)
            self.assertEqual(mock.await_count, 2)

    async def test_missing_scope_or_redis_never_calls_model(self):
        """缺可信身份或Redis时不能落入公共桶或无界付费降级。"""
        with patch.object(module, "_post_vision", AsyncMock()) as model:
            for redis, owner in ((self.redis, ""), (None, "user")):
                result = await module.ReferenceAnalyzer(redis, owner, "task").analyze(self.local, self.rows, 4)
                self.assertEqual(result["state"], "disabled_or_missing_scope")
            model.assert_not_awaited()

    async def test_redis_failure_is_visible_and_no_model_call(self):
        """缓存不可用保守降级并明确状态，不继续付费请求。"""
        self.redis.get = AsyncMock(side_effect=ConnectionError("测试故障"))
        with patch.object(module, "_post_vision", AsyncMock()) as model:
            result = await module.ReferenceAnalyzer(self.redis, "user", "task").analyze(self.local, self.rows, 4)
            self.assertEqual(result["state"], "analysis_unavailable")
            model.assert_not_awaited()

    async def test_budget_survives_retry_and_disables_sdk_retry(self):
        """同任务重试最多一次付费尝试，SDK重试明确为零。"""
        async def extract(command, timeout):
            """给抽帧输出写入小型测试占位图。"""
            Path(command[-1]).write_bytes(b"image")
            return {"ok": True}
        raw = json.dumps({"shots": [{"index": 0, "camera_move": "推近", "confidence": 0.9}]})
        with patch.object(module.compose, "ffmpeg_path", return_value="ffmpeg"), patch.object(
            module.compose, "run", side_effect=extract
        ), patch.object(module, "_post_vision", AsyncMock(return_value=raw)) as model:
            analyzer = module.ReferenceAnalyzer(self.redis, "user", "task")
            args = (self.local, self.rows, 4, "vision-test", {"url": "https://vision.invalid", "key": "test"})
            first = await analyzer._produce(*args)
            second = await analyzer._produce(*args)
            self.assertEqual(first[1], "analyzed")
            self.assertEqual(second[1], "budget_exhausted")
            model.assert_awaited_once()
            self.assertEqual(model.await_args.args[3]["max_retries"], 0)
            self.assertEqual(model.await_args.args[3]["max_tokens"], 1200)

    async def test_untrusted_fields_and_confidence(self):
        """模型散文、伪造镜头与低置信值不进入结构计划。"""
        raw = json.dumps({"shots": [{"index": 0, "camera_move": "推近", "shot_size": "原品牌",
                                     "description": "来源功效", "confidence": 0.9},
                                    {"index": 99, "camera_move": "拉远", "confidence": 1}]})
        dna = module.validate_structure(raw, self.rows)
        self.assertEqual(dna["shots"][0]["camera_move"], "推近")
        self.assertNotIn("原品牌", str(dna))
        self.assertNotIn("来源功效", str(dna))
        low = module.validate_structure('{"shots":[{"index":0,"camera_move":"推近","confidence":0.4}]}', self.rows)
        self.assertEqual(low["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
