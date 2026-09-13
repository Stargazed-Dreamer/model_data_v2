# -*- coding: utf-8 -*-
"""D48 · 导入 OpenCompass（司南）独立评测到主库 benchmarks.independent（只补空白）。

口径（D48 定死，依据 temp/d48_opencompass_probe.md 探路报告）：
  ① 数据源：temp/oc_research_rt.json（学术榜 REALTIME，48 模型 × 客观 6 基准，司南自建
     评测、脚本开源）+ temp/oc_llmv2_data.json（CompassBench v2 26-07 期，15 模型 × 4 能力维）。
     历史月度/多模态榜本轮不导。
  ② 只对 `benchmarks.independent` 为**空数组**的记录补（D40 同款），官方自报/arena 不动。
  ③ 匹配：canon 精确 + vendor 等价组（OC org 字段）；带 (high)/(thinking) 后缀的 OC 条目
     **整条跳过**（变体口径须显式判定，D39 红线——避免把高推理档分数灌进默认档记录）。
  ④ 百分制 ÷100（与库内 AA 条目 0-1 口径一致）；score_type=accuracy。
  ⑤ confidence：学术榜 T1（客观基准+方法论公开可复现，探路报告辩护成立）；
     v2 综合榜 T2（司南自建 CompassBench，按期重定基）。Average 复合列不导（D40 口径）。
  ⑥ date=快照 update_time；source_url=对应榜单页；notes 声明快照日/repeat/重定基口径。
用法：PYTHONUTF8=1 python scripts/d48_import_opencompass.py [--apply]
"""
import collections
import json
import os
import re
import shutil
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
TODAY = datetime.date.today().isoformat()
SRC_URL_RESEARCH = 'https://rank.opencompass.org.cn/leaderboard-llm-academic'
SRC_URL_V2 = 'https://rank.opencompass.org.cn/leaderboard-llm-v2'

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
    ('zhipu', ('zhipu', 'zai', 'thudm', 'chatglm', 'glm')),
    ('moonshot', ('moonshot', 'kimi')),
    ('meta', ('meta', 'facebook', 'llama')),
    ('google', ('google', 'deepmind', 'gemma', 'gemini')),
    ('nvidia', ('nvidia', 'nemotron')),
    ('xiaomi', ('xiaomi', 'mimo')),
    ('ibm', ('ibm', 'granite')),
    ('mistral', ('mistral', 'mixtral')),
    ('microsoft', ('microsoft', 'phi', 'wizardlm')),
    ('cohere', ('cohere', 'command', 'aya')),
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
    ('tencent', ('tencent', 'hunyuan')),
    ('minimax', ('minimax',)),
    ('01ai', ('01ai', '01.ai', 'yi')),
    ('stepfun', ('stepfun', 'step')),
    ('baichuan', ('baichuan',)),
    ('amazon', ('amazon', 'nova')),
    ('anthropic', ('anthropic', 'claude')),
    ('openai', ('openai', 'gpt')),
    ('xai', ('xai', 'x-ai', 'grok')),
    ('internai', ('intern', 'shanghai ai', 'internlm', 'intern-s')),
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


def norm_date(s):
    """'2026/3/9' -> '2026-03-09'。"""
    m = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', str(s or ''))
    if not m:
        return None
    return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'


