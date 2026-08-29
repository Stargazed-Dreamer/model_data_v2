#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
model_data_tool.py —— 主流大模型静态数据集（JSONL）安全读写 / 显式合并工具
================================================================================

设计目标（严格对应需求）：
  1. 所有"写 / 合并"操作都必须【显式声明策略】，不存在"悄悄覆盖"的隐藏默认。
     - 空字段遇到有值字段怎么办？ → on_null 显式指定
     - 新旧两个都有值且不同怎么办？ → on_both 显式指定（含 newer_wins 依据哪个日期）
     - 数组（benchmarks 等）怎么合并？ → on_array 显式指定（替换 / 追加去重 / 按主键合并）
     - schema 版本不一致怎么办？ → on_schema 显式指定（升级 / 保留 / 冲突）
  2. 默认 dry-run：任何写操作在 dry_run=True 时只【生成操作计划】，不改文件。
     必须显式传入 dry_run=False（CLI 用 --apply）才会真正落盘。
  3. 每条变更都生成一条带"原因"的记录（Change），最终可打印成人类可读的计划，
     保证"将要改哪些 model_id、哪些字段路径、旧值→新值、依据哪条规则"一目了然。

本文件只依赖 Python 标准库，方便任何 Agent 子进程直接 import 或 CLI 调用。

------------------------------------------------------------------
典型用法
------------------------------------------------------------------
# 1) 直接读
from model_data_tool import ModelDataStore, MergeStrategy, NullRule, BothPresentRule, ArrayRule, SchemaRule

store = ModelDataStore("sample_openai_deepseek.jsonl")
store.read_field("openai:gpt-5.6:sol", "architecture.total_params_b")   # 指定字段直读
store.read_compare("pricing.input")                                      # 同名同类型字段横向对比多家
store.read_table(["openai:gpt-5.6:sol","deepseek:deepseek-v4-pro:0813"],
                 ["basic_info.release_date","pricing.input","pricing.output"])

# 2) 显式合并（必须先声明每一条规则）
strat = MergeStrategy(
    on_null=NullRule.TAKE_SOURCE,                 # 目标为空 → 用来源填充
    on_both=BothPresentRule.NEWER_WINS,           # 两者都有值 → 按日期，新数据覆盖旧数据
    recency_field="meta.collected_at",            # 依据这条日期判定"谁更新"
    on_array=ArrayRule.UNION_BY_KEY,              # 数组按主键合并
    array_key_default=["benchmark","config","date"],
    array_key_overrides={"benchmarks.arena_elo": ["sub_benchmark","date"]},
    on_schema=SchemaRule.UPGRADE,                 # schema 较旧则升级并规范化结构
)
incoming = ModelDataStore("agent_b_output.jsonl").records_as_list()

plan = store.merge_incoming(incoming, strategy=strat, dry_run=True)  # 默认只出计划
print(plan.describe())                                              # 先看清楚再决定

store.merge_incoming(incoming, strategy=strat, dry_run=False)        # 确认无误后真正写入
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ==================================================================
# 1. 显式合并策略枚举（调用方必须逐一指定，禁止隐藏默认覆盖）
# ==================================================================

class NullRule(str, Enum):
    """目标字段为 null / 缺失键时，遇到来源有值怎么办。"""
    TAKE_SOURCE = "take_source"   # 用来源的值填充（最常见的"补缺"语义）
    KEEP_TARGET = "keep_target"   # 保留目标的空，不填充
    CONFLICT = "conflict"         # 记为冲突，不动，交由人工处理


class BothPresentRule(str, Enum):
    """目标与来源同一字段都有值且不同时，怎么办。"""
    SOURCE_WINS = "source_wins"   # 来源覆盖目标
    TARGET_WINS = "target_wins"   # 保留目标
    NEWER_WINS = "newer_wins"     # 按 recency_field 判定谁更新，新的覆盖旧的
    CONFLICT = "conflict"         # 记为冲突，不动，交由人工处理


class ArrayRule(str, Enum):
    """数组类字段（如 benchmarks.self_reported / arena_elo）如何合并。"""
    REPLACE = "replace"           # 来源整体替换目标数组
    APPEND_UNIQUE = "append_unique"   # 目标 + 来源中不存在的项（按整项相等去重）
    UNION_BY_KEY = "union_by_key"     # 按主键合并：同键项递归合并，异键项追加


class SchemaRule(str, Enum):
    """目标与来源 schema_version 不一致时怎么办。"""
    UPGRADE = "upgrade"                   # 以较高版本为准，并对结构做规范化
    KEEP_TARGET = "keep_target"           # 一律保留目标版本
    REQUIRE_EQUAL = "require_equal"       # 版本必须一致，否则整条记为冲突
    CONFLICT_IF_LOWER = "conflict_if_lower"  # 来源比目标旧则记为冲突，不动


class TieBreakerRule(str, Enum):
    """on_both=newer_wins 且 recency 相等/缺失、无法判定新旧时的平局裁决（P2 修复）。

    天级粒度的 collected_at 无法区分同日内的两次采集；平局时必须显式声明走向，
    禁止"静默保留目标"这类隐藏默认（那会让同日的重采集/修正被无声丢弃）。
    """
    KEEP_TARGET = "keep_target"   # 保留目标（库内旧值），来源不生效
    SOURCE_WINS = "source_wins"   # 来源（本次新采集）覆盖目标 —— 重采集修正场景推荐
    CONFLICT = "conflict"         # 记为冲突，不动，交由人工处理


# ==================================================================
# 2. MergeStrategy：把上述规则打包，构造时强制逐一声明（缺一则报错）
# ==================================================================

