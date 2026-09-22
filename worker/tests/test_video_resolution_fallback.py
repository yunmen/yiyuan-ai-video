# -*- coding: utf-8 -*-
"""分辨率:按模型预压档 + 失败后降档重试

背景(实测):方舟 doubao-seedance-2-0-fast 的 **r2v/v2v 变体只认 720p** —— 传 1080p/1080P
都被 400 拒绝;而同一份配置还要服务支持 1080P 的 1.0 pro。因此在两个层面设防:
  1. 提交前按模型上限**预压**(省掉注定失败的请求与整轮网关故障转移);
  2. 若仍被拒(未知模型/新限制),按错误信息**降档重试**。

⚠️ 降档判定必须看**所有**网关的错误而不能只看最终异常:故障转移会依次试多个网关,
最终抛出的常是备选网关的 401,会把第一站"分辨率不支持"的主因整段盖掉(线上真实踩到过)。
"""
import asyncio

from app.tools.video_tool import VideoGenTool, _cap_resolution, _is_resolution_error

RESOLUTION_ERR = (
    "The parameter `contents[0].text.resolution` specified in the request is not valid: "
    "the specified resolution is not supported for model doubao-seedance-2-0-fast-r2v"
)
AUTH_ERR = "Error code: 401 - Authentication Fails, Your api key: ****7d0e is invalid"


def _make_tool():
    return VideoGenTool(api_key="test-key", base_url="http://localhost/v1")


def _payload(model: str = "happyhorse-1.1-r2v"):
    # 默认用普通模型:seedance-2 会被预压逻辑接管,那是另一组用例的事
    return {
        "model": model,
        "prompt": "复刻",
        "metadata": {"parameters": {"resolution": "1080P", "ratio": "9:16", "duration": 10}},
    }


def _stub_io(monkeypatch, tool, failover):
    """把提交后的 IO 全部打桩:只保留待验证的提交逻辑"""
    async def fake_prepare(payload):
        return payload

    async def fake_poll(*a, **k):
        return "https://cdn/raw.mp4"

    async def fake_persist(urls, prefix=None):
        return urls

    monkeypatch.setattr(tool, "_prepare_media", fake_prepare)
    monkeypatch.setattr(tool, "_with_failover", failover)
    monkeypatch.setattr(tool, "_poll", fake_poll)
    monkeypatch.setattr(tool, "_reset_gateway", lambda: None)
    monkeypatch.setattr("app.tools.video_tool.persist_url_list", fake_persist)


# --- 降档候选 ---

def test_case_variant_is_not_a_downgrade():
    """1080P 与 1080p 是同一档位:不该把它当成"降一级"再白试一次"""
    assert VideoGenTool._resolution_fallbacks("1080P") == ["720p", "480p"]
    assert VideoGenTool._resolution_fallbacks("1080p") == ["720p", "480p"]


def test_ladder_ends_and_empty_input():
    assert VideoGenTool._resolution_fallbacks("720p") == ["480p"]
    assert VideoGenTool._resolution_fallbacks("480p") == []
    assert VideoGenTool._resolution_fallbacks(None) == []


def test_unknown_gear_falls_back_to_720p():
    """认不出的档位名(各网关自定义)直接退回最通用的 720p"""
    assert VideoGenTool._resolution_fallbacks("4K") == ["720p"]


# --- 模型上限预压 ---

def test_seedance2_resolution_capped():
    """Seedance 2.0 的 r2v/v2v 实测只支持 720p,大小写两种写法都要被压下来"""
    assert _cap_resolution("doubao-seedance-2-0-fast-260128", "1080P") == "720p"
    assert _cap_resolution("doubao-seedance-2-0-fast-260128", "1080p") == "720p"


def test_other_models_not_capped():
    """1.0 pro / 其他模型支持 1080P,不能被误压(否则白白降质)"""
    assert _cap_resolution("doubao-seedance-1-0-pro-250528", "1080P") == "1080P"
    assert _cap_resolution("happyhorse-1.1-r2v", "1080P") == "1080P"


def test_cap_only_lowers():
    """压档只降不升:已是 720p/480p 时保持原样"""
    assert _cap_resolution("doubao-seedance-2-0-fast-260128", "720p") == "720p"
    assert _cap_resolution("doubao-seedance-2-0-fast-260128", "480p") == "480p"


def test_cap_keeps_unknown_gear_and_empty():
    """认不出的档位/缺参数交给降档逻辑兜底,不在这里瞎改"""
    assert _cap_resolution("doubao-seedance-2-0-fast-260128", "4K") == "4K"
    assert _cap_resolution(None, "1080P") == "1080P"
    assert _cap_resolution("doubao-seedance-2-0-fast-260128", None) is None


# --- payload 改写 ---

def test_with_resolution_clones_payload():
    """改分辨率不能污染原 payload(降档后原值还要用于回写/断点信息)"""
    payload = _payload()
    cloned = VideoGenTool._with_resolution(payload, "720p")
    assert cloned["metadata"]["parameters"]["resolution"] == "720p"
    assert payload["metadata"]["parameters"]["resolution"] == "1080P"


def test_with_resolution_creates_missing_metadata():
    cloned = VideoGenTool._with_resolution({"model": "m"}, "720p")
    assert cloned["metadata"]["parameters"]["resolution"] == "720p"


