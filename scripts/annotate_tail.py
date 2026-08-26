# -*- coding: utf-8 -*-
"""Task #15 收尾：剩余 121 条长尾标注"""
import json

BASE = r'F:/project_temp/localAgent/workspace/model_data/'
recs = [json.loads(l) for l in open(BASE + 'model_data_v2.jsonl', encoding='utf-8')]

OPEN = '开源权重模型核对（无官方 API 价）'
RET = '官方定价页核对（已下架）'
NOPUB = '官方定价页核对（无公开定价）'

def ann(stype, note):
    return {'currency': None, 'unit': 'per_million_tokens', 'input': None, 'output': None,
            'cached_input': None, 'cache_write': None, 'batch_input': None, 'batch_output': None,
            'free_tier': None, 'promotions': None, 'long_context': None,
            'effective_date': '2026-08-25', 'source_url': None, 'source_type': stype,
            'confidence': 'T0', 'notes': note}

# 逐模型特殊处理
SPECIAL = {
    # OpenAI
    'openai:ada:base': (RET, 'Ada（2020 GPT-3 系）embedding/补全引擎，2024-01-04 已从 OpenAI API 下架'),
    'openai:babbage:base': (RET, 'Babbage（2020 GPT-3 系）引擎，2024-01-04 已下架'),
    'openai:curie:base': (RET, 'Curie（2020 GPT-3 系）引擎，2024-01-04 已下架'),
    'openai:davinci:base': (RET, 'Davinci（2020 GPT-3 系）引擎，2024-01-04 已下架'),
    'openai:text-ada-001:base': (RET, 'text-ada-001 已于 2024-01-04 下架'),
    'openai:text-babbage-001:base': (RET, 'text-babbage-001 已于 2024-01-04 下架'),
    'openai:text-curie-001:base': (RET, 'text-curie-001 已于 2024-01-04 下架'),
    'openai:text-davinci-001:base': (RET, 'text-davinci-001 已于 2024-01-04 下架'),
    'openai:text-davinci-002:base': (RET, 'text-davinci-002 已于 2024-01-04 下架'),
    'openai:text-davinci-003:base': (RET, 'text-davinci-003 已于 2024-01-04 下架'),
    'openai:code-davinci-002:base': (RET, 'Codex 系列 code-davinci-002 已于 2023-03-23 下架'),
    'openai:gpt-3-175b:base': (RET, 'GPT-3 原始 175B 版本经 API 演进为 gpt-3.5-turbo 后原始版不可用'),
    'openai:gpt-oss-120b:base': (OPEN, 'GPT-OSS-120B 为 OpenAI 开源权重模型（Apache 2.0，Hugging Face 发布），OpenAI 官方不提供托管 API；第三方托管价不混录'),
    'openai:gpt-oss-20b:base': (OPEN, 'GPT-OSS-20B 为 OpenAI 开源权重模型（Apache 2.0），官方无托管 API'),
    'openai:openai-gpt-oss-120b-high:base': (OPEN, 'GPT-OSS-120B high reasoning 变体为开源权重模型，官方无托管 API'),
    'openai:o1-mini-2024-09-12-high:base': (RET, 'o1-mini 2024-09-12 快照已被 o1-mini-2024-09-12 正式版替代并从现行价目移除'),
    'openai:criticgpt:base': (NOPUB, 'CriticGPT 为 GPT-4 批注研究模型，未作为独立产品公开售卖'),
    'openai:codex-1:base': (NOPUB, 'Codex-1 为 Codex Agent 产品底层模型，随 ChatGPT Pro 订阅提供，未公开 per-token 价'),
    'openai:chatgpt-agent:base': (NOPUB, 'ChatGPT Agent 底层模型随订阅制提供，未公开独立 per-token 定价'),
    # Amazon（Bedrock 官方有价但本库需精确核实版本映射，暂标注）
    'amazon:amazon-nova-micro-v1-0:base': (NOPUB, 'Amazon Nova Micro 经 AWS Bedrock 提供，美元价需按 region 核实 Bedrock Pricing Calculator，本轮未完成精确核对，不硬填'),
    'amazon:amazon-nova-micro:base': (NOPUB, 'Amazon Nova Micro 同上，待 Bedrock 定价页精确核对'),
    'amazon:amazon-nova-pro-v1-0:base': (NOPUB, 'Amazon Nova Pro 经 AWS Bedrock 提供，价格待精确核对'),
    'amazon:nova-2-pro:base': (NOPUB, 'Amazon Nova 2 Pro 新发布，Bedrock 价目尚未稳定核实'),
    'amazon:amazon-titan-text-premier:base': (RET, 'Titan Text Premier 已被 Nova 系列替代，Bedrock 新区不再提供'),
    'amazon:amazon-q-developer': (NOPUB, 'Amazon Q Developer 属订阅制产品，底层模型未公开独立 per-token 定价'),
    # Cursor / Voyage / DeepMind 等
    'cursor:composer:base': (NOPUB, 'Cursor Composer 随 Cursor IDE 订阅提供，未公开独立 per-token 定价'),
    'cursor:composer-1-5:base': (NOPUB, 'Cursor Composer 1.5 未公开独立定价'),
    'cursor:composer-2:base': (NOPUB, 'Cursor Composer 2 未公开独立定价'),
    'cursor:composer-2-5:base': (NOPUB, 'Cursor Composer 2.5 未公开独立定价'),
    'voyage-ai:voyage-3-5:base': (NOPUB, 'Voyage AI embedding 现行价目存在但版本映射需逐项核对，本轮未完成，不硬填'),
    'voyage-ai:voyage-3-large:base': (NOPUB, 'Voyage AI voyage-3-large 待价目核对'),
    'voyage-ai:voyage-code-2:base': (RET, 'voyage-code-2 已被 voyage-code-3 替代下架'),
    'voyage-ai:voyage-code-3:base': (NOPUB, 'Voyage Code 3 待价目核对'),
    'deepmind:alphaevolve:base': (NOPUB, 'AlphaEvolve 为 DeepMind 研究系统，未公开 API 定价'),
    'deepmind:chinchilla:base': (RET, 'Chinchilla 为研究模型，从未商用化 API'),
    'deepmind:gopher:base': (RET, 'Gopher 为 DeepMind 研究模型，从未商用化 API'),
    'google-research:flan-137b:base': (RET, 'FLAN 137B 研究模型未商用化'),
    'google-research:palm-540b:base': (RET, 'PaLM 540B API 已于 2024 年被 Gemini 替代下架'),
    'google-research:palm:base': (RET, 'PaLM 研究系列未公开现行商用价'),
    'google-brain:big-lstm-cnn-inputs:base': (RET, '2017 年研究模型，从未商用化'),
    'google-brain:meena:base': (RET, 'Meena 对话研究模型，从未商用化'),
    'anthropic:claude-instant-1-2:base': (RET, 'Claude Instant 1.2 已于 2024 年 11 月从 Anthropic API 下架'),
    'mistral-ai-all-hands-ai:devstral-medium:base': (NOPUB, 'Devstral Medium 为 All Hands 联合发布的闭源权重模型，Mistral La Plateforme 价目未单列，不硬填'),
    'ibm-research:granite-20b:base': (OPEN, 'Granite 20B 开源权重发布，开源版无官方按量 API 价；watsonx 平台套餐口径不硬填'),
    'deepl:deepl-llm:base': (NOPUB, 'DeepL LLM 随翻译订阅服务提供，未公开独立 per-token API 定价'),
}

