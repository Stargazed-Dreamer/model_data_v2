# v1 数据清洗日志

> 输入：`model_data_v1.jsonl`（924 条）  
> 输出：`model_data_v1_clean.jsonl`（不删除任何记录，原文件不动）

## 1. source_urls 换行拆分 / 去重

- `ai21:jamba-1-5-large:base`：source_urls 拆分/裁剪/去重，3 → 5 项
- `alibaba:qwen2-0-5b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `alibaba:qwen2-1-5b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `alibaba:qwen2-5-32b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `alibaba:qwen2-57b-a14b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `alibaba:qwen2-72b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `alibaba:qwen2-7b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `alibaba:qwen3-5-0-8b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `alibaba:qwen3-5-122b-a10b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `alibaba:qwen3-5-27b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `alibaba:qwen3-5-2b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `alibaba:qwen3-5-4b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `alibaba:qwen3-5-9b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `allen-institute-for-ai-university-of-washington:tulu-3-405b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `allen-institute-for-ai-university-of-washington:tulu-3-70b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `allen-institute-for-ai-university-of-washington:tulu-3-8b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `amazon:amazon-nova-micro:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `amazon:amazon-titan-text-premier:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `ant-group:ling-1t:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `character-ai:kaiju-large:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `china-unicom:yuanjing-llm:base`：source_urls 拆分/裁剪/去重，3 → 5 项
- `cohere-labs-formerly-cohere-for-ai:aya-expanse-32b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `cohere-labs-formerly-cohere-for-ai:aya-expanse-8b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `cohere:cohere-command-a:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `deep-cogito:cogito-v2-1:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `deepseek:deepseek-llm-1-3b-base:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `deepseek:deepseek-v2:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `deepseek:deepseek-v3-1:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `deepseek:deepseek-v4-pro:0813`：source_urls 拆分/裁剪/去重，3 → 4 项
- `eth-zurich-ecole-polytechnique-f-ed-erale-de-lausanne-epfl-swiss-national-supercomputing-centre-cscs-swisscom:apertus-70b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `eth-zurich-ecole-polytechnique-f-ed-erale-de-lausanne-epfl-swiss-national-supercomputing-centre-cscs-swisscom:apertus-8b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `foxconn:foxbrain:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `gray-swan:cygnet:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `inception-labs:mercury:base`：source_urls 拆分/裁剪/去重，3 → 5 项
- `indosat-tech-mahindra-ai-singapore-goto:gemma2-9b-cpt-sahabat-ai:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `inspur:hairuo:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `inspur:haiyue:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `jiangsu-huizhi-intelligent-digital-technology-co-ltd:carrotai:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `lenovo:tianxi-32b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `lg-ai-research:k-exaone-2-0:base`：source_urls 拆分/裁剪/去重，3 → 5 项
- `meta:code-llama-70b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `meta:llama-2-13b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `meta:llama-2-34b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `meta:llama-2-70b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `meta:muse-spark-1-1:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `microsoft:microsoft-mai-1:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `microsoft:phi-2:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `moonshot:kimi-dev-72b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `motif-technologies:motif-3:base`：source_urls 拆分/裁剪/去重，3 → 5 项
- `nvidia:nemotron-3-ultra:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `nvidia:nemotron-4-340b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `perplexity:sonar-pro:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `saudi-data-and-artificial-intelligence-authority:allam-adapted13b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `shanghai-kuanyu-digital-technology-co-ltd-bilibili:index-1-9b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `sk-telecom:a-x-k1:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `sk-telecom:a-x-k2:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `stability-ai:stable-lm-2-12b:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `stepfun:step-2:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `technology-innovation-institute:falcon-2-11b:base`：source_urls 拆分/裁剪/去重，3 → 3 项
- `tencent:hunyuan-turbos:base`：source_urls 拆分/裁剪/去重，3 → 5 项
- `yandex:yandexgpt-4-pro:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `yandex:yandexgpt-5-pro:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `zhipu:glm-5:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `zhuoshi-technology:xuanji-yuheng:base`：source_urls 拆分/裁剪/去重，3 → 4 项
- `zte:nebula:base`：source_urls 拆分/裁剪/去重，3 → 4 项

## 2. unknown 厂商归属修正

- `unknown:chatglm2-6b:base` → `zhipu:chatglm2-6b:base`（vendor: 'unknown' → 'Zhipu AI'）
- `unknown:codeqwen1-5-7b:base` → `alibaba:codeqwen1-5-7b:base`（vendor: 'unknown' → 'Alibaba'）
- `unknown:palm-2-l:base` → `google:palm-2-l:base`（vendor: 'unknown' → 'Google'）
- `unknown:palm-2-m:base` → `google:palm-2-m:base`（vendor: 'unknown' → 'Google'）
- `unknown:palm-2-s:base` → `google:palm-2-s:base`（vendor: 'unknown' → 'Google'）
- `unknown:palm-62b:base` → `google:palm-62b:base`（vendor: 'unknown' → 'Google'）
- `unknown:pangu-5-0:base` → `huawei:pangu-5-0:base`（vendor: 'unknown' → 'Huawei'）
- `unknown:qwen-1-8b:base` → `alibaba:qwen-1-8b:base`（vendor: 'unknown' → 'Alibaba'）
- `unknown:qwen-3-6-27b:base` → `alibaba:qwen-3-6-27b:base`（vendor: 'unknown' → 'Alibaba'）
- `unknown:qwen2-5-coder-0-5b:base` → `alibaba:qwen2-5-coder-0-5b:base`（vendor: 'unknown' → 'Alibaba'）
- `unknown:qwen2-5-coder-14b:base` → `alibaba:qwen2-5-coder-14b:base`（vendor: 'unknown' → 'Alibaba'）
- `unknown:qwen2-5-coder-3b-instruct:base` → `alibaba:qwen2-5-coder-3b-instruct:base`（vendor: 'unknown' → 'Alibaba'）
- `unknown:super-xiaoai:base` → `xiaomi:super-xiaoai:base`（vendor: 'unknown' → 'Xiaomi'）
- `unknown:text-davinci-003:base` → `openai:text-davinci-003:base`（vendor: 'unknown' → 'OpenAI'）
- `unknown:xtrimopglm-1b:base` → `zhipu:xtrimopglm-1b:base`（vendor: 'unknown' → 'Zhipu AI'）
- `unknown:yi-9b:base` → `zero-one:yi-9b:base`（vendor: 'unknown' → '01.AI'）

**合计**：source_urls 修复 65 条；厂商归属修复 16 条。
