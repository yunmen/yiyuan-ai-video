"""逐段断点和异构媒体的独立回归，不访问模型网关。"""
import asyncio
import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from app.core import compose, media_prep, shots
from app.schemas.base import ToolResult
from app.tools.video_tool import VideoGenTool


class SegmentRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_completed_segment_does_not_submit_again(self):
        tool = VideoGenTool(api_key="test", base_url="http://localhost/v1")
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "segment.mp4")
            with open(path, "wb") as file:
                file.write(b"test")
            edit = AsyncMock(side_effect=AssertionError("成功段不得再次提交"))
            notify = AsyncMock()
            checkpoint = {"result_url": "https://example.com/segment.mp4", "next_frame": "frame.jpg"}
            with patch("app.tools.video_tool.download_to_local", return_value=path), patch.object(tool, "edit_video", edit):
                result = await tool._generate_one_segment(
                    ffmpeg="ffmpeg", seg_prompt="test", ref_duration=30, local_ref=path,
                    reference_video="ref.mp4", materials=[], ratio="9:16", resolution="720p",
                    intent=[], cursor=0, seg_duration=15, workdir=directory, cleanup=[],
                    prev_next_frame="", extract_next=True, checkpoint=checkpoint, on_stage=notify,
                )
            self.assertEqual(result, (path, "frame.jpg"))
            edit.assert_not_called()
            self.assertEqual(notify.await_args.args[1]["status"], "success")

    async def test_only_middle_low_segment_is_repaired(self):
        tool = VideoGenTool(api_key="test", base_url="http://localhost/v1")
        tool._qc_auto_retry = True
        table = [{"index": index, "start": index * 15, "end": (index + 1) * 15} for index in range(3)]
        calls = []
        async def generate_segment(**kwargs):
            calls.append(kwargs["cursor"])
            await kwargs["on_stage"](3, {"result_url": f"segment-{len(calls)}", "status": "success"})
            return f"segment-{len(calls)}", "frame"
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "ref.mp4")
            with open(path, "wb") as file:
                file.write(b"test")
            concat = AsyncMock(side_effect=["first.mp4", "repaired.mp4"])
            checkpoint = {}
            with patch("app.tools.video_tool.download_to_local", return_value=path), \
                    patch.object(compose, "ffmpeg_path", return_value="ffmpeg"), \
                    patch.object(media_prep, "probe_duration", AsyncMock(return_value=45)), \
                    patch.object(media_prep, "probe_size", AsyncMock(return_value=(160, 120))), \
                    patch.object(shots, "detect_shots", AsyncMock(return_value=table)), \
                    patch.object(shots, "narrate_shots", AsyncMock(return_value=table)), \
                    patch.object(tool, "_build_shot_prompts", AsyncMock(return_value={})), \
                    patch.object(tool, "_generate_one_segment", side_effect=generate_segment), \
                    patch.object(tool, "_concat_segments", concat), \
                    patch.object(tool, "_check_output_against_reference", AsyncMock()), \
                    patch.object(tool, "_review_shots_with_vision", AsyncMock(side_effect=[[{"index": 1, "low": True}], []])):
                result = await tool._generate_multi_segment("test", "ref.mp4", [], 45, "4:3", "720p", checkpoint=checkpoint)
            self.assertEqual(calls, [0, 15, 30, 15])
            self.assertEqual(result.content, "repaired.mp4")
            self.assertEqual(concat.await_args.args[1], ["segment-1", "segment-4", "segment-3"])
            self.assertEqual(checkpoint["multi_segment"]["segments"]["1:1"]["status"], "success")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "需要 ffmpeg/ffprobe")
class MediaNormalizationTest(unittest.IsolatedAsyncioTestCase):
    async def test_mixed_size_fps_and_missing_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [os.path.join(directory, f"input_{index}.mp4") for index in range(2)]
            for index, (size, fps) in enumerate([("160x120", 24), ("128x160", 25)]):
                cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=blue:s={size}:r={fps}"]
                if index:
                    cmd += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100"]
                cmd += ["-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", paths[index]]
                result = await compose.run(cmd, timeout=60)
                self.assertTrue(result["ok"], result)
            normalized = await media_prep.normalize_segments(paths, directory, "ffmpeg")
            for path in normalized:
                self.assertEqual(await media_prep.probe_size(path), (160, 120))
                self.assertTrue(await media_prep.has_audio_stream(path))
            with open(os.path.join(directory, "list.txt"), "w") as file:
                file.write(compose.build_concat_list([os.path.basename(path) for path in normalized]))
            output = os.path.join(directory, "merged.mp4")
            result = await compose.run(compose.build_concat_cmd("list.txt", output), cwd=directory)
            self.assertTrue(result["ok"], result)
            self.assertAlmostEqual(await media_prep.probe_duration(output), 2, delta=0.15)
            decoded = await compose.run(["ffmpeg", "-v", "error", "-i", output, "-f", "null", "-"])
            self.assertTrue(decoded["ok"], decoded)
            self.assertFalse(decoded.get("stderr", "").strip())


if __name__ == "__main__":
    unittest.main()