@dataclass
class MergeStrategy:
    """
    显式合并策略。所有"可能导致覆盖/丢弃"的维度都必须是调用方明确传入的值，
    构造时若任一必需项为 None，会立即抛出 ValueError，强制 Agent 想清楚再调用。
    """
    on_null: Optional[NullRule] = None
    on_both: Optional[BothPresentRule] = None
    recency_field: Optional[str] = None          # on_both=NEWER_WINS 时必填
    on_array: Optional[ArrayRule] = None
    array_key_default: List[str] = field(default_factory=list)   # 数组按主键合并时的默认主键
    array_key_overrides: Dict[str, List[str]] = field(default_factory=dict)  # 路径 -> 主键覆盖
    on_schema: Optional[SchemaRule] = None
    tie_breaker: Optional[TieBreakerRule] = None  # on_both=NEWER_WINS 时必填（P2 修复）
    # 路径级 on_both 覆盖：如 {"meta.collected_at": SOURCE_WINS}——数据字段保守 conflict、
    # 个别元数据字段显式放行的场景（2026-08-26 collected_at 口径拍板引入）
    both_overrides: Dict[str, BothPresentRule] = field(default_factory=dict)
    # 空数组保护开关：默认 False，即 on_array=replace 且来源数组为空、目标非空时保留目标。
    # 显式置 True 才允许「用空数组清空目标」，属逃生阀而非合并规则，故不进 validate() 必填项。
    allow_empty_replace: bool = False

    def validate(self) -> None:
        missing = []
        if self.on_null is None:
            missing.append("on_null")
        if self.on_both is None:
            missing.append("on_both")
        if self.on_array is None:
            missing.append("on_array")
        if self.on_schema is None:
            missing.append("on_schema")
        if BothPresentRule.NEWER_WINS == self.on_both:
            if not self.recency_field:
                missing.append("recency_field(因 on_both=newer_wins 必填)")
            if self.tie_breaker is None:
                missing.append("tie_breaker(因 on_both=newer_wins 必填：recency 相等/缺失时的平局裁决)")
        if missing:
            raise ValueError(
                "MergeStrategy 缺少必需项，合并前必须【显式指定】每一项规则，禁止隐藏默认覆盖。缺失："
                + ", ".join(missing)
            )

    def resolve_keys(self, array_path: str) -> List[str]:
        """根据数组路径解析用于 UNION_BY_KEY 的主键字段列表。"""
        if array_path in self.array_key_overrides:
            return self.array_key_overrides[array_path]
        return self.array_key_default

    def describe(self) -> str:
        both = f"on_both={self.on_both.value if self.on_both else '?'}"
        if self.both_overrides:
            ov = ", ".join(f"{k}->{r.value}" for k, r in sorted(self.both_overrides.items()))
            both += f" | both_overrides{{{ov}}}"
        if self.on_both == BothPresentRule.NEWER_WINS:
            both += (
                f"(recency={self.recency_field or '?'}, "
                f"tie_breaker={self.tie_breaker.value if self.tie_breaker else '?'})"
            )
        arr = self.on_array.value if self.on_array else "?"
        if self.on_array == ArrayRule.REPLACE:
            arr += "(空数组保护:关)" if self.allow_empty_replace else "(空数组保护:开)"
        return (
            f"on_null={self.on_null.value if self.on_null else '?'}"
            f" | {both}"
            f" | on_array={arr}"
            f" | on_schema={self.on_schema.value if self.on_schema else '?'}"
        )


# ==================================================================
# 3. Change / MergePlan：每条变更都带"原因"，可审计、可预览
# ==================================================================

@dataclass
class Change:
    model_id: str
    field_path: str
    action: str          # add_record / add_field / fill_null / set_field / replace_old_new
                          # / skip / conflict / append_array / merge_array / upgrade_schema
    old: Any = None
    new: Any = None
    reason: str = ""


class MergePlan:
    """合并操作计划：收集所有 Change，dry-run 下只展示不执行。"""

    def __init__(self) -> None:
        self.changes: List[Change] = []

    def add(self, c: Change) -> None:
        self.changes.append(c)

    def conflicts(self) -> List[Change]:
        return [c for c in self.changes if c.action == "conflict"]

    def summary(self) -> Dict[str, int]:
        s: Dict[str, int] = {}
        for c in self.changes:
            s[c.action] = s.get(c.action, 0) + 1
        return s

    def describe(self, max_shown: int = 200) -> str:
        lines = []
        lines.append("=" * 78)
        lines.append("合并操作计划 (MergePlan)")
        lines.append("=" * 78)
        sm = self.summary()
        lines.append("变更统计: " + ", ".join(f"{k}={v}" for k, v in sm.items()) or "（无变更）")
        if "conflict" in sm:
            lines.append(f"⚠ 存在 {sm['conflict']} 处冲突，需人工处理（默认未改动）。")
        lines.append("-" * 78)
        for c in self.changes[:max_shown]:
            old_s = _short(c.old)
            new_s = _short(c.new)
            arrow = f"  {old_s} → {new_s}" if c.action not in ("add_record", "conflict") else ""
            lines.append(f"[{c.action}] {c.model_id} :: {c.field_path}{arrow}")
            lines.append(f"    原因: {c.reason}")
        if len(self.changes) > max_shown:
            lines.append(f"... 其余 {len(self.changes) - max_shown} 条省略")
        lines.append("=" * 78)
        return "\n".join(lines)


# ==================================================================
# 4. 工具函数
# ==================================================================

def _short(v: Any, n: int = 60) -> str:
    """把值压缩成可打印的短串。"""
    if v is None:
        return "null"
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 3] + "..."


