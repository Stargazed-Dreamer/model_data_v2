# -*- coding: utf-8 -*-
"""alibaba (Qwen) 批次定价写入"""
import json

BASE = r'F:/project_temp/localAgent/workspace/model_data/'
recs = [json.loads(l) for l in open(BASE + 'model_data_v2.jsonl', encoding='utf-8')]
SRC = 'https://help.aliyun.com/zh/model-studio/billing-for-model-studio'

def pr(inp, out, cached, note, promo=None, longctx=None):
    p = {'currency': 'CNY', 'unit': 'per_million_tokens', 'input': inp, 'output': out,
         'cached_input': cached, 'cache_write': None, 'batch_input': None, 'batch_output': None,
         'free_tier': '新用户开通百炼后 90 天内各模型有免费额度（以控制台为准）',
         'promotions': promo, 'long_context': None,
         'effective_date': '2026-08-25', 'source_url': SRC, 'source_type': '官方定价页核对', 'confidence': 'T0',
         'notes': note + '；来源：阿里云百炼计费文档（存档 raw_pages/aliyun_billing.html/.txt），华北2北京地域价'}
    if longctx:
        p['long_context'] = longctx
    return p

def ann(stype, note):
    return {'currency': None, 'unit': 'per_million_tokens', 'input': None, 'output': None,
            'cached_input': None, 'cache_write': None, 'batch_input': None, 'batch_output': None,
            'free_tier': None, 'promotions': None, 'long_context': None,
            'effective_date': '2026-08-25', 'source_url': SRC, 'source_type': stype, 'confidence': 'T0',
            'notes': note}

OPEN = '开源权重模型核对（无官方 API 价）'
RET = '官方定价页核对（已下架）'

