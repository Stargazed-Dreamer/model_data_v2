# -*- coding: utf-8 -*-
"""HF 批量查找：为 open_weights 且缺 HF 链接的记录匹配 HuggingFace 仓库。

用法:
    python hf_batch_lookup.py <start> <end>   # 处理 worklist[start:end]
    python hf_batch_lookup.py all             # 处理全部剩余

结果追加到 hf_lookup_progress.jsonl（model_id 去重，重跑安全）。
匹配规则: strict prefix（cand == target 或 cand.startswith(target)），
官方 org 加权 +0.3，量化/社区仓库惩罚，阈值 score > -0.2 且必须 prefix 命中。
"""
import json, subprocess, time, re, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # model_data 根目录
PATH = os.path.join(ROOT, 'model_data_v2.jsonl')
OUT = os.path.join(ROOT, 'intermediate', 'hf_lookup_progress.jsonl')
PROXY = 'socks5h://127.0.0.1:9909'

ORG_PREF = {
 'alibaba': ['Qwen', 'Alibaba-NLP', 'modelscope', 'iic'],
 'deepseek': ['deepseek-ai'],
 'google': ['google', 'google-deepmind'],
 'meta': ['meta-llama', 'facebook'],
 'mistral': ['mistralai'],
 'microsoft': ['microsoft'],
 'nvidia': ['nvidia'],
 'moonshot': ['moonshotai'],
 'minimax': ['minimaxai', 'minimax'],
 'ibm': ['ibm-granite', 'ibm-ai-platform', 'ibm'],
 'apple': ['apple'],
 'baidu': ['baidu'],
 'bytedance': ['bytedance', 'ByteDance-Seed'],
 'allen-institute-for-ai': ['allenai'],
 'allen-institute-for-ai-university-of-washington': ['allenai'],
 'lg-ai-research': ['lgai-exaone'],
 'tiiuae': ['tiiuae'],
 '01-ai': ['01-ai'],
 'xai': ['xai-org'],
 '360-security-technology': ['qihoo360'],
 'abacus-ai': ['abacusai'],
 'ai21': ['ai21labs'],
}

BAD = ['awq', 'gptq', 'exl2', 'int4', 'int8', '4bit', '8bit',
       'mlx', 'gguf', 'quantized', '-bnb', 'uncensored']


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def hf_search(query, limit=10):
    url = f"https://huggingface.co/api/models?search={query}&limit={limit}"
    out = subprocess.run(['curl', '-s', '-x', PROXY, '--max-time', '25', url],
                         capture_output=True, text=True)
    try:
        return json.loads(out.stdout)
    except Exception:
        return []


def pick(repo_list, model_id, full_name):
    parts = model_id.split(':')
    variant = parts[1] if len(parts) > 1 else full_name
    target = norm(variant)
    vendor = parts[0]
    best = None
    for m in repo_list:
        rid = m['id']
        cand = norm(rid.split('/')[-1])
        if cand != target and not cand.startswith(target):
            continue
        pen = sum(0.5 for b in BAD if b in cand)
        if any(k in rid.lower() for k in ('mlx-community', 'thebloke')):
            pen += 0.6
        org = rid.split('/')[0].lower()
        pref = ORG_PREF.get(vendor, [])
        bonus = 0.3 if any(p.lower() == org for p in pref) else 0
        score = bonus - pen - len(cand) * 0.001 + (0.1 if cand == target else 0)
        if best is None or score > best[0]:
            tags = [t for t in m.get('tags', []) if t.startswith('license:')]
            best = (score, {'hf_repo': rid,
                            'license_tag': tags[0] if tags else None,
                            'downloads': m.get('downloads'),
                            'likes': m.get('likes'),
                            'pipeline_tag': m.get('pipeline_tag'),
                            'created_at': m.get('createdAt'),
                            'match_score': round(score, 3)})
    return best


def load_done():
    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            for line in f:
                try:
                    done.add(json.loads(line)['model_id'])
                except Exception:
                    pass
    return done


def main():
    with open(PATH, encoding='utf-8') as f:
        recs = [json.loads(l) for l in f]
    done = load_done()
    work = [r for r in recs
            if (r['basic_info'].get('access') or {}).get('open_weights')
            and not any('huggingface.co' in u
                        for u in (r['meta'].get('source_urls') or []))
            and r['model_id'] not in done]

    if len(sys.argv) > 1 and sys.argv[1] != 'all':
        start, end = int(sys.argv[1]), int(sys.argv[2])
        batch = work[start:end]
    else:
        batch = work

    print(f'todo={len(work)} batch={len(batch)}')
    ok = 0
    with open(OUT, 'a', encoding='utf-8') as fo:
        for i, r in enumerate(batch):
            mid = r['model_id']
            name = r['basic_info'].get('full_name') or mid.split(':')[1]
            res = hf_search(name)
            b = pick(res, mid, name) if res else None
            row = {'model_id': mid, 'query': name,
                   **(b[1] if b else {'match_score': 0})}
            if b:
                ok += 1
            fo.write(json.dumps(row, ensure_ascii=False) + '\n')
            fo.flush()
            print(f"[{i+1}/{len(batch)}] {mid} -> {row.get('hf_repo', 'NO MATCH')}")
            time.sleep(0.35)
    print(f'DONE: {ok}/{len(batch)} matched')


if __name__ == '__main__':
    main()