def _get(obj: Any, path: str) -> Any:
    """按点号路径取值；中间缺失返回 None。"""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _set(obj: Any, path: str, value: Any, create: bool = False) -> None:
    """
    按点号路径写值（原地修改）。

    create=False（默认）：中间层缺失或非对象 → 抛 KeyError，绝不静默创建。
    create=True：中间层缺失时补空 dict 继续往下写。
    """
    parts = path.split(".")
    cur = obj
    for part in parts[:-1]:
        if not isinstance(cur, dict):
            raise KeyError(f"路径 {path!r} 的中间层 {part!r} 不是对象（实际 {type(cur).__name__}），无法写入")
        if part not in cur or not isinstance(cur.get(part), dict):
            if not create:
                raise KeyError(
                    f"路径 {path!r} 的中间层 {part!r} 缺失或非对象；"
                    f"确认要新建请加 --create-path"
                )
            cur[part] = {}
        cur = cur[part]
    if not isinstance(cur, dict):
        raise KeyError(f"路径 {path!r} 的末层父节点不是对象（实际 {type(cur).__name__}），无法写入")
    cur[parts[-1]] = value


def compare_version(a: str, b: str) -> int:
    """版本号比较，返回 -1/0/1（按点分数字逐段比较）。"""
    def parse(v: str) -> List[int]:
        out = []
        for seg in str(v).split("."):
            out.append(int(seg) if seg.isdigit() else 0)
        return out
    pa, pb = parse(a), parse(b)
    # 补齐长度
    for _ in range(len(pa), len(pb)):
        pa.append(0)
    for _ in range(len(pb), len(pa)):
        pb.append(0)
    return (pa > pb) - (pa < pb)


def _parse_date(s: Any) -> Optional[Tuple[int, int, int]]:
    """解析 YYYY / YYYY-MM / YYYY-MM-DD 为可比较元组；失败返回 None。"""
    if not isinstance(s, str):
        return None
    s = s.strip()
    fmts = ["%Y-%m-%d", "%Y-%m", "%Y"]
    for f in fmts:
        try:
            d = datetime.strptime(s, f)
            return (d.year, d.month, d.day)
        except ValueError:
            continue
    return None


def _key_of(item: Any, keys: List[str]) -> Tuple:
    """为数组项计算合并主键。"""
    if keys:
        if isinstance(item, dict):
            return tuple(item.get(k) for k in keys)
        return (item,)
    # 无主键 → 用整项内容作为身份（等价于按整项去重）
    return (_json_hash(item),)


