# -*- coding: utf-8 -*-
"""D41 台账同步：models 数组中的 model_id 按 D41 归一规则改写。

- qwen3-* family → qwen-3-*（Qwen 3 世代统一连字符式）
- unknown:yue-ai:base → ireader-technology:yue-ai:base（vendor 段语义错误修正）
- submitted_files 保持原样（历史提交物文件名，不改写历史）

用法：python temp/d41_ledger_sync.py [--apply]
"""
import json
import sys

P = 'docs/batch_claim_ledger.jsonl'


def fixmid(m):
    if not isinstance(m, str) or m.count(':') != 2:
        return m
    p, fam, var = m.split(':')
    if fam.startswith('qwen3'):
        fam = 'qwen-3' + fam[len('qwen3'):]
    if m == 'unknown:yue-ai:base':
        p = 'ireader-technology'
    return f'{p}:{fam}:{var}'


def main():
    apply = '--apply' in sys.argv
    out = []
    n = 0
    for line in open(P, encoding='utf-8'):
        if not line.strip():
            continue
        o = json.loads(line)
        ms = o.get('models') or []
        new = [fixmid(m) for m in ms]
        if new != ms:
            n += 1
            print(f'  {o.get("batch_id")}:')
            for a, b in zip(ms, new):
                if a != b:
                    print(f'      {a}  ->  {b}')
            o['models'] = new
        out.append(o)
    print(f'受影响批次: {n}')
    if not apply:
        print('[DRY-RUN] 未写盘')
        return
    with open(P, 'w', encoding='utf-8', newline='\n') as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + '\n')
    print('[APPLIED]', P)


if __name__ == '__main__':
    main()
