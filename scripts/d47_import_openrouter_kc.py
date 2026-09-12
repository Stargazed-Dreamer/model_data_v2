# -*- coding: utf-8 -*-
"""D47 · 导入 OpenRouter 模型清单的 knowledge_cutoff 到主库（只补空值）。

口径：
  ① 只对 `architecture.knowledge_cutoff` 为 null 的记录补；
  ② 匹配只走 canon 精确匹配（OpenRouter id 的 org 段与 ledger vendor 做等价组校验，防跨厂错配）；
  ③ confidence=T2（供应商经 OpenRouter 申报，非官方文档直读），source_url=openrouter 模型页，
     notes 声明抓取日与口径。
数据：https://openrouter.ai/api/v1/models（免鉴权全量 JSON，跟踪源清单 A 层已验证）。
用法：PYTHONUTF8=1 python scripts/d47_import_openrouter_kc.py [--apply]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OR_RAW = os.path.join(ROOT, 'temp', 'd47_openrouter_models.json')
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
TODAY = '2026-09-13'

STRIP_SUFFIX = ('-chat', '-instruct', '-it', '-thinking', '-think', '-non-thinking',
                '-none', '-online', '-base', '-bf16', '-fp8')
VENDOR_PREFIX = ('claude', 'openai', 'google', 'deepmind', 'anthropic', 'meta', 'llama',
                 'xai', 'mistral', 'mixtral', 'cohere', 'nvidia', 'microsoft', 'amazon',
                 'alibaba', 'qwen', 'deepseek', 'baidu', 'zhipu', 'moonshot', 'kimi',
                 'tencent', 'hunyuan', 'huawei', 'meituan', 'xiaomi', 'minimax', 'stepfun',
                 'inclusionai', 'ibm', 'allenai', 'liquid', 'sakana', 'yi')
EFFORT_SUFFIX = re.compile(r'-(minimal|low|medium|high|xhigh|max|default-fallback|'
                           r'with-fallback|non-reasoning|reasoning)$', re.I)

ALIAS_GROUPS = [
    ('ant', ('alibaba', 'qwen', 'tongyi', 'inclusionai', 'ant', 'ling', 'ring')),
    ('zhipu', ('zhipu', 'zai', 'z-ai', 'thudm', 'chatglm', 'glm')),
    ('moonshot', ('moonshot', 'kimi')),
    ('meta', ('meta', 'facebook', 'llama')),
    ('google', ('google', 'deepmind', 'gemma', 'gemini')),
    ('nvidia', ('nvidia', 'nemotron')),
    ('xiaomi', ('xiaomi', 'mimo')),
    ('ibm', ('ibm', 'granite')),
    ('mistral', ('mistral', 'mixtral', 'mistralai')),
    ('microsoft', ('microsoft', 'phi', 'wizardlm', 'mai')),
    ('cohere', ('cohere', 'command')),
    ('deepseek', ('deepseek',)),
    ('baidu', ('baidu', 'ernie')),
    ('bytedance', ('bytedance', 'seed', 'doubao')),
    ('perplexity', ('perplexity', 'sonar')),
    ('ai21', ('ai21', 'jamba')),
    ('cogito', ('cogito',)),
    ('allenai', ('allenai', 'olmo', 'allen institute', 'ai2')),
    ('eth', ('eth', 'apertus')),
    ('upstage', ('upstage', 'solar')),
    ('modelbest', ('modelbest', 'openbmb', 'minicpm')),
    ('qihoo', ('360', 'qihoo')),
    ('meituan', ('meituan', 'longcat')),
    ('baichuan', ('baichuan',)),
    ('tmach', ('thinking machines', 'thinkingmachines', 'inkling', 'tinker')),
    ('amazon', ('amazon', 'nova')),
    ('liquid', ('liquid', 'lfm')),
    ('openai', ('openai', 'gpt')),
    ('anthropic', ('anthropic', 'claude')),
    ('xai', ('xai', 'x-ai', 'grok')),
]


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


def _groups_of(s):
    s = (s or '').lower()
    out = set()
    for g, toks in ALIAS_GROUPS:
        if any(t in s for t in toks):
            out.add(g)
    words = re.sub(r'[^a-z0-9 ]', ' ', s).split()
    if words:
        out.add(words[0])
    return out


def vendor_ok(vendor, org):
    if not vendor or not org:
        return True
    gv, gc = _groups_of(vendor), _groups_of(org)
    if not gv or not gc:
        return True
    return bool(gv & gc)


def fetch_openrouter():
    if os.path.exists(OR_RAW) and os.path.getsize(OR_RAW) > 100000:
        print(f'[缓存] 复用 {OR_RAW}')
        return json.load(open(OR_RAW, encoding='utf-8'))
    r = subprocess.run(['curl', '-sS', '--ssl-no-revoke', '-L', '--max-time', '120',
                        '-o', OR_RAW, '-w', '%{http_code}',
                        'https://openrouter.ai/api/v1/models'],
                       capture_output=True, timeout=180)
    print('HTTP', r.stdout.decode().strip(), '| bytes', os.path.getsize(OR_RAW))
    return json.load(open(OR_RAW, encoding='utf-8'))


def main():
    data = fetch_openrouter()
    models = data.get('data') or []
    print(f'OpenRouter 模型数：{len(models)}')

    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]
    plan, skipped_vendor = [], []
    for r in rows:
        if (r.get('architecture') or {}).get('knowledge_cutoff') is not None:
            continue                                    # 只补空
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if ':' in mid else mid
        var = mid.split(':')[2] if mid.count(':') >= 2 else ''
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        vendor = (r.get('basic_info') or {}).get('vendor') or ''
        hit = None
        # 日期变体护栏：ledger variant 形如日期（0324/0528/2507/1776…）时，OR id/name 必须含同一
        # 数字串，否则该 OR 条目可能对应另一个日期版本（实测 mistral-large:2402 ← 现役
        # mistral-large 的 kc=2024-11 污染），宁可留空。
        var_date = re.fullmatch(r'(\d{4})', var or '') or re.search(r'(\d{4})$', fam or '')
        for key in filter(None, [canon(fam),
                                 canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                                 canon(fn)]):
            for m in models:
                m_id = m.get('id') or ''
                m_name = m.get('name') or ''
                if key in (canon(m_id.split('/')[-1]), canon(m_name)):
                    if var_date and var_date.group(1) not in m_id:
                        continue
                    if not vendor_ok(vendor, m_id.split('/')[0]):
                        skipped_vendor.append((mid, m_id))
                        continue
                    kc = m.get('knowledge_cutoff') or (m.get('pricing') or {}).get('knowledge_cutoff')
                    if isinstance(kc, str) and re.match(r'^\d{4}(-\d{2}){0,2}$', kc):
                        hit = (m, kc)
                        break
            if hit:
                break
        if hit:
            plan.append((r, hit))

    print(f'可补 knowledge_cutoff：{len(plan)} 条（vendor 错配跳过 {len(skipped_vendor)}）')
    for m, s in skipped_vendor[:10]:
        print(f'  [vendor跳过] {m:46s} <- {s}')
    for r, (m, kc) in plan:
        print(f'  {r.get("model_id"):46s} kc={kc:12s} [{m.get("id")}]')
    if not APPLY:
        print('\n(dry-run，未写入。加 --apply 落库)')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d47-or-kc-{TS}.jsonl')
    shutil.copy2(MAIN, bk)
    for r, (m, kc) in plan:
        arch = r.setdefault('architecture', {})
        arch['knowledge_cutoff'] = kc
        note = (f'【D47 OpenRouter 补全】knowledge_cutoff 由 OpenRouter 模型清单申报值补全'
                f'（抓取日 {TODAY}，T2：供应商申报非官方文档直读，官方披露后精化）。')
        arch['notes'] = ((arch.get('notes') or '') + '；' if arch.get('notes') else '') + note
        su = r.setdefault('meta', {}).setdefault('source_urls', [])
        u = f'https://openrouter.ai/{m.get("id")}'
        if u not in su:
            su.append(u)
    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f'\n已写入 {len(plan)} 条 | 备份 -> {os.path.relpath(bk, ROOT)}')


if __name__ == '__main__':
    main()