P = {
    'alibaba:qwen-3-8-max:base': pr(12, 36, None, 'qwen3.8-max，0<Token≤1M 单档计价；上下文缓存享折扣'),
    'alibaba:qwen3-max-2025-09-23:base': pr(6, 24, None, 'qwen3-max-2025-09-23 快照，仅非思考模式；阶梯：0-32K 6/24、32-128K 10/40、128-256K 15/60',
        longctx={'thresholds': '32K/128K', 'tiers': [{'range': '32K<Token≤128K', 'input': 10, 'output': 40}, {'range': '128K<Token≤256K', 'input': 15, 'output': 60}]}),
    'alibaba:qwen-max-2025-01-25:base': ann(RET, 'qwen-max 2025-01-25 历史快照已从现行计费文档移除；现行 qwen-max 无阶梯 2.4/9.6 元但该快照不适用，不硬填'),
    'alibaba:qwen3-6-plus:base': pr(2, 12, None, 'qwen3.6-plus；阶梯：0-256K 2/12、256K-1M 8/48（第三列 12/48 为思考模式思维链+回答输出价）；上下文缓存享折扣',
        longctx={'thresholds': '256K', 'tiers': [{'range': '256K<Token≤1M', 'input': 8, 'output': 48}]}),
    'alibaba:qwen3-7-plus-none:base': pr(2, 8, None, 'qwen3.7-plus（none=非思考口径）；阶梯：0-256K 2/8、256K-1M 6/24；当前原价限时 8 折（实付 1.6/6.4）',
        promo='限时 8 折（原价 2/8 元）', longctx={'thresholds': '256K', 'tiers': [{'range': '256K<Token≤1M', 'input': 6, 'output': 24}]}),
    'alibaba:qwen-plus:base': pr(0.8, 2, None, 'qwen-plus（等同 2025-12-01 快照）；阶梯：0-128K 0.8/2、128-256K 2.4/20、256K-1M 4.8/48（第三列 8/24/64 为思考输出价）',
        longctx={'thresholds': '128K/256K', 'tiers': [{'range': '128K<Token≤256K', 'input': 2.4, 'output': 20}, {'range': '256K<Token≤1M', 'input': 4.8, 'output': 48}]}),
    'alibaba:qwen-3-5-flash:base': pr(0.2, 2, None, 'qwen3.5-flash；阶梯：0-128K 0.2/2、128-256K 0.8/8、256K-1M 1.2/12',
        longctx={'thresholds': '128K/256K', 'tiers': [{'range': '128K<Token≤256K', 'input': 0.8, 'output': 8}, {'range': '256K<Token≤1M', 'input': 1.2, 'output': 12}]}),
    'alibaba:qwen3-7-flash:base': pr(0.2, 0.8, None, 'qwen3.7-flash；阶梯：0-32K 0.2/0.8、32-256K 0.6/2.4、256K-1M 1.2/4.8',
        longctx={'thresholds': '32K/256K', 'tiers': [{'range': '32K<Token≤256K', 'input': 0.6, 'output': 2.4}, {'range': '256K<Token≤1M', 'input': 1.2, 'output': 4.8}]}),
    'alibaba:qwen3-235b-a22b-thinking:2507': pr(2, 20, None, 'qwen3-235b-a22b-thinking-2507，仅思考模式（思维链+回答）'),
    'alibaba:qwen3-235b-a22b-thinking:base': pr(2, 20, None, 'qwen3-235b-a22b（非思考和思考模式）：非思考输出 8 元、思考输出（思维链+回答）20 元；本条按思考口径记录'),
    'alibaba:qwen3-30b-a3b:base': pr(0.75, 3, None, 'qwen3-30b-a3b，非思考输出 3 元、思考输出 7.5 元；本条记非思考口径'),
    'alibaba:qwen3-32b:base': pr(2, 8, None, 'qwen3-32b，非思考输出 8 元、思考输出 20 元；本条记非思考口径'),
    'alibaba:qwen3-8b:base': pr(0.5, 2, None, 'qwen3-8b，非思考输出 2 元、思考输出 5 元；本条记非思考口径'),
    'alibaba:qwen3-next-80b-a3b:base': pr(1, 4, None, 'qwen3-next-80b-a3b-instruct 口径，仅非思考模式；thinking 版输出为 10 元'),
    'alibaba:qwen3-coder-next:base': pr(1, 4, None, 'qwen3-coder-next；阶梯：0-32K 1/4、32-128K 1.5/6、128-256K 2.5/10',
        longctx={'thresholds': '32K/128K', 'tiers': [{'range': '32K<Token≤128K', 'input': 1.5, 'output': 6}, {'range': '128K<Token≤256K', 'input': 2.5, 'output': 10}]}),
    'alibaba:qwen3-coder-480b-a35b:base': pr(6, 24, None, 'qwen3-coder-480b-a35b-instruct；阶梯：0-32K 6/24、32-128K 9/36、128-200K 15/60',
        longctx={'thresholds': '32K/128K', 'tiers': [{'range': '32K<Token≤128K', 'input': 9, 'output': 36}, {'range': '128K<Token≤200K', 'input': 15, 'output': 60}]}),
    'alibaba:qwen3-5-397b-a17b:base': pr(1.2, 7.2, 7.2, 'qwen3.5-397b-a17b；阶梯：0-128K 1.2/7.2（第三列为缓存命中/思考同价列）、128-256K 3/18',
        longctx={'thresholds': '128K', 'tiers': [{'range': '128K<Token≤256K', 'input': 3, 'output': 18}]}),
    'alibaba:qwen3-5-397b-a17b-none:base': pr(1.2, 7.2, 7.2, 'qwen3.5-397b-a17b 非思考口径；阶梯：0-128K 1.2/7.2、128-256K 3/18',
        longctx={'thresholds': '128K', 'tiers': [{'range': '128K<Token≤256K', 'input': 3, 'output': 18}]}),
    'alibaba:qwen3-5-122b-a10b:base': pr(0.8, 6.4, 6.4, 'qwen3.5-122b-a10b；阶梯：0-128K 0.8/6.4、128-256K 2/16',
        longctx={'thresholds': '128K', 'tiers': [{'range': '128K<Token≤256K', 'input': 2, 'output': 16}]}),
    'alibaba:qwen3-5-27b:base': pr(0.6, 4.8, 4.8, 'qwen3.5-27b；阶梯：0-128K 0.6/4.8、128-256K 1.8/14.4',
        longctx={'thresholds': '128K', 'tiers': [{'range': '128K<Token≤256K', 'input': 1.8, 'output': 14.4}]}),
    'alibaba:qwen3-5-35b-a3b:base': pr(0.4, 3.2, 3.2, 'qwen3.5-35b-a3b；阶梯：0-128K 0.4/3.2、128-256K 1.6/12.8',
        longctx={'thresholds': '128K', 'tiers': [{'range': '128K<Token≤256K', 'input': 1.6, 'output': 12.8}]}),
    'alibaba:qwen-3-6-27b:base': pr(3, 18, None, 'qwen3.6-27b，0<Token≤256K 单档；第三列 18 为思考输出价'),
    'alibaba:qwen3-6-27b-none:base': pr(3, 18, None, 'qwen3.6-27b 非思考口径，0<Token≤256K 单档'),
    'alibaba:qwen3-6-35b-a3b:base': pr(1.8, 10.8, None, 'qwen3.6-35b-a3b，0<Token≤256K 单档；思考输出同为 10.8'),
    'alibaba:qwen3-6-35b-a3b-none:base': pr(1.8, 10.8, None, 'qwen3.6-35b-a3b 非思考口径，0<Token≤256K 单档'),
    'alibaba:qwq-plus:base': pr(1.6, 4, None, 'qwq-plus，仅思考模式（思维链+回答）'),
}

