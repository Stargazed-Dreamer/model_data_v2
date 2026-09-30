# -*- coding: utf-8 -*-
"""榜单全量反推漏采（S0-b，常规工具，2026-10-01 D52 立规）。

作用：把榜单快照逐条回查主库，捞出「榜单有、主库无」的条目，分两档交付：
  * naming_diff —— 归一后与库内某条相似度 >= 0.72，疑似「库内已有但命名不同」
  * real_gap    —— 其余，疑似真漏采（**仍需人工复核**，见下）

为什么要它（不能只用差集式 S0）：`glm-5.3-max` 在 Arena 2026-09-11 快照就已单列独立 elo，
不属「新面孔」⇒ 差集式 S0 结构性漏掉，一路挂到 D52 才靠人工发现。D39 曾一次性用过此法
（挖出 84 条），但当时没写成常规步骤，后续几轮又退回差集式、缺陷重复出现。

⚠ 已知误判方向（两档都要人工复核，不能只看档位）：
  * 误报为漏采：归一后与库内互为**超集**关系时相似度会被压低（如榜单 `Opus 4.5` vs 库内
    `claude-opus-4.5-…`，norm 后 'opus45' ⊂ 'claudeopus45'，ratio 仅 0.667 未过 0.72 阈值）
  * 误报为命名差异：D39 曾把 `Claude Opus 5` 错配到 `claude-opus-4-5-…`

用法:
  python scripts/d39_fetch_arena_leaderboard.py        # 先抓最新快照 -> temp/d39_arena_raw.json
  PYTHONUTF8=1 python scripts/arena_gap_reverse.py [--raw <json>] [--out-dir temp/d<轮>]
"""
import argparse
import collections
import difflib
import importlib.util
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELPER = os.path.join(ROOT, 'scripts', 'd39_import_arena_elo.py')

# 匿名 / 实验代号：D39 教训，不可直接采
ANON = re.compile(r'experimental|preview-?anon|anon-|stealth|unnamed|codename', re.I)
# 老社区模型：未必符合本库「主流大模型」收录口径
LEGACY = re.compile(r'vicuna|alpaca|oasst|pythia|gpt4all|fastchat|koala|dolly|guanaco|'
                    r'stablelm-?(tuned|alpha|beta)|wizardlm|openhermes|openchat|'
                    r'starling-lm|nous-hermes|dolphin-|mpt-\d|zephyr-\d', re.I)


