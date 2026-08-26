# -*- coding: utf-8 -*-
"""
backfill_p2_urls.py —— #4 T3 第三方登记站 source_url 补齐
仅填「联网核实过真实基址」的登记站；核实不到的保留 null 并列出。

约束：不得杜撰 URL。
- fresh 本轮(2026-08-25) WebSearch 新核实
- carried 上一轮已核实（沿用）
- unverified 本轮未能核实 → 保持 null
"""
import json, re, shutil, os

SRC = r"F:\project_temp\localAgent\workspace\model_data\incoming\agent_p2.jsonl"
BAK = SRC + ".bak_urlfix"

# 站点名(括号内容) -> (URL, 来源标记)
URL_MAP = {
    # --- fresh: 本轮新核实 ---
    "llmbase":            ("https://llmbase.ai/", "fresh"),
    "benched.ai":         ("https://benched.ai/", "fresh"),
    "evals.report":       ("http://evals.report/", "fresh"),
    "evals.report(Verified)":   ("http://evals.report/", "fresh"),
    "evals.report(Unverified)": ("http://evals.report/", "fresh"),
    "tpsreport.news":     ("http://tpsreport.news/", "fresh"),
    "topreviewed":        ("https://topreviewed.ai/models", "fresh"),
    # --- carried: 上一轮已核实 ---
    "serenitiesai":       ("https://serenitiesai.com/benchmark", "carried"),
    "awesomeagents":      ("https://www.awesomeagents.ai/leaderboards/", "carried"),
    "rankedagi":          ("http://rankedagi.com", "carried"),
    "datalearner":        ("https://www.datalearner.com/leaderboards/external/text-generation", "carried"),
    "llmindex":           ("https://llmindex.net", "carried"),
    "atoms.dev":          ("https://atoms.dev/", "carried"),
    "theairankings":      ("https://theairankings.com/best-ai-models/", "carried"),
    "willitrunai":        ("https://willitrunai.com/zh", "carried"),
    "frankx/chatforest":  ("https://chatforest.com/reviews/llm-evaluation-benchmarking-mcp-servers/", "carried"),
    "frontiernews/korshunov": ("https://korshunov.ai/en/benchmark/swe-bench", "carried"),
    "benchmarklist":      ("http://benchmarklist.com/", "carried"),
}

RE = re.compile(r"^第三方登记站（(.+?)）$")
UNVERIFIED = []

def main():
    if not os.path.exists(BAK):
        shutil.copy2(SRC, BAK)
        print(f"backup -> {BAK}")
    else:
        print(f"(backup already exists: {BAK})")

    rows = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip():
                rows.append(json.loads(line))

    filled = 0
    skipped_had = 0
    for r in rows:
        for item in (r.get("benchmarks") or {}).get("independent", []) or []:
            if item.get("source_url"):
                continue  # 已有 URL（如「独立评测平台」）
            st = item.get("source_type") or ""
            m = RE.match(st)
            if not m:
                continue
            site = m.group(1)
            if site in URL_MAP:
                item["source_url"] = URL_MAP[site][0]
                filled += 1
            else:
                UNVERIFIED.append((r.get("model_id"), item.get("benchmark"), site))

    with open(SRC, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"filled source_url: {filled}")
    print(f"unverified (kept null): {len(UNVERIFIED)}")
    for mid, bench, site in UNVERIFIED:
        print(f"  - site={site!r}  model={mid}  bench={bench}")

if __name__ == "__main__":
    main()