A = {
    'alibaba:agentfounder-30b:base': ann(OPEN, 'AgentFounder-30b 为阿里开源 Agent 模型，Hugging Face 开源权重，未在百炼现行计费文档中单列 API 价'),
    'alibaba:gte-modernbert:base': ann(OPEN, 'GTE-ModernBERT 为阿里开源 embedding 模型，开源权重发布，无官方 API 定价'),
    'alibaba:marco-o1:base': ann(OPEN, 'Marco-O1 为阿里国际开源推理模型，开源权重发布，无官方 API 定价'),
    'alibaba:tongyi-deepresearch:base': ann(OPEN, 'Tongyi DeepResearch 为阿里开源深度研究模型，开源权重发布，百炼现行计费文档未收录'),
    'alibaba:qwq-32b:base': ann(OPEN, 'QwQ-32B 为开源权重模型，百炼现行计费文档已不含该模型（仅保留 qwq-plus 托管服务）'),
    'alibaba:qwen3-max-thinking:base': ann('官方定价页核对（待查）', 'qwen3-max-thinking 未出现在现行百炼计费文档，可能已并入 qwen3-max 思考模式计费；不硬填'),
    'alibaba:qwen3-embedding:base': ann(OPEN, 'Qwen3-Embedding 为开源 embedding 模型；百炼计费文档 embedding 章节仅列 text-embedding 系列'),
    'alibaba:qwen3-reranker:base': ann(OPEN, 'Qwen3-Reranker 为开源 rerank 模型，百炼现行计费文档未收录'),
    'alibaba:qwen3-0-6b:base': ann(OPEN, 'Qwen3-0.6B 开源小模型，百炼计费文档未提供托管价'),
    'alibaba:qwen3-1-7b:base': ann(OPEN, 'Qwen3-1.7B 开源小模型，百炼计费文档未提供托管价'),
    'alibaba:qwen3-4b:base': ann(OPEN, 'Qwen3-4B 开源小模型，百炼计费文档未提供托管价'),
    'alibaba:qwen3-5-0-8b:base': ann(OPEN, 'Qwen3.5-0.8B 开源小模型，百炼计费文档仅列 397b/122b/27b/35b 四个尺寸'),
    'alibaba:qwen3-5-2b:base': ann(OPEN, 'Qwen3.5-2B 开源小模型，百炼计费文档未提供托管价'),
    'alibaba:qwen3-5-4b:base': ann(OPEN, 'Qwen3.5-4B 开源小模型，百炼计费文档未提供托管价'),
    'alibaba:qwen3-5-9b:base': ann(OPEN, 'Qwen3.5-9B 开源小模型，百炼计费文档未提供托管价'),
}

