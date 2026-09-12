# -*- coding: utf-8 -*-
"""D47 · HuggingFace 版 fillplan：给魔搭覆盖不到的开源权重记录补 ctx/arch（只补空值）。

背景：D45 魔搭补全只覆盖了在魔搭有官方组织的厂商；仍有 59 条 open_weights 记录
context_window_tokens 为空（Meta/Mistral/Cohere/Apple 等国际厂商主场在 HF）。

口径（沿用 D44/D45）：
  ① ORGS_HF 白名单组织 → `https://huggingface.co/api/models?author=<org>` 列表 →
     canon 精确匹配主库 → 逐条 `resolve/main/config.json` 抽
     max_position_embeddings（ctx）与 MoE/Dense 结构（arch_type）；
  ② gated 仓库 config 401 → 跳过留人工（Meta 系预期如此）；
  ③ 只补 null：ctx 只进 context_window_tokens 为空的记录，arch_type 只进 null/Unknown；
  ④ total_params 不碰；notes 加【D47 HF 补全】留痕，source_url 指 HF 仓库。
用法：PYTHONUTF8=1 python scripts/d47_fetch_hf.py [--apply] [--orgs a,b]
"""
import argparse
import json
import os
import re
import shutil
import sys
import time
import datetime
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
TODAY = '2026-09-13'
HF = 'https://huggingface.co'

ORGS_HF = {
    'meta-llama': 'Meta', 'mistralai': 'Mistral AI', 'google': 'Google',
    'ibm-granite': 'IBM', 'apple': 'Apple', 'tiiuae': 'TII',
    'databricks': 'Databricks', 'nvidia': 'NVIDIA', 'CohereLabs': 'Cohere',
    'stabilityai': 'Stability AI', 'openai': 'OpenAI', 'upstage': 'Upstage',
    'LGAI-EXAONE': 'LG', 'ai21labs': 'AI21 Labs', 'xai-org': 'xAI',
    'snowflake': 'Snowflake', 'ServiceNow-AI': 'ServiceNow',
    'HuggingFaceTB': 'Hugging Face', 'facebook': 'Meta',
}

STRIP_SUFFIX = ('-chat', '-instruct', '-it', '-thinking', '-think', '-non-thinking',
                '-none', '-online', '-base', '-bf16', '-fp8')
VENDOR_PREFIX = ('claude', 'openai', 'google', 'deepmind', 'anthropic', 'meta', 'llama',
                 'xai', 'mistral', 'mixtral', 'cohere', 'nvidia', 'microsoft', 'amazon',
                 'alibaba', 'qwen', 'deepseek', 'baidu', 'zhipu', 'moonshot', 'kimi',
                 'tencent', 'hunyuan', 'huawei', 'meituan', 'xiaomi', 'minimax', 'stepfun',
                 'inclusionai', 'ibm', 'allenai', 'liquid', 'sakana', 'yi')
EFFORT_SUFFIX = re.compile(r'-(minimal|low|medium|high|xhigh|max|default-fallback|'
                           r'with-fallback|non-reasoning|reasoning)$', re.I)


def canon(s):
    s = (s or '').lower().strip()
    s = re.sub(r'\(.*?\)', ' ', s)
    s = re.sub(r'[_/\s]+', '-', s)
    s = re.sub(r'(\d)\.(\d)', r'\1-\2', s)
    s = re.sub(r'[^a-z0-9\u4e00-\u9fff-]', '', s)
    s = re.sub(r'-+', '-', s).strip('-')
    parts = s.split('-')
    while parts and parts[0] in VENDOR_PREFIX:
        parts.pop(0)
    s = '-'.join(parts)
    ch = True
    while ch:
        ch = False
        for suf in STRIP_SUFFIX:
            if s.endswith(suf) and len(s) > len(suf) + 2:
                s = s[:-len(suf)].strip('-')
                ch = True
        m = EFFORT_SUFFIX.search(s)
        if m and len(s) > len(m.group(0)) + 2:
            s = s[:m.start()].strip('-')
            ch = True
    return s


