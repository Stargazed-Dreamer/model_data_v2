"""D42：model_id 点号归一。

规则（本项目 model_id 命名口径）：
  family 段中 **官方名称里确为小数点** 的连字符一律还原为 `.`；`-` 仅作 token 分隔符。
  - 版本号含小数  -> 点：claude-opus-4.5 / deepseek-v3.1 / qwen-3.5-max-preview
  - 参数量含小数  -> 点：qwen-3-1.7b / exaone-3.5-2.4b / qwen2.5-1.5b
  - 非小数的连字符一律保留：日期(2025-09-23)、整数参数量(A14B / 40k / 236b)、
    模型名内嵌数字(baichuan2-13b / telechat2-115b / llama-2-70b / r1-32b)

判据（证据驱动，机械可复现）：
  对 family 中每一处「数字-数字」的连字符，取左右两侧的**最大连续数字串** a、b，
  若字面串 `a.b` 出现在该记录的 basic_info.full_name 或 basic_info.version 原文中，
  则判定该连字符是小数点，替换为 `.`；否则保留。
  -> 天然排除日期(2025-09-23)、整数参数量、模型名内嵌数字（这些 `a.b` 不会出现在原文里）

用法：
  python temp/d42_dots.py            # dry-run
  python temp/d42_dots.py --apply    # 写入
"""
import sys
import json
import re
import collections

SRC = 'model_data_v2.jsonl'
HAS_CHAIN = re.compile(r'\d-\d')


def digit_runs(s):
    """返回 [(start, end, text)]，每段最大连续数字串。"""
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r'\d+', s)]


def dots_from_evidence(family, pool):
    """pool: 证据中出现的所有 `a.b` 字面串集合。返回 (新family, 命中的 a.b 列表)。"""
    if not pool or not HAS_CHAIN.search(family):
        return None, []
    runs = digit_runs(family)
    by_end = {e: t for s, e, t in runs}
    by_start = {s: t for s, e, t in runs}
    hits = []
    out = []
    for i, ch in enumerate(family):
        if ch == '-' and (i in by_end) and (i + 1 in by_start):
            a, b = by_end[i], by_start[i + 1]
            dec = f'{a}.{b}'
            if dec in pool:
                out.append('.')
                hits.append(dec)
                continue
        out.append(ch)
    if not hits:
        return None, []
    cand = ''.join(out)
    return (cand if cand != family else None), hits


DEC_IN_TEXT = re.compile(r'(?=(\d+\.\d+))')   # 前瞻：允许重叠，覆盖 `1.0.0` 这类连缀
# 下划线当小数点：仅当两侧均为**单个数字**时才认定（避免把 `20250805_16K` 误判）
UND_DEC = re.compile(r'(?<!\d)(\d)_(\d)(?!\d)')

# 人工补录：full_name/version 均无点号证据，但官方名确含小数点
MANUAL = {
    'claude-3-5-sonnet': ('claude-3.5-sonnet', 'Anthropic 官方名 Claude 3.5 Sonnet'),
}

# 排除：连字符不是「小数点转写」问题，而是 family 本身缺参数量等结构问题，另行上报
EXCLUDE = {
    's1-1': 's1 家族三兄弟（s1 / s1-1 / s1-32b）的 `-1` 语义不自洽：'
            'full_name 分别是 s1-32B(v1.0) / s1.1-1.5B / s1.1-32B，'
            '转成 s1.1 会与 s1-32b 的读法冲突，属结构问题非点号问题',
}


