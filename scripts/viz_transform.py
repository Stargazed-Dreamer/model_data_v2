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


def _norm_sub_benchmark(s: Any) -> str:
    """Arena 子榜名归一（仅用于主榜分判断，非数据层归一）。
    'text'/'overall'/'chatbot'/空 → 'text'；其他子榜名保留原意（coding/math/agent 等）。
    """
    s = (s or "").lower().strip()
    if not s:
        return "text"
    if "text" in s or "overall" in s or "chatbot" in s:
        return "text"
    return s  # coding/math/webdev/vision/search/agent/gdpval 等保留


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
    # arena elo 主榜分：D31 修复子榜区隔问题
    # 旧逻辑：max(elos) 会把 agent/coding/math 子榜分误当主榜分（如 GLM-5.2 agent 1524 被显示为主榜）
    # 新逻辑：1) 优先 is_primary=true；2) 否则 sub_benchmark 归一为 text/overall/空 的；3) 都无则 None（避免子榜虚高）
    arena_arr = [e for e in (bench.get("arena_elo") or []) if isinstance(e, dict)]
    primary_scores = [
        e.get("score") for e in arena_arr
        if e.get("is_primary") and isinstance(e.get("score"), (int, float))
    ]
    text_scores = [
        e.get("score") for e in arena_arr
        if _norm_sub_benchmark(e.get("sub_benchmark")) == "text"
        and isinstance(e.get("score"), (int, float))
    ]
    if primary_scores:
        row["arena_elo_max"] = primary_scores[0]  # 多 primary 取首个
    elif text_scores:
        row["arena_elo_max"] = text_scores[0]
    else:
        row["arena_elo_max"] = None  # 仅子榜（agent/coding/math 等）时不作主榜分
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


# ---------------------------------------------------------------------------
# 模型档案（点击模型名 → 全档案视图）
# ---------------------------------------------------------------------------

def load_raw_records(jsonl_path: Path = DEFAULT_JSONL) -> list[dict[str, Any]]:
    """读原始 JSONL 记录（保留 self_reported/independent/arena_elo 子数组结构）"""
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _normalize(v: float | None, mn: float, mx: float) -> float:
    """min-max 归一化到 [0, 1]，缺失返回 0.5（中性）"""
    if v is None or mn == mx:
        return 0.5
    if v < mn:
        return 0.0
    if v > mx:
        return 1.0
    return (v - mn) / (mx - mn)


