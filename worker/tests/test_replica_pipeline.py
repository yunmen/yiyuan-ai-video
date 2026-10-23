# -*- coding: utf-8 -*-
"""后台迁移纯函数测试，不依赖模型、媒体工具或第三方测试框架。"""
import copy
import unittest

from app.services.replica_pipeline import compile_adapted_shot, prepare_replica_plan


class ReplicaPipelineTest(unittest.TestCase):
    """验证结构分离、事实隔离、保守动作及未知状态。"""

    def test_source_text_is_not_target_structure(self):
        """原品牌、原旁白与夹带散文不能进入迁移层，输入保持不变。"""
        rows = [{"index": 0, "start": 0, "end": 4, "description": "原品牌汉堡特写",
                 "narration": "原产品功效", "camera_move": "推近", "shot_size": "特写",
                 "transition": "硬切并恢复原品牌"}]
        original = copy.deepcopy(rows)
        result = prepare_replica_plan(rows, ["product"])
        text = compile_adapted_shot(result["adapted_plan"], 0)
        self.assertNotIn("汉堡", str(result))
        self.assertNotIn("原产品功效", text)
        self.assertIn("推近", text)
        self.assertEqual(result["reference_dna"]["shots"][0]["transition"], "未知")
        self.assertIn("中性外观展示", text)
        self.assertEqual(rows, original)

    def test_no_shots_uses_window_not_fake_analysis(self):
        """无分镜时只记录整体窗口，并显式声明分析不完整。"""
        result = prepare_replica_plan([], ["product"], 12)
        self.assertEqual(result["reference_dna"]["source"], "whole_video_window")
        self.assertEqual(result["reference_dna"]["status"], "partial")
        self.assertEqual(result["adapted_plan"]["shots"][0]["end"], 12)

    def test_failed_probe_does_not_invent_timeline(self):
        """无有效时长时不造镜头，但目标产品规则仍可用。"""
        result = prepare_replica_plan([], ["product"])
        self.assertEqual(result["reference_dna"]["status"], "unavailable")
        self.assertEqual(result["adapted_plan"]["shots"], [])
        self.assertTrue(result["adapted_plan"]["rules"])

    def test_invalid_times_and_untrusted_values(self):
        """跳过非有限和重叠时间，非字符串结构值不导致编译异常。"""
        rows = [{"start": 0, "end": float("inf")},
                {"index": 0, "start": 0, "end": 2, "camera_move": ["推近"]},
                {"start": 1, "end": 3}]
        result = prepare_replica_plan(rows, ["product", "person", "scene"])
        self.assertEqual(len(result["reference_dna"]["shots"]), 1)
        self.assertEqual(result["adapted_plan"]["intent"], ["product", "person", "scene"])
        self.assertEqual(result["adapted_plan"]["shots"][0]["camera_move"], "未知")

    def test_person_only_keeps_product_behavior(self):
        """仅换人物不得注入更改产品动作的指令。"""
        result = prepare_replica_plan([], ["person"], 5)
        text = compile_adapted_shot(result["adapted_plan"], 0)
        self.assertNotIn("中性外观展示", text)
        self.assertIn("其他维度保持原片", text)


if __name__ == "__main__":
    unittest.main()
