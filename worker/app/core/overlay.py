# -*- coding: utf-8 -*-
'''
@文件    :overlay.py
@说明    :代码渲染层(零模型成本)——对标 Hypit 的「纯代码渲染字幕/图形/MG」。
           把设计 spec(字幕/信息卡/角标)用 PIL 画成透明叠加轨道,再叠到成片之上,
           替代/增强原先纯 ffmpeg 烧录的平铺字幕。

           设计前提:
             ① 零模型成本 —— 只调 ffmpeg 与 PIL,不调任何生成模型(与 Hypit 的
                "零成本渲染"思想一致):动态排版、信息卡、角标都是代码画出来的。
             ② 任何环节失败一律返回 None,调用方保留原片(已付费的成片不能被
                "加一层叠加"弄丢,与 subtitle.py 的容错原则一致)。
             ③ 渲染器可插拔 —— 当前默认 PIL(纯 Python,必可用);若容器装有
                无头 Chromium/Playwright,未来可加 _render_html 走 HTML/CSS 动画,
                接口不变(对齐 Hypit 的"模型/渲染器可插拔")。

           元素类型(对应 Hypit captions / lower-thirds / badge):
             - caption:动态排版字幕(圆角半透明底 + 描边文字 + 入场/退场动画)
             - card   :信息卡/下三分之一(标题 + 正文 + 强调色条)
             - badge  :角标(胶囊标签,如品牌/卖点/水印)
'''
from __future__ import annotations

import asyncio
import math
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core import compose
from app.core.plugin import logger
from app.utils.oss import download_to_local, upload_local_file

# 叠加轨道渲染帧率上限与总帧数上限:纯 Python 逐帧绘制,过长视频降帧以控耗时
_OVERLAY_MAX_FPS = 25
_OVERLAY_MIN_FPS = 12
_OVERLAY_MAX_FRAMES = 2400

# 入场/退场动画时长(毫秒):字幕"滑入 + 淡入"与"淡出"的过渡窗口
_ANIM_IN_MS = 240
_ANIM_OUT_MS = 200

# 字幕单行最大字数(优先在标点后折行)
_CAPTION_MAX_LINE_CHARS = 16
# 字幕最多显示行数(超出截断,避免占满屏)
_CAPTION_MAX_LINES = 2

# 元素配色(AARRGGBB 的 RGBA 元组,0~255):深色半透明底 + 白字,高对比通用方案
_PILL_BG = (0, 0, 0, 150)          # 字幕圆角底:半透明黑
_PILL_BG_HILITE = (60, 40, 0, 170) # 醒目字幕底:深橙半透明
_CARD_BG = (10, 12, 20, 210)       # 信息卡底:近黑半透明
_BADGE_BG = (24, 160, 88, 230)     # 角标底:品牌绿
_TEXT_WHITE = (255, 255, 255, 255)
_TEXT_HILITE = (255, 220, 60, 255)
_OUTLINE = (0, 0, 0, 255)
_ACCENT = (24, 160, 88, 255)       # 强调色:品牌绿

# 字幕样式预设:与 compose._CAPTION_PRESETS 视觉一致,供代码渲染复用
_CAPTION_PRESETS = {
    "default":  {"pill": _PILL_BG, "text": _TEXT_WHITE, "outline_w": 2},
    "highlight": {"pill": _PILL_BG_HILITE, "text": _TEXT_HILITE, "outline_w": 2},
    "minimal":  {"pill": (0, 0, 0, 110), "text": _TEXT_WHITE, "outline_w": 1},
    "variety":  {"pill": (0, 80, 30, 170), "text": _TEXT_WHITE, "outline_w": 2},
}

# 动效组件常量(对齐 Hypit 的 ranking/reveal/flash/sticker 动效信息层)
_RANK_ROW_ANIM_MS = 360       # 排行榜逐条落位动画时长(ms)
_REVEAL_ANIM_MS = 420         # 揭示板弹出动画时长(ms)
_STICKER_ANIM_MS = 320        # 评论贴纸滑入/滑出动画时长(ms)
_FLASH_PEAK = 0.5             # 彩色闪烁峰值不透明度(避免盖死画面)
_STICKER_DEF_DUR = 2500       # 评论贴纸默认停留时长(ms)


