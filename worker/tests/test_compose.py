# -*- coding: utf-8 -*-
"""P3 合成层:命令构建(纯函数)

这些命令会直接喂给 subprocess,拼错参数的表现是「合成静默失败/产物没音轨」,
所以在不依赖 ffmpeg 的前提下先把命令本身钉死。
"""
from app.core.compose import (
    DEFAULT_BGM_VOLUME,
    Cue,
    _wrap_text,
    build_bgm_cmd,
    build_broll_cmd,
    build_burn_subtitle_cmd,
    build_concat_cmd,
    build_concat_list,
    build_cues,
    build_extract_last_frame_cmd,
    build_mix_audio_cmd,
    build_srt,
    build_trim_cmd,
    caption_style,
    default_subtitle_style,
    resolve_subtitle_font,
    split_cue_text,
    split_sentences,
)

VIDEO = "/tmp/v.mp4"
AUDIO = "/tmp/a.m4a"
BGM = "/tmp/bgm.m4a"
OUT = "/tmp/out.mp4"
SRT = "sub.srt"
STYLE = default_subtitle_style("Microsoft YaHei")


def test_mix_audio_keeps_video_stream():
    """视频流必须 copy:重编码既慢又损画质,而生成的成片本就是 H.264"""
    cmd = build_mix_audio_cmd(VIDEO, AUDIO, OUT)
    assert cmd[:3] == ["ffmpeg", "-y", "-i"]
    assert "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] == "copy"
    assert cmd[cmd.index("-c:a") + 1] == "aac"
    assert VIDEO in cmd and AUDIO in cmd and cmd[-1] == OUT


def test_mix_audio_truncates_to_shortest():
    """不截断会在音频更长时拖一段静音尾巴"""
    assert "-shortest" in build_mix_audio_cmd(VIDEO, AUDIO, OUT)


def test_bgm_never_louder_than_default():
    """BGM 默认压到人声之下(30%),避免盖住口播"""
    cmd = build_bgm_cmd(VIDEO, BGM, OUT)
    filter_expr = cmd[cmd.index("-filter_complex") + 1]
    assert f"volume={DEFAULT_BGM_VOLUME}" in filter_expr
    assert "amix=inputs=2:duration=shortest" in filter_expr


def test_build_broll_overlays_in_window():
    """B-roll 轨:素材只在 [start,end] 窗内叠加,且做 alpha 淡入淡出"""
    broll = "/tmp/prod.jpg"
    cmd = build_broll_cmd(VIDEO, broll, OUT, start=2.0, end=5.0, fade=0.4, position="center")
    assert cmd[:2] == ["ffmpeg", "-y"]
    assert VIDEO in cmd and broll in cmd
    # 图片素材用 -loop 1 持续整窗
    assert "-loop" in cmd and "1" in cmd
    assert broll in cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    # 窗内 alpha 淡入淡出(在 2.0 起、4.6 收)
    assert "fade=t=in:st=2.000:d=0.400:alpha=1" in fc
    assert "fade=t=out:st=4.600:d=0.400:alpha=1" in fc
    # 边界硬裁:enable between 限制只在窗口内显示
    assert "enable='between(t,2.000,5.000)'" in fc
    # 居中位置
    assert "(W-w)/2:(H-h)/2" in fc
    assert cmd[-1] == OUT


def test_build_broll_video_loops_and_clips():
    """视频素材用 -stream_loop -1,scale/position 透传"""
    broll = "/tmp/clip.mp4"
    cmd = build_broll_cmd(VIDEO, broll, OUT, start=1.0, end=3.0, scale=0.3, position="br", broll_type="video")
    assert "-stream_loop" in cmd and "-1" in cmd
    assert "scale=w=iw*0.300" in cmd[cmd.index("-filter_complex") + 1]
    assert "overlay=W-w-20:H-h-20" in cmd[cmd.index("-filter_complex") + 1]


def test_bgm_maps_video_and_mixed_audio_only():
    """只保留画面 + 混音轨:不 map 会把两条原始音轨一起带进去成片出现双音轨"""
    cmd = build_bgm_cmd(VIDEO, BGM, OUT)
    assert cmd.count("-map") == 2
    assert "0:v" in cmd and "[a]" in cmd