def http_json(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (model_data D47)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def find_ctx(cfg):
    keys = ('max_position_embeddings', 'max_sequence_length', 'max_seq_len',
            'n_positions', 'context_length')
    for scope, c in (('', cfg), ('text_config.', cfg.get('text_config') or {})):
        if not isinstance(c, dict):
            continue
        for k in keys:
            if isinstance(c.get(k), int) and c[k] > 0:
                return (scope + k), c[k]
    return None, None


def arch_of(cfg):
    n_exp = (cfg.get('n_routed_experts') or cfg.get('num_routed_experts')
             or cfg.get('num_local_experts') or cfg.get('num_experts'))
    if n_exp:
        return 'MoE', f'n_routed_experts={n_exp}'
    if cfg.get('num_hidden_layers'):
        return 'Dense', f"num_hidden_layers={cfg['num_hidden_layers']}"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orgs', default='')
    ap.add_argument('--max-config', type=int, default=120)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    APPLY = args.apply
    orgs = {k: v for k, v in ORGS_HF.items() if not args.orgs or k in args.orgs.split(',')}

    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]
    # 待补集合：open_weights 且 ctx/arch 有空
    need = []
    for r in rows:
        acc = (r.get('basic_info') or {}).get('access') or {}
        arch = r.get('architecture') or {}
        if not acc.get('open_weights'):
            continue
        want = []
        if arch.get('context_window_tokens') is None:
            want.append('ctx')
        if arch.get('architecture_type') in (None, 'Unknown'):
            want.append('arch')
        if want:
            need.append((r, want))
    print(f'open_weights 待补记录：{len(need)}（HF 白名单组织 {len(orgs)} 个）')

    # 抓各组织列表并建 canon 索引
    hf_by_canon = {}
    for org, vendor in orgs.items():
        try:
            items = http_json(f'{HF}/api/models?author={org}&limit=1000')
        except Exception as e:
            print(f'  {org:18s} ERR {e}')
            continue
        n = 0
        for it in items:
            full = it.get('modelId') or it.get('id') or ''
            name = full.split('/')[-1] if '/' in full else full
            c = canon(name)
            if c and c not in hf_by_canon:
                hf_by_canon[c] = (org, name)
                n += 1
        print(f'  {org:18s} {len(items):4d} 仓库（新增 canon {n}）')
        time.sleep(0.2)

    plan, gated, budget = [], [], args.max_config
    for r, want in need:
        vendor = (r.get('basic_info') or {}).get('vendor') or ''
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if ':' in mid else mid
        var = mid.split(':')[2] if mid.count(':') >= 2 else ''
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        hit = None
        for key in filter(None, [canon(fam),
                                 canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                                 canon(fn)]):
            if key in hf_by_canon:
                org, name = hf_by_canon[key]
                if (orgs.get(org) or '').lower() != vendor.lower():
                    hit = None
                    break                                # canon 撞名跨厂商 → 放弃该记录
                hit = (org, name)
                break
        if not hit:
            continue
        org, name = hit
        entry = {'model_id': mid, 'hf_repo': f'{org}/{name}', 'nulls': want}
        if budget > 0:
            budget -= 1
            try:
                cfg = http_json(f'{HF}/{org}/{name}/resolve/main/config.json')
                time.sleep(0.15)
            except urllib.error.HTTPError as e:
                cfg = None
                if e.code in (401, 403):
                    gated.append((mid, f'{org}/{name}'))
            except Exception as e:
                cfg = None
                gated.append((mid, f'{org}/{name} ERR {e}'))
            if isinstance(cfg, dict):
                k, v = find_ctx(cfg)
                if k and 'ctx' in want:
                    entry['ctx'] = {'value': v, 'key': k}
                a, ev = arch_of(cfg)
                if a and 'arch' in want:
                    entry['arch'] = {'value': a, 'evidence': ev}
        plan.append(entry)

    print()
    print(f'命中：{len(plan)} 条（config 补拉 {args.max_config - budget} 次，gated/失败 {len(gated)} 跳过）')
    for mid, repo in gated:
        print(f'  [gated] {mid:46s} {repo}')
    for e in plan:
        ctx = (e.get('ctx') or {}).get('value')
        arch = (e.get('arch') or {}).get('value')
        print(f"  {e['model_id']:46s} ctx={str(ctx):>9} arch={arch or '-':6} [{e['hf_repo']}]")
    fillable = [e for e in plan if e.get('ctx') or e.get('arch')]
    if not APPLY:
        print(f'\n(dry-run：可落 {len(fillable)} 条。加 --apply 落库)')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d47-hf-{TS}.jsonl')
    shutil.copy2(MAIN, bk)
    n_ctx = n_arch = 0
    by_id = {r['model_id']: r for r in rows}
    for e in fillable:
        r = by_id[e['model_id']]
        arch = r.setdefault('architecture', {})
        notes_add = []
        if e.get('ctx') and arch.get('context_window_tokens') is None:
            arch['context_window_tokens'] = e['ctx']['value']
            notes_add.append(f"【D47 HF 补全】context_window_tokens 由 {e['hf_repo']} "
                             f"config.json 的 {e['ctx']['key']} 补全（原生标称口径；线上服务可能不同）")
            n_ctx += 1
        if e.get('arch') and arch.get('architecture_type') in (None, 'Unknown'):
            arch['architecture_type'] = e['arch']['value']
            notes_add.append(f"【D47 HF 补全】architecture_type={e['arch']['value']} 由 "
                             f"{e['hf_repo']} config.json 结构判定（{e['arch']['evidence']}）")
            n_arch += 1
        if notes_add:
            arch['notes'] = ((arch.get('notes') or '') + '；' if arch.get('notes') else '') + '；'.join(notes_add)
        su = r.setdefault('meta', {}).setdefault('source_urls', [])
        u = f"https://huggingface.co/{e['hf_repo']}"
        if u not in su:
            su.append(u)
    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f'\n已写入：ctx {n_ctx} / arch {n_arch} | 备份 -> {os.path.relpath(bk, ROOT)}')


if __name__ == '__main__':
    main()
