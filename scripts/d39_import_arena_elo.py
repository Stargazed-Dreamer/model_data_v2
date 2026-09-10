# -*- coding: utf-8 -*-
"""D39 · 把 DataLearner/arena 最新快照（2026-09-02）导入主库 arena_elo。

规则（保守版）：
  * 变体归属：主库无 thinking 标记 -> 只取榜单「无变体标记」条目；
              主库含 thinking/think/reasoning -> 优先 thinking/high/xhigh 条目，回退无标记。
  * 同名冲突（同一类别下有多条无标记同名条目）-> 跳过，交人工。
  * 幂等：已存在同 sub_benchmark + date 的条目则跳过。
  * 追加而非覆盖（沿用库内已有先例：同 sub_benchmark 保留多快照）。

用法: python d39_arena_import.py [--apply]   缺省 dry-run
"""
import json, re, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'temp', 'd39_arena_raw.json')
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')

SNAPSHOT = '2026-09-02'
SIZE_SUFFIX = re.compile(r'(?:-|_)?\d{2,3}k$')
IDX_SUFFIX = re.compile(r'(?:-|_)(?:base|instruct|it|chat|preview)$')
THINK_HINT = re.compile(r'thinking|think|reasoning|(?:^|[-_])o[13](?:$|[-_])')

CAT_URL = {
    'text':   'https://www.datalearner.com/leaderboards/external/text-generation',
    'coding': 'https://www.datalearner.com/leaderboards/external/text-generation-coding',
    'math':   'https://www.datalearner.com/leaderboards/external/text-generation-math',
}
SUB_PRIMARY = {'text': True, 'coding': False, 'math': False}
SOURCE_TYPE = 'LMArena 镜像（DataLearner），原始来源 LM Arena'


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def strip_variant(s):
    return re.sub(r'\s*[\(（][^)）]*[\)）]\s*', ' ', s or '').strip()


def variant_tag(s):
    m = re.search(r'[\(（]([^)）]*)[\)）]', s or '')
    return m.group(1).strip().lower() if m else ''


def is_think_variant(tag):
    return bool(re.search(r'think|reason|high|xhigh|max', tag or ''))


def is_nonthink_variant(tag):
    return bool(re.search(r'non-?\s*think|none|no-?think|chat|instant', tag or ''))


def keys_of_main(r):
    b = r.get('basic_info') or {}
    full = b.get('full_name') or ''
    mid = r.get('model_id') or ''
    seg = mid.split(':')[1] if ':' in mid else mid
    ks = []
    for raw in (full, seg):
        if not raw:
            continue
        n = norm(strip_variant(raw))
        for cand in (n, IDX_SUFFIX.sub('', n), SIZE_SUFFIX.sub('', IDX_SUFFIX.sub('', n))):
            if cand and cand not in ks:
                ks.append(cand)
    return ks


def parse_ci(ci):
    if not ci:
        return None
    m = re.search(r'([\d.]+)', str(ci))
    return float(m.group(1)) if m else None


