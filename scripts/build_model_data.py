#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_model_data.py —— 依据 external_sources 里的「相对官方」资料，生成第一版大模型静态数据集 (JSONL)

数据源：
  1. external_sources/epoch_ai_models/all_ai_models.csv
     Epoch AI《Data on AI Models》—— 模型身份 + 参数量 + 开放权重 + 发布日期。
     许可：CC BY 4.0（epoch.ai）。
  2. external_sources/epoch_benchmark_data/*.csv
     Epoch AI《AI Benchmarking Hub》—— 各模型在主流基准上的独立评测分。
  3. external_sources/table.md
     Sebastian Raschka《The Big LLM Architecture Comparison》—— 上下文长度 / MoE / 注意力等架构细节。

产出：
  model_data_v1.jsonl  —— schema_version "1.1"，严格对齐 prompt.md / 执行细则。
  缺失字段一律填 null（不伪造）；定价 / 多模态 / 跑分自报 不在上述来源中 → 标注 null + notes。
  所有基准分作为 independent（T1，独立评测平台）录入；来源为二手/聚合，meta.notes 统一声明。

用法：
  python build_model_data.py
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(HERE, "external_sources")
CSV_MODELS = os.path.join(EXT, "epoch_ai_models", "all_ai_models.csv")
DIR_BENCH = os.path.join(EXT, "epoch_benchmark_data")
TABLE_MD = os.path.join(EXT, "table.md")
OUT = os.path.join(HERE, "model_data_v1.jsonl")

COLLECTED_AT = "2026-08-24"
EPOCH_MODELS_URL = "https://epoch.ai/data/ai-models"
EPOCH_BENCH_URL = "https://epoch.ai/benchmarks"

# ------------------------------------------------------------------
# 1. 厂商 slug 映射
# ------------------------------------------------------------------
VENDOR_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google deepmind": "google",
    "google": "google",
    "deepseek": "deepseek",
    "alibaba": "alibaba",
    "z.ai (zhipu ai)": "zhipu",
    "zhipu ai": "zhipu",
    "z.ai": "zhipu",
    "moonshot ai": "moonshot",
    "meta": "meta",
    "xai": "xai",
    "mistral ai": "mistral",
    "mistral": "mistral",
    "cohere": "cohere",
    "microsoft": "microsoft",
    "nvidia": "nvidia",
    "tencent": "tencent",
    "baidu": "baidu",
    "bytedance": "bytedance",
    "byte dance": "bytedance",
    "huawei": "huawei",
    "amazon": "amazon",
    "thinking machines": "thinking-machines",
    "databricks": "databricks",
    "ai21 labs": "ai21",
    "apple": "apple",
    "inflection ai": "inflection",
    "aleph alpha": "aleph-alpha",
    "01.ai": "zero-one",
    "minimax": "minimax",
    "stepfun": "stepfun",
    "shanghai ai laboratory": "opencompass",
    "qwen": "alibaba",
    "alibaba qwen": "alibaba",
    "kimi": "moonshot",
}


def vendor_slug(org: str) -> str:
    if not org:
        return "unknown"
    key = org.strip().lower()
    if key in VENDOR_MAP:
        return VENDOR_MAP[key]
    # 去掉常见后缀词后尝试再映射
    norm = re.sub(r"\b(inc|labs|ai|corp|company|technologies|tech)\b", "", key).strip()
    norm = re.sub(r"\s+", " ", norm)
    if norm in VENDOR_MAP:
        return VENDOR_MAP[norm]
    return re.sub(r"[^a-z0-9]+", "-", key).strip("-") or "unknown"


# ------------------------------------------------------------------
# 2. 名称规范化（用于跨表匹配）
# ------------------------------------------------------------------
STOP = {
    "max", "pro", "mini", "flash", "lite", "ultra", "preview", "base", "high",
    "xhigh", "default", "low", "lowest", "medium", "auto", "thinking", "standard",
    "plus", "turbo", "nano", "small", "large", "air", "sonnet", "haiku", "opus",
    "o", "v", "instruct", "chat", "it", "instant", "exp", "experimental",
}


def canon(s: str) -> str:
    """规范化为跨表匹配的键：小写、去括号内容、去营销/后缀词、仅留字母数字。"""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    # 先按非字母数字切词，去掉停用词
    toks = re.split(r"[^a-z0-9]+", s)
    toks = [t for t in toks if t and t not in STOP]
    return "".join(toks)


def strip_config_suffix(mv: str):
    """拆出基准 'Model version' 里的推理档位后缀（_max / -high ...）。"""
    m = re.search(r"[-_](max|high|xhigh|default|low|lowest|medium|auto|thinking|ultra|standard|base|preview|exp|experimental)$",
                  mv, flags=re.I)
    if m:
        return mv[: m.start()], m.group(1).lower()
    return mv, "default"


# ------------------------------------------------------------------
# 3. 解析 all_ai_models.csv → 模型注册表
# ------------------------------------------------------------------

def parse_params_float(val: str):
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def extract_active(params_notes: str):
    """从 '1.6T total, 49B active' / '744B total and 40B active' 抽取激活参数(B)。"""
    if not params_notes:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]\s*(?:active|/)", params_notes)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]\s+active", params_notes)
    if m:
        return float(m.group(1))
    return None


def parse_release_month(d: str):
    if not d:
        return None
    m = re.match(r"(\d{4})-(\d{2})", d)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"(\d{4})", d)
    if m:
        return f"{m.group(1)}-01"
    return None


def load_registry():
    """返回 {canon_key: rec}，rec 含身份/参数/开放权重等；同键保留最新发布日期。"""
    reg: dict = {}
    if not os.path.exists(CSV_MODELS):
        return reg
    with open(CSV_MODELS, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Model") or "").strip()
            if not name:
                continue
            dom = (row.get("Domain") or "").strip().lower()
            # 只收语言模型（Domain 为空也保留，后续用日期/基准兜底）
            if dom and dom != "language":
                continue
            ck = canon(name)
            if not ck:
                continue
            pub = row.get("Publication date") or ""
            org = row.get("Organization") or ""
            params = parse_params_float(row.get("Parameters"))
            notes = row.get("Parameters notes") or ""
            frontier = (row.get("Frontier model") or "").strip().lower() in ("true", "yes", "1")
            rec = reg.get(ck)
            cur_year = int(pub[:4]) if pub[:4].isdigit() else 0
            if rec is None or cur_year > (int(rec["_pub"][:4]) if rec["_pub"][:4].isdigit() else 0):
                reg[ck] = {
                    "name": name,
                    "org": org,
                    "pub": pub,
                    "_pub": pub,
                    "params": params,            # 单位：个（原始）
                    "params_notes": notes,
                    "link": row.get("Link") or "",
                    "confidence": row.get("Confidence") or "",
                    "open_weights": row.get("Open model weights?") or "",
                    "country": row.get("Country (of organization)") or "",
                    "frontier": frontier,
                    "accessibility": row.get("Model accessibility") or "",
                }
    return reg


# ------------------------------------------------------------------
# 4. 解析 table.md → 架构细节（上下文长度 / MoE / 注意力）
# ------------------------------------------------------------------

def parse_context_len(cell: str):
    if not cell:
        return None
    best = None
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([KkMm])", cell):
        num = float(m.group(1))
        unit = m.group(2).lower()
        val = int(num * (1_000 if unit == "k" else 1_000_000))
        if best is None or val > best:
            best = val
    return best


def load_table_md():
    """返回 {canon_key: {context_tokens, arch_type, moa_active}}。"""
    out: dict = {}
    if not os.path.exists(TABLE_MD):
        return out
    with open(TABLE_MD, encoding="utf-8") as f:
        lines = f.readlines()
    # 找主表表头：必须同时含 Model / Context Len. / MoE（排除顶部「列定义」表）
    header = None
    for line in lines:
        if (line.strip().startswith("|") and "Context Len." in line
                and "Model" in line and "MoE" in line):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            break
    if not header:
        return out
    try:
        i_model = header.index("Model")
        i_ctx = header.index("Context Len.")
        i_moe = header.index("MoE")
    except ValueError:
        return out
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) <= max(i_model, i_ctx, i_moe):
            continue
        model = cols[i_model]
        if not model or model == "Model" or set(model) <= set("- "):
            continue
        ck = canon(model)
        if not ck:
            continue
        ctx = parse_context_len(cols[i_ctx])
        moe = cols[i_moe]
        arch_type = "Unknown"
        active = None
        if re.search(r"sparse|moe|expert", moe, re.I):
            arch_type = "MoE"
            am = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]\s*/\s*(\d+(?:\.\d+)?)\s*[Bb]\s*active", moe)
            if am:
                active = float(am.group(2))
        elif re.search(r"dense", moe, re.I):
            arch_type = "Dense"
        out[ck] = {"context_tokens": ctx, "arch_type": arch_type, "moa_active": active}
    return out


