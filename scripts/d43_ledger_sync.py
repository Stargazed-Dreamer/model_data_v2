# -*- coding: utf-8 -*-
"""
D43 台账 models 数组归位同步
原则（沿 D41/D42 约定）：台账 models 数组是「活标识」，同步为主库现行 id；
status / submitted_files / vendor（批次登记身份）等历史字段一律不动；
真正未入库（NO_LIB）的批次条目是真实历史，保留。

解析链（对每条 NOT_LIB 的台账 id）：
  A. family+variant 在主库唯一命中 → 归位（vendor 漂移）
  B. family 经 D42 点号映射后，(新family, variant) 唯一命中 → 归位（连缀漂移）
  C. 其余 → 保留（真未入库）

用法: python d43_ledger_sync.py           # dry-run
      python d43_ledger_sync.py --apply
"""
import json, sys, io, re
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LEDGER = 'docs/batch_claim_ledger.jsonl'
LIB = 'model_data_v2.jsonl'


def build_famvar():
    famvar = defaultdict(list)
    by_vfam = defaultdict(list)
    for line in open(LIB, encoding='utf-8'):
        mid = json.loads(line)['model_id']
        vv, f, v = mid.split(':')
        famvar[(f, v)].append(mid)
        by_vfam[(vv, f)].append(mid)
    return famvar, by_vfam


def build_d42_family_map():
    """从主库 notes 提取 D42 家族改名映射 old_family -> new_family。"""
    m = {}
    pat = re.compile(r'【D42 点号归一】原 model_id: \S+ → \S+')
    for line in open(LIB, encoding='utf-8'):
        r = json.loads(line)
        notes = (r.get('meta') or {}).get('notes') or ''
        for seg in notes.split('；'):
            if '【D42 点号归一】' in seg:
                mm = re.search(r'原 model_id: ([^:\s]+):([^:]+):(\S+) → ([^:\s]+):([^:]+):(\S+)', seg)
                if mm and mm.group(2) != mm.group(5):
                    m[mm.group(2)] = mm.group(5)
    return m


# D43 结构改名映射（family old -> new），与 d43_struct_fix.py RENAMES 一致
D43_FAM = {
    's1-1': 's1.1-1.5b',
    's1-32b': 's1.1-32b',
    'olmo-3-32b-instruct': 'olmo-3.1-32b-instruct',
    'luxia-21-4b-alignment': 'luxia-2.1-4b-alignment',
    'minicpm-1-2b': 'minicpm-1b',
    'minicpm-2-4b': 'minicpm-2b',
}


def resolve(mid, famvar, by_vfam, fam42):
    try:
        v0, f0, ver0 = mid.split(':')
    except ValueError:
        return None, 'MALFORMED'
    cands = famvar.get((f0, ver0), [])
    if len(cands) == 1:
        return cands[0], 'VENDOR_DRIFT'
    nf = fam42.get(f0) or D43_FAM.get(f0)
    if nf:
        cands2 = famvar.get((nf, ver0), [])
        if len(cands2) == 1:
            return cands2[0], 'VENDOR_DOT_DRIFT'
    # C. 同 vendor 下 (归一后) family 唯一 → variant 漂移
    #    （如 anthropic:claude-3-haiku:20240307 → anthropic:claude-3-haiku:base）
    cands3 = by_vfam.get((v0, nf or f0), [])
    if len(cands3) == 1:
        return cands3[0], 'VARIANT_DRIFT'
    return None, 'NO_LIB'


def main(apply):
    lib_ids = {json.loads(l)['model_id'] for l in open(LIB, encoding='utf-8')}
    famvar, by_vfam = build_famvar()
    fam42 = build_d42_family_map()
    print(f'主库 id 数: {len(lib_ids)}；D42 家族映射: {len(fam42)} 条')

    lines = open(LEDGER, encoding='utf-8').read().splitlines()
    out, stats = [], defaultdict(int)
    changed_batches = defaultdict(list)
    unresolved = []
    for line in lines:
        if not line.strip():
            continue
        d = json.loads(line)
        new_models = []
        for m in d.get('models') or []:
            if m in lib_ids:
                new_models.append(m)
                stats['in_lib'] += 1
                continue
            tgt, why = resolve(m, famvar, by_vfam, fam42)
            if tgt:
                new_models.append(tgt)
                stats[why] += 1
                changed_batches[d['batch_id']].append(f'{m} -> {tgt}')
            else:
                new_models.append(m)
                unresolved.append((d['batch_id'], m, why))
                stats['NO_LIB'] += 1
        d['models'] = new_models
        out.append(json.dumps(d, ensure_ascii=False))

    print('统计:', dict(stats))
    print(f'\n改动批次 {len(changed_batches)} 个:')
    for b, items in sorted(changed_batches.items()):
        print(f'  {b}: {len(items)} 条')
    if unresolved:
        print(f'\n未归位（保留原登记）{len(unresolved)} 条，按批:')
        byb = defaultdict(list)
        for b, m, w in unresolved:
            byb[b].append(m)
        for b, ms in sorted(byb.items()):
            print(f'  {b}: {len(ms)} 条')

    if apply:
        with open(LEDGER, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(out) + '\n')
        print('\n已写盘。')
    else:
        print('\n（dry-run，未写盘）')


if __name__ == '__main__':
    main('--apply' in sys.argv)
