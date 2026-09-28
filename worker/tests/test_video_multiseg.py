# -*- coding: utf-8 -*-
"""多段生成:时长超出模型单段上限时的编排

场景:参考视频 30s → 要生成 30s 成片,而 Seedance 2.x 单次只能出约 15s。
编排要点:拆段 → 首段走视频编辑、后续段用**上一段尾帧**续接 → concat 拼接。
这里把「拆几段」「续接用的首帧是哪来的」「某段失败会不会被吞掉」逐条钉死。
"""
import asyncio
import os

from app.core import compose, media_prep
from app.schemas.base import ToolResult
from app.settings import config
from app.tools.video_tool import VideoGenTool

REF = "https://x/ref.mp4"


def _make_tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _params(duration, reference_video=REF):
    return {
        "gen_duration": duration,
        "reference_video": reference_video,
        "materials": ["https://x/a.jpg", "https://x/b.jpg"],
        "script_text": "限时秒杀促销带货。来看这只超乖的小家伙，治愈感拉满，喜欢就点下方链接。",
        "ratio": "9:16",
        "resolution": "720p",
    }


def _stub_infra(monkeypatch, tool, output_exists=True):
    """打桩 ffmpeg / 下载 / 上传 / prompt 改写,只保留被验证的编排逻辑"""
    async def fake_optimize(user_content, system_prompt=None):
        return user_content

    async def fake_run(cmd, timeout=600, cwd=None, truncate=True):
        if output_exists:
            # 输出路径是最后一个参数;concat 用相对名,需要按 cwd 拼
            out = cmd[-1]
            path = out if os.path.isabs(out) else os.path.join(cwd or os.getcwd(), out)
            with open(path, "wb") as fh:
                fh.write(b"x")
        return {"ok": output_exists, "stdout": "", "stderr": "" if output_exists else "boom"}

    monkeypatch.setattr(tool, "_optimize_prompt", fake_optimize)
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(compose, "run", fake_run)
    monkeypatch.setattr(media_prep, "probe_duration", _async_value(30.0))
    # 多段成片现在也会做技术自检(画幅/时长/分辨率),这里把探测一并打桩,避免测试里去真跑 ffprobe
    monkeypatch.setattr(media_prep, "probe_size", _async_value((1080, 1920)))
    monkeypatch.setattr("app.tools.video_tool.download_to_local", lambda url, *a, **k: _fake_local(url))
    monkeypatch.setattr(
        "app.tools.video_tool.upload_local_file",
        lambda path, key: f"https://oss/{os.path.basename(path)}",
    )


def _async_value(value):
    async def _inner(*a, **k):
        return value
    return _inner


def _fake_local(url):
    """把远程地址映射成一个真实存在的临时文件(实现里会读/删它)"""
    import tempfile
    suffix = ".jpg" if str(url).endswith(".jpg") else ".mp4"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


# --- 分流 ---

