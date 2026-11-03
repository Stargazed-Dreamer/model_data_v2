#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D58 · 「致知」小众榜（llm2014/llm_benchmark）导入 + 可视化数据生成。

输入（快照，随仓库入库）：
    viz/data/niche/zhizhi/2026-11/{logic,vision,code_v3}.csv

输出：
    1. incoming/models/d58_zhizhi_202611.jsonl  —— 仅含 model_id + benchmarks.independent 的补丁
       （合并用 merge --on-array union_by_key，主键 benchmark,config,source_site,date）
    2. viz/data/niche/zhizhi.json               —— 小众榜页数据（含未匹配的站点行）

口径（写进每条 notes，勿省）：
    - 榜为个人长期跟踪评测：私有题库 28 题 / 每月滚动，非公开题、不可复核 ⇒ confidence=T3
    - 分数轴取站点主用轴「中位分数」（同模型 3 次测量的中位），换算 0-1；「极限分数」记入 notes
    - 同一模型在榜内出现多行（不同 effort / w- refuse）时取中位分最高的一行，档位记进 config
    - 身份粒度：一律落该型号的 base 记录（档位是测量配置，不改变型号身份）；
      库内无 base 时才落已有的档位记录（如 gpt-5.6-luna 只有 -max/-none）

用法：
    python scripts/d58_zhizhi_import.py            # dry-run：只打印匹配结果 + 写 viz json
    python scripts/d58_zhizhi_import.py --apply    # 额外写出 incoming 补丁文件
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "model_data_v2.jsonl"
SNAP = BASE / "viz" / "data" / "niche" / "zhizhi" / "2026-11"
OUT_JSON = BASE / "viz" / "data" / "niche" / "zhizhi.json"
OUT_PATCH = BASE / "incoming" / "models" / "d58_zhizhi_202611.jsonl"

SOURCE_URL = "https://llm2014.github.io/llm_benchmark/"
BOARD_MONTH = "2026-11"

# 站点名 → 库内 model_id 的显式裁定（模糊匹配够不着或会撞车的那些）。
# 每条都要能说出依据：库内命名差异 / 档位 / 同族歧义。
OVERRIDES: dict[str, str] = {
    # —— logic ——
    "Seed-2.1-pro 0915 (high)": "bytedance:seed-2.1-pro:base",
    "Seed-2.1-pro 0915": "bytedance:seed-2.1-pro:base",
    "Seed-2.0-lite 0428 (high)": "bytedance:seed-2.0-lite:base",
    "Qwen3.8-Max (xhigh)": "alibaba:qwen-3.8-max:base",
    "Qwen3.8-27B (xhigh)": "alibaba:qwen-3.8-27b:base",
    "Qwen3.8-27B": "alibaba:qwen-3.8-27b:base",
    "Qwen3.8-Flash (xhigh)": "alibaba:qwen-3.8-flash:base",
    "DeepSeek V4.1 Flash 1017 (max)": "deepseek:deepseek-v4.1-flash:1017",
    "DeepSeek V4.1 Flash": "deepseek:deepseek-v4.1-flash:base",
    "DeepSeek V4 Pro 0813 (max)": "deepseek:deepseek-v4-pro:0813",
    "MiniMax-M3.1-Flash (max)": "minimax:minimax-m3.1-flash:base",
    "Kimi-K3.1-Pro (max)": "moonshot:kimi-k3.1-pro:base",
    "Muse Wonder 1.0 (xhigh)": "meta:muse-wonder:base",
    "Mistral Large 4 (high)": "mistral:mistral-large-4:base",
    "Step 5 Preview": "stepfun:step-5-preview:base",
    "Hy3 (high)": "tencent:tencent-hy3:base",
    "Ling-3.1-flash (xhigh)": "inclusionai:ling-3.1-flash:base",
    "GPT-5.5 Instant": "openai:gpt-5.5-instant:base",
    "GPT-6 Luna (xhigh)": "openai:gpt-6-luna:base",
    "Grok 4.7 (xhigh)": "xai:grok-4.7:base",
    "GLM-5.3 (max)": "zhipu:glm-5.3:base",
    "GLM-5.3-Flash (max)": "zhipu:glm-5.3-flash:base",
    "Dots3-Note Preview": "dots-studio:dots3-note-preview:base",
    "ERNIE 5.1": "baidu:ernie-5.1:base",
    "Gemini 3.5 Flash Lite (high)": "google:gemini-3.5-flash-lite:base",
    "Gemini 3.8 Flash (high)": "google:gemini-3.8-flash:base",
    "Gemini 4 Argon (high)": "google:gemini-4-argon:base",
    "Haiku 5.5 (xhigh)": "anthropic:claude-haiku-5.5:base",
    "Opus 5.5 (xhigh ~Estimated)": "anthropic:claude-opus-5.5:base",
    "Opus 5.5 (xhigh w/ refuse)": "anthropic:claude-opus-5.5:base",
    "Fable 5.1 (xhigh ~Estimated)": "anthropic:claude-fable-5.1:base",
    "Fable 5.1 (xhigh w/ refuse)": "anthropic:claude-fable-5.1:base",
    "Sonnet 5.5 (xhigh)": "anthropic:claude-sonnet-5.5:base",
    "GPT-6 Astra (xhigh)": "openai:gpt-6-astra:base",
    "GPT-6.1 Sol (xhigh)": "openai:gpt-6.1-sol:base",
    # —— code_v3 ——
    "Opus 5.5 (max)": "anthropic:claude-opus-5.5:base",
    "GPT-6 Astra (max)": "openai:gpt-6-astra:base",
    "GPT-6.1 Sol (max)": "openai:gpt-6.1-sol:base",
    "Qwen3.8-Max-0902 (max)": "alibaba:qwen-3.8-max-0902:base",
    "Gemini 3.7 Flash (high)": "google:gemini-3.7-flash-high:base",  # 库内只有 -high 档记录
    "Hy4 preview (high)": "tencent:hunyuan-hy4-preview:base",
    "MiMo-V2.6-Pro (high)": "xiaomi:mimo-v2.6-pro:base",
    "Muse Spark 1.2 (xhigh)": "meta:muse-spark-1.2:base",
    "GPT-5.6 Luna (max)": "openai:gpt-5.6-luna-max:base",
    "Seed-2.1-Pro 0915 (high)": "bytedance:seed-2.1-pro:base",
    # —— vision ——
    "GPT-5 (high)": "openai:gpt-5-2025-08-07-high:base",
    "qwen3-vl-235b-a22b (Think)": "alibaba:qwen-3-vl-235b-a22b:thinking",
    "Qwen3-vl-235b-a22b": "alibaba:qwen-3-vl-235b-a22b:instruct",
    "Sonnet 4 (Think)": "anthropic:claude-sonnet-4-20250514-59k:base",
    "Sonnet 4": "anthropic:claude-sonnet-4-20250514-59k:base",
    "MiniMax-Text-01": "minimax:minimax-text-01:base",
    "Gemini 3 Pro": "google:gemini-3-pro:base",
    "Gemini 2.5 Pro": "google:gemini-2.5-pro:base",
}

