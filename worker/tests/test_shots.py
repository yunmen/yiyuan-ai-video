# -*- coding: utf-8 -*-
"""参考视频镜头结构解析:镜头边界检测 → 分镜表 → 按镜头切分

贯穿这一组用例的前置条件只有一个:**解析失败必须安静回退**。
镜头解析是增强能力(让生成看懂原片结构),它一旦把任务弄失败,
损失(一次已付费的生成)远大于收益,所以每一条失败路径都要被钉死。
"""
import asyncio
import os

from app.core import asr, compose, multiseg, shots

# 真实 showinfo 输出片段:字段随 ffmpeg 版本增减,但 pts_time 一直在
SHOWINFO = (
    "[Parsed_showinfo_1 @ 0x55] n:   0 pts:      0 pts_time:0 duration:  1 color_range:tv\n"
    "[Parsed_showinfo_1 @ 0x55] n:   1 pts:     36 pts_time:1.2 duration:  1\n"
    "[Parsed_showinfo_1 @ 0x55] n:   2 pts:    300 pts_time:10 duration:  1\n"
    "这行是无关噪声,不含任何时间戳\n"
    "[Parsed_showinfo_1 @ 0x55] n:   3 pts:    303 pts_time:10.0004 duration:  1\n"
    "[Parsed_showinfo_1 @ 0x55] n:   4 pts:    606 pts_time:20.2 duration:  1 color_range:tv\n"
)


def _table(*ranges):
    """按 (start, end) 快速构造分镜表(字段与 shots.build_shot_list 产出一致)"""
    return [
        {
            "index": idx,
            "start": float(start),
            "end": float(end),
            "duration": float(end) - float(start),
        }
        for idx, (start, end) in enumerate(ranges)
    ]


def _run(coro):
    """在同步用例里跑协程(worker 未装 pytest-asyncio,统一用 asyncio.run)"""
    return asyncio.run(coro)


def _fake_ffmpeg_run(payload):
    """构造一个假的 compose.run:直接返回给定结果,不真的起进程"""
    async def _inner(cmd, timeout=600, cwd=None, truncate=True):
        return payload
    return _inner


# --- 切点解析 ---

def test_parse_scene_times_sorts_and_dedups():
    """同一切点被打印多次(10 与 10.0004)必须合并,且结果升序"""
    assert shots.parse_scene_times(SHOWINFO) == [0.0, 1.2, 10.0, 20.2]


def test_parse_scene_times_returns_empty_on_noise():
    """一行时间戳都没有(如 ffmpeg 报错)时返回空表,由调用方回退"""
    assert shots.parse_scene_times("Error: Invalid argument") == []
    assert shots.parse_scene_times("") == []


# --- 分镜表构建 ---

def test_build_shot_list_splits_on_cuts():
    """三个切点 → 四个镜头,且各段时长之和等于总时长"""
    table = shots.build_shot_list(30.0, [2.0, 10.0, 20.0])
    assert [item["duration"] for item in table] == [2.0, 8.0, 10.0, 10.0]
    assert sum(item["duration"] for item in table) == 30.0
    assert [item["index"] for item in table] == [0, 1, 2, 3]


def test_build_shot_list_merges_short_fragments():
    """1.5s 处的切点会造出 0.5s 的碎镜头 → 必须并入相邻镜头,不产出过短镜头"""
    table = shots.build_shot_list(30.0, [1.0, 1.5, 10.0])
    assert len(table) == 3
    assert all(item["duration"] >= shots.MIN_SHOT_SECONDS for item in table)


def test_build_shot_list_ignores_cuts_at_edges():
    """贴着首尾的切点(0.2s / 29.9s)直接丢弃,不产生无意义镜头"""
    table = shots.build_shot_list(30.0, [0.2, 29.9])
    assert len(table) == 1
    assert table[0]["start"] == 0.0 and table[0]["end"] == 30.0


def test_build_shot_list_caps_shot_count():
    """碎剪原片检测出几十个切点 → 超过上限按时间等分,规模必须可控"""
    cuts = [float(i) for i in range(1, 60)]
    table = shots.build_shot_list(60.0, cuts, max_shots=6)
    assert len(table) == 6
    assert {item["duration"] for item in table} == {10.0}


