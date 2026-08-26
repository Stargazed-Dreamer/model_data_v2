# -*- coding: utf-8 -*-
"""
normalize_p2_sourcetype.py —— #5 source_type 受控词表归一
把「第三方登记站（站点名[（Verified/Unverified）]）」统一为受控值「第三方登记站」，
并将站点名 + 限定符写入 notes（保留可聚合 + 不丢语义）。
幂等：已归一（source_type 已是「第三方登记站」）则跳过。
"""
import json, re, shutil, os

SRC = r"F:\project_temp\localAgent\workspace\model_data\incoming\agent_p2.jsonl"
BAK = SRC + ".bak_srcnorm"
RE = re.compile(r"^第三方登记站（(.+?)）$")
CONTROLLED = "第三方登记站"

def parse_site(inner):
    qualifier = None
    site = inner
    for q in ("Verified", "Unverified"):
        suffix = f"({q})"
        if inner.endswith(suffix):
            site = inner[: -len(suffix)]
            qualifier = q
            break
    return site, qualifier

def main():
    if not os.path.exists(BAK):
        shutil.copy2(SRC, BAK)
        print(f"backup -> {BAK}")
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
    changed = 0
    for r in rows:
        for it in (r.get("benchmarks") or {}).get("independent", []) or []:
            st = it.get("source_type") or ""
            m = RE.match(st)
            if not m:
                continue
            if st == CONTROLLED:
                continue
            site, qualifier = parse_site(m.group(1))
            it["source_type"] = CONTROLLED
            tag = "登记站：" + site + (f"（{qualifier}）" if qualifier else "")
            notes = it.get("notes") or ""
            it["notes"] = (notes + "；" + tag) if notes.strip() else tag
            changed += 1
    # 写回
    with open(SRC, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"normalized items: {changed}")
    # 汇总归一后 distinct source_type
    from collections import Counter
    c = Counter()
    for r in rows:
        for it in (r.get("benchmarks") or {}).get("independent", []) or []:
            c[it.get("source_type")] += 1
    print("归一后 independent source_type 分布:", dict(c))

if __name__ == "__main__":
    main()
