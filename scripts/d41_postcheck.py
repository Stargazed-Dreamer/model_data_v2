# -*- coding: utf-8 -*-
"""D41 收尾自检（可复用）：命名归一后的六项核验。

覆盖：
  1. basic_info.vendor 首字母大写一致性（允许品牌自身写法白名单）
  2. model_id 前缀全小写 slug
  3. 无 qwen3-* family 残留
  4. arena sub_benchmark 全在标准段位内
  5. 无重复 model_id / 三段式完整
  6. 对指定备份做数组缩水取证（可选）

用法：
  python scripts/d41_postcheck.py                 # 用最新 pre-d41-normalize 备份做缩水取证
  python scripts/d41_postcheck.py --pre <备份路径>
"""
import collections
import glob
import json
import sys

SRC = 'model_data_v2.jsonl'
# 品牌自身写法即含小写首字母（用户 D41 选「保留品牌惯用写法」）
ALLOW_LOWER = {'xAI', 'iFlytek', '01.AI', '4Paradigm', 'e-INFRA', 'iPhone'}
MAIN_SUB = {'text', 'coding', 'math', 'vision', 'webdev'}


def main():
    pre = None
    if '--pre' in sys.argv:
        pre = sys.argv[sys.argv.index('--pre') + 1]
    else:
        c = sorted(glob.glob('backups/model_data_v2.pre-d41-normalize-*.jsonl'))
        pre = c[-1] if c else None

    recs = [json.loads(l) for l in open(SRC, encoding='utf-8') if l.strip()]
    ok = True

    # 1 vendor
    v = collections.Counter(str(r['basic_info'].get('vendor') or '') for r in recs)
    bad = sorted(k for k in v if k and k[0].islower() and k not in ALLOW_LOWER)
    print(f"[1] vendor 首字母小写残留: {bad if bad else '无'}")
    ok &= not bad

    # 2 前缀
    p = collections.Counter(r['model_id'].split(':')[0] for r in recs)
    up = sorted(k for k in p if k and not k[0].islower() and not k[0].isdigit())
    print(f"[2] model_id 前缀非小写 slug: {up if up else '无'}")
    ok &= not up

    # 3 qwen3
    q = [r['model_id'] for r in recs if r['model_id'].split(':')[1].startswith('qwen3')]
    print(f"[3] qwen3-* family 残留: {q if q else '无'}")
    ok &= not q

    # 4 arena
    odd = [(r['model_id'], e.get('sub_benchmark')) for r in recs
           for e in (r['benchmarks'].get('arena_elo') or []) if e.get('sub_benchmark') not in MAIN_SUB]
    print(f"[4] arena 非标准段位: {odd if odd else '无'}")
    ok &= not odd

    # 5 撞键
    mids = [r['model_id'] for r in recs]
    dup = [k for k, c in collections.Counter(mids).items() if c > 1]
    bad3 = [m for m in mids if m.count(':') != 2]
    print(f"[5] 重复 model_id: {dup if dup else '无'} | 非三段式: {bad3 if bad3 else '无'}")
    ok &= not dup and not bad3

    # 6 缩水
    if pre:
        old = {json.loads(l)['model_id']: json.loads(l) for l in open(pre, encoding='utf-8') if l.strip()}
        shrink = 0
        for r in recs:
            n = r['meta'].get('notes') or ''
            if '【D41 命名归一】原 model_id: ' in n:
                seg = n.split('【D41 命名归一】原 model_id: ')[-1].split('（')[0]
                o = old.get(seg.split('→')[0])
                if o:
                    for f in ('self_reported', 'independent', 'arena_elo'):
                        a = len(o['benchmarks'].get(f) or [])
                        b = len(r['benchmarks'].get(f) or [])
                        if b < a:
                            shrink += 1
                            print(f'    !! 缩水 {seg} {f} {a}->{b}')
        print(f"[6] 数组缩水（对照 {pre}）: {shrink}")
        ok &= shrink == 0
    else:
        print('[6] 跳过缩水取证（无备份）')

    print()
    print('自检结果:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
