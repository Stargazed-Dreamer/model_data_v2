# -*- coding: utf-8 -*-
"""D47 · 导入 Artificial Analysis 观测价到主库 pricing（用户拍板：准入，T2 严格标注，只补空值）。

口径（D47 定死）：
  ① 匹配只走 canon **精确**匹配（D40 教训，fuzzy 弃用）；
  ② 只对 `pricing.input` 为空的记录整套补（input/output/cached_input/cache_write），
     官方价已存在的记录一律不动（口径：主库 pricing 首选官方刊例）；
  ③ AA 不提供 batch 价 → batch_input/batch_output 保持 null；
  ④ source_type=独立评测平台、confidence=T2、source_url=AA 模型页、currency=USD（AA 计价）；
  ⑤ notes 声明「观测价非官方刊例、榜单滚动更新、抓取日」。
数据：temp/d40_aa_models.json（D40 快照，735 条 / 435 条带输入价，字段实测 2026-09-13）。
用法：PYTHONUTF8=1 python scripts/d47_import_aa_price.py [--apply]
"""
import json
import os
import re
import shutil
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AA = os.path.join(ROOT, 'temp', 'd40_aa_models.json')
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

# 护栏④：vendor 等价组（ledger vendor ↔ AA creator.name 一致性）。
# 组内互认（alibaba/inclusionai 同为蚂蚁系，D41 归并产生并存写法）；首词兜底宽容新厂商。
ALIAS_GROUPS = [
    ('ant', ('alibaba', 'qwen', 'tongyi', 'inclusionai', 'ant', 'ling', 'ring')),
    ('zhipu', ('zhipu', 'zai', 'thudm', 'chatglm', 'glm')),
    ('moonshot', ('moonshot', 'kimi')),
    ('meta', ('meta', 'facebook', 'llama', 'muse')),
    ('google', ('google', 'deepmind', 'gemma', 'gemini')),
    ('nvidia', ('nvidia', 'nemotron')),
    ('xiaomi', ('xiaomi', 'mimo')),
    ('ibm', ('ibm', 'granite')),
    ('mistral', ('mistral', 'mixtral')),
    ('microsoft', ('microsoft', 'phi', 'wizardlm')),
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
]


def _groups_of(s):
    s = (s or '').lower()
    out = set()
    for g, toks in ALIAS_GROUPS:
        if any(t in s for t in toks):
            out.add(g)
    words = re.sub(r'[^a-z0-9 ]', ' ', s).split()
    if words:
        out.add(words[0])                            # 首词兜底（新厂商/未注册名）
    return out


