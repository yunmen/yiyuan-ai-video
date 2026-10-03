# -*- coding: utf-8 -*-
'''进程内计数指标:把"坏素材 / 降级 / 跳过"类事件累计成可观测的数字

为什么要它(实测 task 58/59 的教训):彩条成片、参考视频像素不足、字幕被跳过这类问题,
过去只以**一行日志**的形式存在 —— 偶发一次没人管,批量出现更没人知道(用户只会一个个来投诉)。
计数后,一条汇总日志就能看出"今天拦了多少废片、多少坏素材",从而区分
「单个用户的问题素材」与「某个网关/模型开始批量产出坏片」。

刻意做成**进程内计数 + 定期汇总日志**,不引入 Prometheus / Redis 等新依赖:
worker 是长驻单进程,重启即清零(汇总日志已落盘可回溯),够用且零运维成本。
若将来要跨进程聚合,只需替换本模块的 _emit 实现(接口不变)。
'''
import threading
import time
from typing import Dict, List, Tuple

from app.core.plugin import logger

# 汇总日志间隔(秒):太密会淹没业务日志,太疏又发现不了批量问题;10 分钟与人工巡检节奏匹配
FLUSH_INTERVAL = 600.0

_lock = threading.Lock()
# 指标名 → 累计次数
_counters: Dict[str, int] = {}
# 指标名 → 最近一次的事件说明(汇总时带上,便于判断是不是同一批素材)
_last_detail: Dict[str, str] = {}
_last_flush = time.monotonic()

# 需要重点关注的指标:汇总时排在前面并单独提示排查方向
KEY_METRICS = (
    "frame.degenerate_blocked",     # 检出退化画面(彩条/测试卡/纯色),已判失败退款
    "video.reference_pixels_blocked",  # 参考视频像素数低于模型门槛,提交前拦截
    "subtitle.skipped",             # 字幕未烧入成片
    "bgm.skipped",                  # 背景音乐未铺底
)


def incr(key: str, n: int = 1, detail: str = "") -> int:
    """计数 +1(或 +n),返回该指标当前累计值。

    detail 为本次事件的中文说明(如拦截原因),只在汇总日志里带最近一次 ——
    排查时看"最后一次为什么被拦"通常就够定位了。
    """
    global _last_flush
    with _lock:
        total = _counters.get(key, 0) + n
        _counters[key] = total
        if detail:
            _last_detail[key] = detail
        due = (time.monotonic() - _last_flush) >= FLUSH_INTERVAL
        snapshot = _snapshot_locked() if due else None
        if due:
            _last_flush = time.monotonic()
    # 单条事件日志带累计值:既能按 key 检索单条,也能看出"第几次"
    logger.info(f"[指标] {key} 累计={total}" + (f" 最近一次:{detail}" if detail else ""))
    if snapshot:
        _emit_summary(snapshot)
    return total


def _snapshot_locked() -> List[Tuple[str, int, str]]:
    """取当前全量快照(调用方须已持锁)"""
    return [(key, _counters[key], _last_detail.get(key, "")) for key in sorted(_counters)]


def snapshot() -> Dict[str, int]:
    """对外只读快照:便于脚本/排查时一次性取走全部计数"""
    with _lock:
        return dict(_counters)


def flush(force: bool = False) -> None:
    """打一条全量汇总日志(force=True 时忽略间隔,用于任务结束/排查时手动触发)"""
    global _last_flush
    with _lock:
        if not force and (time.monotonic() - _last_flush) < FLUSH_INTERVAL:
            return
        data = _snapshot_locked()
        _last_flush = time.monotonic()
    if data:
        _emit_summary(data)


def _emit_summary(data: List[Tuple[str, int, str]]) -> None:
    """汇总日志:重点指标排前,其余按名字排序;0 值不出现"""
    if not data:
        return
    focused = [item for item in data if item[0] in KEY_METRICS]
    others = [item for item in data if item[0] not in KEY_METRICS]
    lines = [f"{key}={count}" for key, count, _detail in focused + others]
    logger.info(f"[指标汇总] {', '.join(lines)}")
    # 重点指标非零时单独提示排查方向:这些数字变大通常意味着**批量**坏素材或网关异常
    for key, count, detail in focused:
        if count:
            logger.warning(
                f"[指标汇总] {key} 累计 {count} 次,建议排查是否出现批量问题"
                + (f"(最近一次:{detail})" if detail else "")
            )