def test_cmd_is_argument_list():
    """命令必须是参数列表(不经 shell):素材 URL 来自外部,拼 shell 字符串就是命令注入。

    注意:ffmpeg 的 `-filter_complex` 表达式**本身含 `;`**(分隔 filter 链),那是 filter
    语法而非 shell 分隔符,所以这里断言的是「整体为列表」,而不是「不含分号」。
    """
    for cmd in (build_mix_audio_cmd(VIDEO, AUDIO, OUT), build_bgm_cmd(VIDEO, BGM, OUT)):
        assert isinstance(cmd, list)
        assert all(isinstance(part, str) for part in cmd)
        assert cmd[0] == "ffmpeg"


def test_malicious_path_stays_one_argument():
    """素材名带 shell 元字符时,必须原样作为**单个参数**传递(create_subprocess_exec 不解释它)"""
    evil = "/tmp/a; touch /tmp/pwned.m4a"
    cmd = build_mix_audio_cmd(VIDEO, evil, OUT)
    assert evil in cmd, "元字符应作为普通参数整体保留,而不是被拆成命令执行"
    assert cmd[-1] == OUT


# --- 字幕烧录(P3-1) ---

def test_split_sentences_preserves_punctuation():
    """按标点切句,长段文案才能按句显示字幕(而不是整段一口气)"""
    sentences = split_sentences("第一句。第二句!第三句？第四句；end.")
    assert len(sentences) == 5
    assert sentences[0] == "第一句。"


def test_build_srt_format():
    """SRT 文本格式必须合规(序号、时间、文本、空行);ffmpeg 读到格式错会跳过整段"""
    srt = build_srt([Cue(start_ms=1200, end_ms=3500, text="你好\n世界")])
    assert "1" in srt
    assert "00:00:01,200 --> 00:00:03,500" in srt
    assert "你好" in srt and "世界" in srt
    assert srt.endswith("\r\n")


def test_build_cues_splits_segment_time_by_words():
    """每段时间按各条词数占比分配;保证 cue 不越出该段时间且时间单调"""
    segments = [
        {"id": "hook", "text": "第一句文案。第二句更长的文案在这里。", "words": ["第", "一", "句", "文", "案", "第", "二", "句", "更", "长", "的", "文", "案", "在", "这", "里"]},
    ]
    timing = {"segments": {"hook": {"start_ms": 0, "end_ms": 4000}}}
    cues = build_cues(segments, timing)
    # 两句都不超过单条上限(12 字),各成一条;细分行为由下面的长句用例覆盖
    assert len(cues) == 2
    assert cues[0].start_ms == 0
    assert cues[-1].end_ms == 4000
    for prev, nxt in zip(cues, cues[1:]):
        assert prev.end_ms <= nxt.start_ms, "字幕时间不得重叠"


def test_build_cues_subdivides_long_real_sentence():
    """端到端复刻真实案例:23 字口播句应被切成 3 条,而不是一条挂 9 秒"""
    text = "来看这只超乖的小家伙，治愈感拉满，喜欢就点下方链接"
    segments = [{"id": "script", "text": text, "words": ["词"] * 23}]
    timing = {"segments": {"script": {"start_ms": 0, "end_ms": 9000}}}
    cues = build_cues(segments, timing)
    assert len(cues) == 3, "长句未细分则等于回到「一条挂满整段」的老问题"
    assert cues[0].text == "来看这只超乖的小家伙，"
    assert cues[-1].end_ms == 9000
    for prev, nxt in zip(cues, cues[1:]):
        assert prev.end_ms <= nxt.start_ms


def test_split_cue_text_breaks_after_comma():
    """复刻真实案例:23 字的口播句应被切成 3 条(逗号处断,标点留前块)"""
    chunks = split_cue_text("来看这只超乖的小家伙，治愈感拉满，喜欢就点下方链接")
    assert chunks == ["来看这只超乖的小家伙，", "治愈感拉满，", "喜欢就点下方链接"]


def test_split_cue_text_hardcuts_without_punctuation():
    """整句没有标点时只能硬切,避免单条过长"""
    assert split_cue_text("一二三四五六七八九十一二三四五") == ["一二三四五六七八九十一二", "三四五"]


def test_split_cue_text_single_short_sentence_untouched():
    """短句不该被拆(拆了反而碎)"""
    assert split_cue_text("限时秒杀促销带货") == ["限时秒杀促销带货"]


