# -*- coding: utf-8 -*-
"""补写 alibaba:qwen3-14b（百炼托管价 1/4 元，思考输出 10 元）"""
import json

BASE = r'F:/project_temp/localAgent/workspace/model_data/'
recs = [json.loads(l) for l in open(BASE + 'model_data_v2.jsonl', encoding='utf-8')]
SRC = 'https://help.aliyun.com/zh/model-studio/billing-for-model-studio'
n = 0
for r in recs:
    if r['model_id'] == 'alibaba:qwen3-14b:base':
        r['pricing'] = {'currency': 'CNY', 'unit': 'per_million_tokens', 'input': 1, 'output': 4,
                        'cached_input': None, 'cache_write': None, 'batch_input': None, 'batch_output': None,
                        'free_tier': '新用户开通百炼后 90 天内有免费额度（以控制台为准）',
                        'promotions': None, 'long_context': None,
                        'effective_date': '2026-08-25', 'source_url': SRC, 'source_type': '官方定价页核对', 'confidence': 'T0',
                        'notes': 'qwen3-14b，非思考输出 4 元、思考输出 10 元；本条记非思考口径；来源：阿里云百炼计费文档（存档 raw_pages/aliyun_billing.html/.txt），华北2北京地域价'}
        n += 1
with open(BASE + 'model_data_v2.jsonl', 'w', encoding='utf-8') as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print('fixed:', n)
