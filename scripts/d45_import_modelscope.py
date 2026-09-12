# -*- coding: utf-8 -*-
"""D45 · 导入魔搭补全候选（fillplan）到主库——只为空值补，不覆盖任何已有值。

口径（保守，D45 定死）：
  ① context_window_tokens：仅当主库该字段为 null 时，取魔搭官方仓库 config.json 的
     max_position_embeddings 等键（fillplan 里的 ctx_candidate）。抽验（2026-09-13）：
     6 条人工抽验中 5 条与 HF 同名仓库 config.json 完全一致、1 条（GLM-4-32B-0414）
     HF gated，按公开规格（32K）吻合。魔搭 config 即 HF config 的镜像。
     ⚠ 线上 API/官方服务的实际可用长度可能不同，notes 里声明。
  ② architecture_type：仅当主库为 null/Unknown 时，按 config.json 结构判定——
     有 n_routed_experts/num_local_experts 等 → MoE；有 num_hidden_layers 且无专家键 → Dense。
     Hybrid 不可从 config 可靠判定，一律不导。
  ③ total_params_b / active_params_b **不导**：model_size 是权重字节数，推导值不入库（D44 红线）。
  ④ 每处补全在 architecture.notes 追加【D45 魔搭补全】留痕，MS 仓库 URL 追加进 meta.source_urls。

用法：PYTHONUTF8=1 python scripts/d45_import_modelscope.py [--apply]
输入：temp/d44_msscope_fillplan.json（由 scripts/d44_fetch_modelscope.py 产出）
"""
import json
import os
import shutil
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILL = os.path.join(ROOT, 'temp', 'd44_msscope_fillplan.json')
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
TODAY = '2026-09-13'


def main():
    fill = json.load(open(FILL, encoding='utf-8'))
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]
    by_id = {r.get('model_id'): r for r in rows}

    plan = []
    for p in fill.get('plan', []):
        r = by_id.get(p.get('model_id'))
        if r is None:
            print(f"⚠ 主库未见 {p.get('model_id')}（库已被改动？）跳过")
            continue
        arch = r.setdefault('architecture', {})
        acts = []

        ctx = p.get('ctx_candidate') or {}
        if ctx.get('value') and arch.get('context_window_tokens') is None:
            acts.append(('ctx', ctx))

        ac = p.get('arch_candidate') or {}
        if ac.get('value') in ('MoE', 'Dense') and arch.get('architecture_type') in (None, 'Unknown'):
            acts.append(('arch', ac))

        if acts:
            plan.append((r, p, acts))

    n_ctx = sum(1 for _, _, a in plan if any(k == 'ctx' for k, _ in a))
    n_arch = sum(1 for _, _, a in plan if any(k == 'arch' for k, _ in a))
    print(f'候选 {len(fill.get("plan", []))} 条 → 可补 {len(plan)} 条记录'
          f'（ctx {n_ctx} / arch_type {n_arch}；已非空的全部跳过）')
    for r, p, acts in plan[:2000]:
        tags = '+'.join(k for k, _ in acts)
        ctx = next((v for k, v in acts if k == 'ctx'), None)
        ac = next((v for k, v in acts if k == 'arch'), None)
        print(f"  {r.get('model_id'):46s} {tags:10s}"
              f" ctx={ctx['value'] if ctx else '-':>9} arch={ac['value'] if ac else '-'}"
              f"  [{p.get('ms_repo')}]")

    if not APPLY:
        print('\n(dry-run，未写入。加 --apply 落库)')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d45-msfill-{TS}.jsonl')
    shutil.copy2(MAIN, bk)

    for r, p, acts in plan:
        arch = r['architecture']
        notes_add = []
        for kind, v in acts:
            if kind == 'ctx':
                arch['context_window_tokens'] = v['value']
                notes_add.append(
                    f"【D45 魔搭补全】context_window_tokens 由魔搭官方仓库 {p.get('ms_repo')} "
                    f"config.json 的 {v.get('key')} 补全（{TODAY} 抽验与 HF 同名仓库 config 一致）；"
                    f"线上服务实际可用长度可能不同")
            else:
                arch['architecture_type'] = v['value']
                notes_add.append(
                    f"【D45 魔搭补全】architecture_type={v['value']} 由魔搭官方仓库 "
                    f"config.json 结构判定（{v.get('evidence')}，{TODAY}）")
        if notes_add:
            arch['notes'] = ((arch.get('notes') or '') + '；' if arch.get('notes') else '') + '；'.join(notes_add)
        meta = r.setdefault('meta', {})
        su = meta.get('source_urls') or []
        u = f"https://modelscope.cn/models/{p.get('ms_repo')}"
        if u not in su:
            su.append(u)
        meta['source_urls'] = su

    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f"\n已写入：ctx {n_ctx} / arch {n_arch}（记录 {len(plan)} 条）| 备份 -> {os.path.relpath(bk, ROOT)}")


if __name__ == '__main__':
    main()
