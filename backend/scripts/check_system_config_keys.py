# -*- coding: utf-8 -*-
"""校验 tb_system_config 的键名是否合规(点号风格,且与代码一致)。

背景:
  代码里所有键都是「点号」风格,如 gen.llm_base_url / gen.chat_model / sign.daily_credits。
  早期数据可能存成「下划线」风格(gen_llm_base_url),导致:
    - worker 热更新 KEY_MAP 匹配不上 → 静默回退 env 默认模型;
    - backend copy_writer 的 get_by_key 查不到 → 回退默认值。
  本脚本用于发现并给出修复 SQL。

用法:
  # 连库直接校验(在 backend 环境,ENVIRONMENT 已设置)
  python backend/scripts/check_system_config_keys.py

  # 仅打印代码期望的规范键(用于人工比对)
  python backend/scripts/check_system_config_keys.py --print-expected

  # 不连库,用文件里的实际键校验(一行一个 key)
  python backend/scripts/check_system_config_keys.py --keys-file actual_keys.txt

  # 打印修复用的 SQL(把下划线键改名 / 补种缺失键),不执行
  python backend/scripts/check_system_config_keys.py --print-fix-sql

  # 连库并直接修复(谨慎!会改库)
  python backend/scripts/check_system_config_keys.py --apply-fix
"""
from __future__ import annotations

import argparse
import asyncio
import ast
import os
import re
import sys
from pathlib import Path

# 让脚本能从 backend 根目录直接运行
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "dev")

# 仅依赖 DEFAULT_CONFIGS 作为规范键的唯一真源,避免与代码漂移
from app.services.system_config import DEFAULT_CONFIGS  # noqa: E402
from app.settings import config as app_config  # noqa: E402

EXPECTED_KEYS = [item["key"] for item in DEFAULT_CONFIGS]
EXPECTED_SET = set(EXPECTED_KEYS)

# 规范键名:小写字母开头的小写字母/数字段,以 "." 分隔(如 gen.llm_base_url / sign.daily_credits)
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$")

# 下划线风格的「顶级分隔符」会被误用:gen_xxx / sign_xxx 应改为 gen.xxx / sign.xxx
LEGACY_PREFIXES = ("gen_", "sign_")

# worker 实际引用的键(从 KEY_MAP 解析得到),用于反向校验「代码要的键,种子里都有」
WORKER_RUNTIME = ROOT.parent / "worker" / "app" / "core" / "runtime_config.py"


def load_worker_referenced_keys() -> set[str]:
    """从 worker 的 KEY_MAP 字典精确提取其拉取的配置键(左侧 gen.* / sign.*)。"""
    if not WORKER_RUNTIME.exists():
        return set()
    try:
        tree = ast.parse(WORKER_RUNTIME.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "KEY_MAP" and isinstance(node.value, ast.Dict):
                    return {
                        k.value
                        for k in node.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                    }
    return set()


def normalize_legacy(key: str) -> str:
    """把 gen_llm_base_url -> gen.llm_base_url(仅替换首个下划线)。"""
    if key.startswith(LEGACY_PREFIXES):
        return key.replace("_", ".", 1)
    return key


def load_actual_keys(args) -> list[str] | None:
    """返回实际库里的 key 列表;无法连库时回退到 --keys-file 或 None。"""
    if args.keys_file:
        p = Path(args.keys_file)
        if not p.exists():
            print(f"[错误] --keys-file 不存在: {p}", file=sys.stderr)
            sys.exit(2)
        return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]

    # 尝试连库
    try:
        from tortoise import Tortoise
        from app.models.system import SystemConfigModel
    except Exception as exc:  # noqa: BLE001
        print(f"[警告] 无法导入 tortoise / 模型: {exc}", file=sys.stderr)
        return None

    async def _query() -> list[str]:
        await Tortoise.init(config=app_config.ORM_CONFIG)
        try:
            rows = await SystemConfigModel.all().values_list("key", flat=True)
            return list(rows)
        finally:
            await Tortoise.close_connections()

    try:
        return asyncio.run(_query())
    except Exception as exc:  # noqa: BLE001
        print(
            f"[警告] 连接数据库失败({exc})。\n"
            f"        请确认在 backend 环境运行且 ENVIRONMENT/DB 配置正确,\n"
            f"        或使用 --keys-file 传入实际键列表。",
            file=sys.stderr,
        )
        return None


def analyze(actual: list[str], worker_keys: set[str] | None = None) -> dict:
    actual_set = set(actual)
    worker_keys = worker_keys or set()
    report = {
        "ok": [],          # 键在 EXPECTED 中
        "legacy": [],      # 下划线风格,可改名
        "unknown": [],     # 不在代码期望中(自定义或陈旧)
        "malformed": [],   # 完全不符合键名规范(非 legacy 可修正)
        "missing": [],     # 期望中但库里没有(会被 init_config_data 补种)
        "invalid_expected": [],  # 种子定义本身的键名不合规(需改代码)
        "worker_missing": [],    # worker 引用但种子里缺失的键(会导致静默回退)
        "fix_renames": {},  # legacy_key -> canonical_key
        "fix_inserts": [],  # 需要补种的 (key, value, is_public)
    }
    # 种子键名规范自检:代码里定义的规范键本身也得合规
    for k in EXPECTED_KEYS:
        if not KEY_PATTERN.match(k):
            report["invalid_expected"].append(k)
    for k in actual:
        if k in EXPECTED_SET:
            report["ok"].append(k)
        elif not KEY_PATTERN.match(k):
            canon = normalize_legacy(k)
            if canon in EXPECTED_SET:
                report["legacy"].append(k)
                report["fix_renames"][k] = canon
            else:
                report["malformed"].append(k)
        else:
            report["unknown"].append(k)
    for item in DEFAULT_CONFIGS:
        if item["key"] not in actual_set:
            report["missing"].append(item["key"])
            report["fix_inserts"].append(item)
    # 反向校验:worker 代码拉取的键,种子(DEFAULT_CONFIGS)必须包含,否则会静默回退
    for wk in sorted(worker_keys):
        if wk not in EXPECTED_SET and normalize_legacy(wk) not in EXPECTED_SET:
            report["worker_missing"].append(wk)
    return report


