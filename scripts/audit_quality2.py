#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re, os
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # model_data 根目录
V2 = os.path.join(BASE, "model_data_v2.jsonl")
V1C = os.path.join(BASE, "backups", "model_data_v1_clean.jsonl")

def load(p):
    recs = []
    with open(p, encoding="utf-8-sig") as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith("//"): continue
            recs.append(json.loads(line))
    return recs

v2 = load(V2); v1c = load(V1C)
v2_by_id = {r.get("model_id"): r for r in v2}
v1_by_id = {r.get("model_id"): r for r in v1c}
v1_ids = set(v1_by_id)

# 1) 解析官方报告：逐记录 ERROR/WARN 拆分，base vs new
report = os.path.join(BASE, "docs", "validation_v2_official.md")
cur = None; rec_err = 0; rec_warn = 0
err_base = err_new = warn_base = warn_new = 0
err_records_base = []; err_records_new = []
with open(report, encoding="utf-8") as f:
    for line in f:
        m = re.match(r"## `([^`]+)`", line)
        if m:
            if cur is not None:
                if rec_err: 
                    (err_base:=err_base+1, err_records_base.append(cur)) if cur in v1_ids else (err_new:=err_new+1, err_records_new.append(cur))
                if rec_warn and not rec_err:
                    warn_base += 1 if cur in v1_ids else 0
                    warn_new += 0 if cur in v1_ids else 1
            cur = m.group(1); rec_err=0; rec_warn=0
            continue
        if cur is None: continue
        if line.strip().startswith("- **ERROR**"): rec_err += 1
        elif line.strip().startswith("- WARN"): rec_warn += 1
    # last
    if cur is not None:
        if rec_err:
            if cur in v1_ids: err_base+=1; err_records_base.append(cur)
            else: err_new+=1; err_records_new.append(cur)
        elif rec_warn:
            if cur in v1_ids: warn_base+=1
            else: warn_new+=1

print("=== 官方 ERROR 归因（base vs new）===")
print(f"ERROR 涉及记录: base={err_base}  new={err_new}  合计={err_base+err_new}")
print(f"WARN-only 涉及记录: base={warn_base}  new={warn_new}  合计={warn_base+warn_new}")
print(f"ERROR 记录中属新增的 id: {err_records_new}")

# 2) v2 的基座记录是否真与 v1_clean 一致（逐字段 diff）
changed = []
for mid in v1_ids:
    a = v2_by_id.get(mid); b = v1_by_id.get(mid)
    if a != b:
        changed.append(mid)
print(f"\n=== 基座记录变更核对 ===")
print(f"v1_clean 中 id 数: {len(v1_ids)}")
print(f"v2 中相对 v1_clean 内容发生变化的基座记录数: {len(changed)}")
print(f"变化样例(前15): {changed[:15]}")

# 3) 真正有用的记录 = 定价 OR 多模态 OR 跑分 OR positioning（去掉'仅参数量'）
def has_pricing(r):
    p=r.get("pricing") or {}
    return any(p.get(k) is not None for k in ("input","output","cached_input","batch_input","batch_output"))
def has_mod(r):
    m=r.get("modality") or {}
    for s in ("input","output","native_multimodal"):
        for k,v in (m.get(s) or {}).items():
            if k!="notes" and v is not None: return True
    return False
def has_bench(r):
    b=r.get("benchmarks") or {}
    return bool((b.get("self_reported") or [])+(b.get("independent") or [])+(b.get("arena_elo") or []))
def has_pos(r):
    p=(r.get("basic_info") or {}).get("positioning")
    return isinstance(p,list) and len(p)>0

useful = [r for r in v2 if (has_pricing(r) or has_mod(r) or has_bench(r) or has_pos(r))]
print(f"\n=== '有用'记录（定价/多模态/跑分/定位 任一有值）===")
print(f"有用记录: {len(useful)} / {len(v2)} = {round(100*len(useful)/len(v2),1)}%")
print(f"→ 即 {len(v2)-len(useful)} 条 ({round(100*(len(v2)-len(useful))/len(v2),1)}%) 连定价/多模态/跑分/定位 哪一项都没有")

# 4) 已验证的 2 条，真验证了吗？
print(f"\n=== '已验证'记录抽查 ===")
for r in v2:
    if (r.get("meta") or {}).get("verification_status")=="已验证":
        mid=r.get("model_id")
        meta=r.get("meta") or {}
        print(f"  {mid}: verified_at={meta.get('verified_at')} source_urls={meta.get('source_urls')} notes={str(meta.get('notes'))[:80]}")

# 5) 定价数值合理性抽检
print(f"\n=== 定价数值抽检（前15条有价记录）===")
cnt=0
for r in v2:
    if has_pricing(r):
        p=r.get("pricing") or {}
        print(f"  {r.get('model_id')}: in={p.get('input')} out={p.get('output')} cur={p.get('currency')} eff={p.get('effective_date')} src={str(p.get('source_url'))[:40]}")
        cnt+=1
        if cnt>=15: break

# 6) arena_elo 数值范围（看是否真实）
print(f"\n=== arena_elo 分数分布 ===")
scores=[it.get("score") for r in v2 for it in ((r.get('benchmarks') or {}).get('arena_elo') or []) if it.get("score") is not None]
if scores:
    print(f"  条目数={len(scores)} min={min(scores)} max={max(scores)} 均值={round(sum(scores)/len(scores),1)}")
    print(f"  偏低(<1000): {sum(1 for s in scores if s<1000)}  合理(1000-1700): {sum(1 for s in scores if 1000<=s<=1700)}  偏高(>1700): {sum(1 for s in scores if s>1700)}")

# 7) independent 来源 concentration（受控词表问题）
print(f"\n=== independent source_type 词汇 ===")
st=Counter()
for r in v2:
    for it in ((r.get('benchmarks') or {}).get('independent') or []):
        st[it.get('source_type')]+=1
print(f"  去重 source_type 数: {len(st)}")
for k,c in st.most_common(25):
    print(f"    {k!r}: {c}")
# source_url 为 null 的 independent 条目
null_url=sum(1 for r in v2 for it in ((r.get('benchmarks') or {}).get('independent') or []) if not it.get("source_url"))
print(f"  independent 中 source_url 为 null 的条目: {null_url}")