def main():
    research = json.load(open(os.path.join(ROOT, 'temp', 'oc_research_rt.json'), encoding='utf-8'))
    v2 = json.load(open(os.path.join(ROOT, 'temp', 'oc_llmv2_data.json'), encoding='utf-8'))
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]

    # OC 侧扁平化：(name, org, benchmark, score, config, date, conf, src_url)
    flat = []
    rt_tbl = research.get('OverallTable') or []
    rt_update = norm_date(rt_tbl[0].get('update_time')) if rt_tbl else None
    desc = research.get('description') or {}
    for row in rt_tbl:
        nm = str(row.get('model') or '')
        if re.search(r'-(Thinking|Non-Thinking)$', nm, re.I):
            continue                               # 裸 -Thinking 变体：不灌默认档（D39）
        for b in ('AIME2025', 'MMLU-Pro', 'GPQA-Diamond', 'HLE', 'LiveCodeBenchV6', 'IFEval'):
            v = row.get(b)
            if isinstance(v, (int, float)):
                cfg = 'opencompass'
                for k, dv in desc.items():
                    if k.lower() in b.lower() and isinstance(dv, str):
                        cfg = 'opencompass ' + dv[:40]
                flat.append((nm, row.get('org'), b, v / 100.0, cfg,
                             rt_update, 'T1', SRC_URL_RESEARCH, '学术榜（客观基准，repeat 配置公开）'))
    v2_tbl = v2.get('OverallTable') or []
    for row in v2_tbl:
        nm = str(row.get('model') or '')
        if re.search(r'-(Thinking|Non-Thinking)$', nm, re.I):
            continue
        d = norm_date(row.get('update_time')) or None
        for b in ('Knowledge', 'Reasoning', 'Math', 'Code'):
            v = row.get(b)
            if isinstance(v, (int, float)):
                flat.append((nm, row.get('org'), f'CompassBench-v2 {b}', v / 100.0,
                             'CompassBench-2607', d, 'T2', SRC_URL_V2,
                             '司南自建综合榜（按期重定基）'))

    # 索引
    oc_by = collections_ = {}
    for name, org, b, s, cfg, d, conf, url, tag in flat:
        eff = re.search(r'\((high|low|thinking|non-thinking)\)', str(name), re.I)
        if eff:
            continue                                   # 变体口径显式判定前不导（D39）
        c = canon(name)
        if not c:
            continue
        oc_by.setdefault(c, []).append((name, org, b, s, cfg, d, conf, url, tag))

    plan, skipped_vendor = [], []
    for r in rows:
        ind = (r.get('benchmarks') or {}).get('independent')
        if ind:                                        # 只补空白（D40 口径）
            continue
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if ':' in mid else mid
        var = mid.split(':')[2] if mid.count(':') >= 2 else ''
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        vendor = (r.get('basic_info') or {}).get('vendor') or ''
        # 变体口径：库内思考/档位变体记录不与非标注 OC 条目混写
        if re.search(r'-(think|thinking|none|non-thinking)$', fam.lower() + '-' + (var or '')):
            continue
        hit = None
        for key in filter(None, [canon(fam),
                                 canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                                 canon(fn)]):
            if key in oc_by:
                name, org, *_ = oc_by[key][0]
                if not vendor_ok(vendor, org):
                    skipped_vendor.append((mid, name, org))
                    continue
                hit = oc_by[key]
                break
        if hit:
            plan.append((r, hit))

    # 歧义护栏：同一 OC 条目命中多条库内记录（日期变体/家族多档）→ 全部跳过（D39：宁可留空）
    by_oc = collections.defaultdict(list)
    for r, hit in plan:
        by_oc[hit[0][0]].append((r, hit))
    final, skipped_ambig = [], []
    for oc_name, lst in by_oc.items():
        if len(lst) > 1:
            skipped_ambig.append((oc_name, [x[0].get('model_id') for x in lst]))
            continue
        final.append(lst[0])
    plan = final

    n_bench = sum(len(h) for _, h in plan)
    print(f'OC 条目 {len(flat)}（剥变体后可用键 {len(oc_by)}）；'
          f'independent 空的主库记录命中 {len(plan)} 条 / {n_bench} 个基准'
          f'（vendor 错配跳过 {len(skipped_vendor)} / 歧义跳过 {len(skipped_ambig)} 组）')
    for name, ids in skipped_ambig:
        print(f'  [歧义跳过] {name} <- {ids}')
    for m, s, o in skipped_vendor[:8]:
        print(f'  [vendor跳过] {m:44s} <- {s} (org={o})')
    for r, hit in plan:
        print(f"  {r.get('model_id'):46s} +{len(hit)}  <- {hit[0][0]} ({hit[0][1]})")
    if not APPLY:
        print('\n(dry-run，未写入。加 --apply 落库)')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d48-oc-{TS}.jsonl')
    shutil.copy2(MAIN, bk)
    for r, hit in plan:
        items = []
        for name, org, b, s, cfg, d, conf, url, tag in hit:
            items.append({
                'benchmark': b, 'score': round(s, 4), 'score_type': 'accuracy',
                'config': cfg, 'date': d or TODAY,
                'source_url': url, 'source_type': '独立评测平台',
                'confidence': conf, 'gap_to_self_reported': None,
                'notes': f'OpenCompass（司南）独立评测，快照日 {d}；{tag}；百分制÷100；'
                         f'按月重定基跨期弱可比（{TODAY} 导入）。',
            })
        r.setdefault('benchmarks', {})['independent'] = items
        su = r.setdefault('meta', {}).setdefault('source_urls', [])
        for u in {i['source_url'] for i in items}:
            if u not in su:
                su.append(u)
    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f'\n已写入 {len(plan)} 条记录 / {n_bench} 个基准 | 备份 -> {os.path.relpath(bk, ROOT)}')


if __name__ == '__main__':
    main()
