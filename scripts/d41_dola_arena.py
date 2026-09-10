# -*- coding: utf-8 -*-
"""D41 附加修正：bytedance:dola-seed-2-0-pro:base 的 arena 数据结构化落地。

背景：D40 采集 agent 把 DataLearner 镜像的三榜 Elo 只写进了 meta.notes 散文，
benchmarks.arena_elo 实为空数组（D40 报告 §七.2 描述为「仅 arena 数据」不准确）。
用户 D41 裁定「保留」该模型，故按其描述把已有的权威值结构化落地。

权威来源：DataLearner 镜像 LM Arena，快照 versionTime=2026-09-02
  text   rank 59  score 1456.0  ci ±3   votes 74,277
  coding rank 43  score 1513.0  ci ±6   votes 20,711
  math   rank 66  score 1451.0  ci ±10  votes  4,083
（与采集时写入 notes 的 1456/1513/1451 逐项一致，已核对 temp/dl_pg_{text,coding,math}.html）
"""
import json
import os
import sys

SRC = 'model_data_v2.jsonl'
MID = 'bytedance:dola-seed-2-0-pro:base'
SNAP = '2026-09-02'
BASE = 'https://www.datalearner.com/leaderboards/external/'
ST = 'LMArena 镜像（DataLearner），原始来源 LM Arena'

DATA = [
    ('text', 1456.0, 59, 74277, 3.0, True, 'text-generation'),
    ('coding', 1513.0, 43, 20711, 6.0, False, 'text-generation-coding'),
    ('math', 1451.0, 66, 4083, 10.0, False, 'text-generation-math'),
]


def main():
    apply = '--apply' in sys.argv
    recs = [json.loads(l) for l in open(SRC, encoding='utf-8') if l.strip()]
    hit = 0
    for r in recs:
        if r['model_id'] != MID:
            continue
        hit += 1
        if r['benchmarks'].get('arena_elo'):
            print('!! arena_elo 非空，跳过以免覆盖：', json.dumps(r['benchmarks']['arena_elo'], ensure_ascii=False))
            continue
        arr = []
        for sub, score, rank, votes, ci, prim, slug in DATA:
            arr.append({
                'sub_benchmark': sub,
                'score': score,
                'date': SNAP,
                'source_url': BASE + slug,
                'source_type': ST,
                'confidence': 'T1',
                'is_primary': prim,
                'rank': rank,
                'votes': votes,
                'ci_95': ci,
                'notes': ('Arena Elo 原始分（Bradley-Terry），快照 %s（DataLearner 镜像 LM Arena，'
                          '其标注 versionTime=%s）；榜单内排名第 %d；'
                          '【D41 结构化补录】D40 采集时该三榜分值仅写入 meta.notes 散文，'
                          'benchmarks.arena_elo 为空数组，本轮按同一快照结构化落地；'
                          '来源为第三方镜像，非一手 arena.ai（arena.ai 本机不可达）'
                          % (SNAP, SNAP, rank)),
            })
        r['benchmarks']['arena_elo'] = arr
        tag = ('【D41 结构化补录】原采集仅将 DataLearner 镜像三榜 Elo（text 1456 / coding 1513 / math 1451）'
               '写入本字段散文，benchmarks.arena_elo 为空；按用户裁定「保留」后，'
               '依同一快照（versionTotal=2026-09-02）结构化落地 3 条。')
        r['meta']['notes'] = (r['meta'].get('notes') + '；' + tag) if r['meta'].get('notes') else tag
        print('已生成 arena 条目：')
        print(json.dumps(arr, ensure_ascii=False, indent=1))
    print('命中记录:', hit)

    if not apply:
        print('[DRY-RUN] 未写盘')
        return
    import time
    bak = 'backups/model_data_v2.pre-d41-dola-{}.jsonl'.format(time.strftime('%Y%m%d-%H%M%S'))
    with open(SRC, encoding='utf-8') as f, open(bak, 'w', encoding='utf-8', newline='\n') as g:
        g.write(f.read())
    with open(SRC, 'w', encoding='utf-8', newline='\n') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('[APPLIED] 备份', bak)


if __name__ == '__main__':
    main()
