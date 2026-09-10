# -*- coding: utf-8 -*-
"""D40 Wave-1 合并后收尾三自检（docs/增量更新工作流.md §4 强制项）：
  1) 数组缩水取证：老记录（merge 前已存在）的数组长度不得缩水；
  2) 撞键分类：并集主键（self_reported: benchmark,config,date / independent 加 source_site /
     arena_elo: sub_benchmark,date）不得出现重复键；
  3) WARN 基线差值：现基线 ERROR 0 / WARN 0，任何上涨都要解释。
另附：model_id 唯一性与重复检查。
"""
import json, os, sys, collections, glob

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PRE = sorted(glob.glob('backups/model_data_v2.pre-d40-wave1-merge-*.jsonl'))[-1]
CUR = 'model_data_v2.jsonl'
print('基线备份:', PRE)
print('当前主库:', CUR, '\n')


def load(p):
    out = {}
    for line in open(p, encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            out.setdefault(r['model_id'], []).append(r)
    return out


pre = load(PRE)
cur = load(CUR)
print(f'model_id 数：pre={len(pre)}  cur={len(cur)}  Δ={len(cur)-len(pre)}')

# --- 0) 重复 model_id ---
dups = {k: len(v) for k, v in cur.items() if len(v) > 1}
print('\n[0] model_id 重复:', dups if dups else '无 ✓')

# --- 1) 数组缩水取证 ---
ARRAYS = ['benchmarks.self_reported', 'benchmarks.independent', 'benchmarks.arena_elo',
          'meta.source_urls', 'basic_info.positioning']
shrink = []
for mid, recs in pre.items():
    if mid not in cur:
        shrink.append((mid, '整个记录丢失'))
        continue
    a, b = recs[-1], cur[mid][-1]
    for path in ARRAYS:
        x, y = a, b
        for seg in path.split('.'):
            x = (x or {}).get(seg) if isinstance(x, dict) else None
            y = (y or {}).get(seg) if isinstance(y, dict) else None
        nx = len(x) if isinstance(x, list) else 0
        ny = len(y) if isinstance(y, list) else 0
        if ny < nx:
            shrink.append((mid, path, nx, ny))
print(f'\n[1] 数组缩水取证：老记录 {len(pre)} 条 / 检查字段 {len(ARRAYS)} 个 → '
      f'{"无缩水 ✓" if not shrink else "发现缩水 " + str(shrink)}')

# --- 2) 撞键分类 ---
NEW_IDS = [m for m in cur if m not in pre]
KEYS = {
    'benchmarks.self_reported': ('benchmark', 'config', 'date'),
    'benchmarks.independent':   ('benchmark', 'config', 'date', 'source_site'),
    'benchmarks.arena_elo':     ('sub_benchmark', 'date'),
}
collisions = []
for mid in NEW_IDS:
    r = cur[mid][-1]
    for path, keyf in KEYS.items():
        arr = r
        for seg in path.split('.'):
            arr = (arr or {}).get(seg) if isinstance(arr, dict) else None
        for e in arr or []:
            k = tuple(e.get(f) for f in keyf)
            collisions.append((mid, path, k))
cnt = collections.Counter(collisions)
dupc = {k: v for k, v in cnt.items() if v > 1}
print(f'\n[2] 撞键分类：新增 {len(NEW_IDS)} 条记录 → '
      f'{"无重复键 ✓" if not dupc else "重复键 " + str(dupc)}')

# --- 3) WARN 基线差值 ---
print('\n[3] WARN 基线差值：merge 前全库 ERROR 0 / WARN 0 → merge 后见下')
print('     （由 validate_model_data.py 单独复跑，见外部输出）')

# --- 附：新增记录的数组条目统计 ---
print(f'\n[附] 新增 {len(NEW_IDS)} 条记录的数组条目数：')
tot = collections.Counter()
for mid in NEW_IDS:
    r = cur[mid][-1]
    for sec in ('self_reported', 'independent', 'arena_elo'):
        n = len(r['benchmarks'].get(sec) or [])
        tot[sec] += n
print('    ', dict(tot))
