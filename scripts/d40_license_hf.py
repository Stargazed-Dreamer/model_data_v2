# -*- coding: utf-8 -*-
"""D40 · A 类 #5：open_weights=true 但 basic_info.license 空 → 用 HF API 权威补全。

方案（优于 D32 原议的「按 vendor 推断协议」）：
  ① 从记录已有文本里提取 HuggingFace repo id（多种写法：huggingface.co/x/y、HF 仓库: x/y、
     HuggingFace (x/y)、Hugging Face x/y …）
  ② 调 HF API `https://huggingface.co/api/models/{repo}`，读 `tags` 里的 `license:X`
     —— 这是模型卡上的**权威声明**，不是推断
  ③ 归一后写入 basic_info.license（保留厂商限定后缀），notes 记来源
  ④ 拿不到 repo / API 无 license 的：**留空**（宁缺勿错），列入待重采

铁证校正：license 在 `basic_info.license`，非 `basic_info.access.license`（后者全库 0 条）。
本机 curl 必须带 --ssl-no-revoke。

用法：
  python temp/d40_license_hf.py            # dry-run（会真实调用 HF API 但只打印）
  python temp/d40_license_hf.py --apply
"""
import json
import os
import re
import sys
import ssl
import time
import shutil
import datetime
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BACKUP_DIR = os.path.join(ROOT, 'backups')
APPLY = '--apply' in sys.argv
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

REPO_RE = re.compile(
    r'(?:huggingface\.co/|HF\s*(?:仓库|模型卡|repo)?\s*[:：]?\s*|Hugging\s*Face\s*[:：]?\s*\(?\s*|'
    r'HuggingFace\s*[:：]?\s*\(?\s*)([A-Za-z0-9][A-Za-z0-9_.\-]*/[A-Za-z0-9][A-Za-z0-9_.\-]*)')
# 结果必须是 owner/name 形态且不像 URL 片段
BAD_REPO = re.compile(r'^(api|models|datasets|spaces|orgs|blog|docs)/', re.I)

CANON = {'apache-2.0': 'Apache 2.0', 'mit': 'MIT', 'gpl-3.0': 'GPL-3.0',
         'bsd-3-clause': 'BSD-3-Clause', 'cc-by-nc-4.0': 'CC-BY-NC 4.0',
         'cc-by-4.0': 'CC-BY 4.0', 'openrail': 'OpenRAIL', 'other': 'other',
         'cc-by-nc-sa-4.0': 'CC-BY-NC-SA 4.0', 'cc-by-sa-4.0': 'CC-BY-SA 4.0',
         'llama2': 'Llama 2 Community', 'llama3': 'Llama 3 Community',
         'llama3.1': 'Llama 3.1 Community', 'llama3.2': 'Llama 3.2 Community',
         'llama4': 'Llama 4 Community', 'gemma': 'Gemma Community License',
         'bigscience-bloom-rail-1.0': 'BigScience BLOOM RAIL 1.0'}


def hf_license(repo, cache):
    if repo in cache:
        return cache[repo]
    url = f'https://huggingface.co/api/models/{repo}'
    try:
        out = subprocess.run(
            ['curl', '-sS', '--ssl-no-revoke', '--max-time', '30', url],
            capture_output=True, timeout=40)
        data = json.loads(out.stdout.decode('utf-8', 'replace') or '{}')
    except Exception:
        data = {}
    lic = None
    for t in (data.get('tags') or []):
        if isinstance(t, str) and t.lower().startswith('license:'):
            lic = t.split(':', 1)[1].strip()
            break
    if not lic:
        cd = data.get('cardData') or {}
        lic = cd.get('license')
    cache[repo] = lic
    return lic


