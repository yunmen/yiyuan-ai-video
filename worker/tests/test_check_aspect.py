# -*- coding: utf-8 -*-
"""成片画幅校验脚本:纯函数与批量判定

针对 product 硬要求「成片默认竖版 9:16」,这里钉死判定规则,
避免误判(把 3:4 当成 9:16、把横版放过)。
"""
import importlib.util
import tempfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_aspect.py"
_spec = importlib.util.spec_from_file_location("check_aspect", _SCRIPT)
ca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ca)


def test_parse_ratio_valid_and_invalid():
    assert ca.parse_ratio("9:16") == (9, 16)
    assert ca.parse_ratio("9：16") == (9, 16)   # 全角冒号也要认
    assert ca.parse_ratio("16:9") == (16, 9)
    assert ca.parse_ratio("abc") is None
    assert ca.parse_ratio("0:16") is None


def test_judge_accepts_vertical_9_16():
    """720x1280 / 1080x1920 / 1440x2560 都是标准 9:16"""
    for w, h in ((720, 1280), (1080, 1920), (1440, 2560)):
        r = ca.judge(w, h, (9, 16))
        assert r["ok"] is True, (w, h, r)
        assert r["orientation"] == "竖版"


def test_judge_rejects_landscape_and_square():
    assert ca.judge(1280, 720, (9, 16))["ok"] is False
    assert ca.judge(1280, 720, (9, 16))["orientation"] == "横版"
    square = ca.judge(1000, 1000, (9, 16))
    assert square["ok"] is False and square["orientation"] == "方形"


def test_judge_rejects_3_4_vertical():
    """同为竖版但 3:4(偏差 12.5%>3%),不能算通过 —— 这是最易误判的一类"""
    r = ca.judge(1080, 1440, (9, 16))
    assert r["ok"] is False
    assert r["orientation"] == "竖版"
    assert r["deviation_pct"] > ca.DEFAULT_TOLERANCE


def test_judge_respects_tolerance():
    """容忍度可调:792x1280 相对 9:16 偏差约 10% —— 默认 3% 不通过,放宽到 15% 通过"""
    assert ca.judge(792, 1280, (9, 16))["ok"] is False
    assert ca.judge(792, 1280, (9, 16), tolerance=15.0)["ok"] is True


def test_parse_list_file_supports_labels_and_comments():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fp:
        fp.write(
            "# 注释行\n\n"
            "https://cos/1.mp4\n"
            "i2v | https://cos/2.mp4\n"
            "edit | https://cos/3.mp4\n"
        )
        path = fp.name
    try:
        rows = ca.parse_list_file(path)
        assert rows == [
            ("-", "https://cos/1.mp4"),
            ("i2v", "https://cos/2.mp4"),
            ("edit", "https://cos/3.mp4"),
        ]
    finally:
        Path(path).unlink(missing_ok=True)


def test_check_all_counts_and_missing_entries(monkeypatch):
    """批量判定:通过/不通过计数正确,并给出未覆盖入口"""
    sizes = {
        "https://cos/a.mp4": (720, 1280),    # 9:16 通过
        "https://cos/b.mp4": (1280, 720),    # 横版 不通过
        "https://cos/broken.mp4": None,      # 读取失败
    }
    monkeypatch.setattr(ca, "probe_size", lambda binary, url, timeout=60: sizes.get(url))

    inputs = [
        ("t2v", "https://cos/a.mp4"),
        ("edit", "https://cos/b.mp4"),
        ("i2v", "https://cos/broken.mp4"),
    ]
    result = ca.check_all(inputs, (9, 16), ffprobe="ffprobe")
    assert result["total"] == 3
    assert result["passed"] == 1
    assert result["failed"] == 2
    # 已覆盖 t2v/edit/i2v,其余入口应出现在 missing 里
    assert set(result["covered_entries"]) == {"t2v", "edit", "i2v"}
    assert "digital" in result["missing_entries"]