def main():
    apply = '--apply' in sys.argv
    raw = json.load(open(RAW, encoding='utf-8'))
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]

    # 榜单索引 -> norm(code/name) -> [row]
    idx = {'code': collections.defaultdict(list), 'name': collections.defaultdict(list)}
    for cat, blk in raw.items():
        for x in blk['rows']:
            x['_cat'] = cat
            if x.get('modelCode'):
                idx['code'][norm(x['modelCode'])].append(x)
            if x.get('modelName'):
                idx['name'][norm(strip_variant(x['modelName']))].append(x)

    plan, conflicts, stats = [], [], collections.Counter()
    for r in rows:
        mid = r.get('model_id') or ''
        seg = mid.split(':')[1] if ':' in mid else mid
        main_think = bool(THINK_HINT.search(seg))
        ks = keys_of_main(r)

        hits, how = [], None
        for m in ('code', 'name'):
            for k in ks:
                if k in idx[m]:
                    hits = idx[m][k]
                    how = m
                    break
            if hits:
                break
        if not hits:
            continue

        # 按类别归组
        by_cat = collections.defaultdict(list)
        for x in hits:
            by_cat[x['_cat']].append(x)

        for cat, lst in by_cat.items():
            uniq = {id(x): x for x in lst}
            lst = list(uniq.values())
            # 变体筛选
            pool = [x for x in lst if (is_think_variant(variant_tag(x['modelName'])) if main_think
                                       else not variant_tag(x['modelName']) and not is_think_variant(variant_tag(x['modelName'])))]
            if not pool:
                continue
            names = {strip_variant(x['modelName']) for x in pool}
            if len(names) > 1:
                conflicts.append((mid, cat, sorted(names)))
                stats['冲突跳过'] += 1
                continue
            pick = max(pool, key=lambda x: x.get('votes') or 0)
            plan.append((r, cat, pick, how, main_think))

    # ---- 保守过滤 A：同类别下同名条目 > 1（榜单自身重名，无法确定对应哪条）----
    name_count = collections.Counter()
    for cat, blk in raw.items():
        for x in blk['rows']:
            if not variant_tag(x['modelName']):
                name_count[(cat, strip_variant(x['modelName']))] += 1
    plan2 = []
    for r, cat, pick, how, mt in plan:
        if name_count[(cat, strip_variant(pick['modelName']))] > 1:
            stats['榜单重名跳过'] += 1
            continue
        plan2.append((r, cat, pick, how, mt))

    # ---- 保守过滤 B：同一榜单条目被多个主库记录引用 ----
    # 仅允许「同模型不同上下文尺寸」共享（如 -32k / -64k）；真实版本差异（0324 / base）一律跳过。
    def id_key(mid):
        parts = (mid or '').split(':')
        return ':'.join(parts[1:]) if len(parts) > 1 else mid

    def no_size(k):
        return ':'.join(SIZE_SUFFIX.sub('', IDX_SUFFIX.sub('', p)) for p in (k or '').split(':'))

    use = collections.defaultdict(set)
    for r, cat, pick, how, mt in plan2:
        use[(cat, pick['modelName'])].add(r.get('model_id'))
    plan3 = []
    shared = collections.defaultdict(list)
    for r, cat, pick, how, mt in plan2:
        mids = use[(cat, pick['modelName'])]
        if len(mids) > 1:
            keys = {no_size(id_key(m)) for m in mids}
            if len(keys) == 1:
                stats['仅上下文差异-允许共享'] += 1
                plan3.append((r, cat, pick, how, mt))
                continue
            shared[(cat, pick['modelName'])] = sorted(mids)
            stats['版本差异跳过'] += 1
            continue
        plan3.append((r, cat, pick, how, mt))
    plan = plan3

    # 幂等 + 已有快照检查
    final = []
    for r, cat, pick, how, main_think in plan:
        es = (r.get('benchmarks') or {}).get('arena_elo') or []
        if any(e.get('sub_benchmark') == cat and (e.get('date') or '') == SNAPSHOT for e in es):
            stats['已有同快照跳过'] += 1
            continue
        final.append((r, cat, pick, how, main_think))

    print(f'候选可补条目: {len(plan)}  -> 实际写入: {len(final)}')
    print(f'跳过统计: {dict(stats)}')
    new_models = {id(r) for r, _, _, _, _ in final}
    print(f'涉及模型记录数: {len(new_models)}')
    fresh = [r for r, _, _, _, _ in final if not (r.get('benchmarks') or {}).get('arena_elo')]
    print(f'其中当前完全无 arena 的记录: {len({id(x) for x in fresh})}')
    print()
    print('--- 预览 12 条 ---')
    for r, cat, pick, how, mt in final[:12]:
        print(f'  {(r.get("model_id") or "")[:40]:42s} [{cat:6s}] <- {pick["modelName"][:34]:36s} elo={pick["score"]} rank={pick["rank"]} votes={pick.get("votes")} ({how}, think={mt})')
    if conflicts:
        print()
        print(f'--- 同名冲突（跳过，需人工）{len(conflicts)} ---')
        for mid, cat, names in conflicts[:15]:
            print(f'  {mid[:40]:42s} [{cat}] -> {names}')
    if shared:
        print()
        print(f'--- 多条主库记录共用同一榜单条目（跳过，需人工）{len(shared)} 组 ---')
        for (cat, name), mids in sorted(shared.items(), key=lambda kv: -len(kv[1]))[:20]:
            print(f'  [{cat}] {name}  <- {len(mids)} 条: ' + ', '.join(m[:38] for m in mids[:5]))

    if not apply:
        print()
        print('[dry-run] 未写入。加 --apply 生效。')
        return

    # 写入
    n = 0
    for r, cat, pick, how, main_think in final:
        bm = r.setdefault('benchmarks', {})
        es = bm.setdefault('arena_elo', [])
        es.append({
            'sub_benchmark': cat,
            'score': float(pick['score']),
            'date': SNAPSHOT,
            'source_url': CAT_URL[cat],
            'source_type': SOURCE_TYPE,
            'confidence': 'T1',
            'is_primary': SUB_PRIMARY[cat],
            'rank': pick.get('rank'),
            'votes': pick.get('votes'),
            'ci_95': parse_ci(pick.get('ci')),
            'notes': (f'Arena Elo 原始分（Bradley-Terry），快照 {SNAPSHOT}（DataLearner 镜像 LM Arena，'
                      f'其标注 versionTime={SNAPSHOT}）；榜单内排名第 {pick.get("rank")} / 该类别共 '
                      f'{len(raw[cat]["rows"])} 条；变体口径：主库{"thinking" if main_think else "默认"}模式'
                      f'，取榜单{"带 thinking/high 标记" if main_think else "无变体标记"}条目；'
                      f'来源为第三方镜像，非一手 arena.ai（arena.ai 本机不可达）'),
        })
        n += 1
    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n')
    print(f'[apply] 写入 arena 条目 {n} 条')


if __name__ == '__main__':
    main()