def _json_hash(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


# ==================================================================
# 5. schema 规范化（对应 prompt.md v1.1 的结构性变更）
# ==================================================================

_TOP_LEVEL = ["schema_version", "basic_info", "architecture",
              "benchmarks", "pricing", "modality", "meta"]


def normalize_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    把记录规范化为完整 schema 1.1 结构（仅做"补全缺失结构"，不删真实数据）：
      - 补齐缺失的顶层键
      - basic_info / architecture / pricing / modality / meta 各子键补齐（缺则显式 null）
      - modality 三个子块（input/output/native_multimodal）补齐全部布尔键（null）
      - pricing 补齐四必采键 cached_input / cache_write / batch_input / batch_output（null）
      - benchmarks 三个子数组补齐
    关键修复：无论来源是完整记录还是分片补丁（如 p1 仅 arena），落库后都是
    结构完整的骨架，校验器（validate_model_data.py）不致因"缺顶层键/缺 modality 块/
    缺 pricing 必采键"而误报。merge_incoming 的新增记录路径必须过本函数。
    """
    rec = dict(rec)
    for k in _TOP_LEVEL:
        if k not in rec:
            rec[k] = {} if k != "schema_version" else "1.1"
    if not rec.get("schema_version"):
        rec["schema_version"] = "1.1"

    # basic_info
    bi = rec.setdefault("basic_info", {})
    for f in ("full_name", "version", "vendor", "release_date"):
        bi.setdefault(f, None)
    bi.setdefault("positioning", [])
    acc = bi.setdefault("access", {})
    for f in ("open_weights", "api", "local_deployment", "notes"):
        acc.setdefault(f, None)

    # architecture
    ar = rec.setdefault("architecture", {})
    for f in ("total_params_b", "active_params_b", "architecture_type",
              "context_window_tokens", "context_window_effective_tokens",
              "knowledge_cutoff", "notes"):
        ar.setdefault(f, None)

    # benchmarks
    b = rec.setdefault("benchmarks", {})
    for sub in ("self_reported", "independent", "arena_elo"):
        b.setdefault(sub, [])
    if isinstance(b.get("arena_elo"), dict):
        b["arena_elo"] = [b["arena_elo"]]

    # pricing（含四必采键）
    p = rec.setdefault("pricing", {})
    for f in ("currency", "unit", "input", "output", "cached_input", "cache_write",
              "batch_input", "batch_output", "free_tier", "promotions", "long_context",
              "effective_date", "source_url", "source_type", "confidence", "notes"):
        p.setdefault(f, None)

    # modality（三子块全布尔键，缺则显式 null）
    m = rec.setdefault("modality", {})
    MOD_BLOCKS = {
        "input": ["text", "image", "audio", "video", "pdf", "code", "web", "notes"],
        "output": ["text", "code", "image", "audio", "speech", "notes"],
        "native_multimodal": ["input_image", "input_audio", "input_video",
                              "output_image", "output_audio", "notes"],
    }
    for blk, keys in MOD_BLOCKS.items():
        if not isinstance(m.get(blk), dict):
            m[blk] = {}
        for kk in keys:
            m[blk].setdefault(kk, None)

    # meta
    mt = rec.setdefault("meta", {})
    for f in ("collected_at", "verified_at", "verification_status", "notes"):
        mt.setdefault(f, None)
    mt.setdefault("source_urls", [])

    return rec


def make_skeleton(model_id: str, schema_version: str = "1.1") -> Dict[str, Any]:
    """
    生成一条结构完整、值为 null 的空骨架记录。
    供：新增模型的直接起步、单模型采集 agent 的模板、测试构造。
    make_skeleton 后必须经 normalize_record 兜底（此处已直接调用）。
    """
    return normalize_record({"schema_version": schema_version, "model_id": model_id})


# ==================================================================
# 6. ModelDataStore：核心读写 / 合并引擎
# ==================================================================

class ModelDataStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self.records: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ---------- 读 ----------
    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path, encoding="utf-8-sig") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("//"):   # 跳过注释行
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                mid = obj.get("model_id")
                if mid is None:
                    continue
                self.records[mid] = obj

    def list_ids(self) -> List[str]:
        return list(self.records.keys())

    def read_record(self, model_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self.records.get(model_id))

    def read_field(self, model_id: str, path: str) -> Any:
        """指定字段直读：给定 model_id + 点号路径，返回该字段值。"""
        return _get(self.records.get(model_id), path)

    def read_compare(self, path: str, model_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        同名同类型字段横向对比：对多个 model_id 取同一个 path 的值。
        未指定 model_ids 则对比全部。
        """
        mids = model_ids if model_ids is not None else self.list_ids()
        return {mid: _get(self.records.get(mid), path) for mid in mids}

    def read_table(self, model_ids: List[str], paths: List[str]) -> List[Dict[str, Any]]:
        """多字段多模型横向表：rows = [{model_id, <path>: value, ...}, ...]。"""
        rows = []
        for mid in model_ids:
            row: Dict[str, Any] = {"model_id": mid}
            for p in paths:
                row[p] = _get(self.records.get(mid), p)
            rows.append(row)
        return rows

    def find(self, **filters: Any) -> List[str]:
        """按"路径=值"过滤，返回命中的 model_id 列表。"""
        out = []
        for mid, rec in self.records.items():
            ok = True
            for path, val in filters.items():
                if _get(rec, path) != val:
                    ok = False
                    break
            if ok:
                out.append(mid)
        return out

    def records_as_list(self) -> List[Dict[str, Any]]:
        return [copy.deepcopy(r) for r in self.records.values()]

    # ---------- 单字段写入（set） ----------
    def set_fields(
        self,
        model_ids: List[str],
        path: str,
        value: Any,
        expect: Any = None,
        create: bool = False,
        dry_run: bool = True,
        backup: bool = True,
    ) -> Dict[str, Any]:
        """
        把若干条记录的同一字段设成同一值。

        - expect 非 None 时作为乐观锁：任一条记录的当前值不等于 expect → 整体放弃，一条都不写
        - dry_run=True（默认）不落盘，只返回计划
        - 返回 {"changes": [(mid, old, new)], "errors": [(mid, 原因)]}
        """
        changes: List[Tuple[str, Any, Any]] = []
        errors: List[Tuple[str, str]] = []

        # 第一遍：全部校验通过才动手（all-or-nothing）
        for mid in model_ids:
            if mid not in self.records:
                errors.append((mid, "目标文件中不存在该 model_id"))
                continue
            old = _get(self.records[mid], path)
            if expect is not None and old != expect:
                errors.append((mid, f"乐观锁失败：当前值 {_short(old)} != --expect {_short(expect)}"))
                continue
            # 预演一次写入，确认路径可写（不改变真实记录）
            probe = copy.deepcopy(self.records[mid])
            try:
                _set(probe, path, copy.deepcopy(value), create=create)
            except KeyError as e:
                errors.append((mid, str(e)))
                continue
            changes.append((mid, old, value))

        if errors or dry_run:
            return {"changes": changes, "errors": errors, "written": False}

        # 第二遍：真正写入
        for mid, _old, _new in changes:
            _set(self.records[mid], path, copy.deepcopy(value), create=create)
        if backup:
            self._backup()
        self._save(self.records)
        return {"changes": changes, "errors": errors, "written": True}

    # ---------- 合并 ----------
    def merge_incoming(
        self,
        incoming: List[Dict[str, Any]],
        strategy: MergeStrategy,
        dry_run: bool = True,
        backup: bool = True,
    ) -> MergePlan:
        """
        把 incoming（若干模型记录）合并进本 store。

        安全性：
          - dry_run=True（默认）：只在内存副本上计算计划，绝不碰原文件。
          - dry_run=False：先备份原文件，再原子写回。
        每条变更都进入 plan.changes 并带原因，调用前可打印 plan.describe() 审查。
        """
        strategy.validate()
        plan = MergePlan()

        # dry-run 时用深拷贝，避免污染 store；真正写入时直接操作 self.records
        working = copy.deepcopy(self.records) if dry_run else self.records

        for rec in incoming:
            mid = rec.get("model_id")
            if mid is None:
                continue
            if mid not in working:
                # 关键修复：分片补丁（如 p1 仅 arena）直接 deepcopy 会导致新记录缺
                # basic_info/architecture/pricing/modality/meta 等结构 → 校验 ERROR。
                # 必须先按 schema 1.1 规范化为完整骨架（真实数据由 rec 提供，normalize
                # 只补缺失结构、不覆盖已有值），再落库。
                working[mid] = normalize_record(copy.deepcopy(rec))
                plan.add(Change(mid, "<record>", "add_record", None, None,
                                "目标无此 model_id：先按 schema 1.1 规范化为完整骨架再追加（新增，非覆盖）"))
            else:
                working[mid] = self._merge_into(working[mid], rec, strategy, plan, mid)

        if not dry_run:
            if backup:
                self._backup()
            self._save(working)
        return plan

    # ---------- 合并算法（递归、按字段路径） ----------
    def _merge_into(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any],
        strat: MergeStrategy,
        plan: MergePlan,
        mid: str,
    ) -> Dict[str, Any]:
        # 1) schema 版本处理
        tv = str(target.get("schema_version", ""))
        sv = str(source.get("schema_version", ""))
        cmp = compare_version(tv, sv)
        if cmp < 0:  # 目标较旧
            if strat.on_schema == SchemaRule.UPGRADE:
                target = normalize_record(target)
                target["schema_version"] = sv
                plan.add(Change(mid, "schema_version", "upgrade_schema", tv, sv,
                                "目标 schema 较旧，on_schema=upgrade：升级到来源版本并规范化结构"))
            elif strat.on_schema == SchemaRule.CONFLICT_IF_LOWER:
                plan.add(Change(mid, "schema_version", "conflict", tv, sv,
                                "目标 schema 较旧但 on_schema=conflict_if_lower：未改动"))
            elif strat.on_schema == SchemaRule.REQUIRE_EQUAL:
                plan.add(Change(mid, "schema_version", "conflict", tv, sv,
                                "on_schema=require_equal 但版本不一致：整条记为冲突"))
            # KEEP_TARGET：什么都不做
        elif cmp > 0 and strat.on_schema == SchemaRule.UPGRADE:
            plan.add(Change(mid, "schema_version", "skip", sv, tv,
                            "来源 schema 较旧，on_schema=upgrade：保留目标较新版本"))

        # 2) 记录级新旧判定（供 NEWER_WINS 使用）
        source_newer = self._compare_recency(target, source, strat.recency_field)

        # 3) 递归合并（从根开始，path 为空串表示根）
        merged = self._merge_dict(target, source, "", strat, source_newer, plan, mid)

        # 4) 若开启升级，合并结果再规范化一遍，确保新结构字段存在
        if strat.on_schema == SchemaRule.UPGRADE:
            merged = normalize_record(merged)
        return merged

    def _compare_recency(self, target: Dict, source: Dict, field_path: Optional[str]) -> Optional[bool]:
        """比较两记录的"新旧"。返回 True=来源更新，False=目标更新，None=相等/无法判定。"""
        if not field_path:
            return None
        td = _parse_date(_get(target, field_path))
        sd = _parse_date(_get(source, field_path))
        if td is None or sd is None:
            return None
        if sd > td:
            return True
        if td > sd:
            return False
        return None

    def _merge_dict(self, target, source, path, strat, source_newer, plan, mid):
        result = dict(target)
        for k, v in source.items():
            child = f"{path}.{k}" if path else k
            if k not in result:
                # 新增键：属于"补信息"，默认安全写入（不触发 on_null 的冲突语义）
                result[k] = copy.deepcopy(v)
                plan.add(Change(mid, child, "add_field", None, _short(v),
                                "来源存在目标缺失的键，作为新增字段写入（新增，非覆盖）"))
            else:
                result[k] = self._merge_value(result[k], v, child, strat, source_newer, plan, mid)
        return result

    def _merge_value(self, target, source, path, strat, source_newer, plan, mid):
        # 来源为空 → 没有可提供的信息，不动
        if source is None:
            return target

        # 目标为空（null 或缺失键已被补为 null 的情况）→ 由 on_null 决定
        if target is None:
            if strat.on_null == NullRule.TAKE_SOURCE:
                plan.add(Change(mid, path, "fill_null", None, _short(source),
                                "目标为空(null)，来源有值，on_null=take_source：用来源填充"))
                return source
            if strat.on_null == NullRule.KEEP_TARGET:
                plan.add(Change(mid, path, "skip", None, _short(source),
                                "目标为空(null)，但 on_null=keep_target：保留空"))
                return target
            # CONFLICT
            plan.add(Change(mid, path, "conflict", None, _short(source),
                            "目标为空(null)，on_null=conflict：未改动，需人工处理"))
            return target

        # 两者都有值 → 按类型递归或应用 on_both
        if isinstance(target, dict) and isinstance(source, dict):
            return self._merge_dict(target, source, path, strat, source_newer, plan, mid)
        if isinstance(target, list) and isinstance(source, list):
            return self._merge_list(target, source, path, strat, source_newer, plan, mid)

        # 标量且都有值
        if target == source:
            return target
        rule = strat.both_overrides.get(path, strat.on_both)
        if rule == BothPresentRule.SOURCE_WINS:
            plan.add(Change(mid, path, "set_field", _short(target), _short(source),
                            "两者皆有值且不同，on_both=source_wins：来源覆盖目标"))
            return source
        if rule == BothPresentRule.TARGET_WINS:
            plan.add(Change(mid, path, "skip", _short(target), _short(source),
                            "两者皆有值且不同，on_both=target_wins：保留目标"))
            return target
        if rule == BothPresentRule.NEWER_WINS:
            if source_newer is True:
                plan.add(Change(mid, path, "replace_old_new", _short(target), _short(source),
                                "两者皆有值且不同，依据 recency 判定来源更新：新数据覆盖旧数据"))
                return source
            if source_newer is False:
                plan.add(Change(mid, path, "skip", _short(target), _short(source),
                                "两者皆有值且不同，依据 recency 判定目标更新：保留目标"))
                return target
            # recency 缺失/相等 → 平局，按显式声明的 tie_breaker 裁决（P2 修复，禁止静默保旧）
            tb = strat.tie_breaker
            if tb == TieBreakerRule.SOURCE_WINS:
                plan.add(Change(mid, path, "set_field", _short(target), _short(source),
                                "两者皆有值且不同，recency 相等/缺失无法判定新旧，"
                                "tie_breaker=source_wins：来源（本次采集）覆盖目标"))
                return source
            if tb == TieBreakerRule.CONFLICT:
                plan.add(Change(mid, path, "conflict", _short(target), _short(source),
                                "两者皆有值且不同，recency 相等/缺失无法判定新旧，"
                                "tie_breaker=conflict：未改动，需人工处理"))
                return target
            # KEEP_TARGET
            plan.add(Change(mid, path, "skip", _short(target), _short(source),
                            "两者皆有值且不同，recency 相等/缺失无法判定新旧，"
                            "tie_breaker=keep_target：保留目标"))
            return target
        # CONFLICT
        plan.add(Change(mid, path, "conflict", _short(target), _short(source),
                        "两者皆有值且不同，on_both=conflict：未改动，需人工处理"))
        return target

    def _merge_list(self, target, source, path, strat, source_newer, plan, mid):
        policy = strat.on_array
        if policy == ArrayRule.REPLACE:
            # 空数组保护：来源为空、目标非空时 replace 等于「用空白覆盖已有条目」。
            # 2026-08-29 的 277 文件补合并就是这样静默抹掉 76 条记录共 80 个历史数组条目
            # （采集分片常只填 self_reported，independent 留空 []，replace 直接把骨架里的
            # T1 独立跑分整组清零）。确实要清空请显式传 --allow-empty-replace。
            if not source and target and not strat.allow_empty_replace:
                plan.add(Change(mid, path, "skip", _short(target), "[]",
                                "on_array=replace 但来源数组为空、目标非空：按空数组保护保留目标"
                                "（要清空请显式加 --allow-empty-replace）"))
                return target
            if target != source:
                plan.add(Change(mid, path, "set_field", _short(target), _short(source),
                                "on_array=replace：来源数组整体替换目标数组"))
            return copy.deepcopy(source)
        if policy == ArrayRule.APPEND_UNIQUE:
            result = list(target)
            added = 0
            for item in source:
                if item not in result:
                    result.append(copy.deepcopy(item))
                    added += 1
            if added:
                plan.add(Change(mid, path, "append_array", None, added,
                                f"on_array=append_unique：新增 {added} 条目标中不存在的项"))
            return result
        # UNION_BY_KEY
        keys = strat.resolve_keys(path)
        # 仅当数组项都是 dict 且带有主键字段时，主键才真正生效；否则退化为"整项去重"
        all_dict = all(isinstance(i, dict) for i in (target + source))
        effective_keys = keys if (keys and all_dict) else []
        tmap: Dict[Tuple, Tuple[int, Any]] = {}
        for i, item in enumerate(target):
            tmap[_key_of(item, effective_keys)] = (i, item)
        result = list(target)
        merged = 0
        appended = 0
        for item in source:
            k = _key_of(item, effective_keys)
            if k in tmap:
                idx, titem = tmap[k]
                if isinstance(titem, dict) and isinstance(item, dict):
                    new_item = self._merge_dict(titem, item, f"{path}[{idx}]",
                                               strat, source_newer, plan, mid)
                    if new_item != titem:   # 仅当真有变化才记为合并
                        result[idx] = new_item
                        merged += 1
                elif titem != item:
                    result[idx] = copy.deepcopy(item)
                    plan.add(Change(mid, f"{path}[{idx}]", "set_field", _short(titem),
                                    _short(item), "同主键数组项非字典且不同：来源覆盖"))
                    merged += 1
                # 二者完全相同 → 不记为变更（避免自合并时的噪声）
            else:
                result.append(copy.deepcopy(item))
                appended += 1
        if merged or appended:
            key_desc = ",".join(effective_keys) if effective_keys else "整项内容"
            plan.add(Change(mid, path, "merge_array", None,
                            f"合并 {merged} 项 / 新增 {appended} 项",
                            f"on_array=union_by_key（主键={key_desc}）"))
        return result

    # ---------- 写回 / 备份 ----------
    def _backup(self) -> None:
        if os.path.exists(self.path):
            bak = self.path + ".bak"
            try:
                with open(self.path, "rb") as fsrc, open(bak, "wb") as fdst:
                    fdst.write(fsrc.read())
            except OSError:
                pass

    def _save(self, records: Dict[str, Dict[str, Any]]) -> None:
        """原子写：先写同目录临时文件，再 os.replace 覆盖。

        Windows 上 os.replace 会被瞬时锁定拦截（实时杀毒 / 索引器扫描刚写入的
        大文件），报错 `PermissionError: [WinError 5] 拒绝访问`。实测 5.8MB 主库
        随机复现，重试一次即成功。故加重试退避，避免整次写入功亏一篑。
        """
        import time

        d = os.path.dirname(os.path.abspath(self.path)) or "."
        tmp = os.path.join(d, f".{os.path.basename(self.path)}.tmp.{os.getpid()}")
        # newline='\n' 必须显式指定：Windows 下默认会写成 CRLF，而 .gitattributes 强制 LF，
        # 单行 JSONL 里混入 \r 会造成解析隐患与整文件 diff 噪声（DEPLOY.md §5.2）
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            for rec in records.values():
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        last_err = None
        for attempt in range(8):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError as e:          # Windows 瞬时锁定
                last_err = e
                time.sleep(0.3 * (attempt + 1))   # 0.3s → 2.4s 线性退避
            except OSError:
                raise
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise last_err


