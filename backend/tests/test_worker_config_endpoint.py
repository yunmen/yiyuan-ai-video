# -*- coding: utf-8 -*-
"""backend worker-config 接口单测:验证鉴权、全量配置(含网关密钥)、以及 gen-config 不下发敏感密钥。

直接调用路由函数(绕过 OperationLogRoute 对 ctx 中间件的依赖),聚焦业务逻辑。
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
os.environ.setdefault("ENVIRONMENT", "dev")

import pytest

from app.routes.user import common as user_common  # noqa: E402
from app.services import system_config as sc  # noqa: E402
from app.settings import config  # noqa: E402


FULL = {
    "gen.chat_model": "deepseek-chat",
    "gen.video_model_t2v": "doubao-seedance-1.0-pro-250528",
    "gen.llm_base_url": "https://gateway.example/v1",
    "gen.llm_api_key": "super-secret",
}
PUBLIC = {k: v for k, v in FULL.items() if not k.startswith("gen.llm_")}


@pytest.fixture(autouse=True)
def patch_service(monkeypatch):
    async def _full():
        return FULL

    async def _public():
        return PUBLIC

    monkeypatch.setattr(sc.service, "get_full_map", _full)
    monkeypatch.setattr(sc.service, "get_public_map", _public)
    monkeypatch.setattr(config, "WORKER_CALLBACK_SECRET", "worker-callback-secret")


def _body(resp) -> dict:
    return json.loads(resp.body)


def test_worker_config_requires_token():
    resp = asyncio.run(user_common.worker_config(x_worker_token=None))
    # 鉴权失败统一用 code=9(项目协议:1 成功 / 0 业务失败 / 9 鉴权失败),不是 HTTP 401
    assert _body(resp)["code"] == 9


def test_worker_config_ok_with_token():
    resp = asyncio.run(user_common.worker_config(x_worker_token="worker-callback-secret"))
    data = _body(resp)["data"]
    # 含敏感网关密钥
    assert data["gen.llm_base_url"] == "https://gateway.example/v1"
    assert data["gen.llm_api_key"] == "super-secret"
    assert data["gen.chat_model"] == "deepseek-chat"


def test_gen_config_excludes_secret():
    resp = asyncio.run(user_common.gen_config())
    data = _body(resp)["data"]
    # 公开接口不得包含网关密钥
    assert "gen.llm_api_key" not in data
    assert "gen.llm_base_url" not in data
    # 但模型名可见
    assert data["gen.chat_model"] == "deepseek-chat"