# ------------------------------------------------------------------
# 5. 解析基准 CSV → {canon_key: {benchmark_display: [entries]}}
# ------------------------------------------------------------------

# 选取与 prompt.md 推荐基准接近、且覆盖度高的基准文件
BENCH_FILES = {
    "GPQA Diamond": "gpqa_diamond.csv",
    "SWE-bench Verified": "swe_bench_verified.csv",
    "MMLU": "mmlu_external.csv",
    "LiveBench": "live_bench_external.csv",
    "AIME 2025": "otis_mock_aime_2024_2025.csv",
    "HLE": "hle_external.csv",
    "SimpleQA": "simpleqa_verified.csv",
    "GSM8K": "gsm8k_external.csv",
    "MATH Level 5": "math_level_5.csv",
    "BBH": "bbh_external.csv",
    "TriviaQA": "trivia_qa_external.csv",
    "SciCode": "scicode_external.csv",
    "ProofBench": "proofbench_external.csv",
    "Terminal-Bench": "terminalbench_external.csv",
    "DeepSWE": "deepswe_external.csv",
    "FrontierCode": "frontiercode_external.csv",
    "Aider Polyglot": "aider_polyglot_external.csv",
    "Cybench": "cybench_external.csv",
    "ExploitBench": "exploitbench_external.csv",
    "ARC-AGI": "arc_agi_external.csv",
    "Video-MME": "video_mme_external.csv",
}

