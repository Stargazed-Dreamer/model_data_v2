#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Task #16: 全库终验 + 质量报告数据生成（2026-08-25 放量采集收官）"""
import json, os, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(BASE, "model_data_v2.jsonl")

recs = []
with open(V2, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            recs.append(json.loads(line))

errors = []
warns = []

# A. 结构校验：必需字段
REQ_TOP = ["model_id", "basic_info", "pricing", "modality", "meta"]
for r in recs:
    mid = r.get("model_id", "?")
    for k in REQ_TOP:
        if k not in r:
            errors.append(f"{mid}: 缺少顶层字段 {k}")

# B. pricing 完整性：每条必须有 source_type；有价记录必须有 currency/unit/confidence/source_url
priced = annotated = 0
cur_dist = Counter()
stype_dist = Counter()
conf_dist = Counter()
for r in recs:
    mid = r["model_id"]
    p = r.get("pricing") or {}
    st = p.get("source_type")
    if not st:
        errors.append(f"{mid}: pricing 无 source_type 且无价格（空白记录）")
        continue
    has_val = any(p.get(k) is not None for k in ("input", "output", "cached_input", "batch_input", "batch_output"))
    if has_val:
        priced += 1
        for k in ("currency", "unit", "confidence"):
            if p.get(k) is None:
                errors.append(f"{mid}: 有价记录缺 {k}")
        if not p.get("source_url"):
            warns.append(f"{mid}: 有价记录缺 source_url")
        cur_dist[p.get("currency")] += 1
        conf_dist[p.get("confidence")] += 1
    else:
        annotated += 1
    stype_dist[st] += 1
    # 数值合理性
    for k in ("input", "output", "cached_input", "batch_input", "batch_output"):
        v = p.get(k)
        if v is not None and (not isinstance(v, (int, float)) or v < 0 or v > 10000):
            errors.append(f"{mid}: {k}={v} 超出合理范围")

print("=" * 60)
print(f"总记录数: {len(recs)}")
print(f"实价记录: {priced}   标注记录(无价): {annotated}")
print(f"\nERROR: {len(errors)}")
for e in errors[:20]:
    print("  ✗", e)
print(f"WARN: {len(warns)}")
for w in warns[:20]:
    print("  ⚠", w)

print("\n=== 币种分布（有价记录）===")
for k, c in cur_dist.most_common():
    print(f"  {k}: {c}")
print("\n=== 置信分级（有价记录）===")
for k, c in conf_dist.most_common():
    print(f"  {k}: {c}")
print("\n=== source_type 分布 ===")
for k, c in stype_dist.most_common():
    print(f"  {k}: {c}")

# C. 厂商维度统计
prov_total = Counter()
prov_priced = Counter()
for r in recs:
    prov = r["model_id"].split(":")[0]
    prov_total[prov] += 1
    p = r.get("pricing") or {}
    if any(p.get(k) is not None for k in ("input", "output", "cached_input")):
        prov_priced[prov] += 1
print(f"\n=== 厂商覆盖 TOP30（总数/实价数）===")
for prov, t in prov_total.most_common(30):
    print(f"  {prov}: {t} / {prov_priced.get(prov,0)}")

sys.exit(1 if errors else 0)
