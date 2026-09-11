# -*- coding: utf-8 -*-
"""
D43 结构改名 + zhipu vendor 合并（用户拍板 2026-09-11）
  1. s1 家族 → 版本+参数式：s1-1→s1.1-1.5b, s1-32b→s1.1-32b（s1 保持）
  2. olmo-3-32b-instruct → olmo-3.1-32b-instruct（官方名 Olmo 3.1 Instruct 32B）
  3. luxia-21-4b-alignment → luxia-2.1-4b-alignment（full_name 明写 2.1）
  4. minicpm 对齐官方名：minicpm-1-2b→minicpm-1b, minicpm-2-4b→minicpm-2b
  5. z-ai-zhipu-ai-tsinghua-university → zhipu（3 条 vendor 改挂；glm-4.5/glm-4.6 重复档案合并入 zhipu 侧主档）

用法: python d43_struct_fix.py           # dry-run
      python d43_struct_fix.py --apply
"""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
PATH = 'model_data_v2.jsonl'

RENAMES = {
    'allen-institute-for-ai:s1-1:base': (
        'allen-institute-for-ai:s1.1-1.5b:base', 'family 改版本+参数式（full_name=s1.1-1.5B）'),
    'allen-institute-for-ai:s1-32b:base': (
        'allen-institute-for-ai:s1.1-32b:base', 'family 改版本+参数式（full_name=s1.1-32B）'),
    'allen-institute-for-ai:olmo-3-32b-instruct:base': (
        'allen-institute-for-ai:olmo-3.1-32b-instruct:base', '官方发布名 Olmo 3.1 Instruct 32B（HF allenai/Olmo-3.1-32B-Instruct）'),
    'saltlux:luxia-21-4b-alignment:base': (
        'saltlux:luxia-2.1-4b-alignment:base', '官方名 Luxia 2.1 4B Alignment，21 系 2.1 缺小数点'),
    'modelbest:minicpm-1-2b:base': (
        'modelbest:minicpm-1b:base', 'family 对齐官方名 MiniCPM-1B（精确参数 1.2B 见 architecture.total_params_b）'),
    'modelbest:minicpm-2-4b:base': (
        'modelbest:minicpm-2b:base', 'family 对齐官方名 MiniCPM-2B（精确参数 2.7B/非嵌入 2.4B 见 architecture）'),
    'z-ai-zhipu-ai-tsinghua-university:glm-4-32b:0414': (
        'zhipu:glm-4-32b:0414', 'vendor 别名归并（用户拍板统一为 zhipu）'),
}
# (吸收档案, 主档) —— 主档保留，吸收档字段并入后删除
MERGES = [
    ('z-ai-zhipu-ai-tsinghua-university:glm-4.5:base', 'zhipu:glm-4.5:base'),
    ('z-ai-zhipu-ai-tsinghua-university:glm-4.6:base', 'zhipu:glm-4.6:base'),
]
# 主档这些键不允许被吸收档覆盖（即便主档为 null）
KEEP_TARGET_KEYS = {'model_id', 'full_name', 'vendor', 'schema_version', 'collected_at'}


def load():
    recs = []
    for line in open(PATH, encoding='utf-8'):
        line = line.strip()
        if line:
            recs.append(json.loads(line))
    return recs


def fill_none(target, source, path=''):
    """target 为 null/缺失处用 source 补，返回补值清单。"""
    filled = []
    if isinstance(target, dict) and isinstance(source, dict):
        for k, sv in source.items():
            if k in KEEP_TARGET_KEYS:
                continue
            if k not in target or target[k] is None:
                if sv is not None:
                    target[k] = sv
                    filled.append(path + '/' + k)
            elif isinstance(sv, (dict,)) and isinstance(target[k], dict):
                filled += fill_none(target[k], sv, path + '/' + k)
    return filled


