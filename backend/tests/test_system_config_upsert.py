# -*- coding: utf-8 -*-
"""admin 私密配置 upsert 守卫:列表打码后的占位符回传时不得覆盖真实密钥,新值仍正常写入。

直接调用 Service.upsert( monkeypatch 掉 crud,避免依赖真实 DB/ORM 初始化),聚焦守卫逻辑。
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
os.environ.setdefault("ENVIRONMENT", "dev")

from app.services import system_config as sc  # noqa: E402


class _Obj:
    def __init__(self, d):
        self.__dict__.update(d)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class _Query:
    def __init__(self, row):
        self._row = row

    async def update(self, **data):
        self._row.update(data)
        return 1


class _Model:
    def __init__(self, row):
        self._row = row

    def filter(self, **kw):
        return _Query(self._row)


def _patch_crud(monkeypatch, row):
    async def get_by_key(k):
        return _Obj(dict(row)) if k == row["key"] else None

    async def create(data):
        return _Obj(dict(data))

    monkeypatch.setattr(sc.crud, "get_by_key", get_by_key)
    monkeypatch.setattr(sc.crud, "create", create)
    monkeypatch.setattr(sc.crud, "model", _Model(row))


def _secret_row(value="real-secret"):
    return {
        "id": 1,
        "key": "gen.llm_api_key",
        "value": value,
        "remark": "old",
        "group": "gen",
        "is_public": False,
    }


def test_upsert_keeps_secret_when_value_is_mask(monkeypatch):
    """值回传为打码占位符 → 保留原密钥,其它字段照常更新"""
    row = _secret_row()
    _patch_crud(monkeypatch, row)
    payload = sc.UpsertSchema(
        key="gen.llm_api_key", value=sc.MASK, group="gen", remark="new", is_public=False
    )
    out = asyncio.run(sc.service.upsert(payload))
    assert out["value"] == "real-secret"  # 未被 ****** 覆盖
    assert out["remark"] == "new"         # 说明正常更新


def test_upsert_applies_new_value(monkeypatch):
    """传入真实新值 → 正常写入"""
    row = _secret_row()
    _patch_crud(monkeypatch, row)
    payload = sc.UpsertSchema(
        key="gen.llm_api_key", value="brand-new", group="gen", remark="", is_public=False
    )
    out = asyncio.run(sc.service.upsert(payload))
    assert out["value"] == "brand-new"