# 已核实「库内确实没有该型号」的站点行：不猜、不并到同族，只进缺口清单。
FORCE_GAP: dict[str, str] = {
    "openPangu-2.0-Pro": "库内只有 huawei:pangu-5.0 / pangu-ultra / pangu-pro-moe，无 openPangu 开源系",
    "openPangu-2.0-Flash": "同上：openPangu 开源系未采",
    "LongCat-2.0": "库内 LongCat 只有 flash 系与 2.5-preview，无 2.0",
    "Spark X2.6": "库内讯飞只有 spark-4.0 / spark-x1，无 X2.6",
    "Seed-1.6-vision (Think)": "库内字节 Seed 系从 2.0 起，无 Seed-1.6",
    "Seed-1.6-vision": "同上",
    "Seed-1.6-thinking-0715": "同上",
    "Seed-1.6": "同上",
    "GLM-4.5V": "库内 GLM-4.5 只有文本版，无 V 视觉版",
    "Step-3": "库内 stepfun 只有 step-1/2/3.5-flash/3.7-flash/5-preview，无 step-3",
    "Qwen-vl-max-2025-08-13": "库内 Qwen-VL 只有 Qwen3-VL 开源系，无 qwen-vl-max 商用线",
    "hunyuan-t1-vision 0619": "库内腾讯视觉只有 hunyuan-vision-1.5-thinking / large-vision，无 t1-vision",
    "hunyuan-turbos-vision 0619": "同上",
    "SenseNova-V6-Pro": "库内商汤只有 U1 / 6.8-flash-lite，无 V6",
    "SenseNova-V6-Reasoner": "同上",
    "ERNIE 4.5 Turbo VL 0829": "库内文心只有 4.5 开源三尺寸 / 4.0，无 4.5 Turbo VL",
}

