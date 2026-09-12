# -*- coding: utf-8 -*-
"""D44 · 抓取 ModelScope（魔搭）官方组织模型清单 + 主库比对（S0 探测，主库只读）。

发现（2026-09-13 实测）：魔搭有免鉴权结构化 JSON API，不需要 CDP 爬 DOM：
  · 搜索/列表  PUT https://modelscope.cn/api/v1/dolphin/models
      body: {"Name":"<org>/","PageSize":100,"PageNumber":1,"SortBy":"Default"}
      SortBy 合法枚举：Default(实测最新优先) / DownloadsCount / StarsCount / GmtModified
      ⚠ 无组织过滤参数（Owner/Author/Namespace/Publisher 全不生效，实测全站 253090 不变），
        只能 Name 前缀搜索 + 客户端按 Path==org 过滤（会混入 DevQuasar/mlx-community 等
        第三方上传，必须过滤，否则把社区量化当官方新仓库）。
  · 详情      GET https://modelscope.cn/api/v1/models/{org}/{name}
      （License / Tasks / CreatedTime / ModelInfos.safetensors.model_size / tensor_type）
  · 仓库文件  GET .../repo?Revision=master&FilePath=config.json
      （max_position_embeddings=上下文长度、n_routed_experts=MoE 判据、quantization_config）

口径红线（沿用 跟踪源清单.md §3/§4 与 D40 教训）：
  · CreatedTime 是**仓库创建日**（同 HF createdAt），只能当"上架线索"，不是 release_date；
  · 只收 ORGS 白名单官方组织；AI-ModelScope / DevQuasar / mlx-community 等镜像/社区组织不收；
  · 候选一律标 T2（仓库一手线索，官方发布日待核）；名字含 gguf/mlx/awq/gptq 等量化标记的不报；
  · 与主库匹配只走 canon 精确匹配（D40：fuzzy 已弃用）；
  · model_size 是权重字节数**不是参数量**，只作推导参考（fp8≈1B/byte、bf16≈2B/byte），
    total_params_b 的导入仍回官方声明/README。

产物（全部落 temp/，不写主库）：
  ① temp/d44_modelscope_repos.json     原始快照（各官方组织仓库卡片，含被过滤项计数）
  ② temp/d44_msscope_candidates.jsonl  漏采线索（S0 六字段 + 附加列，since 之后的),
                                       可直接喂 candidate_diff.py
  ③ temp/d44_msscope_backlog.jsonl     同口径但 created < since 的存量未采（长尾/变体，人工看）
  ④ temp/d44_msscope_fillplan.json     补全候选（主库 open_weights 空字段 ↔ 魔搭 config/detail）

用法：
  PYTHONUTF8=1 python scripts/d44_fetch_modelscope.py                # 全量抓取+比对
  PYTHONUTF8=1 python scripts/d44_fetch_modelscope.py --since 2026-08-01
  PYTHONUTF8=1 python scripts/d44_fetch_modelscope.py --skip-fetch   # 复用已有快照重新比对
"""
import argparse
import collections
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = os.path.join(ROOT, 'temp')
MAIN = os.path.join(ROOT, 'model_data_v2.jsonl')
BASE = 'https://modelscope.cn'
DOLPHIN = BASE + '/api/v1/dolphin/models'
OUT_REPOS = os.path.join(TEMP, 'd44_modelscope_repos.json')
OUT_CANDS = os.path.join(TEMP, 'd44_msscope_candidates.jsonl')
OUT_BACKLOG = os.path.join(TEMP, 'd44_msscope_backlog.jsonl')
OUT_FILL = os.path.join(TEMP, 'd44_msscope_fillplan.json')

