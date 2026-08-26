#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_roster.py —— 阶段 0 花名册生成器（v2，按模型词干分组去重）

输入：model_data_v1_clean.jsonl
输出：
  roster.jsonl —— 机器可读花名册（每条目标厂商记录一行：status + reason）
  roster.md    —— 人读花名册（厂商分组、in_v1/to_add/out_of_scope 汇总、ID 权威规则）

判定规则（按优先级）：
  1. PRE2023_IDS 名单 / release_date 早于 2023-03 → out_of_scope(pre_2023)
  2. RESEARCH 手工清单（研究项目/论文模型/非独立模型）→ out_of_scope(research)
  3. embedding / 蒸馏 / 量化变体 → out_of_scope
  4. CROSS_DUP 手工映射（跨命名体系的同一模型）→ out_of_scope(dup)，指向规范记录
  5. 按「模型词干」分组：family 去除上下文配置后缀（-16k）、推理配置后缀
     （-high/-none/-max…）、-preview/-beta、快照日期（YYYY-MM-DD / YYYYMMDD /
     MM-DD / 4 位 MMDD）后，同组多条记录只保留一条代表（keeper），
     其余 → out_of_scope(config_dup)。KEEP_ALL_FAMILIES 中的家族例外（其
     日期后缀是真实版本发布，全部保留）。

用法：
  python gen_roster.py
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "model_data_v1_clean.jsonl")
OUT_JSONL = os.path.join(HERE, "roster.jsonl")
OUT_MD = os.path.join(HERE, "roster.md")

TIME_CUTOFF = "2023-03"

TARGET_VENDORS = [
    "openai", "anthropic", "google", "meta", "xai", "mistral", "cohere",
    "inflection", "aleph-alpha", "microsoft", "nvidia", "databricks", "cognition",
    "alibaba", "deepseek", "bytedance", "baidu", "zhipu", "moonshot",
    "iflytek", "baichuan", "tencent", "huawei", "meituan", "xiaomi",
    "zero-one", "modelbest", "aispeech",
]

AGENT_GROUPS = {
    "G1": ["openai", "anthropic"],
    "G2": ["google", "meta", "xai"],
    "G3": ["mistral", "cohere", "inflection", "aleph-alpha", "microsoft", "nvidia", "databricks", "cognition"],
    "G4": ["alibaba", "deepseek", "bytedance"],
    "G5": ["baidu", "zhipu", "moonshot", "tencent", "iflytek"],
    "G6": ["baichuan", "huawei", "meituan", "xiaomi", "zero-one", "modelbest", "aispeech"],
}

EMBEDDING_RE = re.compile(r"(embedding|reranker|gte-|nv-embed)", re.I)
DISTILL_RE = re.compile(r"distill", re.I)
QUANT_RE = re.compile(r"-(fp8|awq|gptq|int4)\b|-(fp8|awq|gptq|int4)$", re.I)

CTX_RE = re.compile(r"-(16k|27k|32k|59k|64k|128k)$")
CONFIG_RE = re.compile(r"-(high|none|low|minimal|max|xhigh)$")
MODE_RE = re.compile(r"-(preview|beta|customtools|reasoning|pre-release)$")
DATE_YMD_RE = re.compile(r"-\d{4}-\d{2}-\d{2}$")
DATE_8D_RE = re.compile(r"-\d{8}$")
DATE_MMDD_RE = re.compile(r"-\d{2}-\d{2}$")
DATE_4D_RE = re.compile(r"-\d{4}$")

# 手工判定：研究/论文项目、非独立模型、遗留非主线、第三方托管重复
RESEARCH = {
    "openai:criticgpt:base", "openai:chatgpt-agent:base", "openai:babbage-002:base",
    "google:griffin:base", "google:hawk:base",
    "google:datagemma:base", "google:datarater-test-model:base", "google:signgemma:base",
    "google:sec-gemini-v1:base", "google:t5gemma:base",
    "meta:llama-4-scout-scalerl:base",
    "alibaba:marco-o1:base", "alibaba:agentfounder-30b:base", "alibaba:tongyi-deepresearch:base",
    "deepseek:deepseekmath-v2:base", "deepseek:deepseek-prover-v1-5:base",
    "deepseek:deepseek-prover-v2-7b:base", "deepseek:deepseek-prover-v2-671b:base",
    "bytedance:bfs-prover:base", "bytedance:seed-prover:base",
    "bytedance:doubao-function-call-model:base", "bytedance:doubao-role-playing-model:base",
    "bytedance:doubao-vectorization-model:base",
    "zhipu:xtrimopglm-1b:base", "zhipu:autoglm-rumination:base",
    "nvidia:mamba2-hybrid:base", "nvidia:hymba:base",
    "databricks:dolly-v2-12b:base",
    "microsoft:microsoft-mai-1:base",
    "tencent:tencent-search-llm:base",
    "moonshot:kimi-explorer:base",
    "moonshot:fireworks-kimi-k2p5:base",   # 第三方（Fireworks）托管重复，非官方发布
}