BOARDS = [
    {
        "key": "logic",
        "label": "逻辑榜",
        "month": "2026-11",
        "benchmark": "致知·逻辑榜",
        "file": "logic.csv",
        "name_col": "模型",
        "median_col": "中位分数",
        "max_col": "极限分数",
        "cost_col": "测试成本(元)",
        "time_col": "平均耗时(秒)",
        "token_col": "Token",
        "price_col": "价格(元/百万)",
        "date_col": "发布时间",
    },
    {
        "key": "code_v3",
        "label": "代码榜（v3）",
        "month": "2026-11",
        "benchmark": None,  # 站点不发布合成分，只出任务级评级 ⇒ 不入主库跑分
        "file": "code_v3.csv",
        "name_col": "Model",
        "task_cols": ["Simple Model(H)", "iOS+Server(I)", "Animation(J)", "Data Process(K)",
                      "Metal(L)", "Science(M)", "Rust App(N)", "Debug(O)"],
        "scaffold_col": "Scaffold",
    },
    {
        "key": "vision",
        "label": "视觉榜",
        "month": "2025-11",
        "benchmark": "致知·视觉榜",
        "file": "vision.csv",
        "name_col": "模型",
        "median_col": "中位分数",
        "max_col": "极限分数",
        "cost_col": "成本",
        "time_col": "平均耗时/s",
        "token_col": "平均Token",
        "price_col": "价格(元/百万)",
        "date_col": "发布时间",
    },
]

EFFORT_RE = re.compile(r"\(([^)]*)\)")


def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = s.replace("~estimated", " ")
    s = re.sub(r"[^a-z0-9.]+", "-", s).strip("-")
    return re.sub(r"-{2,}", "-", s)


def variants(name: str) -> set[str]:
    base = norm(name)
    out = {base}
    for p in ("claude-", "alibaba-", "google-", "tencent-", "xiaomi-", "openai-", "anthropic-"):
        if base.startswith(p):
            out.add(base[len(p):])
    return {v for v in out if v}


def load_candidates() -> list[tuple[str, str, set[str]]]:
    cand = []
    with DB.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            mid = d["model_id"]
            parts = mid.split(":")
            tail = parts[1] if len(parts) > 1 else mid
            tier = parts[2] if len(parts) > 2 else ""
            keys: set[str] = set()
            for s in (mid, tail, (d.get("basic_info") or {}).get("full_name") or "",
                      f"{tail}-{tier}" if tier else tail):
                keys |= variants(s)
            cand.append((mid, (d.get("basic_info") or {}).get("full_name") or "", keys))
    return cand


def resolve(name: str, cand):
    """返回 (model_id|None, 依据说明)。已知缺口优先于显式裁定，避免别名表里留下不存在的 model_id。"""
    if name in FORCE_GAP:
        return None, f"缺口：{FORCE_GAP[name]}"
    if name in OVERRIDES:
        return OVERRIDES[name], "显式裁定"
    vs = variants(name)
    scored = []
    for mid, full, keys in cand:
        best = max((difflib.SequenceMatcher(None, a, b).ratio() for a in vs for b in keys), default=0.0)
        scored.append((best, mid))
    scored.sort(reverse=True)
    top_score, top_mid = scored[0]
    if top_score >= 0.86:
        return top_mid, f"模糊 {top_score:.2f}"
    return None, f"缺口：无同族记录（最接近 {top_mid} {top_score:.2f}）"


def effort_of(name: str) -> str:
    m = EFFORT_RE.search(name)
    if not m:
        return "标准档"
    inner = m.group(1)
    return inner.replace("~Estimated", "").replace("w/ refuse", "").strip() or "标准档"


def money(v: str) -> str | None:
    v = (v or "").strip()
    return v if v and v not in ("-", "—") else None


def load_board(cfg) -> list[dict]:
    path = SNAP / cfg["file"]
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        item = {"site_name": (r.get(cfg["name_col"]) or "").strip()}
        if cfg["key"] == "code_v3":
            item["tasks"] = {c: (r.get(c) or "").strip() for c in cfg["task_cols"]}
            item["scaffold"] = (r.get(cfg.get("scaffold_col") or "") or "").strip()
        else:
            try:
                item["median"] = float(r.get(cfg["median_col"]) or "nan")
            except ValueError:
                item["median"] = None
            try:
                item["max"] = float(r.get(cfg["max_col"]) or "nan")
            except ValueError:
                item["max"] = None
            item["effort"] = effort_of(item["site_name"])
            item["cost_cny"] = money(r.get(cfg["cost_col"], ""))
            item["time_s"] = money(r.get(cfg["time_col"], ""))
            item["tokens"] = money(r.get(cfg["token_col"], ""))
            item["price_cny"] = money(r.get(cfg["price_col"], ""))
            item["release_date_site"] = money(r.get(cfg["date_col"], ""))
            item["think"] = (r.get("Think") or "").strip()
        out.append(item)
    return out