def test_build_shot_list_returns_empty_without_duration():
    """时长未知构不出分镜表 → 空表(调用方回退按秒切分)"""
    assert shots.build_shot_list(0, [1.0, 2.0]) == []


# --- 裁剪到目标时长 ---

def test_clip_shots_truncates_to_target():
    """原片比目标时长长时,尾镜头要被截到目标时长(否则切分会回退按秒)"""
    table = _table((0, 10), (10, 20), (20, 40))
    clipped = shots.clip_shots(table, 30.0)
    assert len(clipped) == 3
    assert clipped[-1]["end"] == 30.0 and clipped[-1]["duration"] == 10.0


def test_clip_shots_pads_tail_when_not_covered():
    """裁剪后覆盖不到目标时长 → 补一个尾镜头,否则最后一段会缺时长"""
    table = _table((0, 10), (10, 20), (20, 40))
    clipped = shots.clip_shots(table, 45.0)
    assert len(clipped) == 4
    assert clipped[-1]["start"] == 40.0 and clipped[-1]["end"] == 45.0
    assert [item["index"] for item in clipped] == [0, 1, 2, 3]


def test_clip_shots_drops_out_of_range_and_empty_input():
    """起点已越界的镜头整条丢弃;目标时长非法/空表返回空"""
    assert len(shots.clip_shots(_table((0, 10), (20, 40)), 15.0)) == 2
    assert shots.clip_shots(_table((0, 10)), 0) == []
    assert shots.clip_shots([], 30.0) == []


# --- 原片台词归集 ---

def test_attach_narration_groups_by_shot():
    """词按起始时间落到所属镜头;中文直连、英文补空格"""
    table = _table((0, 10), (10, 20))
    words = [
        {"word": "限时", "start": 0.5, "end": 0.8},
        {"word": "秒杀", "start": 1.0, "end": 1.3},
        {"word": "hello", "start": 11.0, "end": 11.4},
        {"word": "world", "start": 11.5, "end": 11.9},
    ]
    result = shots.attach_narration(table, words)
    assert result[0]["narration"] == "限时秒杀"
    assert result[1]["narration"] == "hello world"
    # 不修改入参:调用方手上的原分镜表必须保持干净
    assert "narration" not in table[0]


def test_attach_narration_truncates_long_line():
    """单镜头台词超长要截断:分镜表会随 metadata 落库,不能塞整段口播"""
    table = _table((0, 100))
    words = [{"word": "词", "start": float(i), "end": float(i) + 0.5} for i in range(80)]
    result = shots.attach_narration(table, words)
    assert len(result[0]["narration"]) == shots.MAX_NARRATION_CHARS + 1
    assert result[0]["narration"].endswith("…")


def test_attach_narration_keeps_table_without_words():
    """无台词(无音轨/未启用 ASR)时分镜表照常可用,只是台词为空"""
    table = _table((0, 10))
    result = shots.attach_narration(table, [])
    assert result[0]["narration"] == ""
    assert result[0]["duration"] == 10.0


# --- 取帧时间点 ---

def test_shot_frame_times_takes_first_frame_of_each_shot():
    """每镜头一帧,时间点落在镜头内部(贴切点取帧会拿到转场残影)"""
    table = _table((0, 10), (10, 20), (20, 30))
    assert shots.shot_frame_times(table) == [0.08, 10.08, 20.08]


def test_shot_frame_times_respects_limit():
    """超过上限时抽稀:帧数受上游素材数量限制约束"""
    table = _table((0, 10), (10, 20), (20, 30))
    assert len(shots.shot_frame_times(table, per_shot=2)) == 6
    assert len(shots.shot_frame_times(table, per_shot=2, limit=4)) <= 4
    assert len(shots.shot_frame_times(table, limit=2)) == 2


def test_shot_frame_times_empty_table():
    """空分镜表返回空(调用方回退均匀抽帧)"""
    assert shots.shot_frame_times([]) == []


def test_scene_detect_cmd_outputs_to_devnull():
    """输出目标必须是系统空设备而不是 `-`

    末位参数为 `-` 时,调用方或测试桩极易把它当成文件路径落盘
    (实测:单测桩按 cmd[-1] 写文件,在 worker 目录下留下过一个名为 `-` 的杂散文件)。
    """
    cmd = shots.build_scene_detect_cmd("ref.mp4")
    assert cmd[-3:] == ["-f", "null", os.devnull]
    assert cmd[-1] != "-"
    # 结果来自 stderr 的 showinfo,必须保留 select 过滤器
    assert any("select=" in part for part in cmd)