legacy_open = ['alibaba:qwen-14b:base', 'alibaba:qwen-7b:base', 'alibaba:qwen-1-8b:base',
               'alibaba:qwen1-5-110b:base', 'alibaba:qwen1-5-14b:base', 'alibaba:qwen1-5-32b:base',
               'alibaba:qwen1-5-72b:base', 'alibaba:qwen1-5-7b:base',
               'alibaba:qwen2-0-5b:base', 'alibaba:qwen2-1-5b:base', 'alibaba:qwen2-57b-a14b:base',
               'alibaba:qwen2-72b:base', 'alibaba:qwen2-7b:base',
               'alibaba:qwen2-math-1-5b:base', 'alibaba:qwen2-math-72b:base', 'alibaba:qwen2-math-7b:base',
               'alibaba:codeqwen1-5-7b:base']
for m in legacy_open:
    A[m] = ann(RET, m.split(':')[1] + ' 为 Qwen 早期开源权重模型，已从百炼现行计费文档移除（历史版本可经第三方托管调用但不混录）')

q25 = ['alibaba:qwen2-5-1-5b:base', 'alibaba:qwen2-5-14b:base', 'alibaba:qwen2-5-32b:base',
       'alibaba:qwen2-5-3b:base', 'alibaba:qwen2-5-72b:base', 'alibaba:qwen2-5-7b:base',
       'alibaba:qwen2-5-coder:base', 'alibaba:qwen2-5-coder-0-5b:base', 'alibaba:qwen2-5-coder-1-5b:base',
       'alibaba:qwen2-5-coder-3b-instruct:base', 'alibaba:qwen2-5-coder-32b:base', 'alibaba:qwen2-5-coder-7b:base',
       'alibaba:qwen2-5-coder-14b:base', 'alibaba:qwen2-5-math-1-5b:base', 'alibaba:qwen2-5-math-7b-base:base']
for m in q25:
    A[m] = ann(RET, m.split(':')[1] + ' 为开源权重模型，已从百炼现行计费文档移除；历史百炼托管价不再公开，不硬填')

A['alibaba:qwen2-5-max:base'] = ann(RET, 'qwen2.5-max 旧旗舰已被 qwen3/max 系列替代，现行百炼计费文档已无其定价')
A['alibaba:qwen-turbo-2024-11-01:base'] = ann(RET, 'qwen-turbo 2024-11-01 历史快照已下架；现行 qwen-turbo 为 0.3/0.6 元（思考输出 3 元）')

written = 0
missing = []
idx = {r['model_id']: r for r in recs}
for mid, params in P.items():
    if mid in idx:
        idx[mid]['pricing'] = params
        written += 1
    else:
        missing.append(mid)
for mid, note in A.items():
    if mid in idx:
        idx[mid]['pricing'] = note
        written += 1
    else:
        missing.append(mid)

with open(BASE + 'model_data_v2.jsonl', 'w', encoding='utf-8') as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('written:', written)
print('missing:', missing)

from collections import Counter
al = [r for r in recs if r['model_id'].startswith('alibaba:')]
st = Counter()
errs = 0
for r in al:
    p = r['pricing']
    if p.get('input') is None:
        st[('annotated', p.get('source_type'))] += 1
    else:
        st[('priced',)] += 1
        if not p.get('currency') or not p.get('confidence'):
            errs += 1
print(dict(st))
print('field errors:', errs)