def build():
    cand = load_candidates()
    used: dict[str, list[str]] = {}
    boards = []
    patch: dict[str, list[dict]] = {}
    review: list[tuple] = []

    for cfg in BOARDS:
        rows = load_board(cfg)
        for r in rows:
            mid, why = resolve(r["site_name"], cand)
            r["model_id"] = mid
            r["match"] = why
            review.append((cfg["key"], r["site_name"], mid or "—", why))
            if mid:
                used.setdefault(mid, []).append(r["site_name"])

        if cfg["benchmark"]:
            # 同一 model 多行（不同档位 / w- refuse）取中位分最高的那行
            best: dict[str, dict] = {}
            for r in rows:
                if not r["model_id"] or r.get("median") is None:
                    continue
                cur = best.get(r["model_id"])
                if cur is None or r["median"] > (cur.get("median") or -1):
                    best[r["model_id"]] = r
            for mid, r in best.items():
                entry = {
                    "benchmark": cfg["benchmark"],
                    "score": round(r["median"] / 100, 4),
                    "score_type": "median_score",
                    "config": f"{cfg['month']} 月榜 · {r['effort']}",
                    "date": cfg["month"],
                    "source_url": SOURCE_URL,
                    "source_type": "独立第三方评测（其它）",
                    "confidence": "T3",
                    "gap_to_self_reported": None,
                    "notes": (
                        f"「致知」个人长期追踪榜（私有题库 28 题、每月滚动，题目不公开、不可复核）。"
                        f"站点原始行「{r['site_name']}」：中位分数 {r['median']} / 极限分数 {r['max']}（每题 10 分制），"
                        f"实测成本 {r['cost_cny'] or '—'}、平均耗时 {r['time_s'] or '—'}s、Token {r['tokens'] or '—'}；"
                        f"站点标注发布时间 {r['release_date_site'] or '—'}。"
                        f"分数取站点主用轴「中位分数」除以 100；同模型多档位只取最高一行，档位见 config。"
                        f"第三方个人评测 ⇒ T3，不构成立行依据。"
                    ),
                }
                patch.setdefault(mid, []).append(entry)
            r["board_imported"] = True
        else:
            r["board_imported"] = False
        boards.append({
            "key": cfg["key"],
            "label": cfg["label"],
            "benchmark": cfg["benchmark"],
            "month": cfg["month"],
            "rows": rows,
        })

    payload = {
        "meta": {
            "site": "「致知」大模型智力长期追踪榜",
            "url": SOURCE_URL,
            "repo": "https://github.com/llm2014/llm_benchmark",
            "fetched_at": "2026-11-04",
            "boards": {"logic": "2026-11", "code_v3": "2026-11", "vision": "2025-11"},
            "source_type": "独立第三方评测（其它）",
            "confidence": "T3",
            "note": (
                "个人长期跟踪评测：私有题库 28 题、每月滚动更新，题目与评分细则不公开，无法复核 ⇒ 按 T3 记。"
                "逻辑/视觉榜站点发布数值分（每题 10 分制，三次测量取中位），本库取「中位分数」；"
                "代码榜（v3）只发布任务级评级（Pass/A+/A/B+/…/Failed/Skip），站点自身不出合成分，"
                "故本库不为其编造总分，只在页面呈现任务级评级。"
            ),
        },
        "boards": boards,
    }
    return payload, patch, review


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写出 incoming 补丁文件")
    args = ap.parse_args()

    payload, patch, review = build()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{'board':9s} {'site_name':34s} {'model_id':44s} 依据")
    for key, name, mid, why in review:
        print(f"{key:9s} {name[:34]:34s} {mid[:44]:44s} {why}")

    matched = sum(1 for _, _, m, _ in review if m != "—")
    print(f"\n条目 {len(review)} · 匹配 {matched} · 缺口 {len(review) - matched}")
    print(f"待入库 model {len(patch)} 个 / 条目 {sum(len(v) for v in patch.values())}")

    if args.apply:
        OUT_PATCH.parent.mkdir(parents=True, exist_ok=True)
        with OUT_PATCH.open("w", encoding="utf-8", newline="\n") as f:
            for mid, entries in sorted(patch.items()):
                rec = {"schema_version": "1.1", "model_id": mid,
                       "benchmarks": {"independent": entries}}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"已写 {OUT_PATCH.relative_to(BASE)}")
    print(f"已写 {OUT_JSON.relative_to(BASE)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