# --- 检测(IO 层):失败一律空表 ---

def test_detect_shots_skips_without_ffmpeg(monkeypatch):
    """容器没装 ffmpeg → 不检测、不报错,直接回退"""
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: None)
    assert _run(shots.detect_shots("https://x/ref.mp4", 30.0)) == []


def test_detect_shots_returns_empty_on_failure(monkeypatch):
    """ffmpeg 检测失败 → 空表,绝不抛异常打断任务"""
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(compose, "run", _fake_ffmpeg_run({"ok": False, "stderr": "boom"}))
    assert _run(shots.detect_shots("https://x/ref.mp4", 30.0)) == []


def test_detect_shots_skips_when_duration_unknown(monkeypatch):
    """时长探测不到就不检测:分镜表没有总时长构不出来"""
    assert _run(shots.detect_shots("https://x/ref.mp4", None)) == []
    assert _run(shots.detect_shots("", 30.0)) == []


def test_detect_shots_builds_table(monkeypatch):
    """检测成功 → 切点(1.2 / 10 / 20.2)构出四个镜头"""
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(
        compose, "run", _fake_ffmpeg_run({"ok": True, "stdout": "", "stderr": SHOWINFO}),
    )
    table = _run(shots.detect_shots("https://x/ref.mp4", 30.0))
    assert len(table) == 4
    assert [item["start"] for item in table] == [0.0, 1.2, 10.0, 20.2]


# --- 后台可配的镜头切分阈值(gen.shot_scene_threshold) ---

def test_scene_threshold_reads_config(monkeypatch):
    """后台配的阈值生效:字符串原值也要能转成 float"""
    monkeypatch.setattr(shots.config, "SHOT_SCENE_THRESHOLD", "0.5")
    assert shots.scene_threshold() == 0.5
    monkeypatch.setattr(shots.config, "SHOT_SCENE_THRESHOLD", 0.42)
    assert shots.scene_threshold() == 0.42


def test_scene_threshold_falls_back_on_invalid(monkeypatch):
    """脏配置(非数值/越界)一律回退默认 0.3,不让检测退化成全切碎或零切点"""
    for bad in ("abc", "", "3", "-1", "0", "1"):
        monkeypatch.setattr(shots.config, "SHOT_SCENE_THRESHOLD", bad)
        assert shots.scene_threshold() == shots.DEFAULT_SCENE_THRESHOLD


def test_detect_shots_uses_configured_threshold(monkeypatch):
    """detect_shots 未显式传阈值时读后台配置,并注入 ffmpeg 场景检测命令"""
    monkeypatch.setattr(shots.config, "SHOT_SCENE_THRESHOLD", "0.5")
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "ffmpeg")
    captured = {}

    async def _capture(cmd, timeout=600, cwd=None, truncate=True):
        captured["cmd"] = cmd
        return {"ok": True, "stdout": "", "stderr": SHOWINFO}

    monkeypatch.setattr(compose, "run", _capture)
    _run(shots.detect_shots("https://x/ref.mp4", 30.0))
    assert any("gt(scene,0.500)" in part for part in captured["cmd"])


def test_detect_shots_explicit_threshold_overrides_config(monkeypatch):
    """显式传入的阈值优先于后台配置(便于单测与定向调用)"""
    monkeypatch.setattr(shots.config, "SHOT_SCENE_THRESHOLD", "0.5")
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "ffmpeg")
    captured = {}

    async def _capture(cmd, timeout=600, cwd=None, truncate=True):
        captured["cmd"] = cmd
        return {"ok": True, "stdout": "", "stderr": SHOWINFO}

    monkeypatch.setattr(compose, "run", _capture)
    _run(shots.detect_shots("https://x/ref.mp4", 30.0, threshold=0.2))
    assert any("gt(scene,0.200)" in part for part in captured["cmd"])


# --- 原片台词:默认关闭时零开销 ---