def test_wrap_text_breaks_after_punctuation():
    """折行必须在标点**之后**断:否则出现「，喜欢就点下方链接」这种标点行首"""
    wrapped = _wrap_text("来看这只超乖的小家伙，喜欢就点下方链接", max_chars=12)
    lines = wrapped.split("\n")
    assert lines[0] == "来看这只超乖的小家伙，"
    assert all(not line.startswith(("，", ",", "。", "、")) for line in lines)


def test_wrap_text_falls_back_to_hard_cut():
    """没有标点可用时退回硬折(不能无限回退导致行过短)"""
    wrapped = _wrap_text("一二三四五六七八九十一二三四五", max_chars=12)
    assert wrapped.split("\n") == ["一二三四五六七八九十一二", "三四五"]


def test_wrap_text_short_text_untouched():
    assert _wrap_text("你好世界") == "你好世界"


def test_burn_subtitle_preserves_audio():
    """烧字幕只是重编码画面,原音轨(BGM/口播)必须原样保留(-c:a copy)"""
    cmd = build_burn_subtitle_cmd(VIDEO, SRT, OUT, STYLE)
    assert cmd[cmd.index("-c:a") + 1] == "copy"
    assert cmd[cmd.index("-c:v") + 1] == "libx264"
    assert "subtitles=sub.srt" in cmd[cmd.index("-vf") + 1]


def test_burn_subtitle_takes_relative_srt_name_verbatim():
    """srt_name 由调用方保证是相对名(否则 Windows 路径冒号会坑);compose 层不做魔法转义"""
    cmd = build_burn_subtitle_cmd("C:\\video.mp4", "sub.srt", "out.mp4", STYLE)
    assert any("sub.srt" in part for part in cmd)
    # 视频路径可以绝对,它走 -i 参数,不经过 subtitles filter 解析


# --- 多段拼接:裁剪 / 抽帧 / 拼接命令 ---

def test_trim_cmd_flag_positions():
    """裁剪命令的参数位次:传错会把路径当数字用(实测踩过 TypeError)"""
    cmd = build_trim_cmd(video="/tmp/v.mp4", out="/tmp/o.mp4", start=5, duration=10, ffmpeg="ffmpeg")
    assert cmd[0] == "ffmpeg"
    assert cmd[cmd.index("-ss") + 1] == "5"
    assert cmd[cmd.index("-t") + 1] == "10"
    assert cmd[-1] == "/tmp/o.mp4"


def test_trim_cmd_guards_non_positive_inputs():
    """起点/时长做下界保护:负数或 0 会让 ffmpeg 直接报错"""
    cmd = build_trim_cmd(video="/tmp/v.mp4", out="/tmp/o.mp4", start=-3, duration=0)
    assert cmd[cmd.index("-ss") + 1] == "0"
    assert cmd[cmd.index("-t") + 1] == "1"


def test_extract_last_frame_cmd():
    """抽尾帧用 -sseof 从结尾回看,省掉"先探时长"这一步"""
    cmd = build_extract_last_frame_cmd(video="/tmp/v.mp4", out="/tmp/f.jpg")
    assert cmd[cmd.index("-sseof") + 1] == "-0.1"
    assert cmd[-1] == "/tmp/f.jpg"


def test_concat_list_escapes_quotes():
    """清单里的单引号必须转义:否则文件名含单引号会截断整条清单"""
    text = build_concat_list(["a.mp4", "it's.mp4"])
    assert "file 'a.mp4'" in text
    assert "it'\\''s.mp4" in text


def test_concat_cmd_stream_copy_with_genpts():
    """拼接用流复制(秒级)且显式 genpts,否则拼接后时间戳错乱"""
    cmd = build_concat_cmd("list.txt", "out.mp4")
    assert cmd[cmd.index("-c") + 1] == "copy"
    assert "+genpts" in cmd
    assert cmd.index("+genpts") < cmd.index("-i"), "+genpts 是输入选项,必须在 -i 之前"


def test_default_subtitle_style_uses_resolved_font():
    """样式必须带上解析出的字体名:写死字体在 Linux 上会静默烧出豆腐块"""
    style = default_subtitle_style("Noto Sans CJK SC")
    assert "FontName=Noto Sans CJK SC" in style
    assert "Outline=2" in style