def build_model_details(rows: list[dict[str, Any]],
                       raw_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """每个 model_id 的完整档案：
    - 原始 self_reported / independent / arena_elo 子数组
    - 同厂商兄弟 model_id 列表
    - 相似模型推荐（按 total_params + price_input + arena_elo_max 邻近）

    raw_records 为 None 时返回空字典（兼容旧调用）。
    """
    if not raw_records:
        return {}

    # 1. 建立 model_id -> raw_record 索引
    raw_by_id: dict[str, dict] = {}
    for rec in raw_records:
        mid = rec.get("model_id")
        if mid:
            raw_by_id[mid] = rec

    # 2. 同厂商兄弟：vendor -> [model_id, ...]
    vendor_to_models: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        v = r.get("vendor") or "未知"
        mid = r.get("model_id")
        if mid:
            vendor_to_models[v].append(mid)

    # 3. 相似模型：用 total_params / price_input / arena_elo_max 三维 min-max 归一化后欧氏距离
    #    预计算 min/max
    params_vals = [r["total_params_b"] for r in rows if r.get("total_params_b") is not None]
    price_vals = [r["price_input"] for r in rows if r.get("price_input") is not None]
    elo_vals = [r["arena_elo_max"] for r in rows if r.get("arena_elo_max") is not None]
    p_min, p_max = (min(params_vals), max(params_vals)) if params_vals else (0, 1)
    pr_min, pr_max = (min(price_vals), max(price_vals)) if price_vals else (0, 1)
    e_min, e_max = (min(elo_vals), max(elo_vals)) if elo_vals else (0, 1)

    # 计算每个模型的归一化坐标
    row_by_id: dict[str, dict] = {r.get("model_id"): r for r in rows if r.get("model_id")}
    coords: dict[str, tuple[float, float, float]] = {}
    for mid, r in row_by_id.items():
        coords[mid] = (
            _normalize(r.get("total_params_b"), p_min, p_max),
            _normalize(r.get("price_input"), pr_min, pr_max),
            _normalize(r.get("arena_elo_max"), e_min, e_max),
        )

    # 4. 构建每个模型的档案
    details: dict[str, dict[str, Any]] = {}
    for mid, raw in raw_by_id.items():
        bench = raw.get("benchmarks") or {}
        # 兄弟：同 vendor 但 model_id != mid，最多 20 个
        v = (raw.get("basic_info") or {}).get("vendor") or "未知"
        siblings_all = [s for s in vendor_to_models.get(v, []) if s != mid]
        siblings = siblings_all[:20]  # 截 Top 20

        # 相似：欧氏距离最小，排除自身 + 同 vendor 兄弟（避免重复）
        # 简化：全表算距离，取 Top 5，排除自身
        if mid in coords:
            mx, my, mz = coords[mid]
            distances = []
            for other_mid, (ox, oy, oz) in coords.items():
                if other_mid == mid:
                    continue
                d = ((ox - mx) ** 2 + (oy - my) ** 2 + (oz - mz) ** 2) ** 0.5
                distances.append((other_mid, round(d, 3)))
            distances.sort(key=lambda x: x[1])
            similar = [{"model_id": m, "distance": d} for m, d in distances[:5]]
        else:
            similar = []

        details[mid] = {
            "self_reported": bench.get("self_reported") or [],
            "independent": bench.get("independent") or [],
            "arena_elo": bench.get("arena_elo") or [],
            "siblings": siblings,
            "similar": similar,
        }

    return details


def build_gap_analysis(rows: list[dict[str, Any]],
                       raw_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """数据缺口分析：字段填充率雷达 + 跑分覆盖热力图 + 缺口排行"""
    total = len(rows)

    # 1. 字段组填充率（雷达图用）
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for col, info in FIELD_DICT.items():
        filled = sum(1 for r in rows if r.get(col) is not None)
        rate = round(filled / total * 100, 1) if total else 0.0
        groups[info["group"]].append({"column": col, "label": info["label"], "rate": rate})

    group_avg = []
    for g, fields in groups.items():
        avg = round(sum(f["rate"] for f in fields) / len(fields), 1)
        group_avg.append({"group": g, "avg_rate": avg, "field_count": len(fields)})

    # 2. 跑分覆盖热力图：Top 30 benchmark × Top 30 厂商（按模型数）
    bench_cnt = Counter()
    for r in rows:
        sr = (r.get("self_reported_count") or 0)
        ind = (r.get("independent_count") or 0)
        bench_cnt[r.get("vendor") or "未知"] += sr + ind

    # 从 raw_records 提取 benchmark 覆盖
    bench_model_matrix: dict[str, set[str]] = defaultdict(set)
    if raw_records:
        for rec in raw_records:
            mid = rec.get("model_id") or ""
            bench = rec.get("benchmarks") or {}
            for sec in ["self_reported", "independent"]:
                for e in (bench.get(sec) or []):
                    bn = e.get("benchmark") or ""
                    if bn:
                        bench_model_matrix[bn].add(mid)

    # Top 30 benchmarks by model coverage
    top_bench = sorted(bench_model_matrix.items(), key=lambda x: -len(x[1]))[:30]
    bench_names = [b[0] for b in top_bench]

    # Top 30 vendors by model count
    vendor_model_cnt = Counter(r.get("vendor") or "未知" for r in rows)
    top_vendors = [v for v, _ in vendor_model_cnt.most_common(30)]

    # 矩阵：bench × vendor，值=该厂商中有该 benchmark 的模型数
    vendor_models: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        v = r.get("vendor") or "未知"
        mid = r.get("model_id") or ""
        if mid:
            vendor_models[v].add(mid)

    matrix_data = []
    for bn, models in top_bench:
        for vi, v in enumerate(top_vendors):
            cnt = len(models & vendor_models.get(v, set()))
            if cnt > 0:
                matrix_data.append([vi, bench_names.index(bn), cnt])

    # 3. 缺口排行：所有字段按填充率升序
    all_fields = []
    for col, info in FIELD_DICT.items():
        filled = sum(1 for r in rows if r.get(col) is not None)
        rate = round(filled / total * 100, 1) if total else 0.0
        all_fields.append({"column": col, "label": info["label"], "group": info["group"],
                          "filled": filled, "missing": total - filled, "rate": rate})
    all_fields.sort(key=lambda x: x["rate"])

    # 4. 无跑分模型清单
    no_bench = [
        {"model_id": r.get("model_id"), "full_name": r.get("full_name"),
         "vendor": r.get("vendor"), "release_date": r.get("release_date")}
        for r in rows
        if (r.get("self_reported_count") or 0) == 0
        and (r.get("independent_count") or 0) == 0
        and (r.get("arena_elo_count") or 0) == 0
    ]

    # 5. 关键缺口统计
    gaps = {
        "no_benchmarks": len(no_bench),
        "no_price": sum(1 for r in rows if r.get("price_input") is None),
        "no_params": sum(1 for r in rows if r.get("total_params_b") is None),
        "no_kc": sum(1 for r in rows if r.get("knowledge_cutoff") is None),
        "no_elo": sum(1 for r in rows if r.get("arena_elo_max") is None),
        "no_ctx": sum(1 for r in rows if r.get("context_window_tokens") is None),
    }

    return {
        "group_fill_rates": group_avg,
        "benchmark_coverage": {
            "benchmarks": bench_names,
            "vendors": top_vendors,
            "matrix": matrix_data,
        },
        "field_gaps": all_fields,
        "no_bench_models": no_bench[:100],  # 限制 100 条避免过大
        "no_bench_count": len(no_bench),
        "gap_summary": gaps,
    }


# 关键字段清单（缺口矩阵用）—— 覆盖各核心维度，避开过于冷门字段
GAP_MATRIX_FIELDS = [
    "price_input", "price_output", "total_params_b", "active_params_b",
    "context_window_tokens", "knowledge_cutoff", "license",
    "arena_elo_max", "independent_best_mmlu", "independent_best_gsm8k",
    "independent_best_gpqa", "independent_best_humaneval",
    "open_weights", "api_access", "in_image", "positioning_count",
    "source_url_count", "release_date", "verification_status",
]


def build_gap_matrix(rows: list[dict[str, Any]], top_vendors_n: int = 30) -> dict[str, Any]:
    """厂商 × 字段 缺口矩阵 + 智能诊断 + 导出清单。

    返回:
      matrix: 热力图数据（vendor_idx, field_idx, fill_rate%）
      diagnosis: 每个厂商 top_gaps（最缺 Top 3） + 健康度分数
      export: todo_items 一键导出友好格式
    """
    total = len(rows)
    if total == 0:
        return {"matrix": {"vendors": [], "fields": [], "data": [], "vendor_totals": []},
                "diagnosis": [], "export": {"fields_tracked": 0, "vendors_with_gaps": 0, "todo_items": []}}

    # 准备字段元数据
    fields_meta = []
    for col in GAP_MATRIX_FIELDS:
        info = FIELD_DICT.get(col, {})
        fields_meta.append({"col": col, "label": info.get("label", col), "group": info.get("group", "其他")})

    # Top N 厂商 + 其他
    vendor_cnt = Counter(r.get("vendor") or "未知" for r in rows)
    top_vendors = [v for v, _ in vendor_cnt.most_common(top_vendors_n)]
    other_models = [r for r in rows if (r.get("vendor") or "未知") not in set(top_vendors)]
    vendor_names = top_vendors + (["其他"] if other_models else [])

    # 每个厂商的模型数 + 每字段填充数
    vendor_models: dict[str, list[dict]] = {v: [] for v in vendor_names}
    for r in rows:
        v = r.get("vendor") or "未知"
        target = v if v in vendor_models else "其他"
        if target in vendor_models:
            vendor_models[target].append(r)

    vendor_totals = [len(vendor_models[v]) for v in vendor_names]

    # 矩阵: (vendor_idx, field_idx, fill_rate)
    matrix_data = []
    for vi, v in enumerate(vendor_names):
        models = vendor_models[v]
        v_total = len(models)
        if v_total == 0:
            continue
        for fi, fm in enumerate(fields_meta):
            filled = sum(1 for r in models if r.get(fm["col"]) is not None)
            rate = round(filled / v_total * 100, 1) if v_total else 0.0
            # 只输出非零填充（避免稀疏矩阵过大）
            if filled > 0:
                matrix_data.append([vi, fi, rate, filled])

    # 厂商诊断：每家最缺的 Top 3 字段（按缺失数降序，仅算非空字段也需补的）
    diagnosis = []
    for v in vendor_names:
        models = vendor_models[v]
        v_total = len(models)
        if v_total == 0:
            continue
        gaps = []
        for fm in fields_meta:
            filled = sum(1 for r in models if r.get(fm["col"]) is not None)
            missing = v_total - filled
            rate = round(filled / v_total * 100, 1) if v_total else 0.0
            gaps.append({"field": fm["col"], "label": fm["label"], "missing": missing,
                         "filled": filled, "rate": rate})
        # 按缺失数降序取 Top 3（仅算 missing>0 的）
        gaps.sort(key=lambda x: -x["missing"])
        top_gaps = [g for g in gaps if g["missing"] > 0][:3]
        # 健康度：所有字段平均填充率
        health_score = round(sum(g["rate"] for g in gaps) / len(gaps), 1) if gaps else 0.0
        diagnosis.append({
            "vendor": v, "total_models": v_total,
            "top_gaps": top_gaps, "health_score": health_score,
        })
    # 按健康度升序（最差的在前）
    diagnosis.sort(key=lambda x: x["health_score"])

    # 导出清单：vendor × field 的 missing 列表（仅 missing>0）
    todo_items = []
    for v in vendor_names:
        models = vendor_models[v]
        v_total = len(models)
        if v_total == 0:
            continue
        # 找该厂商缺失字段对应的具体 model_id
        for fm in fields_meta:
            missing_models = [r.get("model_id") for r in models if r.get(fm["col"]) is None]
            if not missing_models:
                continue
            todo_items.append({
                "vendor": v,
                "field": fm["col"],
                "label": fm["label"],
                "missing": len(missing_models),
                "total": v_total,
                "rate": round((v_total - len(missing_models)) / v_total * 100, 1),
                "models": missing_models[:50],  # 限制 50 个，避免导出过大
            })
    # 按缺失数降序
    todo_items.sort(key=lambda x: -x["missing"])

    return {
        "matrix": {
            "vendors": vendor_names,
            "fields": fields_meta,
            "data": matrix_data,
            "vendor_totals": vendor_totals,
        },
        "diagnosis": diagnosis,
        "export": {
            "fields_tracked": len(fields_meta),
            "vendors_with_gaps": len(todo_items),
            "todo_items": todo_items,
        },
    }


def build_vendor_fragmentation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """厂商碎片化检测：大小写/空格/连字符变体 + 合并建议"""
    # 按小写 + 去空格/连字符分组
    def norm_key(v):
        return v.lower().replace(" ", "").replace("-", "").replace(".", "").replace("_", "")

    vendor_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    vendor_cnt = Counter()
    for r in rows:
        v = r.get("vendor") or "未知"
        vendor_cnt[v] += 1

    for v, c in vendor_cnt.items():
        key = norm_key(v)
        vendor_groups[key].append({"vendor": v, "count": c})

    # 找出有变体的组
    merge_suggestions = []
    for key, variants in vendor_groups.items():
        if len(variants) > 1:
            total = sum(v["count"] for v in variants)
            preferred = max(variants, key=lambda x: x["count"])
            merge_suggestions.append({
                "key": key,
                "variants": sorted(variants, key=lambda x: -x["count"]),
                "total": total,
                "preferred": preferred["vendor"],
            })

    merge_suggestions.sort(key=lambda x: -x["total"])

    # 厂商气泡图数据：vendor × 模型数 × 平均 Elo × 地缘
    geo_colors = {"中国": "#dc2626", "美国": "#2563eb", "欧洲": "#7c3aed", "其他": "#6b7280"}
    bubble_data = []
    for v, c in vendor_cnt.most_common(30):
        subset = [r for r in rows if r.get("vendor") == v]
        elos = [r["arena_elo_max"] for r in subset if r.get("arena_elo_max") is not None]
        avg_elo = round(sum(elos) / len(elos), 1) if elos else 0
        geo = subset[0].get("vendor_geo") if subset else "其他"
        bubble_data.append({
            "vendor": v, "count": c, "avg_elo": avg_elo,
            "geo": geo, "color": geo_colors.get(geo, "#6b7280"),
        })

    return {
        "merge_suggestions": merge_suggestions,
        "bubble_data": bubble_data,
        "total_vendors": len(vendor_cnt),
        "fragmented_groups": len(merge_suggestions),
    }


def _median(vals: list[float]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 == 1 else (s[mid - 1] + s[mid]) / 2


def build_price_quadrant(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """价格×性能 4 象限散点 + 中位分割线 + 线性回归。

    象限定义（以中位价格 x=med_price、中位 Elo y=med_elo 分割）：
      高性价比：x<med 且 y>=med   （低价高性能）
      低性价比：x>=med 且 y<med   （高价低性能）
      高端：     x>=med 且 y>=med  （高价高性能）
      低端：     x<med 且 y<med    （低价低性能）
    """
    pts = []
    for r in rows:
        p = r.get("price_input")
        e = r.get("arena_elo_max")
        if p is None or e is None or p < 0 or e <= 0:
            continue
        pts.append({
            "model_id": r.get("model_id"),
            "name": r.get("full_name") or r.get("model_id"),
            "vendor": r.get("vendor") or "未知",
            "x": round(p, 4),
            "y": round(e, 1),
            "open": r.get("open_weights") == 1,
            "params": r.get("total_params_b"),
        })
    if not pts:
        return {"points": [], "med_price": None, "med_elo": None,
                "regression": None, "quadrants": {}}

    prices = [p["x"] for p in pts]
    elos = [p["y"] for p in pts]
    med_p = _median(prices)
    med_e = _median(elos)

    # 线性回归 price(x) -> elo(y)：y = a + b*x
    n = len(pts)
    sx = sum(prices)
    sy = sum(elos)
    sxx = sum(x * x for x in prices)
    sxy = sum(x * y for x, y in zip(prices, elos))
    denom = n * sxx - sx * sx
    if denom != 0:
        b = (n * sxy - sx * sy) / denom
        a = (sy - b * sx) / n
        x_min, x_max = min(prices), max(prices)
        regression = {
            "a": round(a, 4), "b": round(b, 6),
            "line": [[round(x_min, 4), round(a + b * x_min, 1)],
                     [round(x_max, 4), round(a + b * x_max, 1)]],
        }
    else:
        regression = None

    # 象限分类
    quad_cnt = {"high_value": 0, "low_value": 0, "premium": 0, "budget": 0}
    for p in pts:
        if p["x"] < med_p and p["y"] >= med_e:
            p["quadrant"] = "high_value"
            quad_cnt["high_value"] += 1
        elif p["x"] >= med_p and p["y"] < med_e:
            p["quadrant"] = "low_value"
            quad_cnt["low_value"] += 1
        elif p["x"] >= med_p and p["y"] >= med_e:
            p["quadrant"] = "premium"
            quad_cnt["premium"] += 1
        else:
            p["quadrant"] = "budget"
            quad_cnt["budget"] += 1

    return {
        "points": pts,
        "med_price": round(med_p, 4) if med_p is not None else None,
        "med_elo": round(med_e, 1) if med_e is not None else None,
        "regression": regression,
        "quadrants": quad_cnt,
        "total": len(pts),
    }


def _parse_kc_date(kc: str | None) -> str | None:
    """knowledge_cutoff 可能是 YYYY / YYYY-MM / YYYY-MM-DD，归一成 YYYY-MM-DD（缺日补01，缺月补01）"""
    if not kc or not isinstance(kc, str):
        return None
    kc = kc.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", kc):
        return kc
    if re.fullmatch(r"\d{4}-\d{2}", kc):
        return kc + "-01"
    if re.fullmatch(r"\d{4}", kc):
        return kc + "-01-01"
    return None


def build_lifecycle_gantt(rows: list[dict[str, Any]], top_n: int = 120) -> dict[str, Any]:
    """模型生命周期甘特图：release_date → knowledge_cutoff（缺则用 today）。

    返回 Top N 条（按 release_date 降序，优先有 Elo 的），避免 933 条全画过载。
    每条带 vendor、duration_days、has_elo、has_kc。
    """
    import datetime

    today = datetime.date.today().isoformat()

    def _parse_rd(rd: str | None) -> str | None:
        if not rd or not isinstance(rd, str):
            return None
        rd = rd.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", rd):
            return rd
        if re.fullmatch(r"\d{4}-\d{2}", rd):
            return rd + "-01"
        if re.fullmatch(r"\d{4}", rd):
            return rd + "-01-01"
        return None

    items = []
    for r in rows:
        rd = _parse_rd(r.get("release_date"))
        if not rd:
            continue
        kc = _parse_kc_date(r.get("knowledge_cutoff")) or today
        # 若 kc < rd，用 today 兜底（异常数据）
        if kc < rd:
            kc = today
        try:
            d1 = datetime.date.fromisoformat(rd)
            d2 = datetime.date.fromisoformat(kc)
            dur = (d2 - d1).days
        except ValueError:
            dur = 0
        items.append({
            "model_id": r.get("model_id"),
            "name": r.get("full_name") or r.get("model_id"),
            "vendor": r.get("vendor") or "未知",
            "release": rd,
            "end": kc,
            "duration_days": dur,
            "has_elo": r.get("arena_elo_max") is not None,
            "elo": r.get("arena_elo_max"),
            "has_kc": r.get("knowledge_cutoff") is not None,
            "geo": r.get("vendor_geo") or "其他",
            "open": r.get("open_weights") == 1,
        })

    # 排序优先级：有 kc（真实生命周期）> 有 elo > 无（仅 release）
    # 取 Top N：优先有 kc 的，其次有 elo 的，再次最新 release
    items.sort(key=lambda x: (not x["has_kc"], not x["has_elo"], x["release"]),
               reverse=False)
    # 取最有信息量的 top_n（即列表末尾，按优先级+时间倒序）
    # 但我们想要"有 kc 的优先 + 时间分布广"，所以取 has_kc 的全部 + 不足再补 has_elo
    with_kc = [it for it in items if it["has_kc"]]
    with_elo_only = [it for it in items if not it["has_kc"] and it["has_elo"]]
    rest = [it for it in items if not it["has_kc"] and not it["has_elo"]]
    # 每段按 release 降序（最新的优先），合并后取 top_n
    with_kc.sort(key=lambda x: x["release"], reverse=True)
    with_elo_only.sort(key=lambda x: x["release"], reverse=True)
    rest.sort(key=lambda x: x["release"], reverse=True)
    picked = (with_kc + with_elo_only + rest)[:top_n]
    # 再按 release 升序排（甘特图从早到晚）
    items = sorted(picked, key=lambda x: x["release"])

    # vendor 色板
    geo_keys = {
        "中国": "#dc2626", "美国": "#2563eb", "欧洲": "#7c3aed", "其他": "#6b7280",
    }

    return {
        "items": items,
        "total_with_release": sum(1 for r in rows if r.get("release_date")),
        "shown": len(items),
        "today": today,
        "geo_colors": geo_keys,
    }


# ---------------------------------------------------------------------------
# D31+ 新增：跑分排行总榜 + scaling law 散点 + 多源一致性
# ---------------------------------------------------------------------------

def _norm_bench_name(s: str) -> str:
    """benchmark 名归一（粗粒度，用于排行总榜）"""
    s = (s or "").lower().strip()
    if not s:
        return ""
    if "mmlu" in s:
        return "mmlu"
    if "gsm8k" in s:
        return "gsm8k"
    if "gpqa" in s:
        return "gpqa"
    if "math" in s and "maths" not in s:
        return "math"
    if "humaneval" in s or "human_eval" in s:
        return "humaneval"
    if "aime" in s:
        return "aime2025"
    if "swe-bench" in s:
        return "swe_bench"
    if "arc" in s and "challenge" in s:
        return "arc_challenge"
    if "hellaswag" in s or "hswag" in s:
        return "hellaswag"
    if "winogrande" in s:
        return "winogrande"
    if "truthfulqa" in s:
        return "truthfulqa"
    return s[:30]


def build_leaderboard(rows: list[dict[str, Any]], raw_records: list[dict[str, Any]] | None = None,
                      top_n: int = 30) -> dict[str, Any]:
    """跑分排行总榜：按 benchmark 维度切换 Top N

    支持的 benchmark：mmlu/gsm8k/gpqa/math/humaneval/aime2025/swe_bench（独立评测）
                       + arena_text/arena_coding/arena_math（Arena Elo 子榜）
    """
    # 准备独立评测排行
    bench_top: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in (raw_records or []):
        mid = raw.get("model_id")
        if not mid:
            continue
        bi = raw.get("basic_info") or {}
        bench = raw.get("benchmarks") or {}
        # 独立评测
        for e in (bench.get("independent") or []):
            if not isinstance(e, dict):
                continue
            bn = _norm_bench_name(e.get("benchmark") or "")
            if not bn:
                continue
            score = e.get("score")
            if not isinstance(score, (int, float)):
                continue
            s = float(score)
            if s > 1.5:
                s = s / 100.0
            if s < 0 or s > 1.01:
                continue
            bench_top[bn].append({
                "model_id": mid, "full_name": bi.get("full_name") or mid,
                "vendor": bi.get("vendor") or "未知", "score": round(s, 4),
                "source_url": e.get("source_url") or "",
                "source_type": e.get("source_type") or "",
                "confidence": e.get("confidence") or "",
            })
    # 每个独立 benchmark 取 top_n（去重同模型取最高）
    for bn in list(bench_top.keys()):
        seen: dict[str, dict] = {}
        for it in bench_top[bn]:
            mid = it["model_id"]
            if mid not in seen or it["score"] > seen[mid]["score"]:
                seen[mid] = it
        bench_top[bn] = sorted(seen.values(), key=lambda x: -x["score"])[:top_n]

    # Arena 子榜排行（直接从 flatten 后的 rows 取）
    arena_subs_top: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        subs = r.get("arena_elo_subs") or []
        for e in subs:
            sub = _norm_sub_benchmark(e.get("sub_benchmark"))
            score = e.get("score")
            if not isinstance(score, (int, float)):
                continue
            arena_subs_top[sub].append({
                "model_id": r["model_id"], "full_name": r.get("full_name") or r["model_id"],
                "vendor": r.get("vendor") or "未知", "score": float(score),
                "source_url": e.get("source_url") or "",
                "is_primary": bool(e.get("is_primary")),
            })
    # 每个 arena 子榜取 top_n
    for sub in list(arena_subs_top.keys()):
        arena_subs_top[sub] = sorted(arena_subs_top[sub], key=lambda x: -x["score"])[:top_n]

    # 各 benchmark 元数据
    bench_meta = {
        "mmlu": {"label": "MMLU", "group": "独立评测", "unit": "%", "scale": 100},
        "gsm8k": {"label": "GSM8K", "group": "独立评测", "unit": "%", "scale": 100},
        "gpqa": {"label": "GPQA", "group": "独立评测", "unit": "%", "scale": 100},
        "math": {"label": "MATH", "group": "独立评测", "unit": "%", "scale": 100},
        "humaneval": {"label": "HumanEval", "group": "独立评测", "unit": "%", "scale": 100},
        "aime2025": {"label": "AIME 2025", "group": "独立评测", "unit": "%", "scale": 100},
        "swe_bench": {"label": "SWE-bench Verified", "group": "独立评测", "unit": "%", "scale": 100},
        "arc_challenge": {"label": "ARC Challenge", "group": "独立评测", "unit": "%", "scale": 100},
        "hellaswag": {"label": "HellaSwag", "group": "独立评测", "unit": "%", "scale": 100},
        "winogrande": {"label": "WinoGrande", "group": "独立评测", "unit": "%", "scale": 100},
        "truthfulqa": {"label": "TruthfulQA", "group": "独立评测", "unit": "%", "scale": 100},
        "arena_text": {"label": "Arena Elo (Text)", "group": "Arena 子榜", "unit": "Elo", "scale": 1},
        "arena_coding": {"label": "Arena Elo (Coding)", "group": "Arena 子榜", "unit": "Elo", "scale": 1},
        "arena_math": {"label": "Arena Elo (Math)", "group": "Arena 子榜", "unit": "Elo", "scale": 1},
        "arena_webdev": {"label": "Arena Elo (WebDev)", "group": "Arena 子榜", "unit": "Elo", "scale": 1},
        "arena_vision": {"label": "Arena Elo (Vision)", "group": "Arena 子榜", "unit": "Elo", "scale": 1},
        "arena_agent": {"label": "Arena Elo (Agent)", "group": "Arena 子榜", "unit": "Elo", "scale": 1},
    }

    # 合并所有可用 benchmark key + 数量 + 是否有数据
    all_benches = []
    for k, meta in bench_meta.items():
        if k.startswith("arena_"):
            sub_key = k.replace("arena_", "")
            items = arena_subs_top.get(sub_key, [])
        else:
            items = bench_top.get(k, [])
        if items:
            all_benches.append({
                "key": k, "label": meta["label"], "group": meta["group"],
                "unit": meta["unit"], "scale": meta["scale"], "n": len(items),
            })

    return {
        "bench_meta": bench_meta,
        "available_benches": all_benches,
        "leaderboards": {**{k: v for k, v in bench_top.items() if v},
                         **{f"arena_{k}": v for k, v in arena_subs_top.items() if v}},
    }


def build_scaling_law(rows: list[dict[str, Any]], raw_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """scaling law 散点：参数量 vs 各 benchmark 分数 + log-log 拟合线 + 异常点

    返回每个 benchmark 的散点数据 + 拟合参数 (a, b, R²) + 预测 score@7B/70B/700B
    """
    import math
    bench_data: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in (raw_records or []):
        mid = raw.get("model_id")
        if not mid:
            continue
        bi = raw.get("basic_info") or {}
        arch = raw.get("architecture") or {}
        bench = raw.get("benchmarks") or {}
        params = arch.get("total_params_b")
        if not isinstance(params, (int, float)) or params <= 0:
            continue
        for e in (bench.get("independent") or []):
            if not isinstance(e, dict):
                continue
            bn = _norm_bench_name(e.get("benchmark") or "")
            if bn not in ("mmlu", "gsm8k", "gpqa", "math"):
                continue
            score = e.get("score")
            if not isinstance(score, (int, float)):
                continue
            s = float(score)
            if s > 1.5:
                s = s / 100.0
            if s <= 0 or s > 1.01:
                continue
            bench_data[bn].append({
                "model_id": mid, "full_name": bi.get("full_name") or mid,
                "vendor": bi.get("vendor") or "未知",
                "params": float(params), "score": round(s, 4),
                "open_weights": bool((bi.get("access") or {}).get("open_weights")),
                "price_input": ((raw.get("pricing") or {}).get("input")),
            })

    result = {}
    for bn in ("mmlu", "gsm8k", "gpqa", "math"):
        pts = bench_data[bn]
        if len(pts) < 5:
            continue
        # log-log 拟合：log(score) = a + b * log(params)
        fit_pts = [(math.log(p["params"]), math.log(p["score"]))
                   for p in pts if p["score"] > 0.001 and p["params"] > 0]
        if len(fit_pts) < 5:
            continue
        xs = [x for x, _ in fit_pts]
        ys = [y for _, y in fit_pts]
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        syy = sum((y - my) ** 2 for y in ys)
        if sxx == 0:
            continue
        b = sxy / sxx
        a = my - b * mx
        r2 = (sxy ** 2) / (sxx * syy) if syy > 0 else 0
        # 预测点
        preds = []
        for p in [1, 7, 30, 70, 200, 700]:
            try:
                preds.append({"params": p, "pred": math.exp(a + b * math.log(p))})
            except Exception:
                pass
        # 异常点标记（实际 vs 拟合差异 > 0.15）
        for p in pts:
            try:
                pred = math.exp(a + b * math.log(p["params"]))
                p["pred"] = round(pred, 4)
                p["diff"] = round(p["score"] - pred, 4)
                p["is_outlier"] = abs(p["score"] - pred) > 0.15
            except Exception:
                p["pred"] = None
                p["diff"] = None
                p["is_outlier"] = False

        result[bn] = {
            "n": len(pts),
            "a": round(a, 3), "b": round(b, 3), "r2": round(r2, 3),
            "predictions": preds,
            "points": pts,
        }

    return {
        "benches": result,
        "params_buckets": [
            {"label": "<1B", "lo": 0, "hi": 1},
            {"label": "1-7B", "lo": 1, "hi": 7},
            {"label": "7-30B", "lo": 7, "hi": 30},
            {"label": "30-100B", "lo": 30, "hi": 100},
            {"label": "100-350B", "lo": 100, "hi": 350},
            {"label": "350B+", "lo": 350, "hi": 100000},
        ],
    }


def build_multi_source_conflict(rows: list[dict[str, Any]],
                                raw_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """多源一致性扫描：同模型同 benchmark 多源差异

    返回：所有多源组（≥2 条）+ 不一致组（差异 ≥5%）+ 各 benchmark 不一致率
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for raw in (raw_records or []):
        mid = raw.get("model_id")
        if not mid:
            continue
        bench = raw.get("benchmarks") or {}
        for e in (bench.get("independent") or []):
            if not isinstance(e, dict):
                continue
            bn = _norm_bench_name(e.get("benchmark") or "")
            if not bn:
                continue
            score = e.get("score")
            if not isinstance(score, (int, float)):
                continue
            s = float(score)
            if s > 1.5:
                s = s / 100.0
            if s < 0 or s > 1.01:
                continue
            groups[(mid, bn)].append({
                "score": round(s, 4), "source_url": e.get("source_url") or "",
                "source_type": e.get("source_type") or "",
                "confidence": e.get("confidence") or "",
            })

    multi = {k: v for k, v in groups.items() if len(v) > 1}
    conflicts = []
    for (mid, bn), entries in multi.items():
        scores = [e["score"] for e in entries]
        diff = max(scores) - min(scores)
        if diff >= 0.05:
            conflicts.append({
                "model_id": mid, "benchmark": bn, "diff": round(diff, 4),
                "max_score": round(max(scores), 4), "min_score": round(min(scores), 4),
                "entries": entries,
            })
    conflicts.sort(key=lambda x: -x["diff"])

    # 按 benchmark 不一致率
    bench_multi_cnt = Counter()
    bench_conf_cnt = Counter()
    for (mid, bn), entries in multi.items():
        bench_multi_cnt[bn] += 1
        scores = [e["score"] for e in entries]
        if max(scores) - min(scores) >= 0.05:
            bench_conf_cnt[bn] += 1

    bench_stats = []
    for bn, multi_n in bench_multi_cnt.most_common():
        conf_n = bench_conf_cnt[bn]
        bench_stats.append({
            "benchmark": bn, "multi_n": multi_n, "conflict_n": conf_n,
            "conflict_rate": round(conf_n / multi_n * 100, 1) if multi_n else 0,
        })

    return {
        "total_groups": len(groups),
        "multi_groups": len(multi),
        "multi_coverage_rate": round(len(multi) / len(groups) * 100, 1) if groups else 0,
        "conflict_groups": len(conflicts),
        "conflict_rate": round(len(conflicts) / len(multi) * 100, 1) if multi else 0,
        "conflicts": conflicts[:100],  # 限制返回数
        "bench_stats": bench_stats,
    }


def build_extended_aggregates(rows: list[dict[str, Any]],
                              raw_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """扩展聚合入口：6 页架构 + 模型对比 + 性价比 + MoE + Arena 子榜 + 来源 + 地缘 + 档案 + 缺口 + 碎片 + 象限 + 甘特"""
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
        # 模型档案（D28+ 新增）
        "model_details": build_model_details(rows, raw_records),
        # D29 新增
        "gap_analysis": build_gap_analysis(rows, raw_records),
        "vendor_fragmentation": build_vendor_fragmentation(rows),
        # D30 新增：可视化增强
        "price_quadrant": build_price_quadrant(rows),
        "lifecycle_gantt": build_lifecycle_gantt(rows),
        # D31 新增：缺口矩阵 + 智能诊断
        "gap_matrix": build_gap_matrix(rows),
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
