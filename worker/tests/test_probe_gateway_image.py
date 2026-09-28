# -*- coding: utf-8 -*-
"""网关探测脚本的参考图真人检测判定(纯函数)。

`probe_gateway.py --image-real-person` 的结论完全取决于"响应 → 判定"这一步:
判定写错会让运营误以为拟态化有效(或无效),所以用单测钉死分类与请求形态。
"""
import pathlib
import sys

# scripts/ 是脚本目录(非包),按脚本自身的做法把 worker/ 加入 sys.path 后导入
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scripts.probe_gateway import _image_probe_request, classify_image_real_person  # noqa: E402


def test_classify_blocked():
    """明确返回"图片含真人" → BLOCKED(未过检测)"""
    assert classify_image_real_person(
        400, '{"error":{"code":"InputImageSensitiveContentDetected.PrivacyInformation"}}'
    ) == "BLOCKED"
    assert classify_image_real_person(
        400, "The request failed because the input image may contain real person."
    ) == "BLOCKED"


def test_classify_passed_creates_task():
    """2xx → 已放行(会创建真实任务、产生费用)"""
    assert classify_image_real_person(200, '{"id":"cgt-1"}') == "PASSED"
    assert classify_image_real_person(201, "ok") == "PASSED"


def test_classify_passed_detection_on_other_rejections():
    """因其它原因被拒(未触发真人检测)→ 也算"过了检测",且不产生费用"""
    assert classify_image_real_person(400, "missing required field prompt") == "PASSED_DETECTION"
    assert classify_image_real_person(422, "invalid parameter") == "PASSED_DETECTION"


def test_classify_auth_and_quota_not_misread_as_passed():
    """鉴权失败 / 余额不足与素材无关,不能误判成'过了检测'"""
    assert classify_image_real_person(401, "unauthorized") == "AUTH"
    assert classify_image_real_person(403, "forbidden") == "AUTH"
    assert classify_image_real_person(402, "insufficient balance") == "QUOTA"


def test_image_probe_request_ark_shape():
    """方舟原生:与线上 r2v 同形(text + image_url/reference_image)"""
    path, body = _image_probe_request("ark", "m", "https://oss/a.jpg")
    assert path == "/contents/generations/tasks"
    assert body["model"] == "m"
    assert body["content"][0]["type"] == "text"
    assert body["content"][1]["image_url"]["url"] == "https://oss/a.jpg"
    assert body["content"][1]["role"] == "reference_image"


def test_image_probe_request_openai_shape():
    """OpenAI 兼容:走 /videos,图片放 image 字段"""
    path, body = _image_probe_request("openai", "m", "https://oss/a.jpg")
    assert path == "/videos"
    assert body["image"] == "https://oss/a.jpg"


def test_image_probe_request_uses_short_duration():
    """只放一张图 + 固定短时长:把"被拒"归因到这张图本身,并压低万一放行时的成本"""
    _, ark_body = _image_probe_request("ark", "m", "https://oss/a.jpg")
    assert "duration 3" in ark_body["content"][0]["text"]
    _, oa_body = _image_probe_request("openai", "m", "https://oss/a.jpg")
    assert oa_body["seconds"] == "3"