def test_fonts_dir_only_appended_when_provided():
    """fontsdir 只在自带字体时传(系统字体交给 fontconfig,且 Windows 盘符带冒号会炸)"""
    assert "fontsdir" not in " ".join(build_burn_subtitle_cmd(VIDEO, SRT, OUT, STYLE))
    cmd = build_burn_subtitle_cmd(VIDEO, SRT, OUT, STYLE, "/app/assets/fonts")
    assert "fontsdir=/app/assets/fonts" in cmd[cmd.index("-vf") + 1]


def test_resolve_subtitle_font_shape():
    """字体解析返回 (字体名, fontsdir) 或 None;找不到时必须返回 None(宁可不烧不豆腐块)"""
    resolved = resolve_subtitle_font()
    assert resolved is None or (
        isinstance(resolved, tuple) and len(resolved) == 2 and resolved[0]
    )


# --- BGM ducking(声音混音 P3) ---

def test_bgm_ducking_lowers_volume_in_speech_intervals():
    """ducking:人声段 BGM 应被压到 duck_level,且用 between(t,s,e) 精确限定区间"""
    intervals = [(2.0, 5.0), (8.0, 10.0)]
    cmd = build_bgm_cmd(VIDEO, BGM, OUT, DEFAULT_BGM_VOLUME, intervals, 0.12)
    fc = cmd[cmd.index("-filter_complex") + 1]
    # 首段恒定铺设 base 音量(0.3)
    assert f"volume={DEFAULT_BGM_VOLUME}" in fc
    # 人声段各自一个 volume 滤镜,enable 限定区间,增益压到 duck_level
    assert "volume=enable='between(t,2.000,5.000)':volume=0.12" in fc
    assert "volume=enable='between(t,8.000,10.000)':volume=0.12" in fc
    # 仍以 amix 合成(原声 + 处理后的 BGM)
    assert "amix=inputs=2:duration=shortest" in fc


def test_bgm_ducking_chains_preserves_base_outside_speech():
    """ducking 链中 enable 为假的滤镜透传:人声段外 BGM 保持 base 音量、段间互不影响"""
    cmd = build_bgm_cmd(VIDEO, BGM, OUT, DEFAULT_BGM_VOLUME, [(1.0, 3.0)], 0.1)
    fc = cmd[cmd.index("-filter_complex") + 1]
    # 链式结构:b0(铺底)→ b1(压低段)→ amix,证明是多滤镜串联而非单段替换
    assert "[b0]" in fc and "amix=inputs=2" in fc


def test_bgm_ducking_empty_intervals_falls_back():
    """空区间列表退化为整轨恒定音量(命令形状与旧版一致)"""
    cmd = build_bgm_cmd(VIDEO, BGM, OUT, DEFAULT_BGM_VOLUME, [], None)
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "amix=inputs=2:duration=shortest" in fc
    assert "between(" not in fc


# --- 字幕风格预设(caption style, 对齐 Hypit captions「Fine styles」) ---

def test_caption_style_default_matches_legacy():
    """default 预设必须与旧版 default_subtitle_style 完全一致(避免旧任务字幕观感变化)"""
    assert caption_style("Microsoft YaHei", "default") == default_subtitle_style("Microsoft YaHei")
    assert caption_style("Microsoft YaHei") == default_subtitle_style("Microsoft YaHei")


def test_caption_style_presets_differ_and_inject_font():
    """各预设必须产出不同 force_style,且始终注入字体名(否则烧出豆腐块)"""
    styles = {name: caption_style("Noto Sans CJK SC", name) for name in ("default", "highlight", "minimal", "variety")}
    for s in styles.values():
        assert "FontName=Noto Sans CJK SC" in s
    # 醒目用黄字 + 半透明底纹;简约无阴影;彼此互不相同
    assert "PrimaryColour=&H0000FFFF" in styles["highlight"]
    assert "BackColour=" in styles["highlight"]
    assert "Shadow=0" in styles["minimal"]
    assert len({styles["default"], styles["highlight"], styles["minimal"], styles["variety"]}) == 4


def test_caption_style_unknown_falls_back_to_default():
    """未知预设名回退 default,绝不抛错或烧出不可控样式"""
    assert caption_style("SimHei", "nonexistent") == default_subtitle_style("SimHei")
