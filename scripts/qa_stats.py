#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""阶段 3 质检统计器（model_data v2）

用法:
    PYTHONUTF8=1 python scripts/qa_stats.py [--out intermediate/qa_stats.json]

产出:
    - 控制台可读摘要
    - JSON 明细（供 qa_report.md 消费）

统计口径:
    - roster 组: docs/batch_claim_ledger.jsonl 里出现过、本轮 v2 采集的 702 个 model_id
    - legacy 组: 主库中其余记录（v1 遗留，schema 已升级到 1.1）
    - 填充判定: 值非 None、非 ""、非空 list、非全 null 的 dict
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_DB = os.path.join(REPO, "model_data_v2.jsonl")
LEDGER = os.path.join(REPO, "docs", "batch_claim_ledger.jsonl")

# 占位符关键词（COLLECTION_PLAN_v2 §6-5 原文：「待补/未含」）
# 口径说明：只有「没采到、等别人来补」才算占位符。
#   - 真占位：待补 / 未含 / 需另行采集 / 待采集 / 未采集
#   - **不算**占位：未披露 / 未公开 / 未提供 / 待测 —— 这些是「查过、官方确实没有」的
#     采集结论，是有效数据。把它们算进来会让长尾模型（参数量确实未公开）被误判成烂尾。
PLACEHOLDER_PAT = re.compile(r"待补|未含|需另行采集|待采集|未采集|待核实")
# 「官方未披露」类表述单独统计，用于区分「无数据」与「确认无此数据」
CONFIRMED_ABSENT_PAT = re.compile(r"未披露|未公开|未提供|待测")


def write_text_atomic(path, text, retries=8):
    """原子写文本。Windows 上覆盖刚写入的文件常撞瞬时锁定（WinError 5 / Errno 13），
    与 model_data_tool._save 同源，故同样重试退避。"""
    import time
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, ".%s.tmp.%d" % (os.path.basename(path), os.getpid()))
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    last = None
    for i in range(retries):
        try:
            os.replace(tmp, path)
            return
        except (PermissionError, OSError) as e:
            last = e
            time.sleep(0.3 * (i + 1))
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise last


def is_filled(v):
    """填充判定：None / "" / [] / 全 null 的 dict 均视为未填充"""
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, tuple)):
        return len(v) > 0
    if isinstance(v, dict):
        return any(is_filled(x) for x in v.values())
    return True


def dig(rec, path, default=None):
    """点号路径取值，任一层缺失返回 default"""
    cur = rec
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


# 逐维度填充定义：(维度名, 路径, 说明)
# 路径带 * 的表示"该 dict 下任意一项填充即算填充"
DIMS = [
    ("发布日期", "basic_info.release_date", "YYYY-MM-DD 或 YYYY-MM"),
    ("定位标签", "basic_info.positioning", "受控词表六值，非空数组"),
    ("开放权重", "basic_info.access.open_weights", "三态布尔"),
    ("API 可用", "basic_info.access.api", "三态布尔"),
    ("本地部署", "basic_info.access.local_deployment", "三态布尔"),
    ("总参数量", "architecture.total_params_b", "B 为单位"),
    ("激活参数量", "architecture.active_params_b", "MoE 模型"),
    ("上下文窗口", "architecture.context_window_tokens", "标称值"),
    ("有效上下文", "architecture.context_window_effective_tokens", "实测值"),
    ("知识截止", "architecture.knowledge_cutoff", "YYYY-MM-DD"),
    ("多模态输入", "modality.input", "除 text 外任一项非 null"),
    ("原生多模态", "modality.native_multimodal", "任一项非 null"),
    ("自报跑分", "benchmarks.self_reported", "非空数组"),
    ("独立评测", "benchmarks.independent", "非空数组"),
    ("Arena Elo", "benchmarks.arena_elo", "非空数组"),
    ("定价-输入", "pricing.input", "USD/M tokens"),
    ("定价-输出", "pricing.output", "USD/M tokens"),
    ("定价-生效日", "pricing.effective_date", "精确到日"),
    ("来源 URL", "meta.source_urls", "非空数组"),
    ("采集日期", "meta.collected_at", "YYYY-MM-DD"),
]