def main():
    apply = '--apply' in sys.argv
    recs = [json.loads(l) for l in open(SRC, encoding='utf-8') if l.strip()]

    fams = collections.defaultdict(list)
    for r in recs:
        p, f, v = r['model_id'].split(':')
        fams[f].append(r)

    # family 级证据池（含 full_name / version 的点号 + 下划线小数点）
    pool_by_fam = {}
    for f, rs in fams.items():
        pf, pv = set(), set()
        for r in rs:
            b = r['basic_info']
            for raw, tgt in ((b.get('full_name'), pf), (b.get('version'), pv)):
                s = str(raw or '')
                tgt |= set(DEC_IN_TEXT.findall(s))
                tgt |= {f'{a}.{b_}' for a, b_ in UND_DEC.findall(s)}
        pool_by_fam[f] = (pf, pv)

    # 亲缘继承（父子双向，仅严格 token 边界扩展关系）：G = F + '-' + ...
    # 同一模型的截断写法共享同一份点号证据，避免「父改子未改」的风格分裂
    kin_fn, kin_ver = collections.defaultdict(set), collections.defaultdict(set)
    fam_list = list(fams)
    for f in fam_list:
        for g in fam_list:
            if f == g:
                continue
            if g.startswith(f + '-') or f.startswith(g + '-'):
                pf, pv = pool_by_fam[g]
                kin_fn[f] |= pf
                kin_ver[f] |= pv

    changes, unsure, noevidence, excluded = {}, [], [], []
    for f, rs in fams.items():
        if not HAS_CHAIN.search(f):
            continue
        if f in EXCLUDE:
            excluded.append((f, EXCLUDE[f]))
            continue
        pf, pv = pool_by_fam[f]
        pool_all = pf | pv | kin_fn[f] | kin_ver[f]
        c, hits = dots_from_evidence(f, pool_all)
        if not c:
            if f in MANUAL:
                nf, why = MANUAL[f]
                changes[f] = (nf, 'manual', rs, why)
            else:
                noevidence.append((f, rs))
            continue
        if re.sub(r'[^a-z0-9]', '', c.lower()) != re.sub(r'[^a-z0-9]', '', f.lower()):
            unsure.append((f, [c], '骨架不一致（有信息损失）'))
            continue
        if f in MANUAL:
            nf, why = MANUAL[f]
            if nf != c:
                unsure.append((f, [c, nf], '自动推导与人工补录不一致'))
                continue
        tags = set()
        if all(h in pf for h in hits):
            tags.add('full_name')
        if all(h in pv for h in hits):
            tags.add('version')
        if all(h in (kin_fn[f] | kin_ver[f]) for h in hits) and not tags:
            tags.add('扩展继承')
        if not tags:
            tags.add('full_name')
        changes[f] = (c, '+'.join(sorted(tags)), rs, '')

    # ---------------- 预检：重命名后碰撞 ----------------
    existing = collections.Counter(r['model_id'] for r in recs)
    new_ids, collide = {}, []
    for f, (c, src, rs, _why) in changes.items():
        for r in rs:
            p, _, v = r['model_id'].split(':')
            nid = f'{p}:{c}:{v}'
            new_ids[r['model_id']] = nid
            if existing.get(nid, 0) > 0:
                collide.append((r['model_id'], nid))
    # family 组内撞名
    grp = collections.defaultdict(set)
    for f, (c, _s, rs, _why) in changes.items():
        p = rs[0]['model_id'].split(':')[0]
        grp[(p, c)].add(f)
    for k, v in grp.items():
        if len(v) > 1:
            collide.append((sorted(v), k))

    n_rec = sum(len(v[2]) for v in changes.values())
    print('=== D42 点号归一 ===')
    print(f'记录总数            : {len(recs)}')
    print(f'含「数字-数字」family: {len([f for f in fams if HAS_CHAIN.search(f)])}')
    print(f'判定需改 family      : {len(changes)}')
    print(f'判定需改记录         : {n_rec}')
    print(f'证据来源             : ' + ', '.join(
        f'{k}={sum(1 for v in changes.values() if v[1] == k)}'
        for k in ('full_name', 'version', 'full_name+version', '扩展继承', 'manual')))
    print(f'无小数证据(不改)     : {len(noevidence)} family')
    print(f'存疑(不改)           : {len(unsure)} family')
    print(f'显式排除             : {len(excluded)} family')
    print(f'重命名碰撞           : {len(collide)}')
    print()
    if collide:
        for a, b in collide:
            print(f'  !! {a} -> {b}')
        print('存在碰撞，中止。')
        return 1

    print('--- A. 变更表 ---')
    for f in sorted(changes):
        c, src, rs, why = changes[f]
        tail = f'  << {why}' if why else ''
        print(f'  {f:44s} -> {c:44s} [{src}] n={len(rs)}{tail}')

    if unsure:
        print()
        print('--- B. 存疑（未改）---')
        for f, cands, why in unsure:
            print(f'  {f:46s} 候选={cands} ({why})')

    print()
    print(f'--- C. 无小数证据、保持连字符（{len(noevidence)} family）---')
    for f, rs in sorted(noevidence):
        print(f'  {f:46s} full={str(rs[0]["basic_info"].get("full_name"))[:44]}')

    if excluded:
        print()
        print('--- D. 显式排除（另行上报）---')
        for f, why in sorted(excluded):
            print(f'  {f:46s} {why}')

    # 亲缘一致性诊断：已改的 family F，其「扩展名」family G=F-* 若未改，二者风格会不一致
    print()
    print('--- E. 亲缘一致性诊断（父已改、子未改）---')
    n_incons = 0
    for f, (c, _src, _rs, _why) in sorted(changes.items()):
        for g in fams:
            if g.startswith(f + '-') and g not in changes and HAS_CHAIN.search(g):
                print(f'  {f} -> {c}   但扩展 {g} 未改')
                n_incons += 1
    print(f'  不一致对数: {n_incons}')

    if not apply:
        print()
        print('[dry-run] 未写入。加 --apply 执行。')
        return 0

    # ---------------- 应用 ----------------
    out, touched = [], 0
    for r in recs:
        mid = r['model_id']
        if mid in new_ids:
            nid = new_ids[mid]
            r['model_id'] = nid
            r['meta']['notes'] = (r['meta'].get('notes') or '') + \
                f'；【D42 点号归一】原 model_id: {mid} → {nid}'
            touched += 1
        out.append(r)
    assert touched == n_rec, (touched, n_rec)
    with open(SRC, 'w', encoding='utf-8', newline='\n') as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'\n已写入 {touched} 条记录。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
