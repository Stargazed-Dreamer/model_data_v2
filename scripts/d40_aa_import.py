# -*- coding: utf-8 -*-
"""D40 · 导入 Artificial Analysis 数据（只补空白，不覆盖已有）。

策略（保守）：
  ① independent 跑分：只对**当前 independent 为空**的主库记录补（实测 34 条），
     避免与主库已有来源的同一 benchmark 重复。
  ② release_date 精确化：主库只到月、AA 有日且**年月一致**时补日（实测 37 条），
     按用户拍板用 basic_info.notes 标注来源。
  ③ 不导入 intelligenceIndex / omniscience：实测值域 3.75–53.37 / -88.58–43.73，
     是复合指数而非 0–1 准确率，进 independent 段会污染度量口径。

可导入字段（实测全部落在 0–1）：gpqa hle mmmuPro terminalbenchHard terminalbenchV21
terminalbenchV40 tau2 tauBanking scicode ifbench critpt apexAgents itbenchSre
gdpvalNormalized analystAgent lcr omniscienceAccuracy omniscienceNonHallucination

用法：python temp/d40_aa_import.py [--apply]
"""
import json
import os
import re
import sys
import shutil
import datetime
import collections
import difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AA = os.path.join(ROOT, 'temp', 'd40_aa_models.json')
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
COLLECTED = '2026-09-10'

BENCH_MAP = {
    'gpqa': 'GPQA Diamond',
    'hle': "Humanity's Last Exam",
    'mmmuPro': 'MMMU-Pro',
    'terminalbenchHard': 'Terminal-Bench Hard',
    'terminalbenchV21': 'Terminal-Bench 2.1',
    'terminalbenchV40': 'Terminal-Bench 4.0',
    'tau2': 'Tau2-Bench',
    'tauBanking': 'Tau-Bench Banking',
    'scicode': 'SciCode',
    'ifbench': 'IFBench',
    'critpt': 'CritPt',
    'apexAgents': 'APEX-Agents',
    'itbenchSre': 'ITBench-SRE',
    'gdpvalNormalized': 'GDPval',
    'analystAgent': 'AnalystAgent',
    'lcr': 'LCR (Long-Context Reasoning)',
    'omniscienceAccuracy': 'Omniscience Accuracy',
    'omniscienceNonHallucination': 'Omniscience Non-Hallucination',
}

STRIP_SUFFIX = ('-chat', '-instruct', '-it', '-thinking', '-think', '-non-thinking',
                '-none', '-online', '-base', '-bf16', '-fp8')
# ⚠ 只放**厂商名/品牌**，不放模型系列名。首版误把 command/gemma/gemini/phi/olmo/jamba/
#   nemotron/lfm/granite 当厂商前缀剥掉，剥出 `a-plus` 这种残片，导致
#   `command-a-plus` 误配到 `qwen-plus`。系列名要留在 canon 里参与比对。
VENDOR_PREFIX = ('claude', 'openai', 'google', 'deepmind', 'anthropic', 'meta', 'llama',
                 'xai', 'mistral', 'mixtral', 'cohere', 'nvidia', 'microsoft', 'amazon',
                 'alibaba', 'qwen', 'deepseek', 'baidu', 'zhipu', 'moonshot', 'kimi',
                 'tencent', 'hunyuan', 'huawei', 'meituan', 'xiaomi', 'minimax', 'stepfun',
                 'inclusionai', 'ibm', 'allenai', 'liquid', 'sakana', 'yi')
# canon 过短（<5）不参与模糊匹配：`plus`/`max`/`pro` 这类残片极易误配
MIN_FUZZY_LEN = 5
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


def aa_sizes(s):
    return {m.group(1) for m in re.finditer(r'(\d+(?:\.\d+)?)\s*b(?!\w)', (s or '').lower())}


def size_ok(aa_slug, mid, full_name):
    """尺寸一致性校验：双方都带参数尺寸且无交集 → 拒。

    实测错配（被此判据拦下）：`qwen3-coder-480b-a35b` ↔ `qwen3-coder-30b-a3b`（480 vs 30）、
    `minicpm-1-2b` ↔ `minicpm5-1b`。
    """
    rs, ms = aa_sizes(aa_slug), aa_sizes(mid) | aa_sizes(full_name)
    if rs and ms and not (rs & ms):
        return False
    return True


