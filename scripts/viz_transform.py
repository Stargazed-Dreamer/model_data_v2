#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""model_data 可视化数据层：JSONL -> 宽表 + 聚合 + 字段字典。

被 viz_server.py 调用；也可独立运行做冒烟测试：
    python viz_transform.py --smoke
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent  # model_data 根目录
DEFAULT_JSONL = BASE_DIR / "model_data_v2.jsonl"

# ---------------------------------------------------------------------------
# 字段字典：宽表列 -> (中文翻译, 类型, 说明)
# type: num=数值 str=文本 bool=布尔 date=日期(YYYY-MM 或 YYYY-MM-DD) list=数组长度可作数值
# ---------------------------------------------------------------------------

FIELD_DICT: dict[str, dict[str, str]] = {}


def _reg(col: str, label: str, typ: str, group: str) -> None:
    FIELD_DICT[col] = {"label": label, "type": typ, "group": group}


_reg("full_name", "模型名称", "str", "基本信息")
_reg("version", "版本", "str", "基本信息")
_reg("vendor", "厂商", "str", "基本信息")
_reg("release_date", "发布日期", "date", "基本信息")
_reg("positioning_count", "定位标签数", "num", "基本信息")
_reg("open_weights", "开放权重", "bool", "基本信息")
_reg("api_access", "API 可用", "bool", "基本信息")
_reg("local_deployment", "可本地部署", "bool", "基本信息")

_reg("total_params_b", "总参数量(B)", "num", "架构")
_reg("active_params_b", "激活参数量(B)", "num", "架构")
_reg("context_window_tokens", "上下文窗口(tokens)", "num", "架构")
_reg("context_window_effective_tokens", "有效上下文(tokens)", "num", "架构")

_reg("self_reported_count", "自报跑分条数", "num", "跑分")
_reg("independent_count", "独立跑分条数", "num", "跑分")
_reg("arena_elo_count", "Arena Elo 条数", "num", "跑分")

_reg("price_input", "输入价($/M tokens)", "num", "定价")
_reg("price_output", "输出价($/M tokens)", "num", "定价")
_reg("price_cached_input", "缓存输入价($/M)", "num", "定价")
_reg("price_batch_input", "批量输入价($/M)", "num", "定价")

_reg("in_text", "输入·文本", "bool", "模态")
_reg("in_image", "输入·图像", "bool", "模态")
_reg("in_audio", "输入·音频", "bool", "模态")
_reg("in_video", "输入·视频", "bool", "模态")
_reg("in_pdf", "输入·PDF", "bool", "模态")
_reg("out_text", "输出·文本", "bool", "模态")
_reg("out_code", "输出·代码", "bool", "模态")
_reg("out_image", "输出·图像", "bool", "模态")
_reg("out_audio", "输出·语音", "bool", "模态")

_reg("collected_at", "采集日期", "date", "元信息")
_reg("verification_status", "验证状态", "str", "元信息")
_reg("source_url_count", "来源 URL 数", "num", "元信息")


# ---------------------------------------------------------------------------
# 展平
# ---------------------------------------------------------------------------

def _to_tristate(v: Any) -> int | None:
    """null->None(缺失), True/False 原样; 'unknown' 等字符串视为缺失。"""
    if v is None or isinstance(v, str):
        return None
    return 1 if v else 0


