# -*- coding: utf-8 -*-
"""D39 · 抓取 DataLearner/arena 文本类榜单并保存为中间 JSON。

固化自 temp/d39_dl_fetch.py（D39 当天生效版），因 temp/ 会被清理。

用法: python scripts/d39_fetch_arena_leaderboard.py
产出: temp/d39_arena_raw.json   （供 scripts/d39_import_arena_elo.py 消费）
        temp/dl_pg_{text,coding,math}.html  （原始页面留档）
"""
import re, json, subprocess, os, sys

BASE = 'https://www.datalearner.com'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = os.path.join(ROOT, 'temp')
os.makedirs(TEMP, exist_ok=True)
TARGETS = {
    'text':   'leaderboards/external/text-generation',
    'coding': 'leaderboards/external/text-generation-coding',
    'math':   'leaderboards/external/text-generation-math',
}
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def fetch(url, out):
    cmd = ['curl', '-sS', '--ssl-no-revoke', '-L', '--max-time', '60',
           '-A', UA, url, '-o', out]
    subprocess.run(cmd, check=True)
    return os.path.getsize(out)


def load_flight(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    out = []
    for m in re.finditer(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', raw):
        try:
            out.append(json.loads(m.group(1)))
        except Exception:
            pass
    return ''.join(out)


def extract_table(s, key='"modelName"'):
    pos = s.find(key)
    if pos < 0:
        return []
    start = s.rfind('"data":[', max(0, pos - 300000), pos)
    if start < 0:
        return []
    i = s.index('[', start)
    depth = 0; j = i; in_str = False; esc = False
    while j < len(s):
        c = s[j]
        if in_str:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == '[': depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0: break
        j += 1
    try:
        rows = json.loads(s[i:j+1])
    except Exception:
        return []
    return rows if rows and isinstance(rows[0], dict) and 'modelName' in rows[0] else []


def main():
    result = {}
    for name, path in TARGETS.items():
        html = os.path.join(TEMP, f'dl_pg_{name}.html')
        n = fetch(f'{BASE}/{path}', html)
        s = load_flight(html)
        raw = open(html, encoding='utf-8', errors='replace').read()
        rows = extract_table(s)
        # 快照日期：页面 lead 的 ld+json 给 dateModified；flight 流里的 meta 更全但常缺
        vt = (re.search(r'"versionTime":"([^"]*)"', s)
              or re.search(r'"dateModified":"([^"]*)"', raw)
              or re.search(r'"dateModified":"([^"]*)"', s))
        tv = re.search(r'"totalVotes":"([^"]*)"', s)
        tm = re.search(r'"totalModels":(\d+)', s)
        ds = re.search(r'"dataSource":"([^"]*)"', s)
        dsu = (re.search(r'"dataSourceUrl":"([^"]*)"', s)
               or re.search(r'"contentUrl":"([^"]*)"', raw)
               or re.search(r'"url":"(https://arena\.ai[^"]*)"', s))
        result[name] = {
            'path': path,
            'url': f'{BASE}/{path}',
            'html_bytes': n,
            'version_time': vt.group(1) if vt else None,
            'total_votes': tv.group(1) if tv else None,
            'total_models': int(tm.group(1)) if tm else None,
            'data_source': ds.group(1) if ds else None,
            'data_source_url': dsu.group(1) if dsu else None,
            'rows': rows,
        }
        print(f'{name:8s} rows={len(rows):4d}  snapshot={result[name]["version_time"]}  '
              f'votes={result[name]["total_votes"]}  src={result[name]["data_source"]}')

    # 主榜另有 JSON API（免鉴权），其 meta 比页面内嵌数据更全（总票数 / 总模型数 / 官方数据源）
    try:
        api_url = f'{BASE}/api/leaderboards/external/text-generation'
        api_file = os.path.join(TEMP, 'dlapi_text-generation.json')
        fetch(api_url, api_file)
        meta = (json.load(open(api_file, encoding='utf-8')).get('meta') or {})
        t = result.get('text') or {}
        for src_k, dst_k in (('versionTime', 'version_time'), ('totalVotes', 'total_votes'),
                             ('totalModels', 'total_models'), ('dataSource', 'data_source'),
                             ('dataSourceUrl', 'data_source_url')):
            if meta.get(src_k):
                t[dst_k] = meta[src_k]
        result['text'] = t
        print(f'[api] text 榜 meta：snapshot={t.get("version_time")} votes={t.get("total_votes")} '
              f'models={t.get("total_models")} src={t.get("data_source")}')
    except Exception as e:
        print('[warn] 主榜 JSON API meta 获取失败（不影响榜单数据）:', e)

    out = os.path.join(TEMP, 'd39_arena_raw.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print('saved ->', out)


if __name__ == '__main__':
    main()
