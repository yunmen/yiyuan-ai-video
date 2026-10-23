# -*- coding: utf-8 -*-
'''图像网格拼合 / 分割工具 — 九宫格(3×3)等规格的确定性图像处理。

与 ImageGenTool 一致:图片走 PIL(overlay.py 已使用),结果经 OSS 转存。
- compose_grid: 多张图 → 一张 cols×rows 网格图(不足时白底填充);
- split_grid:   一张图 → 按 cols×rows 等分切成多张单图(行优先,左到右、上到下)。
本模块不依赖 ImageGenTool,避免循环导入。
'''
import io
import os
import uuid
from typing import List, Optional, Tuple

from app.utils.oss import download_to_local, upload_bytes


def parse_grid(spec: Optional[str]) -> Tuple[int, int]:
    '''解析网格规格字符串(如 "3x3" → (3, 3));非法或缺失回退 3×3。

    限制 cols*rows <= 36,避免误传超大网格导致内存与出图异常。
    '''
    if not spec:
        return 3, 3
    try:
        a, b = str(spec).lower().split("x")
        cols, rows = int(a.strip()), int(b.strip())
        if cols < 1 or rows < 1 or cols * rows > 36:
            return 3, 3
        return cols, rows
    except (ValueError, AttributeError):
        return 3, 3


async def compose_grid(
    urls: List[str], spec: str = "3x3", task_id: str = ""
) -> Optional[str]:
    '''把多张图拼成 cols×rows 网格图,返回 OSS URL;全部下载失败返回 None。

    urls 数量可少于 cols*rows,空缺格以白底填充;超过则按行列顺序截断。
    单元尺寸取所有图宽高的最小值,保证网格整齐且不被最大图撑爆。
    '''
    from PIL import Image

    if not urls:
        return None
    cols, rows = parse_grid(spec)
    local_paths: List[str] = []
    prefix = task_id or uuid.uuid4().hex
    try:
        for u in urls[:cols * rows]:
            p = download_to_local(u, suffix=".jpg")
            if not p:
                return None
            local_paths.append(p)
        imgs = [Image.open(p).convert("RGB") for p in local_paths]
        cell_w = min(im.width for im in imgs)
        cell_h = min(im.height for im in imgs)
        canvas = Image.new("RGB", (cell_w * cols, cell_h * rows), (255, 255, 255))
        for idx, im in enumerate(imgs):
            if idx >= cols * rows:
                break
            r, c = divmod(idx, cols)
            # 等比缩放到单元内(保持比例),居中贴到对应格
            im.thumbnail((cell_w, cell_h), Image.LANCZOS)
            x = c * cell_w + (cell_w - im.width) // 2
            y = r * cell_h + (cell_h - im.height) // 2
            canvas.paste(im, (x, y))
        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=92)
        data = buf.getvalue()
        key = f"generate/result/{prefix}_grid_{uuid.uuid4().hex[:8]}.jpg"
        return upload_bytes(data, key)
    finally:
        for p in local_paths:
            try:
                os.remove(p)
            except OSError:
                pass


async def split_grid(
    url: str, spec: str = "3x3", task_id: str = ""
) -> List[str]:
    '''把单张图按 cols×rows 等分切成多张单图,返回 OSS URL 列表(行优先)。

    顺序:第 0 格=左上,行优先(row-major)。任一格上传失败则整体失败。
    '''
    from PIL import Image

    if not url:
        return []
    cols, rows = parse_grid(spec)
    p = download_to_local(url, suffix=".jpg")
    if not p:
        return []
    prefix = task_id or uuid.uuid4().hex
    out: List[str] = []
    try:
        im = Image.open(p).convert("RGB")
        w, h = im.size
        if w < cols or h < rows:
            return []
        for r in range(rows):
            for c in range(cols):
                box = (c * w // cols, r * h // rows, (c + 1) * w // cols, (r + 1) * h // rows)
                cell = im.crop(box)
                buf = io.BytesIO()
                cell.save(buf, format="JPEG", quality=92)
                data = buf.getvalue()
                key = f"generate/result/{prefix}_split_{r}_{c}_{uuid.uuid4().hex[:8]}.jpg"
                u = upload_bytes(data, key)
                if not u:
                    return []
                out.append(u)
        return out
    finally:
        try:
            os.remove(p)
        except OSError:
            pass