def test_narrate_shots_skips_when_asr_disabled(monkeypatch):
    """词级 ASR 未启用(默认)→ 连下载都不做;返回的分镜表仍带 narration 空字段"""
    monkeypatch.setattr(asr, "enabled", lambda: False)
    called = {"download": False}

    async def _fail_if_called(source):
        called["download"] = True
        return source

    monkeypatch.setattr(shots, "_ensure_local", _fail_if_called)
    result = _run(shots.narrate_shots("https://x/ref.mp4", _table((0, 10))))
    assert called["download"] is False
    assert result[0]["narration"] == ""


def test_narrate_shots_attaches_words(monkeypatch):
    """启用后把词级时间戳按镜头归集进 narration;本地文件不误删"""
    async def _words(media_path, model=None):
        return [{"word": "限时", "start": 1.0, "end": 1.3}]

    async def _local(source):
        return source

    monkeypatch.setattr(asr, "enabled", lambda: True)
    monkeypatch.setattr(asr, "transcribe_words", _words)
    monkeypatch.setattr(shots, "_ensure_local", _local)
    result = _run(shots.narrate_shots("ref.mp4", _table((0, 10))))
    assert result[0]["narration"] == "限时"


def test_narrate_shots_keeps_table_when_asr_fails(monkeypatch):
    """ASR 识别不出(无音轨/网关不支持)→ 分镜表照常返回,台词留空"""
    async def _none(media_path, model=None):
        return None

    async def _local(source):
        return source

    monkeypatch.setattr(asr, "enabled", lambda: True)
    monkeypatch.setattr(asr, "transcribe_words", _none)
    monkeypatch.setattr(shots, "_ensure_local", _local)
    result = _run(shots.narrate_shots("ref.mp4", _table((0, 10))))
    assert result[0]["narration"] == ""


# --- 按镜头切分(必须满足上层依赖的两个不变量) ---

def test_plan_segments_by_shots_uses_shot_boundaries():
    """相邻镜头尽量同段:10s 的镜头两两成段,而不是被切在 15s 处"""
    assert multiseg.plan_segments_by_shots(_table((0, 10), (10, 20), (20, 30)), 30) == [10, 10, 10]


def test_plan_segments_by_shots_keeps_invariants():
    """不变量:各段之和 == 总时长,且每段落在 [下限, 上限] 内"""
    for table, total in (
        (_table((0, 7), (7, 14), (14, 21), (21, 28)), 28),
        (_table((0, 5), (5, 9), (9, 18), (18, 24), (24, 31)), 31),
        (_table((0, 15), (15, 30)), 30),
    ):
        segments = multiseg.plan_segments_by_shots(table, total)
        assert sum(segments) == total
        assert all(multiseg.MIN_SEGMENT_SECONDS <= s <= multiseg.MAX_SEGMENT_SECONDS for s in segments)


def test_plan_segments_by_shots_clips_reference_longer_than_target():
    """原片长于目标时长:先裁到目标时长再切,不允许出现"总和对不上"的分段"""
    segments = multiseg.plan_segments_by_shots(_table((0, 15), (15, 30), (30, 45)), 30)
    assert segments == [15, 15]


def test_plan_segments_by_shots_falls_back_without_table():
    """没有分镜表 → 回退原有按秒均衡切分(行为与改造前完全一致)"""
    assert multiseg.plan_segments_by_shots([], 30) == multiseg.plan_segments(30) == [15, 15]
    assert multiseg.plan_segments_by_shots([], 40) == multiseg.plan_segments(40)


def test_plan_segments_by_shots_falls_back_on_single_long_shot():
    """单个镜头超过模型单段上限 → 凑不出合法分段,回退按秒(绝不产出 20s 的段)"""
    assert multiseg.plan_segments_by_shots(_table((0, 20)), 20) == multiseg.plan_segments(20) == [10, 10]


def test_plan_segments_by_shots_falls_back_when_reference_too_short():
    """原片只有 10s、目标 30s:分镜表被补了一个 20s 尾镜头 → 超上限,回退按秒"""
    assert multiseg.plan_segments_by_shots(_table((0, 10)), 30) == multiseg.plan_segments(30)


def test_plan_segments_by_shots_short_total():
    """总时长本就在单段上限内 → 直接一段"""
    assert multiseg.plan_segments_by_shots(_table((0, 10)), 10) == [10]
    assert multiseg.plan_segments_by_shots([], 0) == []