def _parse_color(c: Any, default: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """把 #RGB / #RRGGBB / #RRGGBBAA 解析为 RGBA 元组;解析失败回退默认(不抛异常)"""
    if not c or not isinstance(c, str):
        return default
    s = c.strip().lstrip("#")
    try:
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
        if len(s) == 8:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
    except Exception:  # noqa: BLE001
        pass
    return default


def _try_pil():
    """延迟导入 PIL(仅当真正需要绘制时才 import),避免没有 Pillow 时整模块加载失败。"""
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
        return Image, ImageDraw, ImageFont
    except Exception:  # noqa: BLE001
        return None


def _smoothstep(t: float) -> float:
    """平滑插值(用于入场/退场动画的缓动)"""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _wrap_line(text: str, max_chars: int = _CAPTION_MAX_LINE_CHARS) -> List[str]:
    """按字数折行,优先在标点后断开(与 compose._wrap_text 同思路,供 PIL 用)

    纯文本无标点且超长时硬切;返回最多 _CAPTION_MAX_LINES 行,超出截断。
    """
    if len(text) <= max_chars:
        return [text]
    lines: List[str] = []
    rest = text
    while len(rest) > max_chars:
        window = rest[:max_chars]
        cut = 0
        for i in range(len(window) - 1, -1, -1):
            if window[i] in "，,、：:；;。！？!?":
                cut = i + 1
                break
        if cut < max_chars // 2:
            cut = max_chars
        lines.append(rest[:cut])
        rest = rest[cut:]
        if len(lines) >= _CAPTION_MAX_LINES - 1:
            break
    if rest:
        lines.append(rest)
    if len(lines) > _CAPTION_MAX_LINES:
        lines = lines[:_CAPTION_MAX_LINES]
        # 末行超出时以省略号收尾,避免字被直接截断
        last = lines[-1]
        lines[-1] = last[: max(1, _CAPTION_MAX_LINE_CHARS - 1)] + "…"
    return lines


# 字体缓存:(字体路径, 字号) → PIL 字体对象。逐帧绘制若每帧每元素都重新 truetype 加载,
# 长视频会重复上千次,缓存后基本零成本(同一字号只加载一次)。
_FONT_CACHE: Dict[Tuple[str, int], Any] = {}


def _load_font(font_path: Optional[str], size: int):
    """按字体文件加载 PIL 字体;失败返回 None(调用方跳过绘制)。结果按(路径,字号)缓存。"""
    if not font_path:
        return None
    key = (font_path, int(size))
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(font_path, size)
        _FONT_CACHE[key] = font
        return font
    except Exception:  # noqa: BLE001
        _FONT_CACHE[key] = None
        return None


def _draw_text_outline(draw, xy, text, font, fill, outline, outline_w, anchor="mm"):
    """带描边的文字绘制(8 方向偏移近似描边,比逐像素便宜)

    anchor="mm" 表示 xy 为文字中心;pill 定位据此计算。
    """
    if outline_w and outline:
        offs = max(1, int(outline_w))
        for dx, dy in (
            (-offs, 0), (offs, 0), (0, -offs), (0, offs),
            (-offs, -offs), (offs, -offs), (-offs, offs), (offs, offs),
        ):
            draw.text((xy[0] + dx, xy[1] + dy), text, font=font, fill=outline, anchor=anchor)
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def _rounded_rect(draw, box, radius, fill):
    """画圆角矩形(PIL 无原生 rounded_rect 的老版本兼容写法)"""
    try:
        draw.rounded_rectangle(box, radius=radius, fill=fill)
    except Exception:  # noqa: BLE001
        draw.rectangle(box, fill=fill)


def _draw_circle(draw, cx, cy, r, fill):
    """画实心圆(名次圆 / 评论贴纸头像底色)"""
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)


def _draw_caption(draw, elem: Dict[str, Any], t_ms: float, font, font_path: str):
    """绘制一条动态字幕(圆角底 + 描边文字 + 入场/退场动画)

    入场:窗口前 _ANIM_IN_MS 内淡入 + 上滑;退场:窗口末 _ANIM_OUT_MS 内淡出。
    位置:带 pos(头部跟随)时锚定头部上沿上方居中;否则底部居中。
    """
    start = float(elem.get("start_ms") or 0)
    end = float(elem.get("end_ms") or start)
    if t_ms < start or t_ms > end:
        return
    style_name = (elem.get("style") or {}).get("preset") or "default"
    preset = _CAPTION_PRESETS.get(style_name.lower(), _CAPTION_PRESETS["default"])
    text = str(elem.get("text") or "").strip()
    if not text:
        return
    lines = _wrap_line(text)
    # 字号:高清画布下按比例放大(以 1080 高为基准 30px),避免大屏字太小
    canvas = elem.get("_canvas") or (1080, 1920)
    base_size = int(30 * canvas[1] / 1080.0)
    fnt = _load_font(font_path, base_size) or font
    line_h = int(base_size * 1.35)
    pad_x = int(base_size * 0.6)
    pad_y = int(base_size * 0.4)
    # 计算整块尺寸(取最宽行)
    widths = []
    for ln in lines:
        bbox = fnt.getbbox(ln) if fnt else (0, 0, len(ln) * base_size, base_size)
        widths.append(bbox[2] - bbox[0])
    block_w = max(widths) + pad_x * 2
    block_h = line_h * len(lines) + pad_y * 2

    # 锚点坐标(块中心)
    pos = elem.get("pos")
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        cx = max(block_w / 2, min(canvas[0] - block_w / 2, pos[0] * canvas[0]))
        cy = max(block_h / 2, min(canvas[1] - block_h / 2, pos[1] * canvas[1]))
        cy -= int(canvas[1] * 0.06)  # 字幕落在头部上方一点
    else:
        cx = canvas[0] / 2.0
        cy = canvas[1] - block_h / 2 - int(canvas[1] * 0.05)

    # 动画:入场淡入+上滑,退场淡出
    alpha = 1.0
    slide = 0.0
    in_p = (t_ms - start) / _ANIM_IN_MS
    if in_p < 1.0:
        s = _smoothstep(in_p)
        alpha *= s
        slide = (1.0 - s) * (base_size * 0.8)
    out_p = (end - t_ms) / _ANIM_OUT_MS
    if 0.0 <= out_p < 1.0:
        alpha *= _smoothstep(out_p)

    box = (cx - block_w / 2, cy - block_h / 2 + slide, cx + block_w / 2, cy + block_h / 2 + slide)
    pill = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate(preset["pill"]))
    _rounded_rect(draw, box, radius=min(box[3] - box[1], base_size), fill=pill)
    # 逐行绘制文字(中心对齐)
    total_h = line_h * len(lines)
    start_y = cy - total_h / 2 + slide
    for i, ln in enumerate(lines):
        ly = start_y + i * line_h + line_h / 2.0
        fill = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate(preset["text"]))
        outl = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate(_OUTLINE))
        _draw_text_outline(draw, (cx, ly), ln, fnt, fill, outl, preset["outline_w"], anchor="mm")