# 联合机构前缀 -> 统一模板
JOINT_OPEN = {
    'alibaba-hong-kong-polytechnic-university': '阿里+香港理工联合开源模型',
    'alibaba-the-university-of-hong-kong-fudan-university': '阿里+港大+复旦联合开源模型',
    'bytedance-peking-university': '字节+北大联合开源模型',
    'bytedance-tsinghua-university-sia-lab-tsinghua-air-bytedance-seed': '字节 Seed+清华联合开源模型',
    'carnegie-mellon-university-cmu-google-brain': 'CMU+Google Brain 联合开源模型',
    'cognition-stanford-university': 'Cognition+斯坦福联合发布模型',
    'cohere-labs-formerly-cohere-for-ai-brown-university-cohere-carnegie-mellon-university-cmu-massachusetts-institute-of-technology-mit': 'Cohere Labs+高校联合开源模型（Aya 相关）',
    'contextual-ai-the-university-of-hong-kong-microsoft': 'Contextual AI+港大+微软联合开源模型',
    'deepseek-peking-university': 'DeepSeek+北大联合开源模型',
    'deepseek-tsinghua-university-peking-university': 'DeepSeek+清华+北大联合开源模型',
    'facebook-university-of-california-san-diego': 'Meta FAIR+UCSD 联合开源模型',
    'facebook-university-of-washington': 'Meta FAIR+华盛顿大学联合开源模型',
    'google-deepmind-google': 'Google DeepMind 开源/研究模型',
    'google-deepmind-mcgill-university-mila-quebec-ai-originally-montreal-institute-for-learning-algorithms': 'DeepMind+McGill+Mila 联合研究模型',
    'google-google-research': 'Google Research 开源/研究模型',
    'hugging-face-korea-advanced-institute-of-science-and-technology-kaist-argilla': 'HF+KAIST+Argilla 联合开源模型',
    'intelligent-internet': 'Intelligent Internet 开源/内部模型',
    'meta-ai-universite-de-technologie-de-compi-gne-cnrs-basque-center-on-cognition': 'Meta AI+法国高校联合开源模型',
    'microsoft-nvidia': '微软+NVIDIA 联合开源模型',
    'microsoft-research-asia-peking-university-tsinghua-university': '微软亚洲研究院+北大+清华联合开源模型',
    'microsoft-research-asia-shanghai-jiao-tong-university-carnegie-mellon-university-cmu': '微软亚研+上交+CMU 联合开源模型',
    'microsoft-university-of-illinois-urbana-champaign-uiuc': '微软+UIUC 联合开源模型',
    'nous-research-arcee-ai': 'Nous Research+Arcee 联合开源模型',
    'nvidia-meta-ai': 'NVIDIA+Meta AI 联合开源模型',
    'nvidia-servicenow': 'NVIDIA+ServiceNow 联合开源模型（StarCoder2 相关）',
    'openbmb-open-lab-for-big-model-base': '清华 OpenBMB 大模型开放实验室开源模型（MiniCPM 相关）',
    'prime-intellect-arcee-ai': 'Prime Intellect+Arcee 联合开源模型',
    'prime-intellect-hugging-face-arcee-ai': 'Prime Intellect+HF+Arcee 联合开源模型',
    'sber-moscow-institute-of-physics-and-technology': 'Sber+莫斯科物理技术学院联合开源模型',
    'shanghai-ai-lab-massachusetts-institute-of-technology-mit-taptap': '上海AI实验室+MIT+TapTap 联合开源模型',
    'shanghai-ai-lab-sensetime-chinese-university-of-hong-kong-cuhk-fudan-university': '上海AI实验室+商汤+港中文+复旦联合开源模型（InternLM 相关）',
    'shanghai-kuanyu-digital-technology-co-ltd-bilibili': '上海宽娱（B站）index 开源模型',
    'silo-ai-university-of-turku': 'SiloGen+图尔库大学联合开源模型（北欧语系）',
    'university-of-chinese-academy-of-sciences-microsoft-research': '国科大+微软研究院联合开源模型',
    'xverse-technology-shenzhen-yuanxiang-technology': '深圳元象 XVERSE 开源模型',
    'z-ai-zhipu-ai-tsinghua-university': '智谱 Z.ai+清华联合 GLM 开源模型',
    'zhejiang-university-zju-institute-for-advanced-algorithms-research-northeastern-university-china-china-telecom-state-key-laboratory-of-media-convergence-production-technology-and-systems': '浙大+东北大学+中国电信联合开源模型',
}