def repo_matches_model(repo, mid, full_name):
    """校验 repo 与模型是否为同一对象，防错配。

    实测错配：`g42:jais-70b` 匹配到 `inception42/jais-13b`（70B vs 13B）、
    `sber:fred-t5-xl` 匹配到 `ai-forever/FRED-T5-1.7B`。判据：
      ① 尺寸标识（NNb / N.Nb / NxNb）双方都有且不一致 → 判否
      ② 否则要求共享至少一个长度 >= 4 的字母数字 token
    """
    repo_model = repo.split('/', 1)[-1]

    def toks(s):
        return {t for t in re.split(r'[^a-z0-9]+', (s or '').lower()) if len(t) >= 3}

    def sizes(s):
        out = set()
        for m in re.finditer(r'(\d+(?:\.\d+)?)\s*b(?!\w)', (s or '').lower()):
            out.add(m.group(1))
        return out

    rs, ms = sizes(repo_model), sizes(mid) | sizes(full_name)
    # 尺寸判据用「交集为空即拦」而非「必须相等」：主库 `mamba-2-2-7b` 会解析出 {2.7, 7}，
    # 而 HF repo `mamba2-2.7b` 只有 {2.7}——要求相等会误伤同模型（实测误伤 4 条）。
    # 真错配（jais-70b vs jais-13b：{70} vs {13}）交集为空，仍被拦下。
    if rs and ms and not (rs & ms):
        return False, 'size-conflict %s vs %s' % (sorted(rs), sorted(ms))
    shared = toks(repo_model) & (toks(mid) | toks(full_name))
    if shared:
        return True, 'shared-token %s' % sorted(shared)[:3]
    return False, 'no-shared-token'


def main():
    rows = [json.loads(l) for l in open(MAIN, encoding='utf-8') if l.strip()]

    def ow(r):
        return ((r.get('basic_info') or {}).get('access') or {}).get('open_weights')

    targets = [r for r in rows if ow(r) is True and not (r.get('basic_info') or {}).get('license')]
    print('待补记录:', len(targets))
    print()

    cache = {}
    plan, no_repo, no_lic, mismatch = [], [], [], []
    for r in targets:
        b = r.get('basic_info') or {}
        acc = b.get('access') or {}
        blob = ' '.join(filter(None, [acc.get('notes'), b.get('notes'),
                                      (r.get('architecture') or {}).get('notes'),
                                      (r.get('meta') or {}).get('notes')]))
        repo, lic = None, None
        for m in REPO_RE.finditer(blob or ''):
            cand = m.group(1).rstrip('.')
            if BAD_REPO.match(cand):
                continue
            got = hf_license(cand, cache)
            time.sleep(0.4)
            if got:
                repo, lic = cand, got
                break
            if repo is None:
                repo = cand
        if not repo:
            no_repo.append(r)
            continue
        if not lic:
            no_lic.append((r, repo))
            continue
        ok, why = repo_matches_model(repo, r.get('model_id') or '',
                                     (r.get('basic_info') or {}).get('full_name') or '')
        if not ok:
            mismatch.append((r, repo, lic, why))
            continue
        val = CANON.get(lic.lower().strip(), lic)
        plan.append((r, val, repo))

    print('=== 分档 ===')
    print(f'  能补（HF API 拿到 license 且 repo 校验通过）: {len(plan)}')
    print(f'  repo 校验不通过（防错配，不写）           : {len(mismatch)}')
    print(f'  提取到 repo 但 API 无 license             : {len(no_lic)}')
    print(f'  提取不到 repo                             : {len(no_repo)}')
    print()
    print('=== 可补明细 ===')
    for r, v, repo in plan:
        print(f'  {v[:34]:36s} <- {repo[:44]:46s} ({r.get("model_id")[:34]})')
    print()
    if mismatch:
        print('=== repo 校验不通过（不写，待人工）===')
        for r, repo, lic, why in mismatch:
            print(f'  {r.get("model_id")[:40]:42s} repo={repo[:40]:42s} {why}')
        print()
    if no_lic:
        print('=== repo 有但 API 无 license ===')
        for r, repo in no_lic:
            print(f'  {repo[:50]:52s} {r.get("model_id")[:38]}')

    if APPLY:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        bk = os.path.join(BACKUP_DIR, f'model_data_v2.pre-d40-licensehf-{TS}.jsonl')
        shutil.copy2(MAIN, bk)
        for r, v, repo in plan:
            b = r.setdefault('basic_info', {})
            b['license'] = v
            note = (f'【D40 补 license】值取自 HuggingFace 模型卡 {repo} 的 license 标签'
                    f'（HF API 直读，非推断）。')
            b['notes'] = ((b.get('notes') or '') + ' ' + note).strip()
        with open(MAIN, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n')
        print()
        print(f'已写入 {len(plan)} 条 | 备份 -> {os.path.relpath(bk, ROOT)}')
    else:
        print()
        print('(dry-run，未写入)')


if __name__ == '__main__':
    main()