def main():
    aa = json.load(open(AA, encoding='utf-8'))
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]

    # AA 按 canon 归并（取 intelligenceIndex 最高者代表该模型）
    aa_by = {}
    for o in aa:
        if not o.get('slug'):
            continue
        c = canon(o.get('slug'))
        if not c:
            continue
        prev = aa_by.get(c)
        if prev is None or (o.get('intelligenceIndex') or -1) > (prev.get('intelligenceIndex') or -1):
            aa_by[c] = o

    # 主库索引（同一记录在 fam/fn 两个键下会重复，用 dict 去重）
    main_by = collections.defaultdict(dict)
    for r in rows:
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if ':' in mid else mid
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        for src in (fam, fn):
            c = canon(src)
            if c:
                main_by[c][id(r)] = r

    # 严格匹配：exact 直接收；fuzzy 必须过尺寸一致性校验
    pairs = {}   # (id(r), aa_canon) -> (r, o, how)
    for c, o in aa_by.items():
        for r in main_by.get(c, {}).values():
            pairs[(id(r), c)] = (r, o, 'exact')
    used = set(aa_by) | {c for c in aa_by if c in main_by}
    for c, o in aa_by.items():
        if c in main_by:
            continue
        if len(c) < MIN_FUZZY_LEN:
            continue
        best = (0.0, None)
        for mc in main_by:
            if len(mc) < MIN_FUZZY_LEN:
                continue
            ratio = difflib.SequenceMatcher(None, c, mc).ratio()
            if c and mc and (c in mc or mc in c):
                sh, lo = sorted((c, mc), key=len)
                if len(sh) / max(len(lo), 1) >= 0.6:
                    ratio = max(ratio, 0.90)
            if ratio > best[0]:
                best = (ratio, mc)
        if best[0] >= 0.90:
            for r in main_by[best[1]].values():
                mid = r.get('model_id') or ''
                fn = (r.get('basic_info') or {}).get('full_name') or ''
                if not size_ok(o.get('slug') or '', mid, fn):
                    continue
                pairs[(id(r), c)] = (r, o, 'fuzzy%.2f' % best[0])
    pairs = list(pairs.values())

    # ---- ① 跑分补（只补 independent 为空的记录）----
    # ⚠ 只收 exact（canon 完全相等）。fuzzy（含尺寸校验放行者）实测仍有
    #   `command-r-plus` ↔ `command-a-plus` 这类同厂近名错配，全部转人工复核，不入库。
    exact_pairs = [(r, o, how) for r, o, how in pairs if how == 'exact']
    fuzzy_pairs = [(r, o, how) for r, o, how in pairs if how != 'exact']
    print('exact 匹配对:', len(exact_pairs), '| fuzzy（转人工，不导入）:', len(fuzzy_pairs))
    print()

    bench_plan = []
    for r, o, how in exact_pairs:
        if (r.get('benchmarks') or {}).get('independent'):
            continue
        url = f'https://artificialanalysis.ai/models/{o.get("slug")}'
        items = []
        for f, bname in BENCH_MAP.items():
            v = o.get(f)
            if not isinstance(v, (int, float)) or not (0 <= v <= 1):
                continue
            items.append({
                'benchmark': bname,
                'score': round(float(v), 4),
                'score_type': 'accuracy',
                'config': 'default',
                'date': COLLECTED,
                'source_url': url,
                'source_type': '独立评测平台',
                'confidence': 'T1',
                'gap_to_self_reported': None,
                'notes': f'Artificial Analysis 榜单实测值（抓取日 {COLLECTED}，该榜为滚动更新，'
                         f'无固定评测日）；AA 模型页：{url}；方法论与库内其它来源未必可比。',
            })
        if items:
            bench_plan.append((r, items, o))

    # ---- ② 日期精确化 ----
    date_plan = []
    for r, o, how in exact_pairs:
        d = o.get('releaseDate') or ''
        rd = ((r.get('basic_info') or {}).get('release_date') or '')
        if len(d) == 10 and len(rd) == 7 and rd == d[:7]:
            if not any(x[0] is r for x in date_plan):
                date_plan.append((r, rd, d))

    print('匹配对:', len(pairs))
    print()
    print('=== ① 跑分补（independent 为空的记录）===')
    print('  记录数:', len(bench_plan), '| 新增 independent 条目:', sum(len(i) for _, i, _ in bench_plan))
    for r, items, o in sorted(bench_plan, key=lambda x: x[0].get('model_id')):
        print(f'  {r.get("model_id")[:44]:46s} +{len(items):2d} 项  (AA slug={o.get("slug")})')
    print()
    print('=== ② 日期精确化 ===')
    print('  条数:', len(date_plan))
    for r, old, new in date_plan:
        print(f'  {r.get("model_id")[:44]:46s} {old} -> {new}')

    if APPLY:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d40-aa-{TS}.jsonl')
        shutil.copy2(MAIN, bk)
        for r, items, o in bench_plan:
            b = r.setdefault('benchmarks', {})
            b.setdefault('independent', [])
            b['independent'].extend(items)
            m = r.setdefault('meta', {})
            su = m.get('source_urls') or []
            u = f'https://artificialanalysis.ai/models/{o.get("slug")}'
            if u not in su:
                su.append(u)
            m['source_urls'] = su
        for r, old, new in date_plan:
            b = r.setdefault('basic_info', {})
            b['release_date'] = new
            note = (f'【D40 日期精确化】release_date 由 {old}（精度：月）精确为 {new}（精度：日），'
                    f'依据 Artificial Analysis 模型页标注的发布日期。')
            b['notes'] = ((b.get('notes') or '') + ' ' + note).strip()
        with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
        print()
        print(f'已写入：跑分 {len(bench_plan)} 条记录 / 日期 {len(date_plan)} 条 | 备份 -> {os.path.relpath(bk, ROOT)}')
    else:
        print()
        print('(dry-run，未写入)')


if __name__ == '__main__':
    main()