def vendor_ok(vendor, creator):
    """vendor/creator 任一缺失放行；都在则要求等价组交集（防跨厂商配价，如 perplexity:r1 ← deepseek-r1）。"""
    if not vendor or not creator:
        return True
    gv, gc = _groups_of(vendor), _groups_of(creator)
    if not gv or not gc:
        return True                                  # 识别不了 → 不拦（保守放行，靠人工抽验）
    return bool(gv & gc)


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
    aa = json.load(open(AA, encoding='utf-8'))
    # 三道护栏（D47 定死）：
    #   ① 0/0 占位价跳过（开源无 API 模型在 AA 的 $0 是"无观测"不是免费）；
    #   ② 同 canon 多条 AA 价不一致 → 该键歧义跳过（D39 红线：歧义一律跳过）；
    #   ③ flavor 错配跳过（ledger :base 配到 -instruct/-chat slug）。
    def priced(o):
        return isinstance(o.get('price1mInputTokens'), (int, float)) or \
               isinstance(o.get('price1mOutputTokens'), (int, float))

    def both_zero(o):
        return o.get('price1mInputTokens') == 0 and o.get('price1mOutputTokens') == 0

    def slug_flavor(slug):
        s = (slug or '').lower()
        if s.endswith('-base'):
            return 'base'
        if re.search(r'-(instruct|chat|it|thinking|think|reasoning)$', s):
            return 'chat'
        return None

    aa_by = {}
    aa_ambig = set()
    for o in aa:
        if not priced(o) or both_zero(o):
            continue
        c = canon(o.get('slug'))
        if not c:
            continue
        prev = aa_by.get(c)
        if prev is not None:
            same = (prev.get('price1mInputTokens') == o.get('price1mInputTokens')
                    and prev.get('price1mOutputTokens') == o.get('price1mOutputTokens'))
            if not same:
                aa_ambig.add(c)
            continue
        aa_by[c] = o
    for c in aa_ambig:
        aa_by.pop(c, None)

    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]

    plan, skipped_flavor, skipped_vendor = [], [], []
    for r in rows:
        p = r.get('pricing') or {}
        if p.get('input') is not None:
            continue                          # 官方价已在，整套不动
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if ':' in mid else mid
        var = mid.split(':')[2] if mid.count(':') >= 2 else ''
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        hit, hit_key = None, None
        for key in filter(None, [canon(fam),
                                 canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                                 canon(fn)]):
            if key in aa_by:
                hit, hit_key = aa_by[key], key
                break
        if not hit:
            continue
        # flavor 护栏：ledger 显式 -base 家族名配到 chat 型 slug → 跳过
        sf = slug_flavor(hit.get('slug'))
        if sf == 'chat' and var.lower() in ('base', '') and re.search(r'-(base)$', fam.lower()):
            skipped_flavor.append((mid, hit.get('slug')))
            continue
        # vendor 护栏：跨厂商错配（如 perplexity:r1 ← deepseek-r1）→ 跳过
        if not vendor_ok((r.get('basic_info') or {}).get('vendor'),
                         ((hit.get('creator') or {}) if isinstance(hit.get('creator'), dict) else {}).get('name')):
            skipped_vendor.append((mid, hit.get('slug'),
                                   ((hit.get('creator') or {}) if isinstance(hit.get('creator'), dict) else {}).get('name')))
            continue
        plan.append((r, hit))

    print(f'AA 带价 {sum(1 for o in aa if isinstance(o.get("price1mInputTokens"), (int, float)))} 条；'
          f'护栏后 canon 可用 {len(aa_by)} 键（歧义剔除 {len(aa_ambig)}）；'
          f'main 命中：{len(plan)} 条（flavor 错配跳过 {len(skipped_flavor)} / vendor 错配跳过 {len(skipped_vendor)}）')
    for m, s in skipped_flavor:
        print(f'  [flavor跳过] {m:46s} <- {s}')
    for m, s, c in skipped_vendor:
        print(f'  [vendor跳过] {m:46s} <- {s} (creator={c})')
    for r, o in plan:
        print(f'  {r.get("model_id"):46s} in={o.get("price1mInputTokens")} out={o.get("price1mOutputTokens")} '
              f'cache={o.get("cacheHitPrice")}/{o.get("cacheWritePrice")}  [{o.get("slug")}]')
    if not APPLY:
        print('\n(dry-run，未写入。加 --apply 落库)')
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d47-aaprice-{TS}.jsonl')
    shutil.copy2(MAIN, bk)
    for r, o in plan:
        p = r.setdefault('pricing', {})
        if isinstance(o.get('price1mInputTokens'), (int, float)):
            p['input'] = float(o['price1mInputTokens'])
        if isinstance(o.get('price1mOutputTokens'), (int, float)):
            p['output'] = float(o['price1mOutputTokens'])
        if isinstance(o.get('cacheHitPrice'), (int, float)):
            p['cached_input'] = float(o['cacheHitPrice'])
        if isinstance(o.get('cacheWritePrice'), (int, float)):
            p['cache_write'] = float(o['cacheWritePrice'])
        if p.get('currency') is None:
            p['currency'] = 'USD'
        if p.get('unit') is None:
            p['unit'] = 'per_million_tokens'
        if p.get('source_url') is None:
            p['source_url'] = f'https://artificialanalysis.ai/models/{o.get("slug")}'
        if p.get('source_type') is None:
            p['source_type'] = '独立评测平台'
        if p.get('confidence') is None:
            p['confidence'] = 'T2'
        note = (f'【D47 AA 观测价】input/output/缓存价由 Artificial Analysis 榜单观测价补全'
                f'（抓取日 {TODAY}，滚动更新值，非官方刊例；batch 价 AA 不提供维持 null）。')
        p['notes'] = ((p.get('notes') or '') + '；' if p.get('notes') else '') + note

    with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
    print(f'\n已写入 {len(plan)} 条 | 备份 -> {os.path.relpath(bk, ROOT)}')


if __name__ == '__main__':
    main()