def merge_benchmarks(tgt_recs, src_recs, group):
    """按 benchmark 名并入；同名且分值同→跳过；同名分值异→保留主档并回报冲突。"""
    idx = {b.get('benchmark'): (i, b) for i, b in enumerate(tgt_recs)}
    added, conflicts = [], []
    for b in src_recs:
        name = b.get('benchmark')
        if not name:
            continue
        if name in idx:
            i, tb = idx[name]
            if b.get('score') is not None and tb.get('score') is not None and b['score'] != tb['score']:
                conflicts.append(f'{group}/{name}: 主档 {tb["score"]} vs 吸收档 {b["score"]}（保留主档）')
            continue
        nb = json.loads(json.dumps(b, ensure_ascii=False))
        note = (nb.get('notes') or '')
        tag = '【D43 合并】并入自 z-ai-zhipu-ai-tsinghua-university 档案'
        nb['notes'] = (note + '；' + tag) if note else tag
        tgt_recs.append(nb)
        added.append(f'{group}/{name}')
    return added, conflicts


def merge_record(src, tgt):
    filled = fill_none(tgt, src)
    added, conflicts = [], []
    for group in ('self_reported', 'independent', 'arena_elo'):
        tb = tgt.setdefault('benchmarks', {}).setdefault(group, []) or []
        sb = (src.get('benchmarks') or {}).get(group) or []
        a, c = merge_benchmarks(tb, sb, group)
        added += a
        conflicts += c
    urls = tgt.setdefault('meta', {}).setdefault('source_urls', []) or []
    for u in (src.get('meta') or {}).get('source_urls') or []:
        if u not in urls:
            urls.append(u)
    note = (f'【D43 合并】吸收档案 z-ai-zhipu-ai-tsinghua-university（vendor 别名归并，用户拍板 2026-09-11）。'
            f'本档为主档（benchmark 条目含 config/date 更完整）；吸收档独有 benchmark {len(added)} 项并入'
            f'（各条 notes 已标注）、null 字段补值 {len(filled)} 处、source_urls 并集。')
    if conflicts:
        note += ' 标量/benchmark 冲突（保留主档值）：' + '；'.join(conflicts)
    tgt.setdefault('meta', {})
    tgt['meta']['notes'] = ((tgt['meta'].get('notes') or '') + '；' + note)
    return filled, added, conflicts


def main(apply):
    recs = load()
    by_id = {r['model_id']: r for r in recs}
    src_ids = set(RENAMES) | {s for s, _ in MERGES}
    dst_ids = {d for d, _ in RENAMES.values()} | {t for _, t in MERGES}
    # 碰撞预检
    dups = [d for d in dst_ids if d in by_id and d not in
            ({t for _, t in MERGES})]
    assert not dups, f'目标 id 已存在: {dups}'

    missing = [i for i in src_ids if i not in by_id]
    assert not missing, f'源 id 不存在: {missing}'

    print(f'改前记录数: {len(recs)}')
    for old, (new, why) in RENAMES.items():
        r = by_id[old]
        note = f'【D43 结构改名】原 model_id: {old} → {new}（{why}）'
        r['meta']['notes'] = ((r['meta'].get('notes') or '') + '；' + note)
        r['model_id'] = new
        print(f'  改名 {old} -> {new}')
    for src_id, tgt_id in MERGES:
        filled, added, conflicts = merge_record(by_id[src_id], by_id[tgt_id])
        print(f'  合并 {src_id} -> {tgt_id}: 补值{len(filled)} 并入benchmark{len(added)} 冲突{len(conflicts)}')
        for c in conflicts:
            print(f'    [冲突] {c}')
        recs.remove(by_id[src_id])
    print(f'改后记录数: {len(recs)}')

    ids = [r['model_id'] for r in recs]
    assert len(ids) == len(set(ids)), 'model_id 出现重复!'
    assert len(recs) == 935, f'记录数应为 935，实际 {len(recs)}'

    if apply:
        with open(PATH, 'w', encoding='utf-8', newline='\n') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print('已写盘。')
    else:
        print('（dry-run，未写盘）')


if __name__ == '__main__':
    main('--apply' in sys.argv)
