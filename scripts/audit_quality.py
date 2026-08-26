#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立数据质量剖析（不依赖官方校验器逻辑，纯数据透视）。
目标：量化 model_data_v2.jsonl 的真实数据浓度，剥离"占位符/空壳"。
"""
import json, re, os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # model_data 根目录
V2 = os.path.join(BASE, "model_data_v2.jsonl")
V1C = os.path.join(BASE, "backups", "model_data_v1_clean.jsonl")

def load(p):
    recs = []
    with open(p, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            recs.append(json.loads(line))
    return recs

v2 = load(V2)
v1c = load(V1C)

PLACEHOLDER = ["待补", "未含", "未披露", "缺失", "需另行", "需另", "来源数据未含",
               "未采集", "暂缺", "暂无", "无数据", "未获取", "待采集", "不含",
               "尚未", "留空", "N/A", "n/a", "TBD", "TODO"]

def is_placeholder(text):
    if not isinstance(text, str):
        return False
    return any(k in text for k in PLACEHOLDER)

def notnull(x):
    return x is not None

# ---- 顶层统计 ----
N = len(v2)
print(f"=== 总量 ===")
print(f"v2 记录数: {N}")
print(f"v1_clean 记录数: {len(v1c)}")

# model_id 三段式 & 重复
ids = [r.get("model_id") for r in v2]
dup = [k for k, c in Counter(ids).items() if c > 1]
print(f"\n=== model_id ===")
print(f"重复 model_id 数: {len(dup)}")
for d in dup[:20]:
    print(f"  重复: {d} x{Counter(ids)[d]}")
bad_fmt = [i for i in ids if not (isinstance(i, str) and len(i.split(':')) == 3 and all(i.split(':')))]
print(f"非三段式 model_id 数: {len(bad_fmt)}")

# v1_clean 的 id 集合，判断哪些是新增
v1_ids = set(r.get("model_id") for r in v1c)
new_ids = [i for i in ids if i not in v1_ids]
print(f"v1_clean 中已有 id 数: {len(v1_ids & set(ids))}")
print(f"v2 相对 v1_clean 新增的 id 数: {len(new_ids)}")
print(f"新增 id 样例: {new_ids[:25]}")

# ---- 字段填充率 ----
def fill_rate(fn):
    c = sum(1 for r in v2 if fn(r))
    return c, round(100*c/N, 1)

print(f"\n=== 关键字段填充率（v2, N={N}）===")

def has_pricing(r):
    p = r.get("pricing") or {}
    return notnull(p.get("input")) or notnull(p.get("output")) or notnull(p.get("cached_input"))

def has_any_bench(r):
    b = r.get("benchmarks") or {}
    return (b.get("self_reported") or []) or (b.get("independent") or []) or (b.get("arena_elo") or [])

def has_modality_info(r):
    m = r.get("modality") or {}
    vals = []
    for sec in ("input","output","native_multimodal"):
        blk = m.get(sec) or {}
        for k, v in blk.items():
            if k == "notes": continue
            if v is not None:
                vals.append(v)
    return len(vals) > 0

def has_positioning(r):
    p = (r.get("basic_info") or {}).get("positioning")
    return isinstance(p, list) and len(p) > 0

def has_arch_params(r):
    a = r.get("architecture") or {}
    return notnull(a.get("total_params_b")) or notnull(a.get("active_params_b"))

def has_context(r):
    a = r.get("architecture") or {}
    return notnull(a.get("context_window_tokens")) or notnull(a.get("context_window_effective_tokens"))

def has_release_date(r):
    return notnull((r.get("basic_info") or {}).get("release_date"))

def has_vendor(r):
    return notnull((r.get("basic_info") or {}).get("vendor"))

metrics = {
    "vendor(厂商)": has_vendor,
    "release_date(发布日期)": has_release_date,
    "架构参数量": has_arch_params,
    "上下文窗口": has_context,
    "定价(有价)": has_pricing,
    "多模态(有标注)": has_modality_info,
    "positioning(定位)": has_positioning,
    "任意跑分": has_any_bench,
}
for name, fn in metrics.items():
    c, pct = fill_rate(fn)
    print(f"  {name:24s}: {c:4d}  ({pct}%)")

# ---- 占位符浓度 ----
def count_placeholder_notes(r):
    n = 0
    notes_fields = []
    a = r.get("architecture") or {}
    notes_fields.append(a.get("notes"))
    p = r.get("pricing") or {}
    notes_fields.append(p.get("notes"))
    m = r.get("modality") or {}
    for sec in m:
        if isinstance(m[sec], dict):
            notes_fields.append(m[sec].get("notes"))
    meta = r.get("meta") or {}
    notes_fields.append(meta.get("notes"))
    for t in notes_fields:
        if is_placeholder(t):
            n += 1
    return n

ph_counts = [count_placeholder_notes(r) for r in v2]
recs_with_ph = sum(1 for x in ph_counts if x > 0)
print(f"\n=== 占位符浓度 ===")
print(f"含占位符 notes 的记录数: {recs_with_ph} ({round(100*recs_with_ph/N,1)}%)")
print(f"占位符 notes 字段总计数: {sum(ph_counts)}")

# ---- 空壳判定 ----
def is_shell(r):
    """空壳：无定价、无跑分、无多模态标注、无定位、参数量也空"""
    return not (has_pricing(r) or has_any_bench(r) or has_modality_info(r) or has_positioning(r) or has_arch_params(r))

shells = [r for r in v2 if is_shell(r)]
print(f"\n=== 空壳判定 ===")
print(f"空壳记录数(无任何实质数据): {len(shells)} ({round(100*len(shells)/N,1)}%)")

# 空壳里多少是基座、多少是新增
shell_base = [r for r in shells if r.get("model_id") in v1_ids]
shell_new = [r for r in shells if r.get("model_id") not in v1_ids]
print(f"  其中来自基座(v1_clean)的空壳: {len(shell_base)}")
print(f"  其中新增记录中的空壳: {len(shell_new)}")

# ---- 唯一有实质数据的记录 ----
real = [r for r in v2 if not is_shell(r)]
print(f"有至少一项实质数据的记录: {len(real)} ({round(100*len(real)/N,1)}%)")

# 细分：仅有架构参数(无定价/跑分/模态)的
only_arch = [r for r in v2 if has_arch_params(r) and not (has_pricing(r) or has_any_bench(r) or has_modality_info(r) or has_positioning(r))]
print(f"  仅含参数量、其它皆空: {len(only_arch)}")

# ---- verification_status 分布 ----
vs = Counter((r.get("meta") or {}).get("verification_status") for r in v2)
print(f"\n=== verification_status 分布 ===")
for k, c in vs.most_common():
    print(f"  {k!r}: {c}")

# collected_at 分布
ca = Counter((r.get("meta") or {}).get("collected_at") for r in v2)
print(f"\n=== collected_at 分布 ===")
for k, c in sorted(ca.items(), key=lambda x:-x[1])[:10]:
    print(f"  {k!r}: {c}")

# ---- 哪些记录触发官方 ERROR（读官方报告）----
report = os.path.join(BASE, "validation_v2_official.md")
err_recs = set()
if os.path.exists(report):
    with open(report, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"## `([^`]+)`", line)
            if m:
                err_recs.add(m.group(1))
print(f"\n=== 官方校验 ERROR 命中记录 ===")
print(f"涉及记录数: {len(err_recs)}")
print(f"其中属新增 id 的: {len(err_recs & set(new_ids))}")
print(f"其中属基座 id 的: {len(err_recs & v1_ids)}")

# ---- pricing 真实价统计 ----
priced = [r for r in v2 if has_pricing(r)]
print(f"\n=== 定价实况 ===")
print(f"有任意定价的记录: {len(priced)} ({round(100*len(priced)/N,1)}%)")
# 定价里 currency
cur = Counter((r.get("pricing") or {}).get("currency") for r in priced)
print(f"  这些记录的 currency 分布: {dict(cur)}")

# ---- benchmark 实况 ----
sr = sum(len((r.get('benchmarks') or {}).get('self_reported') or []) for r in v2)
ind = sum(len((r.get('benchmarks') or {}).get('independent') or []) for r in v2)
are = sum(len((r.get('benchmarks') or {}).get('arena_elo') or []) for r in v2)
print(f"\n=== 跑分实况 ===")
print(f"  self_reported 条目总数: {sr}")
print(f"  independent 条目总数: {ind}")
print(f"  arena_elo 条目总数: {are}")
print(f"  有 self_reported 的记录数: {sum(1 for r in v2 if (r.get('benchmarks') or {}).get('self_reported'))}")
print(f"  有 independent 的记录数: {sum(1 for r in v2 if (r.get('benchmarks') or {}).get('independent'))}")
print(f"  有 arena_elo 的记录数: {sum(1 for r in v2 if (r.get('benchmarks') or {}).get('arena_elo'))}")

# ---- g1 记录质量抽检（incoming 宣称全字段）----
g1_ids_from_incoming = set()
with open(os.path.join(BASE,"incoming","agent_g1.jsonl"), encoding="utf-8-sig") as f:
    for line in f:
        line=line.strip()
        if not line or line.startswith("//"): continue
        g1_ids_from_incoming.add(json.loads(line).get("model_id"))

print(f"\n=== 来自 g1(incoming) 的记录质量 ===")
g1_recs = [r for r in v2 if r.get("model_id") in g1_ids_from_incoming]
print(f"g1 记录数(在 v2 中): {len(g1_recs)}")
for r in g1_recs[:6]:
    mid = r.get("model_id")
    p = r.get("pricing") or {}
    b = r.get("benchmarks") or {}
    print(f"  {mid}: in={p.get('input')} out={p.get('output')} "
          f"sr={len(b.get('self_reported') or [])} ind={len(b.get('independent') or [])} "
          f"are={len(b.get('arena_elo') or [])} pos={len((r.get('basic_info') or {}).get('positioning') or [])}")

# 新增记录中，有多少其实也是空壳(只有身份)
print(f"\n=== 新增 {len(new_ids)} 条记录的本质 ===")
new_recs = [r for r in v2 if r.get("model_id") in set(new_ids)]
new_real = [r for r in new_recs if not is_shell(r)]
new_shell = [r for r in new_recs if is_shell(r)]
print(f"  新增中非空壳(有实质数据): {len(new_real)}")
print(f"  新增中空壳(纯身份+参数或无): {len(new_shell)}")
for r in new_shell[:30]:
    print(f"    空壳新增: {r.get('model_id')}  params={notnull((r.get('architecture') or {}).get('total_params_b'))}")