# 官方组织白名单（org → 主库 vendor 写法，vendor 必须与主库 basic_info.vendor 一致，
# 否则 candidate_diff.py 的同厂判定失效）。org 写错跑出来 own=0，改这里即可。
ORGS = {
    'deepseek-ai': 'DeepSeek',
    'Qwen': 'Alibaba',
    'ZhipuAI': 'Zhipu AI',
    'moonshotai': 'Moonshot AI',
    'Tencent-Hunyuan': 'Tencent',
    'MiniMax': 'MiniMax',
    'Shanghai_AI_Laboratory': 'Shanghai AI Laboratory',
    'inclusionAI': 'inclusionAI',
    'nex-agi': 'nex-agi',
    'meituan-longcat': 'Meituan',
    'XiaomiMiMo': 'Xiaomi',
    'OpenBMB': 'ModelBest',
    'stepfun-ai': 'StepFun',
    '01ai': '01.AI',
    'PaddlePaddle': 'Baidu',
    'baichuan-inc': 'Baichuan',
    'Skywork': 'Kunlun Tech',
    'openmoss': 'OpenMOSS',
    'BAAI': 'BAAI',
    'langboat': 'Langboat',
    'microsoft': 'Microsoft',
}
# 注（2026-09-13 实测）：魔搭组织名**大小写敏感**（OpenMOSS own=0、openmoss 命中）。
# THUDM/InternLM 的模型分别在 ZhipuAI / Shanghai_AI_Laboratory 组织下，不重复挂；
# NVIDIA 在魔搭无官方组织（只有 nv-community 等镜像），继续走 HF。

# 只收文本类任务（LLM/VL）；图/视频/语音生成不收（§3：非模型红线），没见过的任务名
# 不丢——进 EXCLUDED_TASKS 计数，在汇总里可见，避免静默漏报。
TASK_WHITELIST = {
    'text-generation', 'text2text-generation', 'image-text-to-text',
    'visual-question-answering', 'image-to-text', 'any-to-any',
    'multimodal-generation', 'any-to-text',
}
# 量化/推理引擎变体标记（§3：量化变体不单独立行）。注意 -FP8 官方原生权重不在列——
# canon() 会剥掉 -fp8 后缀并入主记录，无需在此拦。
QUANT_RE = re.compile(r'(gguf|mlx|awq|gptq|int4|int8|w8a8|w4a16|nvfp4|onnx|smashed|'
                      r'enum|mindie|tensorrt)', re.I)

# ---- canon 归一：逐字复制 d40_aa_import.py（D40 定死的口径，勿单方面改） ----
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


# ---- HTTP ----
def http_json(url, payload=None, method=None, timeout=25, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8') if payload is not None else None,
                headers={'Content-Type': 'application/json',
                         'User-Agent': 'Mozilla/5.0 (model_data D44 probe)'},
                method=method or ('PUT' if payload is not None else 'GET'))
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise last


def search_org(org, page_size=100, max_pages=20):
    """Name 前缀搜索翻页 + 客户端 Path==org 过滤。返回 (搜索总命中, 本组织仓库列表)。"""
    got, page = [], 1
    total = None
    while page <= max_pages:
        d = http_json(DOLPHIN, {'Name': f'{org}/', 'PageSize': page_size,
                                'PageNumber': page, 'SortBy': 'Default'})
        if not d.get('Success'):
            raise RuntimeError(f'dolphin API: {d.get("Message")}')
        m = (d.get('Data') or {}).get('Model') or {}
        items = m.get('Models') or []
        total = m.get('TotalCount')
        got.extend(items)
        if not items or (total is not None and len(got) >= total):
            break
        page += 1
        time.sleep(0.3)
    return total, [x for x in got if x.get('Path') == org]


def fetch_config(org, name):
    """仓库 config.json（老的 swift 仓库退而求 configuration.json）。"""
    for fp in ('config.json', 'configuration.json'):
        url = (f'{BASE}/api/v1/models/{urllib.parse.quote(org, safe="")}/'
               f'{urllib.parse.quote(name, safe="")}/repo?Revision=master&FilePath={fp}')
        try:
            return http_json(url), fp
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    return None, None


def find_ctx(cfg):
    keys = ('max_position_embeddings', 'max_sequence_length', 'max_seq_len',
            'n_positions', 'context_length')
    for scope, c in (('', cfg), ('text_config.', cfg.get('text_config') or {})):
        if not isinstance(c, dict):
            continue
        for k in keys:
            if isinstance(c.get(k), int) and c[k] > 0:
                return (scope + k), c[k]
    return None, None