def flatten_record(d: dict[str, Any]) -> dict[str, Any]:
    bi = d.get("basic_info") or {}
    arch = d.get("architecture") or {}
    bench = d.get("benchmarks") or {}
    price = d.get("pricing") or {}
    mod_in = ((d.get("modality") or {}).get("input")) or {}
    mod_out = ((d.get("modality") or {}).get("output")) or {}
    meta = d.get("meta") or {}

    def _f(key: str) -> float | None:
        v = price.get(key)
        if isinstance(v, (int, float)):
            return float(v)
        return None

    release = bi.get("release_date")
    row: dict[str, Any] = {
        "model_id": d.get("model_id"),
        "full_name": bi.get("full_name"),
        "version": bi.get("version"),
        "vendor": bi.get("vendor"),
        "release_date": release,
        "positioning_count": len(bi.get("positioning") or []) or None,
        "open_weights": _to_tristate((bi.get("access") or {}).get("open_weights")),
        "api_access": _to_tristate((bi.get("access") or {}).get("api")),
        "local_deployment": _to_tristate((bi.get("access") or {}).get("local_deployment")),
        "total_params_b": arch.get("total_params_b"),
        "active_params_b": arch.get("active_params_b"),
        "context_window_tokens": arch.get("context_window_tokens"),
        "context_window_effective_tokens": arch.get("context_window_effective_tokens"),
        "self_reported_count": len(bench.get("self_reported") or []) or None,
        "independent_count": len(bench.get("independent") or []) or None,
        "arena_elo_count": len(bench.get("arena_elo") or []) or None,
        "price_input": _f("input"),
        "price_output": _f("output"),
        "price_cached_input": _f("cached_input"),
        "price_batch_input": _f("batch_input"),
        "in_text": _to_tristate(mod_in.get("text")),
        "in_image": _to_tristate(mod_in.get("image")),
        "in_audio": _to_tristate(mod_in.get("audio")),
        "in_video": _to_tristate(mod_in.get("video")),
        "in_pdf": _to_tristate(mod_in.get("pdf")),
        "out_text": _to_tristate(mod_out.get("text")),
        "out_code": _to_tristate(mod_out.get("code")),
        "out_image": _to_tristate(mod_out.get("image")),
        "out_audio": _to_tristate(mod_out.get("speech")),
        "collected_at": meta.get("collected_at"),
        "verification_status": meta.get("verification_status"),
        "source_url_count": len(meta.get("source_urls") or []) or None,
    }
    # arena elo：取 is_primary 或 text 子榜作为代表值
    elos = [
        e.get("score") for e in (bench.get("arena_elo") or [])
        if isinstance(e, dict) and isinstance(e.get("score"), (int, float))
    ]
    primary = [
        e.get("score") for e in (bench.get("arena_elo") or [])
        if isinstance(e, dict) and e.get("is_primary")
        and isinstance(e.get("score"), (int, float))
    ]
    row["arena_elo_max"] = (primary[0] if len(primary) == 1 else max(elos)) if elos else None
    _reg("arena_elo_max", "Arena Elo(主榜)", "num", "跑分")
    _reg("independent_best_gsm8k", "GSM8K 最佳分(独立)", "num", "跑分")
    _reg("independent_best_mmlu", "MMLU 最佳分(独立)", "num", "跑分")
    _reg("independent_best_gpqa", "GPQA 最佳分(独立)", "num", "跑分")

    # 独立跑分常见 benchmark 的最佳分（0-1），便于做性能对比图
    _BENCH_KEYS = {"gsm8k": "independent_best_gsm8k", "mmlu": "independent_best_mmlu",
                   "gpqa": "independent_best_gpqa"}
    best: dict[str, float] = {}
    for e in (bench.get("independent") or []):
        if not isinstance(e, dict):
            continue
        name = (e.get("benchmark") or "").lower()
        score = e.get("score")
        for k, col in _BENCH_KEYS.items():
            if k in name and isinstance(score, (int, float)):
                if col not in best or score > best[col]:
                    best[col] = float(score)
    row.update(best)
    return row


def load_rows(jsonl_path: Path = DEFAULT_JSONL) -> list[dict[str, Any]]:
    rows = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(flatten_record(json.loads(line)))
            except json.JSONDecodeError:
                continue
    return rows


# ---------------------------------------------------------------------------
# 字段字典扫描（填充率）
# ---------------------------------------------------------------------------

