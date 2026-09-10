# -*- coding: utf-8 -*-
"""D40 · 抓取并提取 Artificial Analysis 榜单数据（flight 流）。

发现（2026-09-10）：`/api/v2/data/llms/models` 返回 401 需 key，但
`https://artificialanalysis.ai/leaderboards/models` 页面 200 / 2.75MB，
数据以 Next.js App Router flight 流内嵌，含 **644 个模型**的完整字段：
  slug / name / shortName / deprecated / isReasoning / isOpenWeights
  creator.name / releaseDate（**精确到日**） / release.slug
  intelligenceIndex / omniscience / gdpvalNormalized / analystAgent
  terminalbenchHard / terminalbenchV21 / terminalbenchV40 / tau2 / tauBanking
  lcr / hle / gpqa / scicode / ifbench / critpt / apexAgents / itbenchSre / mmmuPro
  price1mInputTokens / price1mOutputTokens / cacheHitPrice / cacheWritePrice
  medianOutputTokensPerSecond / contextWindowTokens

产出：temp/d40_aa_models.json（原始 644 条）
用法：python temp/d40_aa_fetch.py
"""
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = os.path.join(ROOT, 'temp')
URL = 'https://artificialanalysis.ai/leaderboards/models'
HTML = os.path.join(TEMP, 'aa_leaderboard.html')
OUT = os.path.join(TEMP, 'd40_aa_models.json')

FLIGHT_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')


def fetch():
    r = subprocess.run(['curl', '-sS', '--ssl-no-revoke', '-L', '--max-time', '90',
                        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/120 Safari/537.36',
                        '-o', HTML, '-w', '%{http_code}', URL],
                       capture_output=True, timeout=120)
    print('HTTP', r.stdout.decode().strip(), '| bytes', os.path.getsize(HTML))


def load_flight():
    raw = open(HTML, encoding='utf-8', errors='replace').read()
    parts = []
    for m in FLIGHT_RE.finditer(raw):
        try:
            parts.append(json.loads(m.group(1)))
        except Exception:
            pass
    return ''.join(parts)


def slice_objects(stream):
    """按括号平衡切出所有以 {"slug": 开头的 JSON 对象。

    AA 把数据拆成**两类对象**，必须都取再按 slug join：
      类 A（元数据）：slug / name / shortName / releaseDate / creator / deprecated / isReasoning
      类 B（评测）  ：slug / shortName / intelligenceIndex / gpqa / hle / 价格 / 吞吐
    """
    out = []
    for m in re.finditer(r'\{"slug":"', stream):
        start = m.start()
        depth = 0
        in_str, esc = False, False
        for i in range(start, min(len(stream), start + 120000)):
            ch = stream[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    blk = stream[start:i + 1]
                    try:
                        out.append(json.loads(blk))
                    except Exception:
                        pass
                    break
    return out


def main():
    if not os.path.exists(HTML) or os.environ.get('AA_REFETCH'):
        fetch()
    else:
        print('复用已有', os.path.relpath(HTML, ROOT))

    stream = load_flight()
    print('flight 流长度:', len(stream))

    objs = slice_objects(stream)
    print('切出对象:', len(objs))

    # 按 slug join 两类对象
    merged = {}
    for o in objs:
        s = o.get('slug')
        if not s:
            continue
        cur = merged.setdefault(s, {'slug': s})
        for k, v in o.items():
            if v is not None and (cur.get(k) is None):
                cur[k] = v
            elif k not in cur:
                cur[k] = v
    uniq = list(merged.values())
    print('按 slug 归并后:', len(uniq))

    scored = [o for o in uniq if o.get('intelligenceIndex') is not None]
    print('含 intelligenceIndex:', len(scored))
    withdate = [o for o in uniq if o.get('releaseDate')]
    print('含 releaseDate     :', len(withdate))
    withcreator = [o for o in uniq if o.get('creator')]
    print('含 creator         :', len(withcreator))

    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(uniq, f, ensure_ascii=False, indent=1)
    print('写入', os.path.relpath(OUT, ROOT))

    print()
    print('=== 样本（前 3）===')
    for o in uniq[:3]:
        print(json.dumps({k: o.get(k) for k in
                          ('slug', 'name', 'shortName', 'releaseDate', 'isOpenWeights',
                           'intelligenceIndex', 'gpqa', 'hle', 'mmmuPro')},
                         ensure_ascii=False))
    print()
    print('=== 厂商分布（creator.name）===')
    import collections
    c = collections.Counter(((o.get('creator') or {}).get('name') or '?') for o in uniq)
    for k, v in c.most_common(20):
        print(f'  {k[:30]:32s} {v}')
    print()
    print('=== releaseDate 覆盖 ===')
    n = sum(1 for o in uniq if o.get('releaseDate'))
    print(f'  有 releaseDate: {n}/{len(uniq)} ({n/len(uniq):.1%})')
    est = sum(1 for o in uniq if o.get('intelligenceIndexIsEstimated'))
    print(f'  intelligenceIndexIsEstimated=true: {est}')


if __name__ == '__main__':
    main()