def arch_of(cfg):
    n_exp = (cfg.get('n_routed_experts') or cfg.get('num_routed_experts')
             or cfg.get('num_local_experts') or cfg.get('num_experts'))
    if n_exp:
        per_tok = cfg.get('num_experts_per_tok') or cfg.get('num_experts_per_topk')
        return 'MoE', f'n_routed_experts={n_exp}, per_tok={per_tok}'
    if cfg.get('num_hidden_layers'):
        return 'Dense', f"num_hidden_layers={cfg['num_hidden_layers']}"
    return None, None


def params_evidence(model_size, tensor_types):
    """字节数 → 参数量推导范围（仅参考，不入库）。"""
    if not model_size:
        return None
    types = set(tensor_types or [])
    fp8 = bool(types & {'F8_E4M3', 'F8_E8M0', 'FP8'})
    lo, hi = model_size / 2e9, (model_size / 1e9 if fp8 else model_size / 2e9)
    return {'model_size_bytes': model_size, 'tensor_type': sorted(types),
            'derived_params_b_range': [round(lo, 1), round(hi, 1)],
            'note': '按字节数推导（bf16≈2B/param、fp8≈1B/param），非官方声明，'
                    '仅作量级参考；total_params_b 导入仍回官方声明/README'}


def slim_repo(x):
    mi = (x.get('ModelInfos') or {}) if isinstance(x.get('ModelInfos'), dict) else {}
    st = mi.get('safetensors') or {}
    tasks = [t.get('Name') for t in (x.get('Tasks') or []) if t.get('Name')]
    return {
        'org': x.get('Path'), 'name': x.get('Name'),
        'tasks': tasks, 'license': x.get('License'),
        'created': x.get('CreatedTime'), 'last_updated': x.get('LastUpdatedTime'),
        'downloads': x.get('Downloads'), 'stars': x.get('Stars'),
        'architectures': x.get('Architectures'),
        'model_size_bytes': st.get('model_size'),
        'tensor_type': st.get('tensor_type'),
    }


def iso(ts):
    if isinstance(ts, (int, float)) and ts > 0:
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    return None