def test_short_duration_keeps_single_segment_path(monkeypatch):
    """没超上限就走原链路,不得被多段逻辑截胡(否则平白多花钱)"""
    tool = _make_tool()
    called = {"multi": False}

    async def fake_multi(*a, **k):
        called["multi"] = True
        return ToolResult(content="x", metadata={"success": True})

    async def fake_materials(*a, **k):
        return ToolResult(content="https://x/single.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "_generate_multi_segment", fake_multi)
    monkeypatch.setattr(tool, "_generate_by_materials", fake_materials)
    monkeypatch.setattr(tool, "edit_video", fake_materials)

    asyncio.run(tool.generate(_params(10)))
    assert called["multi"] is False


def test_reference_within_edit_limit_uses_single_edit(monkeypatch):
    """参考视频在编辑上限内(≤30s)→ 必须走**单次编辑**,不得拆段

    编辑模型用 duration=-1,成片时长**跟随被编辑视频** —— 这正是"上传多长就生成多长"的语义。
    若先按模板时长拆段,23s 的参考视频会被切成 15+8 生成两段再拼:多花一次钱,
    还破坏跨段一致性(实测踩过)。多段只在参考视频>编辑上限(30s,超出会被裁掉)时才用。
    """
    tool = _make_tool()
    called = {"multi": False, "edit": False}

    async def fake_multi(*a, **k):
        called["multi"] = True
        return ToolResult(content="https://x/merged.mp4", metadata={"success": True})

    async def fake_edit(*a, **k):
        called["edit"] = True
        return ToolResult(content="https://x/edited.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)                 # probe_duration → 30.0(正好在上限内)
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "doubao-seedance-2-5-260628")
    monkeypatch.setattr(tool, "_generate_multi_segment", fake_multi)
    monkeypatch.setattr(tool, "edit_video", fake_edit)

    result = asyncio.run(tool.generate(_params(30)))

    assert called["edit"] is True
    assert called["multi"] is False
    assert result.content == "https://x/edited.mp4"


def test_reference_beyond_edit_limit_uses_multi_segment(monkeypatch):
    """参考视频超出编辑上限(>30s,超出部分会被裁掉)→ 退回多段拼接以保住总时长

    总时长取**参考视频的真实时长**(45s)而非模板时长(30s):用户上传多长就该生成多长,
    按模板时长排段会把 45s 原片的后半段直接丢掉 —— 与"换产品/复刻要保留原片"的诉求相悖。
    同时它必须远大于吸附后的单段档位(10s),拿吸附值判断就永远进不了多段分支。
    """
    tool = _make_tool()
    called = {"multi": False}

    async def fake_multi(prompt, reference_video, materials, duration, ratio, resolution,
                         script_text="", intent=None, fmt=""):
        called["multi"] = True
        assert duration == 45, "多段编排必须拿到参考视频真实时长 45s,而不是模板 30s 或吸附档位 10s"
        return ToolResult(content="https://x/merged.mp4", metadata={"success": True})

    async def fake_single(*a, **k):
        return ToolResult(content="https://x/single.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "doubao-seedance-2-5-260628")
    monkeypatch.setattr(media_prep, "probe_duration", _async_value(45.0))   # 45s > 编辑上限 30s
    monkeypatch.setattr(tool, "_generate_multi_segment", fake_multi)
    monkeypatch.setattr(tool, "_generate_by_materials", fake_single)
    monkeypatch.setattr(tool, "edit_video", fake_single)

    result = asyncio.run(tool.generate(_params(30)))
    assert called["multi"] is True
    assert result.content == "https://x/merged.mp4"


def test_generate_threads_replicate_format_into_multi_segment(monkeypatch):
    """复刻目标形态必须一路穿到多段生成的逐镜头逆推。

    拆解链路(backend deconstruct 下发 format)已按形态组织画面,若出片链路拿不到形态,
    两次逆推会互相打架:拆解说"这是短剧结构",出片仍照抄原片结构 —— 形态等于白选。
    """
    tool = _make_tool()
    captured = {}

    async def fake_multi(prompt, reference_video, materials, duration, ratio, resolution,
                         script_text="", intent=None, fmt=""):
        captured["fmt"] = fmt
        return ToolResult(content="https://x/merged.mp4", metadata={"success": True})

    async def fake_single(*a, **k):
        return ToolResult(content="https://x/single.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(config, "VIDEO_MODEL_EDIT", "doubao-seedance-2-5-260628")
    monkeypatch.setattr(media_prep, "probe_duration", _async_value(45.0))   # 45s > 编辑上限,进多段
    monkeypatch.setattr(tool, "_generate_multi_segment", fake_multi)
    monkeypatch.setattr(tool, "_generate_by_materials", fake_single)
    monkeypatch.setattr(tool, "edit_video", fake_single)

    params = _params(30)
    params["format"] = "short_drama"
    asyncio.run(tool.generate(params))
    assert captured.get("fmt") == "short_drama"


def test_build_replicate_script_returns_narration(monkeypatch):
    """纯复刻(只有对标视频、没有任何文案)时按原片生成口播文案"""
    tool = _make_tool()
    monkeypatch.setattr(config, "CHAT_MODEL", "chat-test")

    async def fake_optimize(prompt, system_prompt=None):
        return '{"scenes": [{"narrations": ["限时秒杀。", "快来抢。"]}]}'

    monkeypatch.setattr(tool, "_optimize_prompt", fake_optimize)
    text = asyncio.run(tool._build_replicate_script(REF, 30, ["product"], {"prompt": "卖货"}))
    assert text == "限时秒杀。\n快来抢。"


def test_build_replicate_script_gates_without_reference_or_model(monkeypatch):
    """没有参考视频(非复刻)或没有 chat 模型 → 返回空,绝不凭空造文案"""
    tool = _make_tool()
    monkeypatch.setattr(config, "CHAT_MODEL", "")
    assert asyncio.run(tool._build_replicate_script(REF, 30, [], {})) == ""
    monkeypatch.setattr(config, "CHAT_MODEL", "chat-test")
    assert asyncio.run(tool._build_replicate_script("", 30, [], {})) == ""


def test_build_replicate_script_falls_back_on_unparsable(monkeypatch):
    """模型没按 JSON 输出 → 空串,回退"无文案"的历史行为(不因增强影响主链路)"""
    tool = _make_tool()
    monkeypatch.setattr(config, "CHAT_MODEL", "chat-test")

    async def fake_optimize(prompt, system_prompt=None):
        return "这是一段散文,不是 JSON"

    monkeypatch.setattr(tool, "_optimize_prompt", fake_optimize)
    assert asyncio.run(tool._build_replicate_script(REF, 30, [], {})) == ""


def test_long_duration_without_reference_stays_single(monkeypatch):
    """没有参考视频就没有可拆的素材,不该硬套多段(那条链路依赖参考视频)"""
    tool = _make_tool()
    called = {"multi": False}

    async def fake_multi(*a, **k):
        called["multi"] = True

    async def fake_materials(*a, **k):
        return ToolResult(content="https://x/t2v.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "_generate_multi_segment", fake_multi)
    monkeypatch.setattr(tool, "_generate_by_materials", fake_materials)

    asyncio.run(tool.generate(_params(30, reference_video="")))
    assert called["multi"] is False


# --- 编排 ---

def test_every_segment_uses_reference_slice_not_free_continuation(monkeypatch):
    """每段都必须按**原片对应切片**走编辑,不能只有首段用原片

    旧实现后续段拿上一段尾帧做 i2v 续接 —— 后半段与原片毫无关系,换产品时商品/场景
    会一路漂移,拼出来像"前半段复刻 + 后半段自由发挥"。
    """
    tool = _make_tool()
    calls = []

    async def fake_edit(prompt, reference_video, **kwargs):
        calls.append(("edit", reference_video))
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    async def fake_i2v(prompt, **kwargs):
        calls.append(("i2v", kwargs.get("input_image")))
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)                     # 参考视频 30s,排两段 15+15
    monkeypatch.setattr(tool, "edit_video", fake_edit)
    monkeypatch.setattr(tool, "image_to_video", fake_i2v)

    result = asyncio.run(tool._generate_multi_segment("提示词", REF, ["https://x/a.jpg"], 30, "9:16", "720p",
                                                     script_text="第一段台词。第二段台词。"))
    assert result.metadata.get("success") is True
    assert [c[0] for c in calls] == ["edit", "edit"], "两段都要走编辑,不得退化成续接"
    # 各自用自己在原片上的窗口(0-15s / 15-30s),而不是同一个参考视频
    assert calls[0][1] == "https://oss/ref_0_15.mp4"
    assert calls[1][1] == "https://oss/ref_15_15.mp4"
    assert result.content.startswith("https://oss/merged"), "最终必须返回拼接产物"


def test_segment_falls_back_to_last_frame_when_reference_too_short(monkeypatch):
    """原片不够长、裁不出本段切片时才退回尾帧续接(总时长不能缺口)"""
    tool = _make_tool()
    calls = []

    async def fake_edit(prompt, reference_video, **kwargs):
        calls.append(("edit", reference_video))
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    async def fake_i2v(prompt, **kwargs):
        calls.append(("i2v", kwargs.get("input_image")))
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(media_prep, "probe_duration", _async_value(20.0))   # 原片只有 20s
    monkeypatch.setattr(tool, "edit_video", fake_edit)
    monkeypatch.setattr(tool, "image_to_video", fake_i2v)

    asyncio.run(tool._generate_multi_segment("提示词", REF, [], 30, "9:16", "720p", script_text=None))
    # 第二段窗口 15-30s 超出 20s 原片 → 裁不出来 → 尾帧续接
    assert [c[0] for c in calls] == ["edit", "i2v"]
    assert str(calls[1][1]).startswith("https://oss/last_")


def test_each_segment_prompt_carries_its_own_lines(monkeypatch):
    """每段只给本段台词:否则两段都会把整篇文案念一遍"""
    tool = _make_tool()
    prompts = []

    async def fake_edit(prompt, reference_video, **kwargs):
        prompts.append(prompt)
        return ToolResult(content="https://x/seg1.mp4", metadata={"success": True})

    async def fake_i2v(prompt, **kwargs):
        prompts.append(prompt)
        return ToolResult(content="https://x/seg2.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "edit_video", fake_edit)
    monkeypatch.setattr(tool, "image_to_video", fake_i2v)

    asyncio.run(tool._generate_multi_segment(
        "基础提示词", REF, [], 30, "9:16", "720p",
        script_text="限时秒杀促销带货。来看这只超乖的小家伙，治愈感拉满。",
    ))
    assert len(prompts) == 2
    assert all("[本段台词]" in p for p in prompts)
    # 两段拿到的台词不能一模一样
    assert prompts[0] != prompts[1]


def test_segments_carry_replace_intent_and_assets(monkeypatch):
    """多段的每段都要带上替换意图与同源素材(P1-6 一致性)

    漏传 replace_intent → 成片改走"跟随参考视频画幅",与用户选的画幅不符、段间也可能不一致;
    漏传 images → 各段只是照抄原片,首轮做的元素替换全部丢失。
    """
    tool = _make_tool()
    captured = []

    async def fake_edit(prompt, reference_video, **kwargs):
        captured.append(kwargs)
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "edit_video", fake_edit)

    asyncio.run(tool._generate_multi_segment(
        "提示词", REF, ["https://x/a.jpg"], 30, "9:16", "720p", intent=["product"],
    ))
    assert captured, "至少要走一段视频编辑"
    assert all(item.get("replace_intent") == ["product"] for item in captured)
    assert all(item.get("images") == ["https://x/a.jpg"] for item in captured)


def test_multisegment_output_selfcheck_marks_mismatch(monkeypatch):
    """多段成片也要做技术自检:画幅不对必须打标(与单段链路一致,且只标记不阻断)

    此前只有单段视频编辑会自检,多段成片的画幅错了不会被任何环节发现 ——
    而多段正是本轮把 replace_intent 补下去、最需要观测画幅的一条链路。
    """
    tool = _make_tool()

    async def fake_edit(prompt, reference_video, **kwargs):
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "edit_video", fake_edit)
    # 成片被压成接近正方形,与目标 9:16 明显不符
    monkeypatch.setattr(media_prep, "probe_size", _async_value((960, 960)))

    result = asyncio.run(tool._generate_multi_segment("提示词", REF, ["https://x/a.jpg"], 30, "9:16", "720p"))
    assert result.metadata.get("success") is True, "自检只打标,绝不把已付费的成片判失败"
    assert "画幅" in str((result.metadata.get("output_mismatch") or {}).get("reason"))


def test_auto_retry_disabled_by_default(monkeypatch):
    """默认关闭:即便质检低分也不自动重跑 —— 避免静默产生额外费用(P1-7)"""
    tool = _make_tool()
    calls = {"edit": 0}

    async def fake_edit(prompt, reference_video, **kwargs):
        calls["edit"] += 1
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "edit_video", fake_edit)
    qc_calls = {"n": 0}

    async def fake_qc(*a, **k):
        qc_calls["n"] += 1
        return [{"index": 0, "low": True, "score": 50, "issue": "x"}]

    monkeypatch.setattr(tool, "_review_shots_with_vision", fake_qc)

    asyncio.run(tool._generate_multi_segment("提示词", REF, ["https://x/a.jpg"], 30, "9:16", "720p"))
    assert qc_calls["n"] == 1, "默认不应复检"
    assert calls["edit"] == 2, "默认不应额外生成"


def test_auto_retry_reruns_low_segments_when_enabled(monkeypatch):
    """开启 VIDEO_QC_AUTO_RETRY 且质检低分 → 从首个低分镜头起的后缀片段重跑一次(有界)"""
    tool = _make_tool()
    calls = {"edit": 0}

    async def fake_edit(prompt, reference_video, **kwargs):
        calls["edit"] += 1
        return ToolResult(content="https://x/seg.mp4", metadata={"success": True})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "edit_video", fake_edit)
    qc_calls = {"n": 0}
    low_qc = [{"index": 0, "low": True, "score": 50, "issue": "x"}]
    clean_qc: list = []

    async def fake_qc(*a, **k):
        qc_calls["n"] += 1
        return low_qc if qc_calls["n"] == 1 else clean_qc

    monkeypatch.setattr(tool, "_review_shots_with_vision", fake_qc)
    monkeypatch.setattr(config, "VIDEO_QC_AUTO_RETRY", True)

    result = asyncio.run(tool._generate_multi_segment(
        "提示词", REF, ["https://x/a.jpg"], 30, "9:16", "720p",
    ))
    assert qc_calls["n"] == 2, "应从第 1 次质检后复检 1 次"
    # 基线 2 段 → 编辑 2 次;自动重跑全部 2 段(首个低分镜头是第 0 段) → 再编辑 2 次 = 4
    assert calls["edit"] == 4, calls
    assert (result.metadata.get("shot_qc") or []) == clean_qc