# ==================================================================
# 7. CLI
# ==================================================================

def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _load_gate():
    """
    加载同目录 validate_model_data.py 的 check_record(rec) -> (errors, warns)。
    加载失败返回 None（门禁校验是增值项，不该阻断写入本身）。
    """
    import importlib.util

    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_model_data.py")
    if not os.path.exists(p):
        return None
    try:
        spec = importlib.util.spec_from_file_location("_vmd_gate", p)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, "check_record", None)
    except Exception:
        return None


def _parse_json_arg(s: str, what: str) -> Any:
    """解析命令行传入的 JSON 字面量。字符串必须写成 '"xxx"'（带引号）。"""
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"--{what} 不是合法 JSON：{s!r}（{e.msg}）。\n"
            f"提示：字符串要带引号，如 --{what} '\"工具调用增强\"'；"
            f"数组如 --{what} '[\"旗舰\",\"中端\"]'；null 直接写 null"
        )


def _enum_val(enum_cls, s: str):
    try:
        return enum_cls(s)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise SystemExit(f"非法取值 '{s}'，可选：{allowed}")


def _parse_both_overrides(items: List[str]) -> Dict[str, BothPresentRule]:
    """解析 路径:规则 形式的覆盖列表；解析失败立即报错退出（宁可拒绝不静默忽略）。"""
    out: Dict[str, BothPresentRule] = {}
    for it in items:
        if ":" not in it:
            raise SystemExit(f"--on-both-override 非法格式 '{it}'，应为 路径:规则，如 meta.collected_at:source_wins")
        path, rule = it.split(":", 1)
        if not path:
            raise SystemExit(f"--on-both-override 路径为空 '{it}'")
        out[path] = _enum_val(BothPresentRule, rule)
    return out