def _draw_card(draw, elem: Dict[str, Any], t_ms: float, font, font_path: str):
    """绘制信息卡/下三分之一(标题 + 正文 + 强调色条 + 淡入)"""
    start = float(elem.get("start_ms") or 0)
    end = float(elem.get("end_ms") or start)
    if t_ms < start or t_ms > end:
        return
    canvas = elem.get("_canvas") or (1080, 1920)
    corner = (elem.get("pos") or {}).get("corner") or "bl"
    margin = int((elem.get("pos") or {}).get("margin", 40))
    title = str(elem.get("title") or "").strip()
    body = str(elem.get("body") or "").strip()
    if not (title or body):
        return
    # 字号随画布缩放(以 1080 高为基准)
    scale = canvas[1] / 1080.0
    title_size = int(34 * scale)
    body_size = int(24 * scale)
    title_fnt = _load_font(font_path, title_size)
    body_fnt = _load_font(font_path, body_size)
    pad = int(28 * scale)
    bar_w = int(10 * scale)
    # 文字尺寸
    max_w = int(canvas[0] * 0.62)
    title_lines = _wrap_line(title, max_chars=12) if title else []
    body_lines = _wrap_line(body, max_chars=16) if body else []
    tw = 0
    if title_fnt:
        for ln in title_lines:
            tw = max(tw, (title_fnt.getbbox(ln) or (0, 0, len(ln) * title_size, 0))[2])
    if body_fnt:
        for ln in body_lines:
            tw = max(tw, (body_fnt.getbbox(ln) or (0, 0, len(ln) * body_size, 0))[2])
    tw = min(tw, max_w)
    block_w = tw + pad * 2 + bar_w
    title_h = title_size * 1.3 * len(title_lines) if title_lines else 0
    body_h = body_size * 1.35 * len(body_lines) if body_lines else 0
    gap = int(12 * scale) if (title_lines and body_lines) else 0
    block_h = title_h + body_h + gap + pad * 2
    # 角标定位
    if corner in ("tl", "tr"):
        x0 = (canvas[0] - block_w - margin) if corner == "tr" else margin
        y0 = margin
    else:
        x0 = (canvas[0] - block_w - margin) if corner == "br" else margin
        y0 = canvas[1] - block_h - margin
    # 淡入
    alpha = _smoothstep((t_ms - start) / _ANIM_IN_MS)
    box = (x0, y0, x0 + block_w, y0 + block_h)
    bg = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate(_CARD_BG))
    _rounded_rect(draw, box, radius=int(16 * scale), fill=bg)
    # 强调色条
    _rounded_rect(draw, (x0, y0, x0 + bar_w, y0 + block_h), radius=0, fill=_ACCENT)
    tx = x0 + bar_w + pad
    ty = y0 + pad
    if title_fnt:
        for ln in title_lines:
            fill = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate(_TEXT_WHITE))
            draw.text((tx, ty), ln, font=title_fnt, fill=fill)
            ty += title_size * 1.3
    ty += gap
    if body_fnt:
        for ln in body_lines:
            fill = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate((200, 210, 220, 255)))
            draw.text((tx, ty), ln, font=body_fnt, fill=fill)
            ty += body_size * 1.35


