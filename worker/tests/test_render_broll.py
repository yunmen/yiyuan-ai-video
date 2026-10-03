# -*- coding: utf-8 -*-
"""视频换口播: B-roll 类型推断逻辑(纯函数,不依赖 ffmpeg)

锁死 _infer_broll_type 的判定规则,避免「前端允许传视频但 worker 误判为图片」这类
副本飘移:显式 type 优先,否则按扩展名识别;素材地址带 OSS ?sign= 查询串也能正确识别。
"""
from app.tools.render_tool import RenderTool


def test_infer_broll_explicit_type_wins():
    """显式给出 type 时直接采用,不按扩展名覆盖"""
    assert RenderTool._infer_broll_type({"type": "video"}, "/x/p.jpg") == "video"
    assert RenderTool._infer_broll_type({"type": "image"}, "/x/c.mp4") == "image"
    # 空/非法 type 视为未给,回落扩展名
    assert RenderTool._infer_broll_type({"type": ""}, "/x/c.mp4") == "video"
    assert RenderTool._infer_broll_type({}, "/x/p.png") == "image"


def test_infer_broll_by_extension():
    """无显式 type 时按扩展名识别图片/视频"""
    videos = ["/a.mp4", "/a.webm", "/a.mov", "/a.m4v", "/a.avi", "/a.mkv", "/A.MP4"]
    for url in videos:
        assert RenderTool._infer_broll_type({}, url) == "video", url
    images = ["/a.jpg", "/a.jpeg", "/a.png", "/a.webp", "/A.PNG"]
    for url in images:
        assert RenderTool._infer_broll_type({}, url) == "image", url


def test_infer_broll_strips_oss_query_string():
    """OSS 签名查询串不能干扰扩展名识别(真实场景素材多为带 ?sign= 的 URL)"""
    assert RenderTool._infer_broll_type({}, "https://oss.x.com/broll.mp4?sign=abc&t=1") == "video"
    assert RenderTool._infer_broll_type({}, "https://oss.x.com/broll.png?sign=abc") == "image"
