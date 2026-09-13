# -*- coding: utf-8 -*-
"""D48 · 基准名大小写归一（D46 qa_outliers r2 扫出 14 簇，用户夜间授权批量清理）。

口径：
  ① 仅处理 casefold 相同、写法不同的基准名簇（同基准不同大小写，跨模型不可比是实害）；
  ② 簇内取**多数派写法**（按全库条目数；平票取条目涉及记录数多者，再平则字典序）；
  ③ 只改 self_reported / independent 两数组的 benchmark 字段（arena_elo 的 sub_benchmark
     另有主键口径，本轮不动）；
  ④ 主键 `benchmark,config,date` 归一后如出现撞键（同记录同基准同 config 同 date 两条
     大小写异形）→ 合并为一条（保留多数派条目、补 null 字段）。
用法：PYTHONUTF8=1 python scripts/d48_normalize_bench_names.py [--apply]
"""
import json
import os
import shutil
import sys
import datetime
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
TODAY = datetime.date.today().isoformat()


def main():
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]

    # 1) 统计簇：casefold -> {writing: [entries, record_ids]}
    detail = collections.defaultdict(dict)
    for r in rows:
        for seg in ('self_reported', 'independent'):
            for b in (r.get('benchmarks') or {}).get(seg) or []:
                n = b.get('benchmark')
                if isinstance(n, str) and n:
                    d = detail[n.casefold()].setdefault(n, [0, set()])
                    d[0] += 1
                    d[1].add(id(r))
    to_fix = {}
    for cf, writings in sorted(detail.items()):
        if len(writings) < 2:
            continue
        ranked = sorted(writings.items(), key=lambda kv: (-kv[1][0], -len(kv[1][1]), kv[0]))
        keep = ranked[0][0]
        to_fix[cf] = keep
        print(f"簇 {cf}: 多数派「{keep}」<- " + ', '.join(f"{w}({v[0]})" for w, v in ranked))

    # 2) 改写 + 撞键合并
    renames = merges = 0
    for r in rows:
        for seg in ('self_reported', 'independent'):
            arr = (r.get('benchmarks') or {}).get(seg)
            if not arr:
                continue
            for b in arr:
                n = b.get('benchmark')
                if isinstance(n, str) and n.casefold() in to_fix and n != to_fix[n.casefold()]:
                    b['benchmark'] = to_fix[n.casefold()]
                    renames += 1
            # 撞键合并：key(benchmark,config,date,source_site) 相同的条目留第一条，其余 null 字段补入
            seen = {}
            keep_arr = []
            for b in arr:
                k = (b.get('benchmark'), b.get('config'), b.get('date'), b.get('source_site'))
                if k in seen:
                    base = seen[k]
                    for f, v in b.items():
                        if base.get(f) is None and v is not None:
                            base[f] = v
                    merges += 1
                else:
                    seen[k] = b
                    keep_arr.append(b)
            if len(keep_arr) != len(arr):
                r['benchmarks'][seg] = keep_arr

    print(f'\n计划：改写 {renames} 处，撞键合并 {merges} 条')
    if not APPLY:
        print('(dry-run，未写入。加 --apply 落库)')
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d48-r2-{TS}.jsonl')
    shutil.copy2(MAIN, bk)
    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f'已写入 | 备份 -> {os.path.relpath(bk, ROOT)}')


if __name__ == '__main__':
    main()