# 多模态输入只看非 text 项，单独处理
MULTIMODAL_EXCLUDE = {"text", "notes"}


def load_roster():
    roster = set()
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                roster.update(json.loads(line).get("models") or [])
    return roster


def load_db():
    recs = []
    with open(MAIN_DB, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                recs.append(json.loads(line))
    return recs


def dim_filled(rec, name, path):
    if name == "多模态输入":
        mi = dig(rec, "modality.input", {}) or {}
        if not isinstance(mi, dict):
            return is_filled(mi)
        return any(is_filled(v) for k, v in mi.items() if k not in MULTIMODAL_EXCLUDE)
    if name == "原生多模态":
        nm = dig(rec, "modality.native_multimodal", {}) or {}
        if not isinstance(nm, dict):
            return is_filled(nm)
        return any(is_filled(v) for k, v in nm.items() if k != "notes")
    return is_filled(dig(rec, path))


def pct(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def main():
    ap = argparse.ArgumentParser(description="阶段 3 质检统计器")
    ap.add_argument("--out", default=os.path.join(REPO, "intermediate", "qa_stats.json"),
                    help="JSON 明细输出路径")
    args = ap.parse_args()

    roster = load_roster()
    recs = load_db()
    groups = {"roster": [], "legacy": []}
    for r in recs:
        groups["roster" if r.get("model_id") in roster else "legacy"].append(r)

    stats = {
        "total": len(recs),
        "roster_n": len(groups["roster"]),
        "legacy_n": len(groups["legacy"]),
        "dims": [],
        "meta": {},
    }

    # 1) 逐维度填充率
    for name, path, desc in DIMS:
        row = {"dim": name, "path": path, "desc": desc}
        for g in ("roster", "legacy"):
            n = sum(1 for r in groups[g] if dim_filled(r, name, path))
            row[g] = {"filled": n, "total": len(groups[g]), "pct": pct(n, len(groups[g]))}
        row["delta"] = round(row["roster"]["pct"] - row["legacy"]["pct"], 1)
        stats["dims"].append(row)

    # 2) verification_status 诚实性
    vs = Counter(r.get("meta", {}).get("verification_status") for r in recs)
    dishonest = [r["model_id"] for r in recs
                 if r.get("meta", {}).get("verification_status") == "已验证"
                 and not r.get("meta", {}).get("verified_at")]
    stats["meta"]["verification_status"] = dict(vs)
    stats["meta"]["dishonest_verified"] = dishonest

    # 3) collected_at 分布
    ca = Counter(r.get("meta", {}).get("collected_at") for r in recs)
    stats["meta"]["collected_at"] = dict(sorted((str(k), v) for k, v in ca.items()))

    # 4) 占位符 notes 占比（区分「未采到」与「确认官方无此数据」）
    ph = 0
    ph_by_group = {}
    for g in ("roster", "legacy"):
        c = sum(1 for r in groups[g]
                if PLACEHOLDER_PAT.search(str(r.get("meta", {}).get("notes") or "")))
        ph_by_group[g] = {"count": c, "total": len(groups[g]), "pct": pct(c, len(groups[g]))}
        ph += c
    absent = sum(1 for r in recs
                 if CONFIRMED_ABSENT_PAT.search(str(r.get("meta", {}).get("notes") or "")))
    stats["meta"]["placeholder_notes"] = {
        "count": ph, "total": len(recs), "pct": pct(ph, len(recs)), "by_group": ph_by_group,
        "confirmed_absent": absent,
    }

    # 4.5) 按「开源权重 / 商业 API」分型看定价填充率
    #      红线 5 要求开源权重模型 pricing 全 null，混在一起统计会低估真实覆盖
    def kind(rec):
        ow = dig(rec, "basic_info.access.open_weights")
        api = dig(rec, "basic_info.access.api")
        if ow is True:
            return "开源权重"
        if ow is False and api is True:
            return "商业API"
        return "未知/混合"

    by_kind = {}
    for g in ("roster", "legacy"):
        for k in ("商业API", "开源权重", "未知/混合"):
            sub = [r for r in groups[g] if kind(r) == k]
            n = sum(1 for r in sub if dig(r, "pricing.input") is not None)
            by_kind[f"{g}/{k}"] = {"pricing_filled": n, "total": len(sub),
                                   "pct": pct(n, len(sub))}
    stats["meta"]["pricing_by_kind"] = by_kind

    # 5) 可信度与来源类型分布
    conf = Counter()
    stype = Counter()
    def walk_bench(rec):
        for key in ("self_reported", "independent", "arena_elo"):
            for item in (dig(rec, f"benchmarks.{key}") or []):
                if isinstance(item, dict):
                    conf[item.get("confidence")] += 1
                    stype[item.get("source_type")] += 1
    for r in recs:
        walk_bench(r)
        p = dig(r, "pricing") or {}
        if isinstance(p, dict):
            if p.get("confidence"):
                conf[f"pricing:{p['confidence']}"] += 1
            if p.get("source_type"):
                stype[f"pricing:{p['source_type']}"] += 1
    stats["meta"]["confidence"] = dict(sorted(conf.items(), key=lambda x: str(x[0])))
    stats["meta"]["source_type"] = dict(sorted(stype.items(), key=lambda x: -x[1]))

    # 6) 定价币种与 effective_date 精度
    cur = Counter(dig(r, "pricing.currency") for r in recs if dig(r, "pricing.input") is not None)
    stats["meta"]["pricing_currency"] = dict(cur)
    ed_day = sum(1 for r in recs
                 if isinstance(dig(r, "pricing.effective_date"), str)
                 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", dig(r, "pricing.effective_date") or ""))
    ed_all = sum(1 for r in recs if dig(r, "pricing.effective_date"))
    stats["meta"]["effective_date"] = {"to_day": ed_day, "with_value": ed_all}

    # 7) 门禁结果
    try:
        out = subprocess.run(
            [sys.executable, os.path.join(REPO, "scripts", "validate_model_data.py"), MAIN_DB],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONUTF8": "1"}, cwd=REPO)
        tail = (out.stdout or "").strip().splitlines()[-1:]
        stats["meta"]["gate_tail"] = tail[0] if tail else ""
        m = re.search(r"(\d+)\s*条.*?ERROR\s*(\d+)\s*项.*?WARN\s*(\d+)\s*项", out.stdout or "")
        if m:
            stats["meta"]["gate"] = {"records": int(m.group(1)),
                                     "error": int(m.group(2)), "warn": int(m.group(3))}
    except Exception as e:  # pragma: no cover
        stats["meta"]["gate"] = {"error": "校验脚本执行失败: %s" % e}

    # ---- 输出 ----
    write_text_atomic(args.out, json.dumps(stats, ensure_ascii=False, indent=2) + "\n")

    print("=" * 74)
    print("阶段 3 质检统计  |  全库 %d 条 = 花名册 %d + v1 遗留 %d"
          % (stats["total"], stats["roster_n"], stats["legacy_n"]))
    print("=" * 74)
    print("%-12s %-9s %-9s %-8s" % ("维度", "花名册%", "遗留%", "差值"))
    print("-" * 74)
    for row in stats["dims"]:
        print("%-12s %8.1f%% %8.1f%% %+8.1f"
              % (row["dim"], row["roster"]["pct"], row["legacy"]["pct"], row["delta"]))
    print("-" * 74)
    print("占位符 notes: %d/%d = %.1f%%" % (ph, len(recs), pct(ph, len(recs))))
    print("verification_status: %s" % dict(vs))
    print("不诚实「已验证」: %d 条" % len(dishonest))
    print("门禁: %s" % stats["meta"].get("gate"))
    print("明细已写出: %s" % args.out)


if __name__ == "__main__":
    main()