# ---- 主库 ----
def load_ledger():
    """返回 (records, canon 索引)。索引键：canon(family)、canon(family-variant)、canon(full_name)。"""
    records, index = [], collections.defaultdict(set)   # canon -> {id(r)}
    for line in open(MAIN, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        records.append(r)
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if mid.count(':') >= 1 else mid
        var = mid.split(':')[2] if mid.count(':') >= 2 else ''
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        for key in filter(None, [canon(fam),
                                 canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                                 canon(fn)]):
            index[key].add(id(r))
    return records, index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', default='2026-08-01',
                    help='candidates/backlog 分界（ISO 日期，默认 2026-08-01）')
    ap.add_argument('--max-detail', type=int, default=400,
                    help='fillplan 阶段 detail/config 补拉的总封顶')
    ap.add_argument('--orgs', default='', help='逗号分隔，覆盖 ORGS 白名单')
    ap.add_argument('--skip-fetch', action='store_true', help='复用已有快照，不重新抓列表')
    args = ap.parse_args()

    orgs = {k: ORGS[k] for k in (args.orgs.split(',') if args.orgs else ORGS)}
    since_ts = datetime.datetime.strptime(args.since, '%Y-%m-%d').timestamp()

    # ① 组织清单抓取
    if args.skip_fetch and os.path.exists(OUT_REPOS):
        snap = json.load(open(OUT_REPOS, encoding='utf-8'))
        print(f"[skip-fetch] 复用快照 {OUT_REPOS}（fetched_at={snap.get('fetched_at')}）")
        repos_all = snap['repos']
        org_stat = snap['org_stat']
    else:
        repos_all, org_stat = [], {}
        for org, vendor in orgs.items():
            try:
                total, own = search_org(org)
            except Exception as e:
                print(f'  {org:26s} ERR {e}')
                org_stat[org] = {'vendor': vendor, 'error': str(e)}
                continue
            slim = [slim_repo(x) for x in own]
            repos_all.extend(slim)
            org_stat[org] = {'vendor': vendor, 'search_total': total, 'own_count': len(slim)}
            print(f'  {org:26s} 搜索命中 {str(total):>6s}  本组织 {len(slim):>4d}')
            time.sleep(0.3)
        snap = {'fetched_at': datetime.datetime.now().isoformat(timespec='seconds'),
                'api_note': 'Name="<org>/" 前缀搜索 + Path==org 客户端过滤；CreatedTime=仓库创建日非发布日',
                'org_stat': org_stat, 'repos': repos_all}
        json.dump(snap, open(OUT_REPOS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'快照 -> {os.path.relpath(OUT_REPOS, ROOT)}')

    bad = {o: s for o, s in org_stat.items() if not s.get('own_count')}
    for org in bad:
        print(f'⚠ {org} own=0：组织名可能写错（改脚本顶部 ORGS），或该组织在魔搭无公开仓库')

    # ② 比对主库
    records, index = load_ledger()
    task_tally = collections.Counter()
    rows = []
    for x in repos_all:
        tasks = x.get('tasks') or []
        hit = next((t for t in tasks if t in TASK_WHITELIST), None)
        if not hit:
            task_tally[tasks[0] if tasks else '(无任务标记)'] += 1
            continue
        if QUANT_RE.search(x.get('name') or ''):
            task_tally['(量化/引擎变体，按§3不报)'] += 1
            continue
        c = canon(x.get('name'))
        if not c or c in index:
            continue
        ts = x.get('created') or 0
        rows.append((ts, c, x, hit))
    # 同家族去重：① canon 相同（-fp8/-chat 等尾缀被 canon 剥掉）→ 取下载量最高的代表仓，
    # 其余记进 variants；② 剥 -fp4/-fp8/-bf16 后命中主库或其他候选 → 按 §3 并入，不单列
    QUANT_TAIL = re.compile(r'-(fp4|fp8|bf16|fp16|int8)$', re.I)
    by_canon = collections.defaultdict(list)
    for ts, c, x, hit in rows:
        by_canon[c].append((ts, x, hit))
    cand_canons = set(by_canon)
    cands, backlog = [], []
    for c, grp in by_canon.items():
        grp.sort(key=lambda t: -(t[1].get('downloads') or 0))
        ts, x, hit = grp[0]
        base = QUANT_TAIL.sub('', c)
        if base != c and (base in cand_canons or base in index):
            task_tally[f'(量化变体并入 {x.get("name")})'] += 1
            continue
        row = {
            'name': x.get('name'), 'vendor': orgs.get(x.get('org'), x.get('org')),
            'release_date': iso(ts),
            'tier': 'T2',
            'evidence': f'{BASE}/models/{x.get("org")}/{x.get("name")}',
            'note': (f'魔搭官方组织仓库（创建日=仓库创建日，非发布日，待核）；'
                     f'task={hit}; downloads={x.get("downloads")}; stars={x.get("stars")}'),
            'org': x.get('org'), 'task': hit, 'downloads': x.get('downloads'),
            'stars': x.get('stars'), 'license': x.get('license'),
        }
        if len(grp) > 1:
            row['variants'] = [f"{g[1].get('name')}({iso(g[0])})" for g in grp[1:]]
            row['note'] += f'; 同canon变体{len(grp) - 1}个（fp8/量化等，§3 并入不单列）'
        (cands if ts >= since_ts else backlog).append((ts, row))
    cands.sort(key=lambda t: -t[0])
    backlog.sort(key=lambda t: -t[0])
    with open(OUT_CANDS, 'w', encoding='utf-8', newline='\n') as f:
        for _, row in cands:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    with open(OUT_BACKLOG, 'w', encoding='utf-8', newline='\n') as f:
        for _, row in backlog:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    # ③ 补全候选：open_weights 且有空字段的记录 ←→ 魔搭 config.json
    ms_canon_lists = collections.defaultdict(list)
    for x in repos_all:
        if x.get('tasks') and not set(x['tasks']) & TASK_WHITELIST:
            continue
        c = canon(x.get('name'))
        if c:
            ms_canon_lists[c].append(x)

    def _chat_flavor(name):
        return bool(re.search(r'-(chat|instruct|it)$', name or '', re.I))

    def pick_repo(canon_key, variant):
        """同 canon 多仓库时，选与主库 variant 风味一致的（base 记录优先无 -Chat 仓库）。"""
        lst = ms_canon_lists.get(canon_key) or []
        if not lst:
            return None
        if len(lst) > 1:
            want = variant.lower() not in ('base', 'none', '')
            lst = sorted(lst, key=lambda x: _chat_flavor(x.get('name')) != want)
        return lst[0]

    plan, budget, matched_null = [], args.max_detail, 0
    for r in records:
        arch = r.get('architecture') or {}
        acc = (r.get('basic_info') or {}).get('access') or {}
        if not acc.get('open_weights'):
            continue
        want = []
        if arch.get('context_window_tokens') is None:
            want.append('context_window_tokens')
        if arch.get('architecture_type') in (None, 'Unknown'):
            want.append('architecture_type')
        if arch.get('total_params_b') is None:
            want.append('total_params_b(仅推导参考)')
        if not want:
            continue
        mid = r.get('model_id') or ''
        fam = mid.split(':')[1] if ':' in mid else mid
        var = mid.split(':')[2] if mid.count(':') >= 2 else ''
        fn = (r.get('basic_info') or {}).get('full_name') or ''
        hit = None
        for key in filter(None, [canon(fam),
                                 canon(f'{fam}-{var}') if var.lower() not in ('base', 'none', '') else None,
                                 canon(fn)]):
            hit = pick_repo(key, var)
            if hit:
                break
        if not hit:
            continue
        matched_null += 1
        org, name = hit['org'], hit['name']
        entry = {'model_id': mid, 'ms_repo': f'{org}/{name}',
                 'ms_url': f'{BASE}/models/{org}/{name}', 'nulls': want,
                 'license_ms': hit.get('license'),
                 'params_evidence': params_evidence(hit.get('model_size_bytes'),
                                                    hit.get('tensor_type'))}
        if budget > 0 and (arch.get('context_window_tokens') is None
                           or arch.get('architecture_type') in (None, 'Unknown')):
            budget -= 1
            try:
                cfg, fp = fetch_config(org, name)
                time.sleep(0.15)
            except Exception as e:
                cfg, fp = None, f'ERR {e}'
            if isinstance(cfg, dict):
                k, v = find_ctx(cfg)
                if k:
                    entry['ctx_candidate'] = {
                        'value': v, 'key': k, 'source': f'{fp}@master',
                        'confidence': 'T2',
                        'note': '权重仓库事实（线上 API/官方服务可能另有限制），导入需在 notes 标注来源'}
                a, ev = arch_of(cfg)
                if a:
                    entry['arch_candidate'] = {'value': a, 'evidence': ev, 'source': fp}
                entry['config_top_keys'] = sorted(cfg.keys())[:24]
            elif fp:
                entry['config_error'] = str(fp)
        plan.append(entry)

    fill = {'fetched_at': snap.get('fetched_at'),
            'open_weights_null_matched': matched_null, 'plan': plan}
    json.dump(fill, open(OUT_FILL, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # ④ 汇总
    print()
    print('=== 汇总 ===')
    print(f'组织：{len(org_stat)} 个，其中 own=0 警告 {len(bad)} 个；'
          f'仓库快照共 {len(repos_all)} 条')
    print(f'漏采线索（>={args.since}）：{len(cands)} 条 -> {os.path.basename(OUT_CANDS)}')
    print(f'存量未采（<{args.since}）：{len(backlog)} 条 -> {os.path.basename(OUT_BACKLOG)}')
    print(f'补全候选：open_weights 空字段且魔搭命中 {matched_null} 条'
          f'（config 补拉 {args.max_detail - budget} 次）-> {os.path.basename(OUT_FILL)}')
    ctx_n = sum(1 for p in plan if p.get('ctx_candidate'))
    arch_n = sum(1 for p in plan if p.get('arch_candidate'))
    print(f'  其中 ctx 可补 {ctx_n} 条 / arch_type 可判 {arch_n} 条')
    if task_tally:
        print('被过滤任务/变体（可见性，不写文件）：')
        for t, n in task_tally.most_common():
            print(f'  {n:4d}  {t}')
    print()
    print('(dry-run：以上均为 temp/ 候选，未写主库。导入另行走 S1 拍板 + S2/S3 流程)')


if __name__ == '__main__':
    main()
