# -*- coding: utf-8 -*-
"""D48 · 漏采线索扫描：AA 快照 + OpenRouter 快照 ↔ 主库 canon diff（只读）。

产出 temp/d48_leads.jsonl（S0 六字段 + 源标记 + 附加列），喂 candidate_diff.py 分诊。
红线沿用：canon 精确匹配；日期是上架/收录日不是发布日；候选一律待 S0/S1 核。
用法：PYTHONUTF8=1 python scripts/d48_scan_leads.py
"""
import json
import os
import re
import datetime
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
AA = os.path.join(ROOT, 'temp', 'd40_aa_models.json')
OR = os.path.join(ROOT, 'temp', 'd47_openrouter_models.json')
OUT = os.path.join(ROOT, 'temp', 'd48_leads.jsonl')

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


def main():
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]
    have = set()
    for r in rows:
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if ':' in mid else mid
        var = mid.split(':')[2] if mid.count(':') >= 2 else ''
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        for k in filter(None, [canon(fam),
                               canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                               canon(fn)]):
            have.add(k)

    leads = {}
    for o in json.load(open(AA, encoding='utf-8')):
        slug = o.get('slug') or ''
        c = canon(slug)
        if not c or c in have or c in leads:
            continue
        leads[c] = {
            'name': slug, 'vendor': (o.get('creator') or {}).get('name') if isinstance(o.get('creator'), dict) else None,
            'release_date': o.get('releaseDate'), 'tier': 'T2',
            'evidence': f'https://artificialanalysis.ai/models/{slug}',
            'note': f"AA 榜单有/主库无（收录日口径待核）；isOpenWeights={o.get('isOpenWeights')}",
            'source': 'AA', 'ctx': o.get('contextWindowTokens'),
        }
    for m in json.load(open(OR, encoding='utf-8')).get('data') or []:
        m_id = m.get('id') or ''
        name = m_id.split('/')[-1]
        c = canon(name)
        if not c or c in have or c in leads:
            continue
        created = m.get('created')
        rd = datetime.datetime.utcfromtimestamp(created).strftime('%Y-%m-%d') if isinstance(created, (int, float)) else None
        leads[c] = {
            'name': name, 'vendor': m_id.split('/')[0], 'release_date': rd, 'tier': 'T2',
            'evidence': f'https://openrouter.ai/{m_id}',
            'note': f"OpenRouter 上架/主库无（上架日口径，滞后可达 20 天）；{m.get('description', '')[:80]}",
            'source': 'OpenRouter', 'ctx': m.get('context_length'),
        }

    rows_out = sorted(leads.values(), key=lambda x: (x.get('release_date') or '', x['name']), reverse=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        for r in rows_out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    by_src = collections.Counter(r['source'] for r in rows_out)
    recent = [r for r in rows_out if (r.get('release_date') or '') >= '2026-08-01']
    print(f'漏采线索 {len(rows_out)} 条（AA {by_src.get("AA", 0)} / OR {by_src.get("OpenRouter", 0)}）'
          f' -> {os.path.relpath(OUT, ROOT)}；其中 2026-08-01 后 {len(recent)} 条')


if __name__ == '__main__':
    main()