# unknown 前缀：社区微调/行业模型，来源不明
UNKNOWN_NOTE = '社区微调/行业定制模型（来源聚合站标注 unknown），无可靠官方定价源；遵循"不硬填"原则标注待查'
written = 0

idx = {r['model_id']: r for r in recs}
for mid, (stype, note) in SPECIAL.items():
    if mid in idx and not idx[mid]['pricing'].get('source_type'):
        idx[mid]['pricing'] = ann(stype, mid.split(':')[1] + '：' + note)
        written += 1

for pref, desc in JOINT_OPEN.items():
    for mid, r in idx.items():
        if mid.startswith(pref + ':') and not r['pricing'].get('source_type'):
            name = mid.split(':')[1]
            r['pricing'] = ann(OPEN, name + '：' + desc + '，开源权重或研究发布，无官方按量 API 定价')
            written += 1

for mid, r in idx.items():
    if mid.startswith('unknown:') and not r['pricing'].get('source_type'):
        r['pricing'] = ann(NOPUB, mid.split(':')[1] + '：' + UNKNOWN_NOTE)
        written += 1

with open(BASE + 'model_data_v2.jsonl', 'w', encoding='utf-8') as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print('annotated:', written)

from collections import Counter
gaps = Counter()
for r in recs:
    p = r.get('pricing') or {}
    if p.get('input') is None and not p.get('source_type'):
        gaps[r['model_id']] += 1
print('remaining gaps:', sum(gaps.values()), list(gaps)[:10])
