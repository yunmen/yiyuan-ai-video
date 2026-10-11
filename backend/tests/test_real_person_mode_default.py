# -*- coding: utf-8 -*-
"""真人素材处理策略(gen.image_real_person_mode)默认值跨端一致性测试。

背景:该配置此前存在三处默认值不一致 ———
    backend/app/services/system_config.py 的 DEFAULT_CONFIGS  = "drop"
    worker/app/settings.py 的 IMAGE_REAL_PERSON_MODE            = "stylize"
    worker/app/tools/video_tool.py 的注释                        = "系统默认已为 stylize"
而运行期真正生效的是**后台配置表的值**,非法/未配置时才回退各侧默认值。
一旦数据库里存的是 drop(或为空回退 drop),拟态化分支会被跳过,人物参考图被**整张丢弃**,
只留文字描述喂给模型 —— 成片主角很可能还是原片那个人,而用户完全看不出发生了什么
("我传了自己的照片,怎么还是原来那个人")。

注意:DEFAULT_CONFIGS 只在配置表为空时初始化,**已存在的库改这里不会生效**,
所以本测试锁的是"代码默认值一致",线上仍需运营手工把该配置项改成 stylize(见交付说明)。
"""
import re
from pathlib import Path

import pytest

from app.services.generate_task import _detect_missing
from app.services.system_config import DEFAULT_CONFIGS

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = BACKEND_ROOT.parent / "worker"

CFG_KEY = "gen.image_real_person_mode"
# 唯一正确的默认值:拟态化(保住"有这个人、长这样"的替换目标)
EXPECTED = "stylize"


def _cfg_default() -> str:
    """从 DEFAULT_CONFIGS 取该配置项的默认值"""
    for item in DEFAULT_CONFIGS:
        if item.get("key") == CFG_KEY:
            return str(item.get("value") or "").strip()
    pytest.fail(f"DEFAULT_CONFIGS 中缺少配置项 {CFG_KEY}")


def _worker_settings_default() -> str:
    """从 worker/app/settings.py 解析 IMAGE_REAL_PERSON_MODE 的默认值(源码级,避免跨进程 import)"""
    path = WORKER_ROOT / "app" / "settings.py"
    if not path.exists():
        pytest.skip(f"未找到 worker 源码({path}),跳过跨端默认值校验")
    match = re.search(
        r'IMAGE_REAL_PERSON_MODE\s*:\s*str\s*=\s*"([^"]*)"',
        path.read_text(encoding="utf-8"),
    )
    assert match, "worker/app/settings.py 中未找到 IMAGE_REAL_PERSON_MODE 默认值"
    return match.group(1).strip()


def test_backend_default_is_stylize():
    """backend 侧默认值必须是 stylize(原为 drop,会导致人物图被丢弃)"""
    assert _cfg_default() == EXPECTED


def test_worker_default_matches_backend():
    """worker 侧默认值必须与 backend 一致,否则配置下发失败时两端行为分叉"""
    assert _worker_settings_default() == _cfg_default()


def test_detect_missing_fallback_not_drop():
    """未传策略时(读库失败/无缓存)不得按 drop 处理:person 意图不该被误判为"真人做不了"

    _detect_missing 是纯函数,直接以 real_person_mode="" 模拟"未读到配置"的兜底路径。
    """
    missing = _detect_missing(["/s/person.jpg", "/s/ref.mp4"], ["person"], real_person_mode="")
    fields = {m["field"] for m in missing}
    assert "real_person_unsupported" not in fields, (
        "未读到配置时按 drop 处理会误报「真人照片做不了换人物」,与 stylize 默认值不一致"
    )


def test_detect_missing_still_warns_when_explicitly_drop():
    """回归:运营显式配成 drop 时,仍须给出真人照片提示(不能被本次改动一并关掉)"""
    missing = _detect_missing(
        ["/s/person.jpg", "/s/ref.mp4"], ["person"], real_person_mode="drop"
    )
    assert "real_person_unsupported" in {m["field"] for m in missing}
