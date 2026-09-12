# -*- coding: utf-8 -*-
"""D47 · r1 同厂商同名三组拍板处置（D46 qa_outliers 扫出，用户拍板「1234都可」）。

组 A 合并：donor `alibaba:qwen2.5-coder:base` → keeper `alibaba:qwen2.5-coder-32b:base`
  两侧 full_name/tp/ctx/license 全同（真同物）；keeper 取 D43「版本+参数式」命名；
  donor 独有的 ap/version 补入 keeper，ind 数组并集去重，标量冲突（release_date
  2024-09 vs epoch 2024-11-12 待核）保留主档并留痕。
组 B 合并：donor `openbmb-open-lab-for-big-model-base:minicpm-4-8b:base` → keeper `modelbest:minicpm-4:base`
  full_name/release_date/tp 全同；keeper 取 D41 归并后的正规 vendor 侧（D43 先例）；
  硬冲突 license（MIT vs Apache）与 ctx（32K vs 128K）**保留主档值**，donor 值写入 notes
  待核（license 挂 LICENSE_GAP_BACKLOG 同款跟踪）。
组 C 改名不合并：`zhipu:glm-5.2-none:base` full_name → 「GLM-5.2（Non-Think）」
  两侧跑分表不同（D34 deepseek-v4-pro 同款：思考/非思考两档必须分行），仅消除同名。

主键变化：950 → 949（组 A/B 各 -1，组 C 0）。
用法：PYTHONUTF8=1 python scripts/d47_merge_r1.py [--apply]
"""
import json
import os
import shutil
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
TODAY = '2026-09-13'
BENCH_KEY = ('benchmark', 'config', 'date', 'source_site')


def bench_key(b):
    return tuple(b.get(k) for k in BENCH_KEY)


def main():
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]
    by_id = {r['model_id']: r for r in rows}
    donor_ids = []

    # ---- 组 A：qwen2.5-coder 合并 ----
    ka, da = by_id['alibaba:qwen2.5-coder-32b:base'], by_id['alibaba:qwen2.5-coder:base']
    for seg in ('independent', 'arena_elo', 'self_reported'):
        have = {bench_key(b) for b in (ka.get('benchmarks') or {}).get(seg) or []}
        for b in (da.get('benchmarks') or {}).get(seg) or []:
            if bench_key(b) not in have:
                ka.setdefault('benchmarks', {}).setdefault(seg, []).append(b)
                have.add(bench_key(b))
    ka.setdefault('architecture', {})
    for f in ('active_params_b', 'version'):
        tgt = ka['architecture'] if f == 'active_params_b' else ka.setdefault('basic_info', {})
        if tgt.get(f) is None:
            src = (da.get('architecture') or {} if f == 'active_params_b' else da.get('basic_info') or {})
            if src.get(f) is not None:
                tgt[f] = src[f]
    note_a = (f'【D47 r1 合并】吸收重复档案 alibaba:qwen2.5-coder:base（同 full_name/参数；'
              f'该侧 release_date=2024-11-12 取自 epoch Publication date 待核，主档保留 2024-09；'
              f'ind 数组并集 +{len(da.get("benchmarks", {}).get("independent") or [])} 条候选去重）。')
    ka.setdefault('basic_info', {})['notes'] = ((ka['basic_info'].get('notes') or '') + '；' if ka['basic_info'].get('notes') else '') + note_a
    for u in (da.get('meta') or {}).get('source_urls') or []:
        su = ka.setdefault('meta', {}).setdefault('source_urls', [])
        if u not in su:
            su.append(u)
    donor_ids.append('alibaba:qwen2.5-coder:base')

    # ---- 组 B：minicpm-4 合并 ----
    kb, db = by_id['modelbest:minicpm-4:base'], by_id['openbmb-open-lab-for-big-model-base:minicpm-4-8b:base']
    dbi, kbi = db.get('basic_info') or {}, kb.setdefault('basic_info', {})
    if kbi.get('license') is None:
        kbi['license'] = dbi.get('license')
    if (kb.get('architecture') or {}).get('active_params_b') is None:
        ap = (db.get('architecture') or {}).get('active_params_b')
        if ap is not None:
            kb.setdefault('architecture', {})['active_params_b'] = ap
    note_b = (f'【D47 r1 合并】吸收重复档案 openbmb-open-lab-for-big-model-base:minicpm-4-8b:base'
              f'（同 full_name/日期/参数）。标量冲突保留主档并留痕待核：'
              f'license 主档 {kbi.get("license")} vs donor {dbi.get("license")}；'
              f'ctx 主档 {(kb.get("architecture") or {}).get("context_window_tokens")} vs donor '
              f'{(db.get("architecture") or {}).get("context_window_tokens")}。')
    kbi['notes'] = ((kbi.get('notes') or '') + '；' if kbi.get('notes') else '') + note_b
    for u in (db.get('meta') or {}).get('source_urls') or []:
        su = kb.setdefault('meta', {}).setdefault('source_urls', [])
        if u not in su:
            su.append(u)
    donor_ids.append('openbmb-open-lab-for-big-model-base:minicpm-4-8b:base')

    # ---- 组 C：glm-5.2-none 改名 ----
    kc = by_id['zhipu:glm-5.2-none:base']
    old_fn = kc['basic_info'].get('full_name')
    kc['basic_info']['full_name'] = 'GLM-5.2（Non-Think）'
    note_c = (f'【D47 r1 改名不合并】full_name 由 {old_fn} 改为 GLM-5.2（Non-Think）：'
              f'与 zhipu:glm-5.2:base 为同模型思考/非思考两档（跑分表不同，D34 deepseek-v4-pro 先例），'
              f'改名消除同厂商同名（D46 qa_outliers r1）。')
    kc['basic_info']['notes'] = ((kc['basic_info'].get('notes') or '') + '；' if kc['basic_info'].get('notes') else '') + note_c

    print('计划：')
    print('  A 合并: alibaba:qwen2.5-coder:base -> alibaba:qwen2.5-coder-32b:base（id 删除）')
    print('  B 合并: openbmb-...:minicpm-4-8b:base -> modelbest:minicpm-4:base（id 删除）')
    print('  C 改名: zhipu:glm-5.2-none:base full_name -> GLM-5.2（Non-Think）')
    print(f'  记录数 {len(rows)} -> {len(rows) - len(donor_ids)}')
    if not APPLY:
        print('\n(dry-run，未写入。加 --apply 落库)')
        return

    rows = [r for r in rows if r['model_id'] not in donor_ids]
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d47-r1-{TS}.jsonl')
    shutil.copy2(MAIN, bk)
    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f'已写入：{len(rows)} 条 | 备份 -> {os.path.relpath(bk, ROOT)}')


if __name__ == '__main__':
    main()
