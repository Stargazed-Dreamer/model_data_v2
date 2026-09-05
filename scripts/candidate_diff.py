#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量更新 S1「范围判定」辅助：候选新模型 vs 主库差异比对（只读）。

用法（两种任选）：
    PYTHONUTF8=1 python scripts/candidate_diff.py candidates.jsonl
    PYTHONUTF8=1 python scripts/candidate_diff.py --inline 'GPT-6 Astra@openai' 'GLM-5.3-Flash@zhipu'

candidates.jsonl 每行一个候选（S0 发现环节的产出）：
    {"name":"GPT-6 Astra","vendor":"openai","release_date":"2026-09-03",
     "tier":"T1","evidence":"https://...","note":"..."}

输出：每条候选的判定建议
    NEW           库内未见（该厂商下亦无同名/同版本号记录）→ 走采集
    CHECK_VARIANT 库内有同家族记录且版本号相邻（如已有 5.0，候选 5.1）→ 可能是新版本，也可能已被现有记录覆盖
    EXISTS        高度疑似已在库（token 重合度高）→ 一般不需采集，人工确认即可
退出码：存在至少一条 NEW 时返回 10（可用于 CI 提醒），否则 0。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "model_data_v2.jsonl"

TOKEN_RE = re.compile(r"[a-z0-9.]+")
IGNORE = {"base", "none", "high", "low", "max", "mini", "minimal", "preview", "it", "latest", "stable", "pro", "flash"}


def norm(s: str) -> list[str]:
    return [t for t in TOKEN_RE.findall((s or "").lower()) if t not in IGNORE]


def main() -> int:
    args = sys.argv[1:]
    cands: list[dict] = []
    if "--inline" in args:
        items = [a for a in args[args.index("--inline") + 1:] if not a.startswith("--")]
        cands = [{"name": it.split("@")[0], "vendor": it.split("@")[1] if "@" in it else "", "note": "inline"} for it in items]
    else:
        path = args[0]
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                cands.append(json.loads(line))

    recs = [json.loads(l) for l in open(SRC, encoding="utf-8")]
    by_vendor: dict[str, list] = {}
    for r in recs:
        bi = r.get("basic_info") or {}
        v = (bi.get("vendor") or "?").lower()
        by_vendor.setdefault(v, []).append((
            r["model_id"].lower(),
            (bi.get("full_name") or "").lower(),
            (bi.get("release_date") or ""),
        ))

    out_rows, has_new = [], False
    for c in cands:
        name = c.get("name") or ""
        vendor = (c.get("vendor") or "").lower()
        toks = set(norm(name))
        best = None  # (score, model_id, release)
        for mid, fn, rd in by_vendor.get(vendor, []):
            hay = set(norm(mid)) | set(norm(fn))
            if not hay:
                continue
            overlap = len(toks & hay) / max(1, len(toks))
            if best is None or overlap > best[0]:
                best = (overlap, mid, rd)
        score = best[0] if best else 0.0
        if best and score >= 0.9:
            verdict = "EXISTS"
        elif best and score >= 0.4:
            verdict = "CHECK_VARIANT"
        else:
            verdict = "NEW"
        if verdict == "NEW":
            has_new = True
        out_rows.append({
            "candidate": name, "vendor": vendor, "release_date": c.get("release_date", ""),
            "verdict": verdict, "best_overlap": round(score, 2),
            "closest": best[1] if best else "-", "closest_release": best[2] if best else "-",
            "note": c.get("note", ""),
        })

    w = max(len(r["candidate"]) for r in out_rows) + 2
    for r in out_rows:
        print(f"{r['verdict']:<14} {r['candidate']:<{w}} closest={r['closest']} ({r['closest_release']}, overlap={r['best_overlap']})")
    print(f"\n共 {len(out_rows)} 条：NEW {sum(1 for r in out_rows if r['verdict']=='NEW')} / "
          f"CHECK_VARIANT {sum(1 for r in out_rows if r['verdict']=='CHECK_VARIANT')} / "
          f"EXISTS {sum(1 for r in out_rows if r['verdict']=='EXISTS')}")
    return 10 if has_new else 0


if __name__ == "__main__":
    sys.exit(main())
