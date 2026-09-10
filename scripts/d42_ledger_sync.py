"""D42：台账 model_id 同步。

`models` 数组随新 model_id 更新（活标识）；`submitted_files` 保持历史文件名不改写。
映射来源：model_data_v2.jsonl 中 D42 的改名留痕。
"""
import json
import re
import sys

SRC = 'model_data_v2.jsonl'
LEDGER = 'docs/batch_claim_ledger.jsonl'
PAT = re.compile(r'【D42 点号归一】原 model_id: (\S+?) → (\S+?)(?:；|$)')


def main():
    apply = '--apply' in sys.argv
    mapping = {}
    for l in open(SRC, encoding='utf-8'):
        if not l.strip():
            continue
        r = json.loads(l)
        m = PAT.search(r['meta'].get('notes') or '')
        if m:
            mapping[m.group(1)] = m.group(2)
    print(f'改名映射: {len(mapping)} 条')
    assert len(set(mapping.values())) == len(mapping), '映射目标不唯一'

    lines = [l for l in open(LEDGER, encoding='utf-8').read().split('\n') if l.strip()]
    hits, out = 0, []
    for l in lines:
        o = json.loads(l)
        ms = o.get('models') or []
        new_ms = [mapping.get(m, m) for m in ms]
        if new_ms != ms:
            changed = [(a, b) for a, b in zip(ms, new_ms) if a != b]
            hits += len(changed)
            print(f"  {o.get('batch_id')}: " + ', '.join(f'{a}->{b}' for a, b in changed))
            o['models'] = new_ms
        out.append(json.dumps(o, ensure_ascii=False))

    print(f'台账 models 字段改写: {hits} 处')
    if not apply:
        print('[dry-run] 未写入。加 --apply 执行。')
        return 0
    with open(LEDGER, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')
    print('已写入。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