def test_resolution_error_detection():
    assert _is_resolution_error(RuntimeError(RESOLUTION_ERR))
    assert not _is_resolution_error(RuntimeError(AUTH_ERR))
    assert not _is_resolution_error(RuntimeError("task_type r2v does not support model"))


# --- 提交层 ---

def test_seedance2_capped_before_submit_single_attempt(monkeypatch):
    """Seedance 2.0 + 1080P:提交前就压到 720p,一次成功(不该先失败再降档)"""
    tool = _make_tool()
    submitted = []
    calls = {"n": 0}

    async def fake_failover(capability, call, label="", prefer_current=True):
        calls["n"] += 1
        return {"id": "task-ok"}

    async def fake_prepare(payload):
        submitted.append(payload["metadata"]["parameters"]["resolution"])
        return payload

    async def fake_poll(*a, **k):
        return "https://cdn/raw.mp4"

    async def fake_persist(urls, prefix=None):
        return urls

    monkeypatch.setattr(tool, "_prepare_media", fake_prepare)
    monkeypatch.setattr(tool, "_with_failover", fake_failover)
    monkeypatch.setattr(tool, "_poll", fake_poll)
    monkeypatch.setattr("app.tools.video_tool.persist_url_list", fake_persist)

    payload = _payload("doubao-seedance-2-0-fast-260128")
    result = asyncio.run(tool._submit_and_poll(payload, "视频编辑", 10, "1080P", "9:16"))

    assert submitted == ["720p"], "提交给模型的就应该是 720p"
    assert calls["n"] == 1, "预压到位就不该再多试一轮"
    assert result.metadata.get("success") is True
    assert result.metadata.get("resolution") == "720p", "回写用量应是真实生效档位"


def test_retry_when_resolution_error_hidden_by_fallback(monkeypatch):
    """核心回归:最终异常是备选网关的 401,但主因(分辨率)必须仍被识别并降档重试"""
    tool = _make_tool()
    used = []
    calls = {"n": 0}

    async def fake_ark(method, path, body=None):
        raise RuntimeError(RESOLUTION_ERR)

    async def fake_failover(capability, call, label="", prefer_current=True):
        calls["n"] += 1
        if calls["n"] == 1:
            # 复刻真实链路:第一站报分辨率错(被 _submit 收集),故障转移继续切备选,
            # 最后抛出的是备选网关的鉴权错误 —— 主因被盖住
            try:
                await call({"url": "https://ark.example", "key": "k", "proto": "ark"})
            except Exception:
                pass
            raise RuntimeError(AUTH_ERR)
        return {"id": "task-ok"}

    monkeypatch.setattr(tool, "_is_ark", lambda: True)
    monkeypatch.setattr(tool, "_ark_request", fake_ark)
    _stub_io(monkeypatch, tool, fake_failover)

    # 先留一份原实现:打桩函数里必须调它,直接调 VideoGenTool._with_resolution 会打到自己(无限递归)
    original = VideoGenTool._with_resolution

    def fake_with_resolution(payload, resolution):
        used.append(resolution)
        return original(payload, resolution)

    monkeypatch.setattr(VideoGenTool, "_with_resolution", staticmethod(fake_with_resolution))

    result = asyncio.run(tool._submit_and_poll(_payload(), "视频编辑", 10, "1080P", "9:16"))

    assert calls["n"] == 2, "应在识别出分辨率问题后降档重试一次"
    assert used == ["720p"], "重试必须用降档后的分辨率"
    assert result.metadata.get("success") is True


def test_non_resolution_error_does_not_retry(monkeypatch):
    """余额/鉴权类错误换分辨率也没用,必须立刻失败(否则白白多打网关)"""
    tool = _make_tool()
    calls = {"n": 0}

    async def fake_ark(method, path, body=None):
        raise RuntimeError(AUTH_ERR)

    async def fake_failover(capability, call, label="", prefer_current=True):
        calls["n"] += 1
        try:
            await call({"url": "https://ark.example", "key": "k", "proto": "ark"})
        except Exception:
            pass
        raise RuntimeError(AUTH_ERR)

    monkeypatch.setattr(tool, "_is_ark", lambda: True)
    monkeypatch.setattr(tool, "_ark_request", fake_ark)
    _stub_io(monkeypatch, tool, fake_failover)

    result = asyncio.run(tool._submit_and_poll(_payload(), "视频编辑", 10, "1080P", "9:16"))

    assert result.metadata.get("success") is False
    assert calls["n"] == 1, "非分辨率错误不该降档重试"


def test_failure_message_shows_first_gateway_error(monkeypatch):
    """失败信息要留第一站的真实原因:报备选网关的 401 只会把排查带偏"""
    tool = _make_tool()

    async def fake_ark(method, path, body=None):
        raise RuntimeError("Insufficient balance")

    async def fake_failover(capability, call, label="", prefer_current=True):
        try:
            await call({"url": "https://ark.example", "key": "k", "proto": "ark"})
        except Exception:
            pass
        raise RuntimeError(AUTH_ERR)

    monkeypatch.setattr(tool, "_is_ark", lambda: True)
    monkeypatch.setattr(tool, "_ark_request", fake_ark)
    _stub_io(monkeypatch, tool, fake_failover)

    result = asyncio.run(tool._submit_and_poll(_payload(), "视频编辑", 10, "1080P", "9:16"))

    assert "Insufficient balance" in str(result.content), "应保留第一站(方舟)的真实错误"
