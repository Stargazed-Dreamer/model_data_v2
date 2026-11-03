# -*- coding: utf-8 -*-
"""小众榜聚合数据构建（D58 修订版）

口径（用户 2026-11-04 裁定）：
  「小众榜」= 我们跟踪的**一类非官方榜**（致知 / atmeplz / galbands / 亿模亿样），
  在可视化里**只是「跑分排行」下拉的一个分组**，不另设独立页面。
  atmeplz / galbands / arenaofbias **不进主库**（口径存疑，见 D53/D55），只在此落页面数据。

输入（快照已入库，勿删）：
  viz/data/niche/atmeplz/<date>/site.json
  viz/data/niche/galbands/<date>/leaderboard.json
  viz/data/niche/arenaofbias/<date>/bootstrap.json   ← 无票矩阵，只出收录清单
  （致知的分数已由 scripts/d58_zhizhi_import.py 写进主库 independent，不在此重复）

输出：
  viz/data/niche/sources.json  —— viz_transform.build_leaderboard() 读取并合并进排行榜

用法：
  python scripts/build_niche_boards.py            # 预览匹配（不写文件）
  python scripts/build_niche_boards.py --apply    # 写 sources.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "model_data_v2.jsonl"
NICHE = ROOT / "viz/data/niche"

ATMEPlZ_META = {
    "source": "atmeplz",
    "label": "atmeplz",
    "url": "https://atmeplz.github.io/ai-test-prompt/",
    "snapshot": "2026-09-11",
    "note": "端到端工程产出（7 题 / 4 方向），私榜；D53 已裁定不构成立行依据",
}
GALBANDS_META = {
    "source": "galbands",
    "label": "galbands",
    "url": "https://benchmark.galbands.com/",
    "snapshot": "2026-10-09",
    "note": "RP（角色扮演）竞技场，OpenRouter 目录镜像；综合榜为百分制、其余四榜为 Elo",
}
AOB_META = {
    "source": "arenaofbias",
    "label": "亿模亿样",
    "url": "https://gallery.arenaofbias.icu/#/leaderboard",
    "snapshot": "2026-10-10",
    "note": "策展式前沿榜；bootstrap 不含票矩阵、无法离线复算 Elo ⇒ 只作发现源，不出排行",
}


# ---------------------------------------------------------------- 名称归一
def norm(s: str) -> str:
    """去全部非字母数字 + 小写（`qwen3.8-flash` 与 `qwen-3.8-flash` 视为同物）"""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def strip_vendor(name: str) -> str:
    """`Google: Gemini 3.8 Flash` → `Gemini 3.8 Flash`"""
    return name.split(":", 1)[1].strip() if ":" in (name or "") else (name or "")


# 站点显示名 → 主库命名的清洗表。
# ⛔ 只收「已逐条核实过」的映射；拿不准的一律留空（标未收录），不许用相似度猜。
#    教训：D58 曾把 `Gemini 3.7 Flash` 以 0.94 相似度误配到 `gemini-3.8-flash`。
NAME_FIXUPS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^Doubao\s+Seed\s+", re.I), "Seed "),      # ByteDance: Doubao Seed 2.1 Pro → seed-2.1-pro
    (re.compile(r"^Hy(\d)", re.I), r"Hunyuan Hy\1"),        # Tencent: Hy4 preview → hunyuan-hy4-preview
    (re.compile(r"\s+Contributor$", re.I), ""),             # Meta: Muse Spark 1.2 Contributor
    (re.compile(r"^Codex\s+", re.I), ""),                   # OpenAI: Codex Auto Review（非模型条目）
]

# 人工裁定：清洗后仍对不上、但已核实是同一型号的
EXPLICIT_ALIAS: dict[str, str] = {
    "gemini40930": "google:gemini-4-argon:base",   # 站点用发布日代号，主库用 Argon
    "musespark12contributor": "meta:muse-spark-1.2:base",   # atmeplz 用 contributor 标注渠道
    "dots3noteprev": "dots-studio:dots3-note-preview:base",  # 站点缩写 prev
}


def clean_site_name(name: str) -> str:
    s = strip_vendor(name)
    for pat, rep in NAME_FIXUPS:
        s = pat.sub(rep, s)
    return s.strip()


# 主库把「档位 / 快照日期 / 参数量」写进了 family 段，站点名常常没有。
# 只有当站点名是主库 family 的**前缀**、剩余部分是下列白名单之一、且全库唯一命中时才采用。
# ⛔ 不白名单化就会误配：`Claude Sonnet 5` 是 `claude-sonnet-5.5` 的前缀（差 1 字符）、
#    `MiMo-V2.5` 是 `mimo-v2.5-pro` 的前缀——两者都**不是同一型号**。
SUFFIX_WHITELIST = {
    "high", "low", "none", "max", "xhigh", "minimal",
    "thinking", "instant", "preview", "base", "chat", "turbo",
}


def suffix_ok(rest: str) -> bool:
    """rest = 主库 family 去掉站点名后的剩余部分。"""
    if rest in SUFFIX_WHITELIST:
        return True
    if re.fullmatch(r"\d{8}", rest):            # 快照日期 20240718
        return True
    if re.fullmatch(r"\d+(\.\d+)?b[a-z0-9]*", rest):  # 参数量 30ba3b / 7b
        return True
    return False


def vendor_ok(site_vendor: str, lib_vendor: str) -> bool:
    """厂商相容校验：站点 vendor slug 与库内 vendor 显示名归一后互含。

    ⛔ 去掉这层校验会串厂（D53 实测：`norm('') in x` 恒真导致 28/31 假匹配）。
    """
    lv = norm(lib_vendor)
    if not lv:
        return False
    sv = norm(site_vendor)
    if not sv:
        return True  # 站点没给厂商时不设限，交由名称判定
    return sv in lv or lv in sv


class LibIndex:
    """主库索引：family 段 / full_name / 「family+版本段」拼接串。

    第三个索引是为 `deepseek:deepseek-v4-pro:0813` 这类「版本日期在 model_id 第 3 段」的记录准备的，
    站点常写成 `DeepSeek V4 Pro 0813`（日期在名字里）。
    """

    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.by_family: dict[str, list[dict]] = defaultdict(list)
        self.by_full: dict[str, list[dict]] = defaultdict(list)
        self.by_full_id: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            mid = r.get("model_id") or ""
            parts = mid.split(":")
            if len(parts) > 1:
                self.by_family[norm(parts[1])].append(r)
                if len(parts) > 2 and parts[2] and parts[2] != "base":
                    self.by_full_id[norm(parts[1] + parts[2])].append(r)
            self.by_full[norm((r.get("basic_info") or {}).get("full_name") or "")].append(r)

    def match(self, name: str, vendor: str, extra: str | None = None, effort: str | None = None):
        """返回 (row|None, 方式)。只做精确判定，绝不用相似度猜。

        方式取值：
          `exact`  —— 清洗后归一相等
          `effort` —— 站点把档位拆成独立字段（atmeplz 的 `claude-fable-5` + `max`），
                      拼成 `claude-fable-5-max` 后**唯一**命中主库档位行；多个候选时不采用
          `alias`  —— 人工裁定表
          `""`     —— 未收录
        """
        cleaned = clean_site_name(name)
        cands: list[str] = []
        for raw in (cleaned, extra or ""):
            n = norm(raw)
            if n:
                cands.append(n)
        for n in cands:
            mid = EXPLICIT_ALIAS.get(n)
            if mid:
                for r in self.rows:
                    if r["model_id"] == mid:
                        return r, "alias"
            if len(n) < 3:
                continue
            for pool in (self.by_family, self.by_full, self.by_full_id):
                for row in pool.get(n, []):
                    if vendor_ok(vendor, (row.get("basic_info") or {}).get("vendor") or ""):
                        return row, "exact"
        # 型号 + 档位（仅唯一命中才采用，避免多档位歧义）
        if effort:
            e = norm(effort)
            for n in cands:
                hits = [r for r in self.by_family.get(n + e, [])
                        if vendor_ok(vendor, (r.get("basic_info") or {}).get("vendor") or "")]
                if len(hits) == 1:
                    return hits[0], "effort"
        # 白名单后缀 + 全库唯一（见 SUFFIX_WHITELIST 注释）
        for n in cands:
            pool: list[dict] = []
            for key, rows_ in self.by_family.items():
                if key.startswith(n) and len(key) > len(n) and suffix_ok(key[len(n):]):
                    pool.extend(rows_)
            uniq = {r["model_id"] for r in pool
                    if vendor_ok(vendor, (r.get("basic_info") or {}).get("vendor") or "")}
            if len(uniq) == 1:
                return pool[0], "suffix"
        return None, ""

    def suggest(self, name: str, vendor: str = "", extra: str | None = None, limit: int = 3) -> list[str]:
        """仅用于缺口报告的「可能是它」提示，不进榜。"""
        cleaned = clean_site_name(name)
        out: list[str] = []
        for raw in (cleaned, extra or ""):
            n = norm(raw)
            if len(n) < 5:
                continue
            for key, pool in self.by_family.items():
                if key.startswith(n) or (n in key and abs(len(n) - len(key)) <= 4):
                    for row in pool:
                        if vendor_ok(vendor, (row.get("basic_info") or {}).get("vendor") or ""):
                            out.append(row["model_id"])
        return out[:limit]


def pack(row, site_name: str, score: float, rank: int, extra: dict | None = None) -> dict:
    """打包一行榜单。row 为 None 表示库内未收录，仍保留（榜单照实呈现）。"""
    hit = row is not None
    bi = (row or {}).get("basic_info") or {}
    out = {
        "model_id": row["model_id"] if hit else None,
        "site_name": site_name,
        # 榜单是站点的榜，显示名统一用站点写法（否则同一列混着主库名，像两个榜拼的）
        "full_name": strip_vendor(site_name),
        "lib_name": bi.get("full_name") or "",
        "vendor": bi.get("vendor") or (site_name.split(":", 1)[0].strip() if ":" in site_name else ""),
        "score": score,
        "rank": rank,
        "in_lib": hit,
    }
    if extra:
        out.update(extra)
    return out


def dedupe(rows: list[dict]) -> list[dict]:
    """同一模型多行时保留最好名次的一行；未收录的按站点名去重。"""
    best: dict[str, dict] = {}
    for r in rows:
        key = r["model_id"] or f"site:{norm(r['site_name'])}"
        cur = best.get(key)
        if cur is None or r["rank"] < cur["rank"]:
            best[key] = r
    return sorted(best.values(), key=lambda x: x["rank"])


# ---------------------------------------------------------------- atmeplz
def build_atmeplz(lib: LibIndex, preview: bool) -> tuple[list[dict], dict]:
    path = NICHE / "atmeplz/2026-09-11/site.json"
    site = json.loads(path.read_text(encoding="utf-8"))
    meta = site["meta"]
    src_rows = site["rows"]
    total_ref = meta.get("total_ref") or 400

    boards_spec = [
        ("atmeplz_total", "atmeplz 综合", f"端到端工程产出合计（满分 {total_ref}）",
         "分", 1, 0, lambda r: r["total"]),
        ("atmeplz_text", "atmeplz 文字", "文字方向",
         "分", 1, 0, lambda r: (r["directions"].get("text") or {}).get("value")),
        ("atmeplz_frontend", "atmeplz 前端", "前端方向",
         "分", 1, 0, lambda r: (r["directions"].get("frontend") or {}).get("value")),
        ("atmeplz_backend", "atmeplz 后端", "后端方向",
         "分", 1, 0, lambda r: (r["directions"].get("backend") or {}).get("value")),
        ("atmeplz_knowledge", "atmeplz 知识", "知识方向",
         "分", 1, 0, lambda r: (r["directions"].get("knowledge") or {}).get("value")),
    ]

    boards, resolve_log = [], {"matched": [], "unmatched": []}
    for key, label, note, unit, scale, minv, getter in boards_spec:
        packed = []
        for r in src_rows:
            score = getter(r)
            if not isinstance(score, (int, float)):
                continue
            row, how = lib.match(r["model"], r["vendor"], effort=r.get("effort"))
            packed.append(pack(row, r.get("card_label") or r["board"], round(float(score), 4), r["rank"],
                               {"platform": r.get("platform"), "effort": r.get("effort"),
                                "tested": r.get("tested")}))
            if key == "atmeplz_total":
                if row is None:
                    resolve_log["unmatched"].append(
                        {"name": f"{r['model']} ({r.get('platform') or '-'}/{r.get('effort') or '-'})",
                         "vendor": r["vendor"],
                         "suggest": lib.suggest(r["model"], r["vendor"])})
                else:
                    resolve_log["matched"].append({"name": r["board"], "how": how,
                                                   "model_id": row["model_id"]})
        deduped = dedupe(packed)
        for i, it in enumerate(deduped, 1):
            it["rank"] = i
        boards.append({
            "key": key, "label": label, "group": "小众榜", "unit": unit, "scale": scale,
            **({"min": minv} if minv is not None else {}),
            "source": "atmeplz", "snapshot": "2026-09-11", "url": ATMEPlZ_META["url"],
            "board_note": note, "confidence": "T3", "rows": deduped,
        })
    return boards, resolve_log


# ---------------------------------------------------------------- galbands
def build_galbands(lib: LibIndex, preview: bool) -> tuple[list[dict], dict]:
    path = NICHE / "galbands/2026-10-09/leaderboard.json"
    lb = json.loads(path.read_text(encoding="utf-8"))

    # 综合榜是百分制（21–69），其余四榜是 Elo（745–1223）—— 坐标轴必须分开
    spec = {
        "综合评分": ("galbands_overall", "galbands 综合", "分", 0, "综合评分（百分制）"),
        "同人": ("galbands_fan", "galbands 同人", "Elo", 600, "同人方向 Elo"),
        "原创": ("galbands_original", "galbands 原创", "Elo", 600, "原创方向 Elo"),
        "长程": ("galbands_long", "galbands 长程", "Elo", 600, "长程方向 Elo"),
        "翻译": ("galbands_translation", "galbands 翻译", "Elo", 600, "翻译方向 Elo"),
    }

    boards, resolve_log = [], {"matched": [], "unmatched": []}
    for b in lb.get("boards") or []:
        name = b.get("name")
        if name not in spec:
            continue
        key, label, unit, minv, note = spec[name]
        packed = []
        for i, r in enumerate(b.get("rows") or [], 1):
            orid = r.get("openrouter_id") or ""
            site_name = r.get("name") or ""
            row, how = lib.match(site_name, "", extra=orid.split("/")[-1] if orid else None)
            packed.append(pack(row, site_name, round(float(r.get("score") or 0), 4), i,
                               {"winrate": round(float(r.get("winrate") or 0), 2),
                                "votes": r.get("votes"), "openrouter_id": orid}))
            if key == "galbands_overall":
                if row is None:
                    resolve_log["unmatched"].append(
                        {"name": site_name, "vendor": "",
                         "suggest": lib.suggest(site_name, "", orid.split("/")[-1] if orid else None)})
                else:
                    resolve_log["matched"].append({"name": site_name, "how": how,
                                                   "model_id": row["model_id"]})
        deduped = dedupe(packed)
        for i, it in enumerate(deduped, 1):
            it["rank"] = i
        boards.append({
            "key": key, "label": label, "group": "小众榜", "unit": unit, "scale": 1, "min": minv,
            "source": "galbands", "snapshot": "2026-10-09", "url": GALBANDS_META["url"],
            "board_note": note, "confidence": "T3", "rows": deduped,
        })
    return boards, resolve_log


# ---------------------------------------------------------------- arenaofbias
def build_arenaofbias(lib: LibIndex) -> dict:
    """无 Elo 可算 ⇒ 只出「谁在榜 / 库内收了没」清单，不造排行。"""
    path = NICHE / "arenaofbias/2026-10-10/bootstrap.json"
    boot = json.loads(path.read_text(encoding="utf-8"))
    seen: dict[str, dict] = {}
    for w in boot.get("works") or []:
        m = w.get("model")
        if not m:
            continue
        e = seen.setdefault(m, {"model": m, "modelName": w.get("modelName"), "vendor": w.get("vendor"),
                                "works": 0, "efforts": set()})
        e["works"] += 1
        if w.get("effort"):
            e["efforts"].add(w["effort"])
    items = []
    for e in sorted(seen.values(), key=lambda x: -x["works"]):
        row, how = lib.match(e["model"], "", extra=e.get("modelName"))
        items.append({"site_name": e["modelName"] or e["model"], "vendor": e.get("vendor"),
                      "works": e["works"], "efforts": sorted(e["efforts"]),
                      "model_id": row["model_id"] if row else None})
    return {
        "source": "arenaofbias", **AOB_META,
        "total_models": len(items),
        "covered": sum(1 for x in items if x["model_id"]),
        "items": items,
    }


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写入 viz/data/niche/sources.json")
    args = ap.parse_args()

    rows = [json.loads(l) for l in MAIN.read_text(encoding="utf-8").splitlines() if l.strip()]
    lib = LibIndex(rows)
    print(f"主库 {len(rows)} 条")

    boards, log_a = build_atmeplz(lib, not args.apply)
    gboards, log_g = build_galbands(lib, not args.apply)
    aob = build_arenaofbias(lib)
    boards += gboards

    print("\n=== 榜单 ===")
    for b in boards:
        print(f"  {b['label']:18s} {len(b['rows']):4d} 行  单位={b['unit']:4s} 来源={b['source']}")

    print("\n=== arenaofbias（不出排行，只列收录） ===")
    print(f"  {aob['covered']}/{aob['total_models']} 已在库")

    for tag, log in (("atmeplz", log_a), ("galbands", log_g)):
        n_hit, n_gap = len(log["matched"]), len(log["unmatched"])
        n_all = n_hit + n_gap
        print(f"\n=== {tag} 未收录 {n_gap}/{n_all} ===")
        for u in log["unmatched"]:
            hint = f"  ← 可能是 {u['suggest']}" if u["suggest"] else ""
            print(f"  ▸ {u['name'][:44]:44s}{hint}")
        n_alias = sum(1 for m in log["matched"] if m["how"] == "alias")
        print(f"  库内命中 {n_hit}/{n_all} = {n_hit / n_all * 100:.1f}%（其中人工裁定 {n_alias}）")

    if not args.apply:
        print("\n[dry-run] 加 --apply 才写文件")
        return

    out = {
        "generated": "2026-11-04",
        "note": "小众榜 = 跟踪的非官方榜合集；只是「跑分排行」下拉的一个分组，不是独立页面",
        "sources": [
            {**ATMEPlZ_META, "in_main": False},
            {**GALBANDS_META, "in_main": False},
            {**AOB_META, "in_main": False},
            {"source": "zhizhi", "label": "致知", "url": "https://llm2014.github.io/llm_benchmark/",
             "snapshot": "2026-11", "in_main": True,
             "note": "私有题库 28 题；分数已入主库 independent（致知·逻辑榜 / 致知·视觉榜），本文件不重复"},
        ],
        "boards": boards,
        "coverage": {"atmeplz": log_a, "galbands": log_g, "arenaofbias": aob},
    }
    dst = NICHE / "sources.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[已写] {dst.relative_to(ROOT)}  {dst.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