def build_schema_info(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for col, info in FIELD_DICT.items():
        filled = sum(1 for r in rows if r.get(col) is not None)
        true_cnt = sum(1 for r in rows if r.get(col) == 1)
        false_cnt = sum(1 for r in rows if r.get(col) == 0)
        entry = {
            "column": col,
            "label": info["label"],
            "type": info["type"],
            "filled": filled,
            "fill_rate": round(filled / total * 100, 1) if total else 0.0,
            "true_cnt": true_cnt,
            "false_cnt": false_cnt,
        }
        groups[info["group"]].append(entry)

    field_groups = []
    order = ["基本信息", "架构", "跑分", "定价", "模态", "元信息"]
    for g in sorted(groups.keys(), key=lambda x: order.index(x) if x in order else 99):
        field_groups.append({"group": g, "fields": groups[g]})
    return {
        "total_models": total,
        "field_groups": field_groups,
    }


# ---------------------------------------------------------------------------
# 预聚合
# ---------------------------------------------------------------------------

def build_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    vendor_cnt = Counter(r["vendor"] or "未知" for r in rows)
    year_cnt = Counter(
        (r["release_date"] or "")[:4] for r in rows if r.get("release_date")
    )
    month_cnt = Counter(r["release_date"] for r in rows if r.get("release_date"))

    key_fields = ["price_input", "price_output", "context_window_tokens",
                  "total_params_b", "arena_elo_max", "independent_best_mmlu",
                  "independent_best_gsm8k", "in_image", "positioning_count"]
    fill = {k: round(sum(1 for r in rows if r.get(k) is not None) / total * 100, 1)
            for k in key_fields} if total else {}

    open_w_true = sum(1 for r in rows if r.get("open_weights") == 1)
    api_true = sum(1 for r in rows if r.get("api_access") == 1)

    elo_top = sorted(
        (r for r in rows if r.get("arena_elo_max") is not None),
        key=lambda r: -r["arena_elo_max"],
    )[:30]
    elo_top = [
        {
            "model_id": r["model_id"], "full_name": r["full_name"],
            "vendor": r["vendor"], "elo": r["arena_elo_max"],
            "price_input": r.get("price_input"), "price_output": r.get("price_output"),
        }
        for r in elo_top
    ]

    scatter_pts = [
        {
            "name": r.get("full_name") or r["model_id"],
            "vendor": r.get("vendor") or "未知",
            "x": r.get("price_input"), "y": r.get("price_output"),
            "elo": r.get("arena_elo_max"),
            "ctx": r.get("context_window_tokens"),
            "params": r.get("total_params_b"),
        }
        for r in rows if r.get("price_input") is not None and r.get("price_output") is not None
    ]

    verif_cnt = Counter(r.get("verification_status") or "缺失" for r in rows)

    return {
        "total_models": total,
        "vendor_count": len(vendor_cnt),
        "vendor_dist": vendor_cnt.most_common(),
        "year_dist": sorted(year_cnt.items()),
        "month_dist": sorted(month_cnt.items()),
        "key_fill_rates": fill,
        "access": {"open_weights": open_w_true, "api": api_true},
        "verification_dist": verif_cnt.most_common(),
        "elo_top": elo_top,
        "price_scatter": scatter_pts,
    }


# ---------------------------------------------------------------------------

def build_all(jsonl_path: Path = DEFAULT_JSONL) -> dict[str, Any]:
    rows = load_rows(jsonl_path)
    schema = build_schema_info(rows)
    aggregates = build_aggregates(rows)
    return {"rows": rows, "schema": schema, "aggregates": aggregates}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    data = build_all()
    print(f"models={data['aggregates']['total_models']}")
    print(f"vendors={data['aggregates']['vendor_count']}")
    print(f"fill={data['aggregates']['key_fill_rates']}")
    print(f"elo_top={len(data['aggregates']['elo_top'])}")
    print(f"scatter_pts={len(data['aggregates']['price_scatter'])}")
    print(f"dict_fields={len(FIELD_DICT)}")


if __name__ == "__main__":
    main()