def _draw_badge(draw, elem: Dict[str, Any], t_ms: float, font, font_path: str):
    """绘制角标(胶囊标签,如品牌/卖点/水印)"""
    start = float(elem.get("start_ms") or 0)
    end = float(elem.get("end_ms") or start)
    if t_ms < start or t_ms > end:
        return
    canvas = elem.get("_canvas") or (1080, 1920)
    corner = (elem.get("pos") or {}).get("corner") or "tr"
    margin = int((elem.get("pos") or {}).get("margin", 36))
    text = str(elem.get("text") or "").strip()
    if not text:
        return
    scale = canvas[1] / 1080.0
    size = int(26 * scale)
    fnt = _load_font(font_path, size)
    bbox = fnt.getbbox(text) if fnt else (0, 0, len(text) * size, size)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x = int(22 * scale)
    pad_y = int(12 * scale)
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    if corner in ("tl", "tr"):
        x0 = (canvas[0] - bw - margin) if corner == "tr" else margin
        y0 = margin
    else:
        x0 = (canvas[0] - bw - margin) if corner == "br" else margin
        y0 = canvas[1] - bh - margin
    alpha = _smoothstep((t_ms - start) / _ANIM_IN_MS)
    box = (x0, y0, x0 + bw, y0 + bh)
    bg = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate(_BADGE_BG))
    _rounded_rect(draw, box, radius=bh // 2, fill=bg)
    fill = tuple(int(c * alpha) if i == 3 else c for i, c in enumerate(_TEXT_WHITE))
    draw.text((x0 + bw / 2, y0 + bh / 2), text, font=fnt, fill=fill, anchor="mm")


def _draw_ranking(draw, elem: Dict[str, Any], t_ms: float, font, font_path: str):
    """绘制排行榜(对齐 Hypit「榜单随音效逐条落位」):标题 + 多条目,逐条滑入淡入。

    每条目在 start_ms + i*stagger_ms 出现,带轻微上滑 + 淡入;整块停留在 end_ms。
    仅当 params.overlay_ranking 显式提供 items 时才进入 design_spec,绝不臆造内容。
    """
    start = float(elem.get("start_ms") or 0)
    end = float(elem.get("end_ms") or start)
    if t_ms < start or t_ms > end:
        return
    canvas = elem.get("_canvas") or (1080, 1920)
    scale = canvas[1] / 1080.0
    corner = (elem.get("corner") or "bl")
    items = elem.get("items") or []
    if not items:
        return
    title = str(elem.get("title") or "").strip()
    stagger = max(80, int(elem.get("stagger_ms") or 500))
    pad = int(22 * scale)
    title_size = int(30 * scale)
    row_size = int(26 * scale)
    row_h = int(row_size * 1.7)
    bar_w = int(8 * scale)
    tf = _load_font(font_path, row_size)
    max_label = 0
    for it in items:
        lb = str((it or {}).get("label") or "")
        if tf:
            max_label = max(max_label, (tf.getbbox(lb) or (0, 0, len(lb) * row_size, 0))[2])
    panel_w = int(min(canvas[0] * 0.62, max_label + int(220 * scale) + pad * 2 + bar_w))
    title_h = (title_size * 1.4) if title else 0
    panel_h = title_h + row_h * len(items) + pad * 2
    margin = int(40 * scale)
    if corner in ("tl", "tr"):
        x0 = (canvas[0] - panel_w - margin) if corner == "tr" else margin
        y0 = margin
    else:
        x0 = (canvas[0] - panel_w - margin) if corner == "br" else margin
        y0 = canvas[1] - panel_h - margin
    # 面板底 + 强调色条
    _rounded_rect(draw, (x0, y0, x0 + panel_w, y0 + panel_h), radius=int(16 * scale),
                  fill=(10, 12, 20, 215))
    _rounded_rect(draw, (x0, y0, x0 + bar_w, y0 + panel_h), radius=0, fill=_ACCENT)
    ty = y0 + pad
    if title and title_h:
        tf2 = _load_font(font_path, title_size)
        draw.text((x0 + bar_w + pad, ty), title, font=tf2, fill=(255, 255, 255, 255))
        ty += title_h
    for i, it in enumerate(items):
        it = it or {}
        appear = start + i * stagger
        p = (t_ms - appear) / _RANK_ROW_ANIM_MS
        if p < 0:
            continue
        a = _smoothstep(p) if p < 1 else 1.0
        slide = (1.0 - _smoothstep(p)) * row_h * 0.5 if p < 1 else 0.0
        ry = ty + i * row_h - slide
        # 行底(逐条淡入)
        row_bg = tuple(int(c * a) if idx == 3 else c for idx, c in enumerate((30, 34, 46, 230)))
        _rounded_rect(draw, (x0 + bar_w + pad, ry, x0 + panel_w - pad, ry + row_h - int(8 * scale)),
                      radius=int(10 * scale), fill=row_bg)
        # 名次圆(第一名用强调色突出)
        cx = x0 + bar_w + pad + int(26 * scale)
        cyc = ry + row_h / 2 - int(4 * scale)
        _draw_circle(draw, cx, cyc, int(18 * scale),
                     _ACCENT if i == 0 else (90, 100, 120, 255))
        rank_f = _load_font(font_path, int(22 * scale))
        if rank_f:
            draw.text((cx, cyc), str(i + 1), font=rank_f, fill=(255, 255, 255, int(255 * a)), anchor="mm")
        # 标签(左) + 值(右对齐,醒目色)
        lb = str(it.get("label") or "")
        vb = str(it.get("value") or "")
        if tf:
            draw.text((cx + int(34 * scale), ry + row_h / 2 - int(4 * scale)), lb, font=tf,
                      fill=(255, 255, 255, int(255 * a)), anchor="lm")
            vbw = (tf.getbbox(vb) or (0, 0, len(vb) * row_size, 0))[2]
            draw.text((x0 + panel_w - pad - vbw, ry + row_h / 2 - int(4 * scale)), vb, font=tf,
                      fill=(255, 220, 60, int(255 * a)), anchor="lm")


def _draw_reveal(draw, elem: Dict[str, Any], t_ms: float, font, font_path: str):
    """绘制揭示板(对齐 Hypit「表情符号揭示板」):at_ms 处 emoji + 文案弹出,带缩放与淡入。

    仅当 params.overlay_reveal 显式提供 text 时才进入 design_spec。emoji 受字体支持度限制,
    渲染不出时静默跳过(仍保留文案与背后色爆),不影响成片。
    """
    at = float(elem.get("at_ms") or 0)
    dur = max(600, int(elem.get("duration_ms") or 1800))
    if t_ms < at or t_ms > at + dur:
        return
    canvas = elem.get("_canvas") or (1080, 1920)
    scale = canvas[1] / 1080.0
    corner = (elem.get("corner") or "br")
    text = str(elem.get("text") or "").strip()
    emoji = str(elem.get("emoji") or "✨").strip()
    # 入场:由大缩小到 1 并淡入
    p = (t_ms - at) / _REVEAL_ANIM_MS
    if p < 1:
        a = _smoothstep(p)
        s = 1.0 + 0.5 * (1.0 - _smoothstep(p))
    else:
        a = 1.0
        s = 1.0
    # 退场:最后 300ms 淡出
    remain = at + dur - t_ms
    if remain < 300:
        a *= max(0.0, remain / 300.0)
    # 锚点(靠近 corner 的居中爆点)
    base = int(280 * scale)
    if corner in ("tl", "tr"):
        bx = (canvas[0] - base) if corner == "tr" else base
        by = int(260 * scale)
    else:
        bx = (canvas[0] - base) if corner == "br" else base
        by = canvas[1] - int(260 * scale)
    # 背后色爆(随缩放进退)
    burst_r = int(90 * scale * s)
    burst = tuple(int(c * a * 0.85) if i == 3 else c for i, c in enumerate((255, 220, 60, 255)))
    _draw_circle(draw, bx, by, burst_r, burst)
    # emoji(大字,尽力渲染)
    emoji_f = _load_font(font_path, int(70 * scale * s))
    if emoji_f:
        draw.text((bx, by), emoji, font=emoji_f, fill=(255, 255, 255, int(255 * a)), anchor="mm")
    # 文案(emoji 下方)
    tf = _load_font(font_path, int(34 * scale))
    if tf and text:
        tw = (tf.getbbox(text) or (0, 0, len(text) * 34 * scale, 0))[2]
        draw.text((bx - tw / 2, by + burst_r + int(10 * scale)), text, font=tf,
                  fill=(255, 255, 255, int(255 * a)))


def _draw_flash(draw, elem: Dict[str, Any], t_ms: float, font, font_path: str):
    """绘制彩色闪烁(对齐 Hypit「彩色闪烁」):at_ms 处全屏色闪,sin 包络淡入淡出。

    峰值不透明度受 _FLASH_PEAK 限制,避免盖死画面。仅当 params.overlay_flash 显式提供才进入。
    """
    at = float(elem.get("at_ms") or 0)
    dur = max(120, int(elem.get("duration_ms") or 400))
    if t_ms < at or t_ms > at + dur:
        return
    canvas = elem.get("_canvas") or (1080, 1920)
    color = _parse_color(elem.get("color"), (255, 212, 0, 255))
    p = (t_ms - at) / dur
    a = _FLASH_PEAK * math.sin(math.pi * max(0.0, min(1.0, p)))
    if a <= 0.001:
        return
    fill = tuple(int(c * a) if i == 3 else c for i, c in enumerate(color))
    draw.rectangle((0, 0, canvas[0], canvas[1]), fill=fill)


def _draw_sticker(draw, elem: Dict[str, Any], t_ms: float, font, font_path: str):
    """绘制评论贴纸(对齐 Hypit「评论区贴纸」):从侧边滑入的聊天气泡,停留后滑出。

    仅当 params.overlay_sticker 显式提供 text 时才进入 design_spec。
    """
    at = float(elem.get("at_ms") or 0)
    dur = max(800, int(elem.get("duration_ms") or _STICKER_DEF_DUR))
    if t_ms < at or t_ms > at + dur:
        return
    canvas = elem.get("_canvas") or (1080, 1920)
    scale = canvas[1] / 1080.0
    side = (elem.get("side") or "l")
    text = str(elem.get("text") or "").strip()
    if not text:
        return
    # 进场/出场偏移(滑入滑出)
    p_in = (t_ms - at) / _STICKER_ANIM_MS
    p_out = (at + dur - t_ms) / _STICKER_ANIM_MS
    if p_in < 1:
        a = _smoothstep(p_in)
        off = (1.0 - _smoothstep(p_in)) * int(120 * scale)
    elif p_out < 1:
        a = _smoothstep(p_out)
        off = (1.0 - _smoothstep(p_out)) * int(120 * scale)
    else:
        a = 1.0
        off = 0.0
    size = int(26 * scale)
    tf = _load_font(font_path, size)
    pad_x = int(24 * scale)
    pad_y = int(14 * scale)
    av_r = int(26 * scale)
    bubble_pad_left = av_r * 2 + int(16 * scale)
    tw = 0
    if tf:
        tw = (tf.getbbox(text) or (0, 0, len(text) * size, 0))[2]
    tw = min(tw, int(canvas[0] * 0.6))
    bh = size + pad_y * 2
    bw = bubble_pad_left + tw + pad_x
    margin = int(40 * scale)
    x0 = (canvas[0] - bw - margin + off) if side == "r" else (margin - off)
    y0 = int(canvas[1] * 0.30)  # 靠上 1/3,避开字幕区
    # 气泡
    bubble = tuple(int(c * a) if i == 3 else c for i, c in enumerate((255, 255, 255, 245)))
    _rounded_rect(draw, (x0, y0, x0 + bw, y0 + bh), radius=bh // 2, fill=bubble)
    # 头像圆(可配 avatar_color)
    av_color = _parse_color(elem.get("avatar_color"), _ACCENT)
    av_fill = tuple(int(c * a) if i == 3 else c for i, c in enumerate(av_color))
    _draw_circle(draw, x0 + av_r + int(8 * scale), y0 + bh / 2, av_r, av_fill)
    if tf:
        draw.text((x0 + bubble_pad_left, y0 + bh / 2), text, font=tf,
                  fill=(20, 24, 34, int(255 * a)), anchor="lm")


# 元素类型 → 绘制函数(在 caption/card/badge 基础上补 Hypit 式动效层)
_DRAWERS = {
    "caption": _draw_caption,
    "card": _draw_card,
    "badge": _draw_badge,
    "ranking": _draw_ranking,
    "reveal": _draw_reveal,
    "flash": _draw_flash,
    "sticker": _draw_sticker,
}


def build_design_spec(
    cues: List[Any], params: Dict[str, Any], canvas: Optional[Tuple[int, int]] = None,
) -> Optional[Dict[str, Any]]:
    """把字幕 cue + 业务参数转成设计 spec(供代码渲染层消费)

    ① caption:逐条 cue 转为动态字幕(携带 pos 实现头部跟随);
    ② card  :仅当 params.overlay_card 显式提供 {title,body,corner} 才加,绝不臆造商品信息;
    ③ badge :仅当 params.overlay_badge 显式提供 {text,corner} 才加。

    返回 None 表示无需叠加(如没有任何字幕且未提供卡/标),调用方跳过渲染。
    """
    if not canvas or len(canvas) != 2:
        return None
    elements: List[Dict[str, Any]] = []
    for c in cues or []:
        text = getattr(c, "text", None) or (c.get("text") if isinstance(c, dict) else None)
        if not text:
            continue
        start_ms = int(getattr(c, "start_ms", 0) or (c.get("start_ms") if isinstance(c, dict) else 0) or 0)
        end_ms = int(getattr(c, "end_ms", 0) or (c.get("end_ms") if isinstance(c, dict) else 0) or 0)
        pos = getattr(c, "pos", None) or (c.get("pos") if isinstance(c, dict) else None)
        elements.append({
            "type": "caption",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": text,
            "style": {"preset": params.get("caption_style") or "default"},
            "pos": list(pos) if pos else None,
        })
    card = params.get("overlay_card") or {}
    if isinstance(card, dict) and (card.get("title") or card.get("body")):
        elements.append({
            "type": "card",
            "start_ms": int(card.get("start_ms", 0) or 0),
            "end_ms": int(card.get("end_ms", 9_999_999) or 9_999_999),
            "title": str(card.get("title") or ""),
            "body": str(card.get("body") or ""),
            "pos": {"corner": card.get("corner") or "bl", "margin": int(card.get("margin", 40) or 40)},
        })
    badge = params.get("overlay_badge") or {}
    if isinstance(badge, dict) and badge.get("text"):
        elements.append({
            "type": "badge",
            "start_ms": int(badge.get("start_ms", 0) or 0),
            "end_ms": int(badge.get("end_ms", 9_999_999) or 9_999_999),
            "text": str(badge.get("text") or ""),
            "pos": {"corner": badge.get("corner") or "tr", "margin": int(badge.get("margin", 36) or 36)},
        })
    # ④ ranking:仅当 params.overlay_ranking 显式提供 items 才加(对齐 Hypit 榜单逐条落位)
    ranking = params.get("overlay_ranking") or {}
    if isinstance(ranking, dict):
        items = ranking.get("items") or []
        if items:
            elements.append({
                "type": "ranking",
                "start_ms": int(ranking.get("start_ms", 0) or 0),
                "end_ms": int(ranking.get("end_ms", 9_999_999) or 9_999_999),
                "title": str(ranking.get("title") or ""),
                "items": [{"label": str((it or {}).get("label") or ""),
                           "value": str((it or {}).get("value") or "")} for it in items],
                "corner": ranking.get("corner") or "bl",
                "stagger_ms": int(ranking.get("stagger_ms", 500) or 500),
            })
    # ⑤ reveal:仅当 params.overlay_reveal 显式提供 text 才加(对齐 Hypit 表情符号揭示板)
    reveal = params.get("overlay_reveal") or {}
    if isinstance(reveal, dict) and reveal.get("text"):
        elements.append({
            "type": "reveal",
            "at_ms": int(reveal.get("at_ms", 0) or 0),
            "duration_ms": int(reveal.get("duration_ms", 1800) or 1800),
            "text": str(reveal.get("text") or ""),
            "emoji": str(reveal.get("emoji") or "✨"),
            "corner": reveal.get("corner") or "br",
        })
    # ⑥ flash:仅当 params.overlay_flash 显式提供 color 才加(对齐 Hypit 彩色闪烁)
    flash = params.get("overlay_flash") or {}
    if isinstance(flash, dict) and flash.get("color"):
        elements.append({
            "type": "flash",
            "at_ms": int(flash.get("at_ms", 0) or 0),
            "duration_ms": int(flash.get("duration_ms", 400) or 400),
            "color": str(flash.get("color") or "#FFD400"),
        })
    # ⑦ sticker:仅当 params.overlay_sticker 显式提供 text 才加(对齐 Hypit 评论区贴纸)
    sticker = params.get("overlay_sticker") or {}
    if isinstance(sticker, dict) and sticker.get("text"):
        elements.append({
            "type": "sticker",
            "at_ms": int(sticker.get("at_ms", 0) or 0),
            "duration_ms": int(sticker.get("duration_ms", 2500) or 2500),
            "text": str(sticker.get("text") or ""),
            "side": sticker.get("side") or "l",
            "avatar_color": str(sticker.get("avatar_color") or "#18a058"),
        })
    if not elements:
        return None
    duration = float(params.get("duration") or 0) or 0.0
    for e in elements:
        # 把画布塞进元素,供绘制函数计算缩放与定位(纯函数无需全局状态)
        e["_canvas"] = list(canvas)
    return {"canvas": list(canvas), "duration": duration, "elements": elements}


def build_overlay_track_cmd(frames_dir: str, fps: float, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """把逐帧透明 PNG 序列重组成保留 alpha 的叠加轨道(与 compose.build_rgba_frames_assemble 同构)"""
    pattern = os.path.join(frames_dir, "frame_%08d.png")
    return [
        ffmpeg, "-y", "-framerate", f"{fps:.3f}", "-i", pattern,
        "-c:v", "png", out,
    ]


def build_overlay_compose_cmd(base: str, track: str, out: str, ffmpeg: str = "ffmpeg") -> List[str]:
    """把透明叠加轨道叠到成片之上(scale2ref 适配尺寸,alpha 自然抠边)

    与 compose.build_matte_overlay_cmd 同思路:轨道[1:v]适配背景[0:v]尺寸后 overlay。
    shortest=1 让成片以主视频时长为准,避免叠加轨道略长拖尾。
    """
    fc = (
        "[1:v][0:v]scale2ref=w=iw:h=ih[trk][bg];"
        "[bg][trk]overlay=shortest=1[v]"
    )
    return [
        ffmpeg, "-y", "-i", base, "-i", track,
        "-filter_complex", fc,
        "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-shortest", out,
    ]


async def _render_track(spec: Dict[str, Any], font_path: str, out_mov: str, ffmpeg: str) -> bool:
    """逐帧 PIL 绘制透明叠加轨 → ffmpeg 合成 MOV;任一环节失败返回 False。

    帧率自适应:duration 过长时降帧,把总帧数控制在 _OVERLAY_MAX_FRAMES 内,
    纯 Python 逐帧绘制在大视频上也不会失控。
    """
    Image, ImageDraw, ImageFont = _try_pil() or (None, None, None)
    if Image is None:
        logger.warning("[overlay] 未安装 Pillow,跳过代码渲染")
        return False
    canvas = tuple(spec.get("canvas") or [1080, 1920])
    duration = float(spec.get("duration") or 0)
    fps = float(_OVERLAY_MAX_FPS)
    total_frames = int(duration * fps) if duration > 0 else 1
    if total_frames > _OVERLAY_MAX_FRAMES and duration > 0:
        fps = max(float(_OVERLAY_MIN_FPS), _OVERLAY_MAX_FRAMES / duration)
        total_frames = int(duration * fps)
    if total_frames <= 0:
        total_frames = 1
    frames_dir = tempfile.mkdtemp(prefix="overlay_frames_")
    try:
        base_font = _load_font(font_path, 30)
        for i in range(total_frames):
            t_ms = (i / fps) * 1000.0
            img = Image.new("RGBA", canvas, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            for elem in spec.get("elements") or []:
                drawer = _DRAWERS.get(elem.get("type"))
                if drawer:
                    try:
                        drawer(draw, elem, t_ms, base_font, font_path)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"[overlay] 单元素绘制失败,跳过该元素: {exc}")
            frame_path = os.path.join(frames_dir, f"frame_{i:08d}.png")
            img.save(frame_path, "PNG")
        # 合成透明 MOV
        cmd = build_overlay_track_cmd(frames_dir, fps, out_mov, ffmpeg)
        result = await compose.run(cmd, timeout=compose.DEFAULT_TIMEOUT)
        return bool(result.get("ok"))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[overlay] 叠加轨渲染异常: {exc}")
        return False
    finally:
        for f in os.listdir(frames_dir):
            try:
                os.remove(os.path.join(frames_dir, f))
            except OSError:
                pass
        try:
            os.rmdir(frames_dir)
        except OSError:
            pass


async def apply_overlay(
    video_url: str, spec: Dict[str, Any], prefix: str = "", font_path: Optional[str] = None,
) -> Optional[str]:
    """代码渲染层总入口:下载成片 → 渲染透明叠加轨 → 合成 → 上传;失败返回 None。

    任何一步失败(无 ffmpeg / 无字体 / 渲染异常 / 上传失败)都返回 None,
    调用方据此保留原片。零模型成本:全程只调 ffmpeg + PIL。
    """
    ffmpeg = compose.ffmpeg_path()
    if not ffmpeg:
        logger.info("[overlay] 跳过代码渲染:ffmpeg 不可用")
        return None
    if not font_path:
        font_path = compose.subtitle_font_path()
    if not font_path:
        logger.warning("[overlay] 跳过代码渲染:未找到可用中文字体")
        return None
    if not spec or not spec.get("elements"):
        return None
    workdir = tempfile.mkdtemp(prefix="overlay_")
    local_video = None
    track = os.path.join(workdir, "track.mov")
    composed = os.path.join(workdir, "composed.mp4")
    try:
        local_video = await asyncio.to_thread(download_to_local, video_url, ".mp4")
        if not local_video:
            logger.warning(f"[overlay] 跳过代码渲染:视频下载失败 {video_url}")
            return None
        ok = await _render_track(spec, font_path, track, ffmpeg)
        if not ok or not os.path.exists(track):
            logger.warning("[overlay] 叠加轨渲染失败,保留原片")
            return None
        cmd = build_overlay_compose_cmd(local_video, track, composed, ffmpeg)
        result = await compose.run(cmd, timeout=compose.DEFAULT_TIMEOUT)
        if not result.get("ok"):
            logger.warning(f"[overlay] 叠加合成失败,保留原片: {result.get('stderr')}")
            return None
        key = f"generate/result/{prefix or 'overlay'}_{uuid.uuid4().hex[:8]}.mp4"
        try:
            new_url = await asyncio.wait_for(
                asyncio.to_thread(upload_local_file, composed, key), timeout=300,
            )
        except asyncio.TimeoutError:
            logger.warning("[overlay] 叠加产物上传超时,保留原片")
            return None
        if not new_url:
            logger.warning("[overlay] 叠加产物上传失败,保留原片")
            return None
        logger.info(f"[overlay] 代码渲染叠加完成 → {new_url}")
        return new_url
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[overlay] 代码渲染异常,保留原片: {exc}")
        return None
    finally:
        for path in (local_video, track, composed):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        if os.path.isdir(workdir):
            try:
                os.rmdir(workdir)
            except OSError:
                pass