SCORE_TYPE = {
    "GPQA Diamond": "accuracy",
    "SWE-bench Verified": "pass@1",
    "MMLU": "EM",
    "LiveBench": "accuracy",
    "AIME 2025": "accuracy",
    "HLE": "accuracy",
    "SimpleQA": "accuracy",
    "GSM8K": "accuracy",
    "MATH Level 5": "accuracy",
    "BBH": "accuracy",
    "TriviaQA": "accuracy",
    "SciCode": "pass@1",
    "ProofBench": "pass@1",
    "Terminal-Bench": "accuracy",
    "DeepSWE": "resolved",
    "FrontierCode": "pass@1",
    "Aider Polyglot": "pass@1",
    "Cybench": "pass@1",
    "ExploitBench": "accuracy",
    "ARC-AGI": "accuracy",
    "Video-MME": "accuracy",
}


def load_benchmarks():
    """返回 {canon_key: {bench_display: best_entry_dict}}。每个 (模型,基准) 取最高分代表。"""
    index: dict = {}
    for disp, fname in BENCH_FILES.items():
        path = os.path.join(DIR_BENCH, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mv = (row.get("Model version") or "").strip()
                if not mv:
                    continue
                base, cfg = strip_config_suffix(mv)
                ck = canon(base)
                if not ck:
                    continue
                # 分数：mean_score 或 EM
                score = None
                for col in ("mean_score", "EM", "Best score (across scorers)"):
                    if row.get(col):
                        try:
                            score = float(row[col])
                            break
                        except ValueError:
                            pass
                if score is None:
                    continue
                org = row.get("Organization") or ""
                rdate = row.get("Release date") or ""
                rec = {
                    "benchmark": disp,
                    "score": score,
                    "score_type": SCORE_TYPE.get(disp, "accuracy"),
                    "config": cfg,
                    "date": rdate[:7] if rdate[:7] else None,
                    "org": org,
                    "model_version": mv,
                }
                sub = index.setdefault(ck, {})
                cur = sub.get(disp)
                if cur is None or score > cur["score"]:
                    sub[disp] = rec
    return index


# ------------------------------------------------------------------
# 6. 组装记录
# ------------------------------------------------------------------

def build_model_id(vendor: str, name: str):
    base = name.lower()
    base = re.sub(r"\([^)]*\)", "", base)
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    # 抽取尾部日期/快照作为 variant
    m = re.search(r"-(\d{4}(?:-\d{2})?|\d{6}|\d{8})$", base)
    if m:
        variant = m.group(1).replace("-", "")
        family = base[: m.start()].strip("-")
    else:
        variant = "base"
        family = base
    if not family:
        family = base or "model"
    return f"{vendor}:{family}:{variant}"


def blank_modality():
    note = "来源数据未含多模态信息；需另行采集官方产品页/API 文档（决策7）"
    return {
        "input": {"text": None, "image": None, "audio": None, "video": None,
                  "pdf": None, "code": None, "web": None, "notes": note},
        "output": {"text": None, "code": None, "image": None, "audio": None,
                   "speech": None, "notes": note},
        "native_multimodal": {"input_image": None, "input_audio": None, "input_video": None,
                              "output_image": None, "output_audio": None, "notes": note},
    }


def blank_pricing():
    return {
        "currency": "USD", "unit": "per_million_tokens",
        "input": None, "output": None,
        "cached_input": None, "cache_write": None,
        "batch_input": None, "batch_output": None,
        "free_tier": None, "promotions": None, "long_context": None,
        "effective_date": None, "source_url": None, "source_type": None,
        "confidence": None,
        "notes": "来源数据未含定价信息（Epoch AI 模型库/基准聚合不含定价）；需另行采集官方定价页（决策1，严禁伪造 T0）",
    }


def build_records(registry, table_md, bench_index):
    records = []
    seen_ids = set()

    # 候选键：注册表 + 基准出现的键
    keys = set(registry.keys()) | set(bench_index.keys())

    for ck in sorted(keys):
        reg = registry.get(ck)
        benchs = bench_index.get(ck, {})
        # 范围裁剪：只保留「前沿 / 2024 年后发布 / 出现在基准」的模型，聚焦第一版
        pub_year = 0
        if reg and reg["_pub"][:4].isdigit():
            pub_year = int(reg["_pub"][:4])
        keep = (reg and (reg["frontier"] or pub_year >= 2024)) or bool(benchs)
        if not keep:
            continue

        name = reg["name"] if reg else next(
            (b["model_version"] for b in benchs.values()), ck)
        org = reg["org"] if reg else next(
            (b["org"] for b in benchs.values() if b["org"]), "")
        vendor = vendor_slug(org)

        model_id = build_model_id(vendor, name)
        # 唯一性兜底
        if model_id in seen_ids:
            model_id = f"{model_id}-{ck[:4]}"
        seen_ids.add(model_id)

        # ---- basic_info ----
        release = parse_release_month(reg["pub"]) if reg else None
        if release is None and benchs:
            # 用任一基准的日期
            for b in benchs.values():
                if b["date"]:
                    release = b["date"][:7]
                    break
        open_weights = None
        api = None
        local_deploy = None
        if reg:
            ow = (reg["open_weights"] or "").lower()
            if ow in ("true", "yes", "1"):
                open_weights = True
            elif ow in ("false", "no", "0"):
                open_weights = False
            acc = (reg["accessibility"] or "").lower()
            if "open weights" in acc:
                open_weights = True
            api = True if open_weights else (None if not acc else True)
        basic_info = {
            "full_name": name,
            "version": None,
            "vendor": org or vendor,
            "release_date": release,
            "positioning": [],
            "access": {"open_weights": open_weights, "api": api,
                       "local_deployment": local_deploy, "notes": None},
        }

        # ---- architecture ----
        total_b = None
        active_b = None
        arch_type = "Unknown"
        ctx = None
        notes_parts = []
        if reg and reg["params"]:
            total_b = round(reg["params"] / 1e9, 3)
            active_b = extract_active(reg["params_notes"])
            if active_b is not None and total_b is not None and active_b < total_b:
                arch_type = "MoE"
            elif re.search(r"moe|expert|mixture", reg["params_notes"], re.I):
                arch_type = "MoE"
        if ck in table_md:
            t = table_md[ck]
            if t["context_tokens"]:
                ctx = t["context_tokens"]
            if t["arch_type"] != "Unknown":
                arch_type = t["arch_type"]
            if t["moa_active"]:
                active_b = t["moa_active"]
        if total_b is None:
            notes_parts.append("官方未披露参数量")
        if ctx is None:
            notes_parts.append("上下文长度未从架构来源获取，待补")
        else:
            notes_parts.append(f"标称上下文 {ctx:,} tokens（来自架构对比表），有效上下文未独立测试")
        if arch_type == "MoE":
            notes_parts.append("MoE 架构")
        arch_notes = "；".join(notes_parts) if notes_parts else None
        architecture = {
            "total_params_b": total_b,
            "active_params_b": active_b,
            "architecture_type": arch_type,
            "context_window_tokens": ctx,
            "context_window_effective_tokens": None,
            "knowledge_cutoff": None,
            "notes": arch_notes,
        }

        # ---- benchmarks ----
        independent = []
        for disp, b in benchs.items():
            independent.append({
                "benchmark": disp,
                "score": round(b["score"], 4),
                "score_type": b["score_type"],
                "config": b["config"],
                "date": b["date"],
                "source_url": EPOCH_BENCH_URL,
                "source_type": "独立评测平台",
                "confidence": "T1",
                "gap_to_self_reported": None,
                "notes": f"Epoch AI Benchmarking Hub 独立聚合；原始 Model version={b['model_version']}",
            })
        independent.sort(key=lambda x: x["benchmark"])
        benchmarks = {
            "self_reported": [],
            "independent": independent,
            "arena_elo": [],
        }

        # ---- meta ----
        srcs = []
        if reg and reg["link"]:
            srcs.append(reg["link"])
        srcs.append(EPOCH_MODELS_URL)
        srcs.append(EPOCH_BENCH_URL)
        meta_notes = ("数据来自 Epoch AI 公开数据集（《Data on AI Models》模型清单 + 《AI Benchmarking Hub》基准聚合）"
                      "及 Raschka《The Big LLM Architecture Comparison》（table.md），均为二手/聚合来源，非厂商官方直读；"
                      "参数量以官方披露为准、部分由 Epoch 汇总；定价/多模态/跑分自报缺失，需后续以官方页核实（决策1 降级采集）。")
        meta = {
            "collected_at": COLLECTED_AT,
            "verified_at": None,
            "verification_status": "待验证",
            "source_urls": srcs,
            "notes": meta_notes,
        }

        rec = {
            "schema_version": "1.1",
            "model_id": model_id,
            "basic_info": basic_info,
            "architecture": architecture,
            "benchmarks": benchmarks,
            "pricing": blank_pricing(),
            "modality": blank_modality(),
            "meta": meta,
        }
        records.append(rec)
    return records


def main():
    print(f"[1/4] 读取模型注册表 {os.path.basename(CSV_MODELS)} ...")
    registry = load_registry()
    print(f"      注册表模型(语言类, 去重后): {len(registry)}")

    print("[2/4] 读取架构对比表 table.md ...")
    table_md = load_table_md()
    print(f"      架构表命中模型: {len(table_md)}")

    print("[3/4] 读取基准 CSV ...")
    bench_index = load_benchmarks()
    total_bench = sum(len(v) for v in bench_index.values())
    print(f"      基准索引: {len(bench_index)} 模型, {total_bench} 条 (模型×基准)")

    print("[4/4] 组装并写出 ...")
    records = build_records(registry, table_md, bench_index)
    records.sort(key=lambda r: r["model_id"])
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:  # 强制 LF，符合 prompt.md 规范
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"      写出 {len(records)} 条 -> {os.path.basename(OUT)}")

    # 简单覆盖统计
    with_params = sum(1 for r in records if r["architecture"]["total_params_b"] is not None)
    with_ctx = sum(1 for r in records if r["architecture"]["context_window_tokens"] is not None)
    with_bench = sum(1 for r in records if r["benchmarks"]["independent"])
    print("---- 覆盖统计 ----")
    print(f"  总记录数        : {len(records)}")
    print(f"  有参数量        : {with_params}")
    print(f"  有上下文长度    : {with_ctx}")
    print(f"  有独立跑分      : {with_bench}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