# 手工判定：早于采集时间范围（2023-03）的无日期记录
PRE2023_IDS = {
    "openai:ada:base", "openai:curie:base", "openai:davinci:base", "openai:babbage:base",
    "openai:text-ada-001:base", "openai:text-babbage-001:base", "openai:text-curie-001:base",
    "openai:text-davinci-001:base", "openai:text-davinci-002:base", "openai:text-davinci-003:base",
    "openai:code-davinci-002:base",
    "anthropic:claude-1-3:base", "anthropic:claude-instant-1-1:base",
}

# 跨命名体系的同一模型（快照/别名 → 规范记录）
CROSS_DUP = {
    "mistral:mistral-large:2407": "mistral:mistral-large-2:base",          # 2407 即 Mistral Large 2
    "mistral:mistral-large:2411": "mistral:mistral-large-2-1:base",        # 2411 即 Mistral Large 2.1
    "openai:openai-gpt-oss-120b-high:base": "openai:gpt-oss-120b:base",    # Epoch 带厂商前缀的重复
    "anthropic:claude-2-0:base": "anthropic:claude-2:base",                # 同一发布
    "microsoft:phi-3-medium-128k-instruct:base": "microsoft:phi-3-medium-14b:base",
    "microsoft:phi-3-small-8k-instruct:base": "microsoft:phi-3-small-7-4b:base",
    "microsoft:phi-3-mini-4k-instruct:base": "microsoft:phi-3-mini-3-8b:base",
}

# 日期后缀是真实版本发布、不可合并的家族
KEEP_ALL_FAMILIES = {"mistral-small", "mistral-medium", "claude-3-5-sonnet"}


def stem_family(family: str) -> str:
    """把 family 归约为模型词干：去配置/上下文/预览后缀与快照日期。"""
    s = family
    for _ in range(4):
        s2 = CTX_RE.sub("", s)
        s2 = CONFIG_RE.sub("", s2)
        s2 = MODE_RE.sub("", s2)
        s2 = DATE_YMD_RE.sub("", s2)
        s2 = DATE_8D_RE.sub("", s2)
        s2 = DATE_MMDD_RE.sub("", s2)
        s2 = DATE_4D_RE.sub("", s2)
        if s2 == s:
            break
        s = s2
    return re.sub(r"-0$", "", s)


def split_mid(mid: str):
    vendor, family, variant = mid.split(":", 2)
    return vendor, family, variant


def bench_count(rec):
    return len(rec.get("benchmarks", {}).get("independent") or [])


