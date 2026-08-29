#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""incoming 采集文件 vs 主库 差异扫描器（阶段 3 · 冲突裁决清单输入）

背景：
    合并策略是 `--on-both source_wins --on-null take_source --on-array replace`，
    即「采集值覆盖骨架值」。因此主库里仍与 incoming 源文件不一致的字段，
    只可能来自三类：
      1. 骨架独有字段（incoming 没有，主库保留骨架值）→ 非冲突
      2. 数组/对象按策略递归合并后残留的结构差异 → 需人工看
      3. 采集值为 null 而骨架有值（take_source 不覆盖已有的非 null）→ **实质冲突候选**

用法:
    PYTHONUTF8=1 python scripts/diff_incoming_db.py [--out intermediate/conflicts.json] [--show 15]

产出:
    - 控制台摘要（差异字段 TOP、冲突候选计数、典型案例）
    - JSON 明细
"""

import argparse
import json
import os
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_DB = os.path.join(REPO, "model_data_v2.jsonl")
INCOMING = os.path.join(REPO, "incoming", "models")

# 这些字段的差异常属正常（采集日期、来源集合随合并变化），不列为冲突候选
IGNORE_PATHS = {
    "meta.collected_at",
    "meta.source_urls",
    "meta.notes",
    "schema_version",
    "model_id",
}


def flatten(obj, prefix="", out=None):
    """把嵌套 dict 摊平成 点号路径 -> 值；list 视为叶子（整体比较）"""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        if not obj:
            out[prefix] = obj
        for k, v in obj.items():
            flatten(v, f"{prefix}.{k}" if prefix else str(k), out)
    else:
        out[prefix] = obj
    return out


def load_db():
    db = {}
    with open(MAIN_DB, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                db[r["model_id"]] = r
    return db


def load_incoming():
    files = {}
    for name in sorted(os.listdir(INCOMING)):
        if not name.endswith(".jsonl"):
            continue
        p = os.path.join(INCOMING, name)
        try:
            with open(p, encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                continue
            rec = json.loads(content)
            files[name] = rec
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            files[name] = {"__error__": str(e)}
    return files


def main():
    ap = argparse.ArgumentParser(description="incoming vs 主库 差异扫描器")
    ap.add_argument("--out", default=os.path.join(REPO, "intermediate", "conflicts.json"))
    ap.add_argument("--show", type=int, default=15, help="打印典型案例条数")
    args = ap.parse_args()

    db = load_db()
    inc = load_incoming()

    field_diff = Counter()          # 差异字段 -> 出现次数
    conflicts = []                  # 实质冲突候选明细
    skeleton_only = Counter()       # 骨架独有字段
    missing_in_db = []              # incoming 有、主库没有 model_id
    parse_errors = []               # 解析失败文件

    for name, rec in inc.items():
        if "__error__" in rec:
            parse_errors.append((name, rec["__error__"]))
            continue
        mid = rec.get("model_id")
        if mid not in db:
            missing_in_db.append((name, mid))
            continue
        flat_src = flatten(rec)
        flat_dst = flatten(db[mid])
        for path, sval in flat_src.items():
            if path in IGNORE_PATHS:
                continue
            if path not in flat_dst:
                continue                      # 骨架没有，合并后主库也没有 → 非差异
            dval = flat_dst[path]
            if sval == dval:
                continue
            field_diff[path] += 1
            # 实质冲突候选：采集值非空，却没写进主库（说明骨架值胜出）
            if sval not in (None, "", [], {}):
                conflicts.append({
                    "file": name,
                    "model_id": mid,
                    "path": path,
                    "incoming": sval,
                    "db": dval,
                })
        for path in flat_dst:
            if path not in flat_src and path not in IGNORE_PATHS:
                skeleton_only[path] += 1

    summary = {
        "incoming_files": len(inc),
        "matched": len(inc) - len(missing_in_db) - len(parse_errors),
        "missing_in_db": missing_in_db,
        "parse_errors": parse_errors,
        "field_diff_top": field_diff.most_common(40),
        "skeleton_only_top": skeleton_only.most_common(20),
        "conflict_count": len(conflicts),
        "conflicts": conflicts[:500],
    }

    d = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(d, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("=" * 74)
    print("incoming vs 主库 差异扫描")
    print("=" * 74)
    print("采集文件: %d   匹配主库: %d   缺 model_id: %d   解析失败: %d"
          % (len(inc), summary["matched"], len(missing_in_db), len(parse_errors)))
    print()
    print("--- 差异字段 TOP 15（采集值与主库值不同）---")
    for path, n in field_diff.most_common(15):
        print("  %-56s %4d 处" % (path, n))
    print()
    print("--- 实质冲突候选（采集值非空却未写入主库）: %d 条 ---" % len(conflicts))
    for c in conflicts[:args.show]:
        sv = json.dumps(c["incoming"], ensure_ascii=False)[:42]
        dv = json.dumps(c["db"], ensure_ascii=False)[:42]
        print("  %s" % c["model_id"])
        print("      %s: 采集=%s | 主库=%s" % (c["path"], sv, dv))
    if len(conflicts) > args.show:
        print("  ... 另有 %d 条，见 %s" % (len(conflicts) - args.show, args.out))
    print()
    print("--- 骨架独有字段 TOP 10（主库有、采集文件没有，合并时保留）---")
    for path, n in skeleton_only.most_common(10):
        print("  %-56s %4d 条记录" % (path, n))
    print()
    print("明细已写出: %s" % args.out)


if __name__ == "__main__":
    main()