def load_helper():
    spec = importlib.util.spec_from_file_location('imp', HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'无法加载解析辅助模块: {HELPER}')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=os.path.join(ROOT, 'temp', 'd39_arena_raw.json'))
    ap.add_argument('--out-dir', default=os.path.join(ROOT, 'temp'))
    ap.add_argument('--main', default=os.path.join(ROOT, 'model_data_v2.jsonl'))
    a = ap.parse_args()

    imp = load_helper()
    raw = json.load(open(a.raw, encoding='utf-8'))
    rows = [json.loads(l) for l in open(a.main, encoding='utf-8') if l.strip()]

    idx = {'code': collections.defaultdict(list), 'name': collections.defaultdict(list)}
    snap = None
    for cat, blk in raw.items():
        snap = snap or blk.get('version_time')
        for x in blk['rows']:
            x['_cat'] = cat
            if x.get('modelCode'):
                idx['code'][imp.norm(x['modelCode'])].append(x)
            if x.get('modelName'):
                idx['name'][imp.norm(imp.strip_variant(x['modelName']))].append(x)

    main_names = {}
    for r in rows:
        b = r.get('basic_info') or {}
        mid = r.get('model_id') or ''
        for s in (b.get('full_name'), mid.split(':')[1] if ':' in mid else None):
            if s:
                main_names.setdefault(imp.norm(imp.strip_variant(s)), mid)
    main_keys = list(main_names.keys())

    hit = set()
    for r in rows:
        got = []
        for m in ('code', 'name'):
            for k in imp.keys_of_main(r):
                if k in idx[m]:
                    got = idx[m][k]
                    break
            if got:
                break
        for x in got:
            hit.add(id(x))

    best = {}
    for blk in raw.values():
        for x in blk['rows']:
            if id(x) in hit:
                continue
            base = imp.strip_variant(x['modelName'])
            k = imp.norm(base)
            if k not in best or (x.get('votes') or 0) > (best[k].get('votes') or 0):
                y = dict(x)
                y['_base'] = base
                best[k] = y

    real, naming = [], []
    for k, x in best.items():
        close = difflib.get_close_matches(k, main_keys, n=1, cutoff=0.72)
        by_cat = {}
        for cat, blk in raw.items():
            for y in blk['rows']:
                if imp.norm(imp.strip_variant(y['modelName'])) == k:
                    by_cat[cat] = {'rank': y.get('rank'), 'score': y.get('score'),
                                   'votes': y.get('votes'), 'thinkingMode': y.get('thinkingMode'),
                                   'modelCode': y.get('modelCode')}
        rec = {
            'name': x.get('_base'), 'vendor': x.get('organization'), 'license': x.get('license'),
            'thinkingMode': x.get('thinkingMode'), 'modelCode': x.get('modelCode'),
            'rank_text': (by_cat.get('text') or {}).get('rank'),
            'elo_text': (by_cat.get('text') or {}).get('score'),
            'categories': sorted(by_cat), 'by_cat': by_cat,
            'anon_or_exp': bool(ANON.search(x.get('_base') or '')),
            'legacy_community': bool(LEGACY.search(x.get('_base') or '')),
            'similar_in_db': main_names[close[0]] if close else None,
            'similar_score': round(difflib.SequenceMatcher(None, k, close[0]).ratio(), 3) if close else None,
        }
        (naming if close else real).append(rec)

    real.sort(key=lambda r: (r['rank_text'] or 9999))
    naming.sort(key=lambda r: (r['rank_text'] or 9999))

    print(f'快照 {snap}；主库 {len(rows)} 条')
    print(f'榜单未命中（按基础名聚合）: {len(best)}')
    print(f'  疑似命名差异: {len(naming)}')
    print(f'  ★ 疑似真漏采: {len(real)}'
          f'（匿名/实验 {sum(1 for r in real if r["anon_or_exp"])}'
          f' / 老社区 {sum(1 for r in real if r["legacy_community"])}'
          f' / 其余待核 {sum(1 for r in real if not r["anon_or_exp"] and not r["legacy_community"])}）')
    print()
    print('=== 疑似真漏采 TOP25（按 text 榜名次）===')
    for r in real[:25]:
        flag = ' [匿名/实验]' if r['anon_or_exp'] else (' [社区]' if r['legacy_community'] else '')
        print(f'  {str(r["rank_text"] or "-"):>4}  {r["name"][:40]:42s}'
              f' {str(r["vendor"])[:18]:20s} elo={r["elo_text"]}{flag}')

    os.makedirs(a.out_dir, exist_ok=True)
    p1 = os.path.join(a.out_dir, 'arena_gap_raw.json')
    p2 = os.path.join(a.out_dir, 'arena_gap_candidates.jsonl')
    with open(p1, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'snapshot': snap, 'real_gap': real, 'naming_diff': naming}, f,
                  ensure_ascii=False, indent=1)
    with open(p2, 'w', encoding='utf-8', newline='\n') as f:
        for r in real:
            f.write(json.dumps({
                'name': r['name'], 'vendor': r['vendor'], 'release_date': None, 'tier': 'T3',
                'evidence': 'https://www.datalearner.com/leaderboards/external/text-generation',
                'note': f"榜单全量反推（快照 {snap}）；text r{r['rank_text']} elo={r['elo_text']}；"
                        f"categories={r['categories']}；thinkingMode={r['thinkingMode']}；"
                        f"modelCode={r['modelCode']}；待 S1 核实是否模型/是否在收录口径内",
            }, ensure_ascii=False) + '\n')
    print()
    print('saved ->', os.path.relpath(p1, ROOT))
    print('saved ->', os.path.relpath(p2, ROOT))


if __name__ == '__main__':
    main()
