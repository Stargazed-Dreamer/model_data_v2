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
_reg("license", "开源协议", "str", "基本信息")
_reg("open_weights", "开放权重", "bool", "基本信息")
_reg("api_access", "API 可用", "bool", "基本信息")
_reg("local_deployment", "可本地部署", "bool", "基本信息")

_reg("total_params_b", "总参数量(B)", "num", "架构")
_reg("active_params_b", "激活参数量(B)", "num", "架构")
_reg("context_window_tokens", "上下文窗口(tokens)", "num", "架构")
_reg("context_window_effective_tokens", "有效上下文(tokens)", "num", "架构")
_reg("knowledge_cutoff", "知识截止日期", "date", "架构")

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
    # 保留 arena_elo 子榜数组 + source_urls，供子榜覆盖 / 来源可信度分析使用
    arena_elo_arr = [
        {
            "sub_benchmark": e.get("sub_benchmark"),
            "score": e.get("score") if isinstance(e.get("score"), (int, float)) else None,
            "source_url": e.get("source_url"),
            "is_primary": bool(e.get("is_primary")),
        }
        for e in (bench.get("arena_elo") or [])
        if isinstance(e, dict)
    ]
    row: dict[str, Any] = {
        "model_id": d.get("model_id"),
        "full_name": bi.get("full_name"),
        "version": bi.get("version"),
        "vendor": bi.get("vendor"),
        "release_date": release,
        "positioning": bi.get("positioning") or [],
        "positioning_count": len(bi.get("positioning") or []) or None,
        "open_weights": _to_tristate((bi.get("access") or {}).get("open_weights")),
        "api_access": _to_tristate((bi.get("access") or {}).get("api")),
        "local_deployment": _to_tristate((bi.get("access") or {}).get("local_deployment")),
        "total_params_b": arch.get("total_params_b"),
        "active_params_b": arch.get("active_params_b"),
        "context_window_tokens": arch.get("context_window_tokens"),
        "context_window_effective_tokens": arch.get("context_window_effective_tokens"),
        "knowledge_cutoff": arch.get("knowledge_cutoff"),
        "license": (bi.get("license") or {}).get("name") if isinstance(bi.get("license"), dict) else bi.get("license"),
        "self_reported_count": len(bench.get("self_reported") or []) or None,
        "independent_count": len(bench.get("independent") or []) or None,
        "arena_elo_count": len(bench.get("arena_elo") or []) or None,
        "arena_elo_subs": arena_elo_arr,  # 新增：子榜数组
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
        "source_urls": [u for u in (meta.get("source_urls") or []) if isinstance(u, str)],  # 新增
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
    _reg("independent_best_humaneval", "HumanEval 最佳分(独立)", "num", "跑分")
    _reg("independent_best_math", "MATH 最佳分(独立)", "num", "跑分")
    _reg("independent_best_bbh", "BBH 最佳分(独立)", "num", "跑分")
    _reg("independent_best_musr", "MuSR 最佳分(独立)", "num", "跑分")
    _reg("independent_best_ifeval", "IFEval 最佳分(独立)", "num", "跑分")
    _reg("cost_per_elo", "单位 Elo 成本($/Elo, 输入价)", "num", "定价")
    _reg("moe_sparsity", "MoE 稀疏度(active/total)", "num", "架构")
    _reg("vendor_geo", "厂商地缘", "str", "基本信息")

    # 独立跑分常见 benchmark 的最佳分（0-1），便于做雷达对比图
    _BENCH_KEYS = {
        "gsm8k": "independent_best_gsm8k",
        "mmlu": "independent_best_mmlu",
        "gpqa": "independent_best_gpqa",
        "humaneval": "independent_best_humaneval",
        "human_eval": "independent_best_humaneval",
        "math": "independent_best_math",
        "bbh": "independent_best_bbh",
        "musr": "independent_best_musr",
        "ifeval": "independent_best_ifeval",
    }
    best: dict[str, float] = {}
    for e in (bench.get("independent") or []):
        if not isinstance(e, dict):
            continue
        name = (e.get("benchmark") or "").lower()
        score = e.get("score")
        for k, col in _BENCH_KEYS.items():
            if k in name and isinstance(score, (int, float)):
                # 自动判断 0-100 vs 0-1，统一为 0-1
                s = float(score)
                if s > 1.5:
                    s = s / 100.0
                if col not in best or s > best[col]:
                    best[col] = s
    row.update(best)

    # 单位 Elo 成本：输入价 / Elo（仅当两者都有）
    elo_val = row.get("arena_elo_max")
    price_in = row.get("price_input")
    if elo_val and price_in and elo_val > 0:
        row["cost_per_elo"] = round(price_in / elo_val, 4)

    # MoE 稀疏度
    ap = row.get("active_params_b")
    tp = row.get("total_params_b")
    if ap and tp and tp > 0:
        row["moe_sparsity"] = round(ap / tp, 3)

    # 厂商地缘分组（粗粒度关键词映射，仅作可视化用，非权威归类）
    v = (bi.get("vendor") or "").lower()
    geo = "其他"
    CN_KEYS = ["alibaba", "qwen", "baidu", "ernie", "zhipu", "z.ai", "glm",
               "deepseek", "kimi", "moonshot", "minimax", "baichuan", "01-ai", "01.ai",
               "yi-", "yi ", "xiaomi", "meituan", "sensetime", "kunlun", "360",
               "tencent", "huawei", "iflytek", "sino", "datacanvas", "unicom",
               "shanghai ai", "tsinghua", "sichuan", "youth",
               "tongyi", "huoshan", "volcengine", "bytedance", "longcat", "talkingdata"]
    US_KEYS = ["openai", "anthropic", "google", "meta ", "metaai", "meta ai",
               "nvidia", "microsoft", "amazon", "apple", "xai", "perplexity",
               "cohere", "databricks", "ibm", "neeva", "huggingface",
               "facebook", "eleuther", "stability", "ai21"]
    EU_KEYS = ["mistral", "deepmind", "alephalpha", "aleph alpha", "phil",
               "silicon", "jetbrains", "lighton", "kobold", "deutsches", "silo"]
    if any(k in v for k in CN_KEYS):
        geo = "中国"
    elif any(k in v for k in US_KEYS):
        geo = "美国"
    elif any(k in v for k in EU_KEYS):
        geo = "欧洲"
    row["vendor_geo"] = geo

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
# 扩展聚合（6 页架构新增）
# ---------------------------------------------------------------------------

# positioning 标签中英文映射
POSITIONING_ORDER = ["旗舰", "轻量", "推理增强", "中端", "多模态", "工具调用增强"]


def build_vendor_capability(rows: list[dict[str, Any]], top_n: int = 20) -> dict[str, Any]:
    """厂商 × positioning 能力矩阵（Top N 厂商 + 其他）"""
    vendor_cnt = Counter(r["vendor"] or "未知" for r in rows)
    top_vendors = [v for v, _ in vendor_cnt.most_common(top_n)]

    # 收集所有 positioning 标签
    all_tags: set[str] = set()
    for r in rows:
        for p in r.get("positioning") or []:
            all_tags.add(p)
    # 按 POSITIONING_ORDER 排序，未列入的按字典序追加
    ordered = [t for t in POSITIONING_ORDER if t in all_tags]
    extra = sorted(all_tags - set(POSITIONING_ORDER))
    tags = ordered + extra

    # 矩阵：vendor x positioning
    matrix: dict[str, Counter] = {v: Counter() for v in top_vendors}
    matrix["其他"] = Counter()
    for r in rows:
        v = r["vendor"] or "未知"
        target = v if v in matrix else "其他"
        for p in r.get("positioning") or []:
            matrix[target][p] += 1

    # 转置为 ECharts 可用格式（行=vendor，列=positioning，值=数量）
    return {
        "vendors": top_vendors + ["其他"],
        "positioning_tags": tags,
        "matrix": [[matrix[v][t] for t in tags] for v in (top_vendors + ["其他"])],
        "vendor_totals": [vendor_cnt.get(v, 0) for v in top_vendors] + [sum(1 for r in rows if (r["vendor"] or "未知") not in top_vendors)],
    }


def build_price_bracket_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """价格段位 × 平均 Elo 统计"""
    brackets = [
        ("<$1", lambda p: p is not None and p < 1),
        ("$1-5", lambda p: p is not None and 1 <= p < 5),
        ("$5-10", lambda p: p is not None and 5 <= p < 10),
        ("$10-50", lambda p: p is not None and 10 <= p < 50),
        ("$50+", lambda p: p is not None and p >= 50),
        ("无价格", lambda p: p is None),
    ]
    result = []
    for label, cond in brackets:
        subset = [r for r in rows if cond(r.get("price_input"))]
        elos = [r["arena_elo_max"] for r in subset if r.get("arena_elo_max") is not None]
        prices = [r["price_input"] for r in subset if r.get("price_input") is not None]
        result.append({
            "bracket": label,
            "count": len(subset),
            "avg_elo": round(sum(elos) / len(elos), 1) if elos else None,
            "median_price": round(sorted(prices)[len(prices) // 2], 3) if prices else None,
        })
    return {"brackets": result}


def build_modality_combo(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """输入模态组合 Top 10"""
    combos: Counter = Counter()
    for r in rows:
        modes = []
        for k, label in [("in_text", "文本"), ("in_image", "图像"), ("in_audio", "音频"),
                         ("in_video", "视频"), ("in_pdf", "PDF")]:
            if r.get(k) == 1:
                modes.append(label)
        combo = "+".join(modes) if modes else "纯文本(无模态声明)"
        combos[combo] += 1
    top = combos.most_common(10)
    return {"combos": [{"name": c, "count": n} for c, n in top]}


def build_time_trend(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """时间趋势：按月模型数 + 按年指标"""
    # 按月
    month_cnt = Counter()
    for r in rows:
        rd = r.get("release_date")
        if rd and len(rd) >= 7:
            month_cnt[rd[:7]] += 1
    months = sorted(month_cnt.keys())
    monthly = [{"month": m, "count": month_cnt[m]} for m in months]

    # 按年聚合：平均参数量 + 平均上下文 + 平均价格
    years = sorted({(r.get("release_date") or "")[:4] for r in rows if r.get("release_date")})
    yearly = []
    for y in years:
        subset = [r for r in rows if (r.get("release_date") or "").startswith(y)]
        params = [r["total_params_b"] for r in subset if r.get("total_params_b") is not None]
        ctx = [r["context_window_tokens"] for r in subset if r.get("context_window_tokens") is not None]
        prices = [r["price_input"] for r in subset if r.get("price_input") is not None]
        yearly.append({
            "year": y,
            "count": len(subset),
            "avg_params": round(sum(params) / len(params), 1) if params else None,
            "avg_ctx": round(sum(ctx) / len(ctx)) if ctx else None,
            "avg_price": round(sum(prices) / len(prices), 3) if prices else None,
        })

    return {"monthly": monthly, "yearly": yearly}


def build_data_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """数据质量：缺失字段警告 + license / kc 清单"""
    total = len(rows)
    # 所有字段填充率
    field_fill = []
    for col, info in FIELD_DICT.items():
        filled = sum(1 for r in rows if r.get(col) is not None)
        rate = round(filled / total * 100, 1) if total else 0
        field_fill.append({
            "column": col, "label": info["label"], "group": info["group"],
            "type": info["type"], "filled": filled, "fill_rate": rate,
        })
    # 按填充率升序（最缺失在前）
    field_fill.sort(key=lambda x: x["fill_rate"])

    # 缺失清单（< 30% 填充率）
    critical = [f for f in field_fill if f["fill_rate"] < 30]
    warning = [f for f in field_fill if 30 <= f["fill_rate"] < 70]
    good = [f for f in field_fill if f["fill_rate"] >= 70]

    # 验证状态分布
    verif = Counter(r.get("verification_status") or "缺失" for r in rows)

    return {
        "total": total,
        "critical_fields": critical,
        "warning_fields": warning,
        "good_fields": good,
        "verification_dist": verif.most_common(),
        "license_filled": sum(1 for r in rows if r.get("license")),
        "kc_filled": sum(1 for r in rows if r.get("knowledge_cutoff")),
    }


def build_arena_subboards(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Arena 子榜覆盖：各子榜模型数 + Top 5 模型"""
    # 子榜归一映射（处理碎片化命名）
    SUB_NORM = {
        # 主榜（text/overall）的各种写法归一为 "text"
        "text": "text",
        "lmarena (overall, text)": "text",
        "lmarena text generation (chatbot arena)": "text",
        "lm arena text (open-weight leaderboard)": "text",
        "lmsys chatbot arena (overall)": "text",
        "chatbot arena overall elo": "text",
        "lmarena": "text",
        "lmarena (overall)": "text",
        # coding 子榜
        "coding": "coding",
        "code": "coding",
        "codearena": "coding",
        "lm arena code arena/webdev": "coding",
        # math 子榜
        "math": "math",
        # webdev 子榜
        "webdev arena": "webdev",
        "webdev arena (lmarena)": "webdev",
        # vision 子榜
        "vision": "vision",
        # search 子榜
        "search": "search",
        # agent 子榜
        "arena agent leaderboard (智能体排行榜)": "agent",
        # 特殊：LiveCodeBench Pro 不属于 Arena Elo 子榜，应移至 independent
        "livecodebench pro": "_other",
        # GDPval-AA 经济价值评估，单列
        "gdpval-aa": "gdpval",
    }
    # 聚合每个模型的子榜 -> 最高分
    sub_scores: dict[str, dict[str, float]] = {}  # sub_benchmark -> {model_id -> score}
    sub_models: dict[str, set] = {}  # sub -> set of model_id
    unknown_subs: Counter = Counter()

    for r in rows:
        model_id = r.get("model_id")
        if not model_id:
            continue
        for e in r.get("arena_elo_subs") or []:
            raw = (e.get("sub_benchmark") or "").strip()
            score = e.get("score")
            if not raw or not isinstance(score, (int, float)):
                continue
            norm = SUB_NORM.get(raw.lower(), None)
            if norm == "_other":
                continue
            if norm is None:
                # 未知子榜，单独归一类（聚合各种杂项命名）
                unknown_subs[raw] += 1
                norm = "其他"
            sub_models.setdefault(norm, set()).add(model_id)
            d = sub_scores.setdefault(norm, {})
            if model_id not in d or score > d[model_id]:
                d[model_id] = score

    # 构建结果：各子榜模型数 + Top 5
    subs = []
    for name in ["text", "coding", "math", "webdev", "vision", "search", "agent", "gdpval", "其他"]:
        if name not in sub_models:
            continue
        model_ids = list(sub_models[name])
        scores = sub_scores.get(name, {})
        top5 = sorted(
            ((mid, scores.get(mid)) for mid in model_ids if scores.get(mid) is not None),
            key=lambda x: -(x[1] or 0),
        )[:5]
        # 找 vendor
        mid_to_vendor = {r.get("model_id"): r.get("vendor") for r in rows}
        mid_to_name = {r.get("model_id"): r.get("full_name") or r.get("model_id") for r in rows}
        top5_list = [{"model_id": mid, "name": mid_to_name.get(mid, mid),
                      "vendor": mid_to_vendor.get(mid, "未知"), "score": sc}
                     for mid, sc in top5]
        subs.append({"sub": name, "count": len(model_ids), "top5": top5_list})

    return {"subboards": subs, "unknown_subs": unknown_subs.most_common()}


def build_source_url_domains(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """跑分来源 URL 域名分布 + 来源集中度"""
    from urllib.parse import urlparse
    domains = Counter()
    for r in rows:
        for u in r.get("source_urls") or []:
            try:
                netloc = urlparse(u).netloc
                if netloc.startswith("www."):
                    netloc = netloc[4:]
                if netloc:
                    domains[netloc] += 1
            except Exception:
                pass
    total = sum(domains.values())
    top10 = domains.most_common(10)
    return {
        "total_urls": total,
        "total_domains": len(domains),
        "top10": [{"domain": d, "count": c, "pct": round(c / total * 100, 1) if total else 0}
                  for d, c in top10],
        "top5_concentration": round(sum(c for _, c in domains.most_common(5)) / total * 100, 1) if total else 0,
        "top10_concentration": round(sum(c for _, c in domains.most_common(10)) / total * 100, 1) if total else 0,
    }


def build_cost_effectiveness(rows: list[dict[str, Any]], top_n: int = 30) -> dict[str, Any]:
    """性价比单位成本：$/Elo point 排行（越低越值）"""
    pts = []
    for r in rows:
        if r.get("cost_per_elo") is None:
            continue
        pts.append({
            "model_id": r.get("model_id"),
            "name": r.get("full_name") or r.get("model_id"),
            "vendor": r.get("vendor") or "未知",
            "cost_per_elo": r["cost_per_elo"],
            "price_input": r.get("price_input"),
            "elo": r.get("arena_elo_max"),
            "open_weights": r.get("open_weights") == 1,
        })
    # 升序（越低越值）
    pts.sort(key=lambda x: x["cost_per_elo"])
    return {"ranking": pts[:top_n], "total_with_cost": len(pts)}


def build_moe_sparsity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """MoE 稀疏度散点：active vs total params + 稀疏度分布"""
    pts = []
    for r in rows:
        ap = r.get("active_params_b")
        tp = r.get("total_params_b")
        if ap is None or tp is None or tp <= 0:
            continue
        pts.append({
            "model_id": r.get("model_id"),
            "name": r.get("full_name") or r.get("model_id"),
            "vendor": r.get("vendor") or "未知",
            "active": ap,
            "total": tp,
            "sparsity": round(ap / tp, 3),
            "is_moe": ap < tp * 0.95,  # 稀疏度 < 0.95 视为 MoE
            "elo": r.get("arena_elo_max"),
        })
    # 统计 MoE vs Dense
    moe_cnt = sum(1 for p in pts if p["is_moe"])
    dense_cnt = len(pts) - moe_cnt
    # 稀疏度分布
    buckets = {"<0.05": 0, "0.05-0.1": 0, "0.1-0.3": 0, "0.3-0.6": 0, "0.6-0.95": 0, "≥0.95": 0}
    for p in pts:
        s = p["sparsity"]
        if s < 0.05:
            buckets["<0.05"] += 1
        elif s < 0.1:
            buckets["0.05-0.1"] += 1
        elif s < 0.3:
            buckets["0.1-0.3"] += 1
        elif s < 0.6:
            buckets["0.3-0.6"] += 1
        elif s < 0.95:
            buckets["0.6-0.95"] += 1
        else:
            buckets["≥0.95"] += 1
    return {
        "scatter": pts,
        "total_models": len(pts),
        "moe_count": moe_cnt,
        "dense_count": dense_cnt,
        "sparsity_buckets": buckets,
    }


def build_benchmark_dimensions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """模型对比页：返回每个模型的多维度跑分（0-1 normalized）"""
    dims = ["independent_best_mmlu", "independent_best_gsm8k", "independent_best_gpqa",
            "independent_best_humaneval", "independent_best_math", "independent_best_bbh",
            "independent_best_musr", "independent_best_ifeval"]
    dim_labels = ["MMLU", "GSM8K", "GPQA", "HumanEval", "MATH", "BBH", "MuSR", "IFEval"]
    # 每个模型的多维度跑分
    models = []
    for r in rows:
        scores = {d: r.get(d) for d in dims}
        # 至少有一个维度有分才纳入
        if not any(v is not None for v in scores.values()):
            continue
        # 归一为 0-100
        norm = {d: (round(v * 100, 1) if isinstance(v, (int, float)) else None) for d, v in scores.items()}
        models.append({
            "model_id": r.get("model_id"),
            "name": r.get("full_name") or r.get("model_id"),
            "vendor": r.get("vendor") or "未知",
            "elo": r.get("arena_elo_max"),
            "price_input": r.get("price_input"),
            "total_params_b": r.get("total_params_b"),
            "context_window_tokens": r.get("context_window_tokens"),
            "open_weights": r.get("open_weights") == 1,
            "scores": norm,
        })
    # 维度填充率
    fill_rates = []
    for d, lbl in zip(dims, dim_labels):
        n = sum(1 for m in models if m["scores"].get(d) is not None)
        fill_rates.append({"dim": d, "label": lbl, "filled": n, "total": len(models),
                           "fill_rate": round(n / len(models) * 100, 1) if models else 0})
    return {
        "dimensions": [{"key": d, "label": l} for d, l in zip(dims, dim_labels)],
        "models": models,
        "fill_rates": fill_rates,
    }


def build_vendor_geo_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """厂商地缘分组统计：中国/美国/欧洲/其他 × 模型数 + 平均跑分"""
    from statistics import mean
    geo_data: dict[str, list] = {"中国": [], "美国": [], "欧洲": [], "其他": []}
    for r in rows:
        g = r.get("vendor_geo") or "其他"
        geo_data.setdefault(g, []).append(r)
    result = []
    for g in ["中国", "美国", "欧洲", "其他"]:
        rs = geo_data.get(g, [])
        if not rs:
            continue
        elos = [r["arena_elo_max"] for r in rs if r.get("arena_elo_max") is not None]
        prices = [r["price_input"] for r in rs if r.get("price_input") is not None]
        opens = sum(1 for r in rs if r.get("open_weights") == 1)
        result.append({
            "geo": g,
            "model_count": len(rs),
            "vendor_count": len({r["vendor"] for r in rs}),
            "avg_elo": round(mean(elos), 1) if elos else None,
            "elo_count": len(elos),
            "avg_price": round(mean(prices), 3) if prices else None,
            "open_weights_count": opens,
        })
    return {"geo_stats": result}


def build_extended_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """扩展聚合入口：6 页架构 + 模型对比 + 性价比 + MoE + Arena 子榜 + 来源 + 地缘"""
    return {
        # 原 6 页架构
        "vendor_capability": build_vendor_capability(rows),
        "price_brackets": build_price_bracket_stats(rows),
        "modality_combo": build_modality_combo(rows),
        "time_trend": build_time_trend(rows),
        "data_quality": build_data_quality(rows),
        # 新增
        "arena_subboards": build_arena_subboards(rows),
        "source_domains": build_source_url_domains(rows),
        "cost_effectiveness": build_cost_effectiveness(rows),
        "moe_sparsity": build_moe_sparsity(rows),
        "benchmark_dims": build_benchmark_dimensions(rows),
        "vendor_geo": build_vendor_geo_stats(rows),
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
