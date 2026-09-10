"""D42 收尾自检：验证点号归一「只动小数点、不动其他字符」，并核对无副作用。

用法：python scripts/d42_postcheck.py
"""
import json
import re
import glob
import collections
import sys

SRC = 'model_data_v2.jsonl'


def load(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def main():
    pre_p = sorted(glob.glob('backups/model_data_v2.pre-d42-dots-*.jsonl'))[-1]
    old = {r['model_id']: r for r in load(pre_p)}
    cur = load(SRC)
    fails = []

    print(f'对照备份: {pre_p}')
    print(f'记录数: 前 {len(old)} -> 后 {len(cur)}')
    print()

    # 1. model_id 唯一
    c = collections.Counter(r['model_id'] for r in cur)
    dup = [k for k, v in c.items() if v > 1]
    print(f'1. model_id 唯一性           : {"PASS" if not dup else "FAIL " + str(dup)}')
    if dup:
        fails.append('dup model_id')

    # 2. 仅点号位发生变化（family 段：新名把 `.` 还原成 `-` 必须等于旧名）
    changed, bad = 0, []
    for r in cur:
        nid = r['model_id']
        note = r['meta'].get('notes') or ''
        m = re.search(r'【D42 点号归一】原 model_id: (\S+?) → (\S+?)(?:；|$)', note)
        if not m:
            continue
        changed += 1
        oid = m.group(1)
        if m.group(2) != nid:
            bad.append((oid, nid, '留痕与现值不符'))
            continue
        ov, of, ovr = oid.split(':')
        nv, nf, nvr = nid.split(':')
        if ov != nv or ovr != nvr:
            bad.append((oid, nid, 'vendor / variant 段被改动'))
            continue
        if nf.replace('.', '-') != of or '.' not in nf:
            bad.append((oid, nid, 'family 变化不是 `-`→`.`'))
    print(f'2. 仅点号位变化（{changed} 条）   : {"PASS" if not bad else "FAIL"}')
    for x in bad[:10]:
        print('     ', x)
    if bad:
        fails.append('illegal char change')

    # 3. 数组缩水取证
    shrink = 0
    for r in cur:
        note = r['meta'].get('notes') or ''
        m = re.search(r'【D42 点号归一】原 model_id: (\S+?) →', note)
        if not m:
            continue
        o = old.get(m.group(1))
        if not o:
            continue
        for f in ('self_reported', 'independent', 'arena_elo'):
            if len(r['benchmarks'].get(f) or []) < len(o['benchmarks'].get(f) or []):
                shrink += 1
                print(f'     缩水 {m.group(1)} {f}')
    print(f'3. 数组缩水                  : {"PASS" if shrink == 0 else "FAIL"}')
    if shrink:
        fails.append('array shrink')

    # 4. 记录数不变、非 model_id 字段不变
    print(f'4. 记录数与字段             : {"PASS" if len(old) == len(cur) else "FAIL"}')
    if len(old) != len(cur):
        fails.append('record count')

    # 5. 点号规范抽查：family 中不应再有「数字-数字」且能被 `a.b` 证据证伪的残留
    #    （显式排除项另行上报，不计为失败）
    EXCLUDED = {'s1-1'}
    resid, excl = [], []
    ev = collections.defaultdict(set)
    for r in cur:
        b = r['basic_info']
        fam = r['model_id'].split(':')[1]
        for s in (str(b.get('full_name') or ''), str(b.get('version') or '')):
            ev[fam] |= set(re.findall(r'(?=(\d+\.\d+))', s))
    for r in cur:
        fam = r['model_id'].split(':')[1]
        for m in re.finditer(r'(?<!\d)(\d+)-(\d+)(?!\d)', fam):
            if f'{m.group(1)}.{m.group(2)}' in ev[fam]:
                (excl if fam in EXCLUDED else resid).append((r['model_id'], f'{m.group(1)}.{m.group(2)}'))
    print(f'5. 可证伪的连字符残留        : {"PASS" if not resid else "FAIL"} ({len(resid)})')
    for x in resid[:10]:
        print('     ', x)
    if resid:
        fails.append('residual')
    for x in excl:
        print(f'     [已排除·另行上报] {x[0]} 证据 {x[1]}')

    print()
    print('结论:', 'ALL PASS' if not fails else f'FAIL -> {fails}')
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
