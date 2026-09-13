# -*- coding: utf-8 -*-
"""D48b · OpenCompass 深挖：历史月度快照（16 期）+ 多模态 mm 榜 → 只补 independent 空的记录。

与 d48_import_opencompass.py 同口径（canon 精确 + vendor 等价组 + 变体跳过 + 歧义跳过
+ 百分制 ÷100 + 只补空），差异：
  ① 每条空记录按快照**从新到旧**找首个命中，date=该期 updateTime；
  ② 列名动态取（历史期列集不同：AIME2024/GAOKAO 时代），排除元数据列与 Average；
  ③ mm 榜（MMBench 系）同样处理，供 VL 记录命中。
用法：PYTHONUTF8=1 python scripts/d48_import_oc_deep.py [--apply]
"""
import collections
import datetime
import json
import os
import re
import shutil
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
CDN = 'https://cdn.opencompass.org.cn/'
TODAY = datetime.date.today().isoformat()
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
META_COLS = {'key', 'model', 'org', 'num', 'time', 'update_time', 'chat_or_base', 'Average'}
EFF_RE = re.compile(r'\((high|low|thinking|non-thinking)\)', re.I)
THINK_RE = re.compile(r'-(Thinking|Non-Thinking)$', re.I)

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
    ('snowflake', ('snowflake', 'arctic')),
    ('databricks', ('databricks', 'dbrx')),
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
    m = re.match(r'(\d{4})/(\d{1,2})/(\d{1,2})', str(s or ''))
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(s or ''))
    return m.group(0) if m else None


def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return json.load(open(dest, encoding='utf-8'))
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read()
    if raw[:2] == b'\x1f\x8b':
        import gzip
        raw = gzip.decompress(raw)
    data = json.loads(raw.decode('utf-8'))
    json.dump(data, open(dest, 'w', encoding='utf-8'))
    time.sleep(0.15)
    return data


def main():
    months = json.load(open(os.path.join(ROOT, 'temp', 'oc_months.json'), encoding='utf-8'))['data']
    # 快照清单：研究榜历史期（新→旧）+ mm 榜 REALTIME
    snaps = []
    for m in months:
        snaps.append(('research', m['fileName'], m.get('updateTime')))
    # mm 榜：从 REALTIME 文件名找（探路样本 oc_mmlb.json 已有，直接用）
    snaps.append(('mm', 'assets/mm-rank/mmlb-data.REALTIME.20260903.json', '2026-09-03'))

    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]
    empty = []
    for r in rows:
        if not (r.get('benchmarks') or {}).get('independent'):
            empty.append(r)
    print(f'independent 为空：{len(empty)} 条；快照 {len(snaps)} 期（含缓存复用）')

    # 逐期建索引，找每条记录的首个命中
    hit = {}          # id(r) -> (snapshot_date, conf, src_url, [(bench, score), ...])
    used_snap = collections.Counter()
    for kind, fname, upd in snaps:
        date = norm_date(upd) or upd
        conf = 'T1' if kind == 'research' else 'T2'
        dest = os.path.join(ROOT, 'temp', 'oc_deep_' + os.path.basename(fname))
        try:
            data = fetch(CDN + fname, dest)
        except Exception as e:
            print(f'  [{kind} {date}] ERR {e}')
            continue
        tbl = data.get('OverallTable') or []
        if not tbl:
            continue
        # 建 canon 索引（带 vendor/变体规则）
        idx = collections.defaultdict(list)
        for row in tbl:
            nm = str(row.get('model') or '')
            if THINK_RE.search(nm) or EFF_RE.search(nm):
                continue
            c = canon(nm)
            if c:
                idx[c].append((nm, row.get('org'), row))
        got_this_snap = 0
        for r in empty:
            if id(r) in hit:
                continue
            mid = r.get('model_id') or ''
            fam = mid.split(':')[1] if ':' in mid else mid
            var = mid.split(':')[2] if mid.count(':') >= 2 else ''
            fn = (r.get('basic_info') or {}).get('full_name') or ''
            vendor = (r.get('basic_info') or {}).get('vendor') or ''
            if re.search(r'-(think|thinking|none|non-thinking)$', fam.lower() + '-' + (var or '')):
                continue
            for key in filter(None, [canon(fam),
                                     canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                                     canon(fn)]):
                cands = idx.get(key)
                if not cands:
                    continue
                nm, org, row = cands[0]
                if not vendor_ok(vendor, org):
                    break
                items = []
                for b, v in row.items():
                    if b in META_COLS or not isinstance(v, (int, float)):
                        continue
                    items.append((b, round(v / 100.0, 4)))
                if items:
                    src = (SRC := ('https://rank.opencompass.org.cn/leaderboard-llm-academic'
                                   if kind == 'research' else
                                   'https://rank.opencompass.org.cn/leaderboard?tab=multimodal'))
                    hit[id(r)] = (date, conf, src, nm, items)
                    got_this_snap += 1
                break
        used_snap[f'{kind} {date}'] = got_this_snap
        print(f'  [{kind} {date}] 本期新命中 {got_this_snap}')
        if len(hit) >= len(empty):
            break

    print()
    # 歧义护栏：同快照同 OC 条目命中多条库记录 → 全跳（D39：宁可留空）
    by_oc = collections.defaultdict(list)
    for r in empty:
        h = hit.get(id(r))
        if h:
            by_oc[(h[3], h[0])].append((r, h))
    for (nm, d), lst in by_oc.items():
        if len(lst) > 1:
            for r, _ in lst:
                hit.pop(id(r), None)
            print(f'  [歧义跳过] {nm} @{d} <- {[x[0].get("model_id") for x in lst]}')
    for r in empty:
        h = hit.get(id(r))
        if h:
            d, conf, src, nm, items = h
            print(f"  {r.get('model_id'):46s} +{len(items):2d}  [{nm}] snap={d} conf={conf}")

    if not APPLY:
        print(f'\n(dry-run：可落 {len(hit)} 条。加 --apply 落库)')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d48b-ocdeep-{TS}.jsonl')
    shutil.copy2(MAIN, bk)
    for r in empty:
        h = hit.get(id(r))
        if not h:
            continue
        d, conf, src, nm, items = h
        arr = []
        for b, s in items:
            arr.append({
                'benchmark': b, 'score': s, 'score_type': 'accuracy',
                'config': 'opencompass', 'date': d,
                'source_url': src, 'source_type': '独立评测平台',
                'confidence': conf, 'gap_to_self_reported': None,
                'notes': f'OpenCompass（司南）独立评测，快照日 {d}；百分制÷100；'
                         f'按月重定基跨期弱可比（{TODAY} 导入）。',
            })
        r.setdefault('benchmarks', {})['independent'] = arr
        su = r.setdefault('meta', {}).setdefault('source_urls', [])
        if src not in su:
            su.append(src)
    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f'\n已写入 {len(hit)} 条 | 备份 -> {os.path.relpath(bk, ROOT)}')


if __name__ == '__main__':
    main()