def print_fix_sql(report: dict) -> None:
    print("-- ===== 修复 SQL(请人工复核后执行) =====")
    for old, new in report["fix_renames"].items():
        print(f"UPDATE tb_system_config SET `key` = '{new}' WHERE `key` = '{old}';")
    for item in report["fix_inserts"]:
        key = item["key"]
        val = (item.get("value") or "").replace("'", "''")
        is_public = 1 if item.get("is_public", True) else 0
        remark = (item.get("remark") or "").replace("'", "''")
        group = item.get("group", "gen")
        print(
            f"INSERT INTO tb_system_config (`key`, `value`, `group`, `remark`, `is_public`) "
            f"VALUES ('{key}', '{val}', '{group}', '{remark}', {is_public});"
        )


async def apply_fix(report: dict) -> None:
    from tortoise import Tortoise
    from app.models.system import SystemConfigModel

    await Tortoise.init(config=app_config.ORM_CONFIG)
    try:
        for old, new in report["fix_renames"].items():
            n = await SystemConfigModel.filter(key=old).update(key=new)
            print(f"[修复] 改名 {old} -> {new} (影响 {n} 行)")
        for item in report["fix_inserts"]:
            obj = await SystemConfigModel.get_or_none(key=item["key"])
            if not obj:
                await SystemConfigModel.create(
                    key=item["key"],
                    value=item.get("value", ""),
                    group=item.get("group", "gen"),
                    remark=item.get("remark", ""),
                    is_public=item.get("is_public", True),
                )
                print(f"[修复] 补种 {item['key']}")
    finally:
        await Tortoise.close_connections()


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 tb_system_config 键名合规性")
    parser.add_argument("--keys-file", help="实际键列表文件(一行一个 key),不连库时使用")
    parser.add_argument("--print-expected", action="store_true", help="仅打印代码期望的规范键")
    parser.add_argument("--print-fix-sql", action="store_true", help="打印修复 SQL 但不执行")
    parser.add_argument("--apply-fix", action="store_true", help="连库并直接修复(谨慎)")
    parser.add_argument("--no-strict", action="store_true", help="即使发现问题也以退出码 0 结束")
    args = parser.parse_args()

    if args.print_expected:
        for k in EXPECTED_KEYS:
            print(k)
        return 0

    actual = load_actual_keys(args)
    if actual is None:
        # 连库失败且未给 --keys-file:打印期望键供人工比对
        print("[提示] 未获取到实际键。代码期望的规范键如下(可人工比对 DB):", file=sys.stderr)
        for k in EXPECTED_KEYS:
            print(f"  {k}", file=sys.stderr)
        return 0 if args.no_strict else 1

    worker_keys = load_worker_referenced_keys()
    report = analyze(actual, worker_keys)

    print("=" * 64)
    print(f"实际键总数: {len(actual)} | 规范键总数: {len(EXPECTED_KEYS)}")
    print("=" * 64)
    print(f"[OK]   合规键 ({len(report['ok'])})")
    for k in report["ok"]:
        print(f"       {k}")
    if report["legacy"]:
        print(f"[LEGACY] 下划线风格,建议改名 ({len(report['legacy'])})")
        for old in report["legacy"]:
            print(f"       {old}  ->  {report['fix_renames'][old]}")
    if report["unknown"]:
        print(f"[UNKNOWN] 代码未引用的键,可能自定义或陈旧 ({len(report['unknown'])})")
        for k in report["unknown"]:
            print(f"       {k}")
    if report["malformed"]:
        print(f"[MALFORMED] 不符合键名规范(非 legacy 可修正) ({len(report['malformed'])})")
        for k in report["malformed"]:
            print(f"       {k}")
    if report["invalid_expected"]:
        print(f"[INVALID-SEED] 种子定义本身键名不合规(需改代码) ({len(report['invalid_expected'])})")
        for k in report["invalid_expected"]:
            print(f"       {k}")
    if report["worker_missing"]:
        print(f"[WORKER-MISSING] worker 引用但种子缺失(会静默回退 env) ({len(report['worker_missing'])})")
        for k in report["worker_missing"]:
            print(f"       {k}")
    if report["missing"]:
        print(f"[MISSING] 期望但库里缺失(会被 init_config_data 补种) ({len(report['missing'])})")
        for k in report["missing"]:
            print(f"       {k}")

    if args.print_fix_sql:
        print()
        print_fix_sql(report)

    if args.apply_fix:
        if report["fix_renames"] or report["fix_inserts"]:
            print("\n[执行修复]")
            asyncio.run(apply_fix(report))
        else:
            print("\n[无需修复]")

    has_problem = bool(
        report["legacy"] or report["unknown"] or report["malformed"]
        or report["invalid_expected"] or report["worker_missing"]
    )
    if has_problem and not args.no_strict:
        print("\n[结论] 发现不合规键,请修复后再上线(非零退出)。", file=sys.stderr)
        return 1
    print("\n[结论] 键名校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