def _build_strategy(args) -> MergeStrategy:
    return MergeStrategy(
        on_null=_enum_val(NullRule, args.on_null),
        on_both=_enum_val(BothPresentRule, args.on_both),
        recency_field=args.recency,
        tie_breaker=_enum_val(TieBreakerRule, args.tie_breaker) if getattr(args, "tie_breaker", None) else None,
        on_array=_enum_val(ArrayRule, args.on_array),
        array_key_default=args.array_key or [],
        array_key_overrides=dict(args.array_key_override or {}),
        on_schema=_enum_val(SchemaRule, args.on_schema),
        both_overrides=_parse_both_overrides(getattr(args, "on_both_override", None) or []),
        allow_empty_replace=bool(getattr(args, "allow_empty_replace", False)),
    )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="主流大模型静态数据集 JSONL 显式读写 / 合并工具（默认 dry-run）")
    sub = p.add_subparsers(dest="cmd", required=True)

    # read
    pr = sub.add_parser("read", help="指定字段直读")
    pr.add_argument("--file", required=True)
    pr.add_argument("--model", required=True)
    pr.add_argument("--field", required=True, help="点号路径，如 architecture.total_params_b")

    # compare
    pc = sub.add_parser("compare", help="同名同类型字段横向对比多家")
    pc.add_argument("--file", required=True)
    pc.add_argument("--field", required=True)
    pc.add_argument("--models", nargs="*", default=None)

    # table
    pt = sub.add_parser("table", help="多字段多模型横向表")
    pt.add_argument("--file", required=True)
    pt.add_argument("--models", nargs="+", required=True)
    pt.add_argument("--fields", nargs="+", required=True)

    # list
    pl = sub.add_parser("list", help="列出所有 model_id")
    pl.add_argument("--file", required=True)

    # set —— 单字段写入（主库唯一直接编辑入口；默认 dry-run）
    ps = sub.add_parser("set", help="把若干条记录的同一字段设为同一值（默认 dry-run，需 --apply）")
    ps.add_argument("--file", required=True, help="目标 JSONL（通常是 model_data_v2.jsonl）")
    ps.add_argument("--models", nargs="+", required=True, help="一个或多个 model_id")
    ps.add_argument("--field", required=True, help="点号路径，如 basic_info.positioning")
    ps.add_argument("--value", required=True, help="新值，JSON 字面量，如 '[\"工具调用增强\"]' 或 '\"中端\"' 或 null")
    ps.add_argument("--expect", default=None,
                    help="乐观锁：当前值必须等于该 JSON 值，否则整体放弃（一条都不写）")
    ps.add_argument("--create-path", action="store_true",
                    help="中间层缺失时自动补空对象（默认拒绝，避免静默造结构）")
    ps.add_argument("--apply", action="store_true", help="真正写入（默认仅 dry-run 预览）")
    ps.add_argument("--no-backup", action="store_true", help="写入时不自动备份")
    ps.add_argument("--no-gate", action="store_true", help="写入后不自动跑门禁校验")

    # merge
    pm = sub.add_parser("merge", help="显式合并（默认 dry-run，需 --apply 才写）")
    pm.add_argument("--file", required=True, help="目标 JSONL")
    pm.add_argument("--incoming", required=True, nargs="+",
                    help="待合并的 JSONL（另一 Agent 产出）；可给多个文件、目录（展开其下 *.jsonl），"
                         "或 @清单文件（每行一个路径，规避命令行长度上限）。"
                         "多文件时在内存中依次合并，最后只落盘一次、只备份一次")
    pm.add_argument("--on-null", required=True, help="NullRule: take_source|keep_target|conflict")
    pm.add_argument("--on-both", required=True, help="BothPresentRule: source_wins|target_wins|newer_wins|conflict")
    pm.add_argument("--on-both-override", nargs="*", default=[],
                    help="路径:规则 形式（可重复），如 meta.collected_at:source_wins；"
                         "对指定字段路径覆盖 --on-both 规则")
    pm.add_argument("--recency", default=None, help="newer_wins 依据的日期路径，如 meta.collected_at")
    pm.add_argument("--tie-breaker", default=None,
                    help="newer_wins 且 recency 相等/缺失时的平局裁决：keep_target|source_wins|conflict（必填）")
    pm.add_argument("--on-array", required=True, help="ArrayRule: replace|append_unique|union_by_key")
    pm.add_argument("--allow-empty-replace", action="store_true",
                    help="默认关闭：on_array=replace 且来源数组为空、目标非空时保留目标（空数组保护）。"
                         "显式传本参数才允许用空数组清空目标已有条目")
    pm.add_argument("--array-key", nargs="*", default=[], help="UNION_BY_KEY 默认主键，如 benchmark config date")
    pm.add_argument("--array-key-override", nargs="*", default=[],
                    help="路径:键1,键2 形式，可重复，如 benchmarks.arena_elo:sub_benchmark,date")
    pm.add_argument("--on-schema", required=True, help="SchemaRule: upgrade|keep_target|require_equal|xxx")
    pm.add_argument("--apply", action="store_true", help="真正写入（默认仅 dry-run 出计划）")
    pm.add_argument("--no-backup", action="store_true", help="写入时不自动备份")

    args = p.parse_args(argv)

    if args.cmd == "read":
        store = ModelDataStore(args.file)
        val = store.read_field(args.model, args.field)
        print(json.dumps({args.field: val}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "compare":
        store = ModelDataStore(args.file)
        res = store.read_compare(args.field, args.models)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "table":
        store = ModelDataStore(args.file)
        rows = store.read_table(args.models, args.fields)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "list":
        store = ModelDataStore(args.file)
        for mid in store.list_ids():
            print(mid)
        return 0

    if args.cmd == "set":
        value = _parse_json_arg(args.value, "value")
        expect = _parse_json_arg(args.expect, "expect") if args.expect is not None else None

        store = ModelDataStore(args.file)
        if not store.records:
            print(f"❌ 目标文件为空或不存在：{args.file}", file=sys.stderr)
            return 2

        mode = "APPLY（真实写入）" if args.apply else "DRY-RUN（仅预览，不改动文件）"
        print(f"# 目标文件：{args.file}（{len(store.list_ids())} 条）")
        print(f"# 字段路径：{args.field}")
        print(f"# 新值：{_short(value)}")
        print(f"# 乐观锁：{_short(expect) if expect is not None else '（未设）'}")
        print(f"# 备份：{'关闭' if args.no_backup else '开启（写入前自动 .bak）'}")
        print(f"# 模式：{mode}\n")

        gate = None if args.no_gate else _load_gate()
        before = {}
        if gate:
            for mid in args.models:
                rec = store.records.get(mid)
                if rec is not None:
                    e, w = gate(rec)
                    before[mid] = (len(e), len(w))

        res = store.set_fields(
            args.models, args.field, value,
            expect=expect, create=args.create_path,
            dry_run=not args.apply, backup=not args.no_backup,
        )

        for mid, old, new in res["changes"]:
            print(f"  {mid}\n    {args.field}: {_short(old)} → {_short(new)}")
        for mid, why in res["errors"]:
            print(f"  ❌ {mid}: {why}")

        if res["errors"]:
            print(f"\n⛔ 有 {len(res['errors'])} 条校验失败，全部放弃（未写入任何记录）。")
            return 2

        if not res["written"]:
            print(f"\n⚠ DRY-RUN 预览：{len(res['changes'])} 条待改，原文件未改动。确认后加 --apply。")
            return 0

        print(f"\n✅ 已写入 {len(res['changes'])} 条。")

        if gate:
            print("\n# 门禁复检（受影响记录）：")
            bad = 0
            for mid in args.models:
                rec = store.records.get(mid)
                if rec is None:
                    continue
                e, w = gate(rec)
                be, bw = before.get(mid, (0, 0))
                mark = "OK " if not e else "ERR"
                delta = ""
                if (len(e), len(w)) != (be, bw):
                    delta = f"  （原 ERROR {be} / WARN {bw}）"
                print(f"  [{mark}] {mid}: ERROR {len(e)} / WARN {len(w)}{delta}")
                for msg in e:
                    print(f"         - {msg}")
                bad += len(e)
            if bad:
                print(f"\n⚠ 写入成功，但这些记录现共 {bad} 项 ERROR。可用原值再跑一次 set 回滚，"
                      f"或从 {args.file}.bak 恢复。")
            else:
                print("\n  门禁通过（ERROR 0）。")
        return 0

    if args.cmd == "merge":
        overrides: Dict[str, List[str]] = {}
        for kv in args.array_key_override:
            if ":" not in kv:
                raise SystemExit("array-key-override 格式应为 路径:键1,键2")
            k, v = kv.split(":", 1)
            overrides[k] = [x for x in v.split(",") if x]
        args.array_key_override = overrides

        strat = _build_strategy(args)
        try:
            strat.validate()
        except ValueError as e:
            print(f"❌ 策略校验失败：{e}", file=sys.stderr)
            return 2

        target_store = ModelDataStore(args.file)

        # --incoming 支持多文件 / 目录：展开成文件列表，依次读入拼成一份来源
        src_files: List[str] = []
        for item in args.incoming:
            if item.startswith("@"):                     # 清单文件：每行一个路径
                list_path = item[1:]
                with open(list_path, encoding="utf-8") as lf:
                    src_files.extend(ln.strip() for ln in lf if ln.strip())
            elif os.path.isdir(item):
                src_files.extend(sorted(
                    os.path.join(item, n) for n in os.listdir(item)
                    if n.endswith(".jsonl") and not n.startswith(".")
                ))
            else:
                src_files.append(item)
        if not src_files:
            raise SystemExit(f"--incoming 未匹配到任何 .jsonl 文件：{args.incoming}")

        incoming: List[Dict[str, Any]] = []
        for fp in src_files:
            incoming.extend(_load_jsonl(fp))

        print(f"# 合并策略：{strat.describe()}")
        print(f"# 目标文件：{args.file}（{len(target_store.list_ids())} 条）")
        print(f"# 来源文件：{len(src_files)} 个（{len(incoming)} 条记录）")
        if len(src_files) <= 5:
            for fp in src_files:
                print(f"#   - {fp}")
        else:
            for fp in src_files[:3]:
                print(f"#   - {fp}")
            print(f"#   ... 另有 {len(src_files) - 3} 个")
        print(f"# 模式：{'APPLY（真实写入）' if args.apply else 'DRY-RUN（仅预览，不改动文件）'}\n")

        plan = target_store.merge_incoming(
            incoming, strategy=strat, dry_run=not args.apply, backup=not args.no_backup
        )
        print(plan.describe())
        if not args.apply:
            print("\n⚠ 以上为 DRY-RUN 预览，原文件未改动。确认无误后加 --apply 执行写入。")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