def test_segment_failure_fails_whole_job(monkeypatch):
    """某段失败必须整单失败:交出残缺成片比失败更糟(用户会以为成功了)"""
    tool = _make_tool()
    state = {"n": 0}

    async def fake_edit(prompt, reference_video, **kwargs):
        state["n"] += 1
        if state["n"] == 1:
            return ToolResult(content="https://x/seg1.mp4", metadata={"success": True})
        return ToolResult(content="第二段生成失败", metadata={"success": False, "error_type": "timeout"})

    _stub_infra(monkeypatch, tool)
    monkeypatch.setattr(tool, "edit_video", fake_edit)

    result = asyncio.run(tool._generate_multi_segment("提示词", REF, [], 30, "9:16", "720p"))
    assert result.metadata.get("success") is False
    assert "第 2/2 段失败" in result.content


def test_no_ffmpeg_fails_with_clear_reason(monkeypatch):
    """没有 ffmpeg 就不要假装能拼:明确报配置问题"""
    tool = _make_tool()
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: None)

    result = asyncio.run(tool._generate_multi_segment("提示词", REF, [], 30, "9:16", "720p"))
    assert result.metadata.get("success") is False
    assert "ffmpeg" in result.content


def test_merge_failure_reported(monkeypatch):
    """拼接失败必须报错,不能返回未拼接的中间产物"""
    tool = _make_tool()

    async def fake_edit(prompt, reference_video, **kwargs):
        return ToolResult(content="https://x/seg1.mp4", metadata={"success": True})

    async def fake_i2v(prompt, **kwargs):
        return ToolResult(content="https://x/seg2.mp4", metadata={"success": True})

    # run 全部失败 → 抽帧/拼接都会失败
    _stub_infra(monkeypatch, tool, output_exists=False)
    monkeypatch.setattr(tool, "edit_video", fake_edit)
    monkeypatch.setattr(tool, "image_to_video", fake_i2v)

    result = asyncio.run(tool._generate_multi_segment("提示词", REF, [], 30, "9:16", "720p"))
    assert result.metadata.get("success") is False
    assert "首帧" in result.content or "拼接" in result.content