def pick_keeper(mids, recs_by_id, stem):
    """同词干组内选代表记录：优先 family==词干的锚点，其次数据最全、发布最近。"""
    def score(mid):
        r = recs_by_id[mid]
        _, family, variant = split_mid(mid)
        anchor = 1 if family == stem else 0
        base = 1 if variant == "base" else 0
        return (anchor, base, bench_count(r), r.get("basic_info", {}).get("release_date") or "")

    return sorted(mids, key=score, reverse=True)[0]


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    recs = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    recs_by_id = {r["model_id"]: r for r in recs}

    # 校验手工映射的目标都存在
    for src_mid, dst_mid in CROSS_DUP.items():
        assert dst_mid in recs_by_id, f"CROSS_DUP 目标不存在：{dst_mid}"
    for mid in RESEARCH | PRE2023_IDS:
        assert mid in recs_by_id, f"手工清单 model_id 不存在：{mid}"

    # 第一遍：逐条基础分类
    entries = {}
    for r in recs:
        mid = r["model_id"]
        vendor, family, variant = split_mid(mid)
        if vendor not in TARGET_VENDORS:
            continue
        bi = r.get("basic_info", {})
        rd = bi.get("release_date") or ""
        status, reason = None, ""

        if mid in PRE2023_IDS or (rd and rd < TIME_CUTOFF):
            status, reason = "out_of_scope", f"pre_2023：早于采集时间范围起点 {TIME_CUTOFF}"
        elif mid in RESEARCH:
            status, reason = "out_of_scope", "research：手工判定的研究/论文项目或非独立模型"
        elif EMBEDDING_RE.search(mid) or EMBEDDING_RE.search(bi.get("full_name") or ""):
            status, reason = "out_of_scope", "embedding：向量/重排模型，不属于文本生成主线"
        elif DISTILL_RE.search(mid) or DISTILL_RE.search(bi.get("full_name") or ""):
            status, reason = "out_of_scope", "distilled：蒸馏变体，采集范围明确排除"
        elif QUANT_RE.search(mid) or QUANT_RE.search(bi.get("full_name") or ""):
            status, reason = "out_of_scope", "quant：量化变体，采集范围明确排除"
        elif mid in CROSS_DUP:
            status, reason = "out_of_scope", f"dup：与 {CROSS_DUP[mid]} 为同一模型（别名/快照）"

        entries[mid] = {
            "model_id": mid, "vendor": vendor, "family": family,
            "full_name": bi.get("full_name"), "release_date": bi.get("release_date"),
            "status": status, "reason": reason,
        }

    # 第二遍：词干分组去重（仅对未排除的记录）
    groups = defaultdict(list)
    for mid, e in entries.items():
        if e["status"] is None:
            groups[(e["vendor"], stem_family(e["family"]))].append(mid)

    dup_count = 0
    for (vendor, stem), mids in groups.items():
        if len(mids) < 2:
            continue
        if stem in KEEP_ALL_FAMILIES:
            continue
        keeper = pick_keeper(mids, recs_by_id, stem)
        for mid in mids:
            if mid != keeper:
                entries[mid]["status"] = "out_of_scope"
                entries[mid]["reason"] = f"config_dup：与 {keeper} 为同一模型的配置/快照变体"
                dup_count += 1

    # 剩余未排除 → in_v1
    for e in entries.values():
        if e["status"] is None:
            e["status"], e["reason"] = "in_v1", ""

    roster = sorted(entries.values(), key=lambda x: (x["vendor"], x["release_date"] or "", x["model_id"]))
    stats = Counter((x["vendor"], x["status"]) for x in roster)
    in_v1 = [x for x in roster if x["status"] == "in_v1"]
    out = [x for x in roster if x["status"] == "out_of_scope"]

    # 范围内但 v1 缺失、需采集新增（to_add）
    TO_ADD = [
        ("anthropic:claude-3-sonnet:base", "anthropic", "Claude 3 Sonnet", "2024-03 Claude 3 三件套之一，v1 缺失"),
        ("openai:gpt-4.1-mini:base", "openai", "GPT-4.1 mini", "2025-04 官方主线，v1 仅有 gpt-4.1"),
        ("google:gemini-1.0-ultra:base", "google", "Gemini 1.0 Ultra", "2023-12 首批旗舰之一，v1 缺失"),
        ("google:gemini-2.0-flash:base", "google", "Gemini 2.0 Flash", "2024-12 主线模型，v1 缺失"),
        ("google:gemini-3-pro:base", "google", "Gemini 3 Pro", "2025-11 旗舰，v1 缺失"),
        ("meta:llama-4-maverick:base", "meta", "Llama 4 Maverick", "v1 仅有 fp8 量化版，需采官方版"),
        ("xai:grok-1:base", "xai", "Grok-1", "2023-11 首个版本，v1 缺失"),
        ("xai:grok-3:base", "xai", "Grok 3", "2025-02 旗舰，v1 仅有 mini"),
        ("mistral:mistral-medium:base", "mistral", "Mistral Medium", "2024-01 首发三件套之一，v1 缺失"),
        ("cohere:command-r:base", "cohere", "Command R", "2024-03 主线，v1 缺失"),
        ("cohere:command-r-plus:base", "cohere", "Command R+", "2024-04 旗舰，v1 缺失"),
        ("inflection:inflection-3:base", "inflection", "Inflection-3", "2024-06，v1 缺失"),
        ("microsoft:phi-4:base", "microsoft", "Phi-4", "2024-12 主线，v1 缺失"),
        ("alibaba:qwen3-235b-a22b:base", "alibaba", "Qwen3-235B-A22B", "2025-04 旗舰基础版，v1 仅有 thinking 变体"),
        ("baidu:ernie-4.0:base", "baidu", "ERNIE 4.0", "2023-10 旗舰 API，v1 缺失"),
        ("baidu:ernie-x1:base", "baidu", "ERNIE X1", "2025-03 推理模型，v1 缺失"),
        ("zhipu:glm-4:base", "zhipu", "GLM-4", "2024-01 旗舰，v1 缺失"),
        ("zhipu:glm-4.5:base", "zhipu", "GLM-4.5", "2025-07 旗舰（开源+API），v1 缺失"),
        ("zhipu:glm-4.6:base", "zhipu", "GLM-4.6", "2025-09 旗舰，v1 缺失"),
        ("moonshot:kimi-k2:base", "moonshot", "Kimi K2", "2025-07 旗舰开源，v1 缺失（仅有后续版本）"),
        ("tencent:hunyuan-t1:base", "tencent", "Hunyuan-T1", "2025-03 推理模型，v1 缺失"),
        ("tencent:hunyuan-a13b:base", "tencent", "Hunyuan-A13B", "2025-05 开源 MoE，v1 缺失"),
        ("iflytek:spark-x1:base", "iflytek", "讯飞星火 X1", "2025-03 推理模型，v1 缺失"),
        ("xiaomi:mimo-7b:base", "xiaomi", "MiMo-7B", "2025-04 开源，v1 缺失"),
        ("meituan:longcat-flash:base", "meituan", "LongCat-Flash", "2025 美团开源 MoE，v1 无美团记录"),
        ("modelbest:minicpm-4:base", "modelbest", "MiniCPM 4", "2025-06 面壁旗舰开源，v1 无面壁记录"),
    ]

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for item in roster:
            f.write(json.dumps({k: item[k] for k in
                                ("model_id", "vendor", "full_name", "release_date", "status", "reason")},
                               ensure_ascii=False) + "\n")
        for mid, vendor, name, note in TO_ADD:
            f.write(json.dumps({"model_id": mid, "vendor": vendor, "full_name": name,
                                "release_date": None, "status": "to_add", "reason": note},
                               ensure_ascii=False) + "\n")

    reason_stats = Counter(x["reason"].split("：")[0] for x in out)
    md = []
    md.append("# 花名册（roster）—— 28 厂商 × 旗舰/主线模型范围判定")
    md.append("")
    md.append("> 阶段 0 产物。生成脚本：`gen_roster.py`；数据基线：`model_data_v1_clean.jsonl`。")
    md.append("> 机器可读版本：`roster.jsonl`（每行：model_id / vendor / status / reason）。")
    md.append("")
    md.append("## model_id 权威规则（P1 修复，全体采集 agent 必须遵守）")
    md.append("")
    md.append("1. 花名册是 model_id 的**唯一权威**。")
    md.append("2. `in_v1` 模型：**原样沿用本花名册中的 model_id**（v1 风格：连字符 family + `:base`），"
              "严禁「纠正」成点号风格或营销代号风格。")
    md.append("3. `to_add` 模型：**原样使用花名册分配的 model_id**（prompt 决策 6 风格），采集产出必须逐字一致。")
    md.append("4. 采集 agent 不得自行发明新 model_id，不得修改已有记录的 model_id。")
    md.append("5. 花名册外的模型（`out_of_scope`）不采集；发现范围外的新旗舰/主线 → 回报主 agent 补录花名册后再采。")
    md.append("")
    md.append(f"## 汇总：目标厂商记录 {len(roster)} 条")
    md.append("")
    md.append(f"- `in_v1`（沿用并富集）：**{len(in_v1)}** 条")
    md.append(f"- `to_add`（花名册分配、待采集）：**{len(TO_ADD)}** 条")
    md.append(f"- `out_of_scope`（归档、不采集）：**{len(out)}** 条")
    md.append("")
    md.append("out_of_scope 原因分布：" + "、".join(f"{k} {v}" for k, v in reason_stats.most_common()))
    md.append("")
    md.append("## 采集 agent 分组（阶段 1 分片依据）")
    md.append("")
    md.append("| 组 | 厂商（in_v1 / to_add 数量） |")
    md.append("|---|---|")
    for g, vendors in AGENT_GROUPS.items():
        parts = []
        for v in vendors:
            iv = stats.get((v, "in_v1"), 0)
            ta = sum(1 for t in TO_ADD if t[1] == v)
            parts.append(f"{v}（{iv}/{ta}）")
        md.append(f"| {g} | {'、'.join(parts)} |")
    md.append("")
    md.append("> 格式：厂商名（in_v1 数 / to_add 数）。P1 平台 agent（LMArena）与 P2 平台 agent（独立跑分）不分厂商。")
    md.append("")
    md.append("## to_add 清单（新模型，按此 model_id 全量采集）")
    md.append("")
    md.append("| model_id | 名称 | 备注 |")
    md.append("|---|---|---|")
    for mid, vendor, name, note in TO_ADD:
        md.append(f"| `{mid}` | {name} | {note} |")
    md.append("")
    md.append("## 各厂商 in_v1 明细")
    md.append("")
    by_vendor = defaultdict(list)
    for x in in_v1:
        by_vendor[x["vendor"]].append(x)
    for v in TARGET_VENDORS:
        items = by_vendor.get(v, [])
        ta = [t for t in TO_ADD if t[1] == v]
        md.append(f"### {v}（in_v1 {len(items)}，to_add {len(ta)}）")
        md.append("")
        for x in sorted(items, key=lambda a: (a["release_date"] or "", a["model_id"])):
            md.append(f"- `{x['model_id']}`（{x['full_name']}，{x['release_date'] or '日期缺失'}）")
        for t in ta:
            md.append(f"- `[to_add]` `{t[0]}`（{t[2]}）")
        md.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"roster written: {OUT_JSONL}")
    print(f"in_v1={len(in_v1)}, to_add={len(TO_ADD)}, out_of_scope={len(out)} (config_dup={dup_count})")
    print("out reasons:", dict(reason_stats))


if __name__ == "__main__":
    main()
