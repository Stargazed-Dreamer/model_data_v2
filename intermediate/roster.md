# 花名册（roster）—— 28 厂商 × 旗舰/主线模型范围判定

> 阶段 0 产物。生成脚本：`gen_roster.py`；数据基线：`model_data_v1_clean.jsonl`。
> 机器可读版本：`roster.jsonl`（每行：model_id / vendor / status / reason）。

## model_id 权威规则（P1 修复，全体采集 agent 必须遵守）

1. 花名册是 model_id 的**唯一权威**。
2. `in_v1` 模型：**原样沿用本花名册中的 model_id**（v1 风格：连字符 family + `:base`），严禁「纠正」成点号风格或营销代号风格。
3. `to_add` 模型：**原样使用花名册分配的 model_id**（prompt 决策 6 风格），采集产出必须逐字一致。
4. 采集 agent 不得自行发明新 model_id，不得修改已有记录的 model_id。
5. 花名册外的模型（`out_of_scope`）不采集；发现范围外的新旗舰/主线 → 回报主 agent 补录花名册后再采。

## 汇总：目标厂商记录 480 条

- `in_v1`（沿用并富集）：**333** 条
- `to_add`（花名册分配、待采集）：**26** 条
- `out_of_scope`（归档、不采集）：**147** 条

out_of_scope 原因分布：config_dup 60、pre_2023 33、research 32、embedding 8、dup 7、distilled 6、quant 1

## 采集 agent 分组（阶段 1 分片依据）

| 组 | 厂商（in_v1 / to_add 数量） |
|---|---|
| G1 | openai（33/1）、anthropic（21/1） |
| G2 | google（33/3）、meta（22/1）、xai（14/2） |
| G3 | mistral（36/1）、cohere（2/2）、inflection（3/1）、aleph-alpha（1/0）、microsoft（15/1）、nvidia（20/0）、databricks（1/0）、cognition（3/0） |
| G4 | alibaba（67/1）、deepseek（18/0）、bytedance（4/0） |
| G5 | baidu（4/2）、zhipu（7/3）、moonshot（9/1）、tencent（3/2）、iflytek（1/1） |
| G6 | baichuan（5/0）、huawei（3/0）、meituan（0/1）、xiaomi（1/1）、zero-one（7/0）、modelbest（0/1）、aispeech（0/0） |

> 格式：厂商名（in_v1 数 / to_add 数）。P1 平台 agent（LMArena）与 P2 平台 agent（独立跑分）不分厂商。

## to_add 清单（新模型，按此 model_id 全量采集）

| model_id | 名称 | 备注 |
|---|---|---|
| `anthropic:claude-3-sonnet:base` | Claude 3 Sonnet | 2024-03 Claude 3 三件套之一，v1 缺失 |
| `openai:gpt-4.1-mini:base` | GPT-4.1 mini | 2025-04 官方主线，v1 仅有 gpt-4.1 |
| `google:gemini-1.0-ultra:base` | Gemini 1.0 Ultra | 2023-12 首批旗舰之一，v1 缺失 |
| `google:gemini-2.0-flash:base` | Gemini 2.0 Flash | 2024-12 主线模型，v1 缺失 |
| `google:gemini-3-pro:base` | Gemini 3 Pro | 2025-11 旗舰，v1 缺失 |
| `meta:llama-4-maverick:base` | Llama 4 Maverick | v1 仅有 fp8 量化版，需采官方版 |
| `xai:grok-1:base` | Grok-1 | 2023-11 首个版本，v1 缺失 |
| `xai:grok-3:base` | Grok 3 | 2025-02 旗舰，v1 仅有 mini |
| `mistral:mistral-medium:base` | Mistral Medium | 2024-01 首发三件套之一，v1 缺失 |
| `cohere:command-r:base` | Command R | 2024-03 主线，v1 缺失 |
| `cohere:command-r-plus:base` | Command R+ | 2024-04 旗舰，v1 缺失 |
| `inflection:inflection-3:base` | Inflection-3 | 2024-06，v1 缺失 |
| `microsoft:phi-4:base` | Phi-4 | 2024-12 主线，v1 缺失 |
| `alibaba:qwen3-235b-a22b:base` | Qwen3-235B-A22B | 2025-04 旗舰基础版，v1 仅有 thinking 变体 |
| `baidu:ernie-4.0:base` | ERNIE 4.0 | 2023-10 旗舰 API，v1 缺失 |
| `baidu:ernie-x1:base` | ERNIE X1 | 2025-03 推理模型，v1 缺失 |
| `zhipu:glm-4:base` | GLM-4 | 2024-01 旗舰，v1 缺失 |
| `zhipu:glm-4.5:base` | GLM-4.5 | 2025-07 旗舰（开源+API），v1 缺失 |
| `zhipu:glm-4.6:base` | GLM-4.6 | 2025-09 旗舰，v1 缺失 |
| `moonshot:kimi-k2:base` | Kimi K2 | 2025-07 旗舰开源，v1 缺失（仅有后续版本） |
| `tencent:hunyuan-t1:base` | Hunyuan-T1 | 2025-03 推理模型，v1 缺失 |
| `tencent:hunyuan-a13b:base` | Hunyuan-A13B | 2025-05 开源 MoE，v1 缺失 |
| `iflytek:spark-x1:base` | 讯飞星火 X1 | 2025-03 推理模型，v1 缺失 |
| `xiaomi:mimo-7b:base` | MiMo-7B | 2025-04 开源，v1 缺失 |
| `meituan:longcat-flash:base` | LongCat-Flash | 2025 美团开源 MoE，v1 无美团记录 |
| `modelbest:minicpm-4:base` | MiniCPM 4 | 2025-06 面壁旗舰开源，v1 无面壁记录 |

## 各厂商 in_v1 明细

### openai（in_v1 33，to_add 1）

- `openai:gpt-4:0613`（gpt-4-0613，2023-06）
- `openai:gpt-4-turbo:base`（gpt-4-turbo，2023-11）
- `openai:gpt-3-5-turbo:0125`（gpt-3.5-turbo-0125，2024-01）
- `openai:gpt-4o-mini-2024-07-18:base`（gpt-4o-mini-2024-07-18，2024-07）
- `openai:o1-mini:base`（o1-mini，2024-09）
- `openai:gpt-4o-2024-11-20:base`（gpt-4o-2024-11-20，2024-11）
- `openai:o1-2024-12-17-high:base`（o1-2024-12-17_high，2024-12）
- `openai:o3-mini-2025-01-31-high:base`（o3-mini-2025-01-31_high，2025-01）
- `openai:gpt-4-5-preview-2025-02-27:base`（gpt-4.5-preview-2025-02-27，2025-02）
- `openai:gpt-4-1-2025-04-14:base`（gpt-4.1-2025-04-14，2025-04）
- `openai:o3-2025-04-16-high:base`（o3-2025-04-16_high，2025-04）
- `openai:o4-mini-2025-04-16-high:base`（o4-mini-2025-04-16_high，2025-04）
- `openai:codex-1:base`（codex-1，2025-05）
- `openai:codex-mini:base`（codex-mini，2025-05）
- `openai:o3-pro:base`（o3-pro，2025-06）
- `openai:gpt-5-2025-08-07-high:base`（gpt-5-2025-08-07_high，2025-08）
- `openai:gpt-5-mini-2025-08-07-minimal:base`（gpt-5-mini-2025-08-07_minimal，2025-08）
- `openai:gpt-oss-120b:base`（gpt-oss-120b，2025-08）
- `openai:gpt-oss-20b:base`（gpt-oss-20b，2025-08）
- `openai:gpt-5-codex:base`（GPT-5-Codex，2025-09）
- `openai:gpt-5-1-2025-11-13-high:base`（gpt-5.1-2025-11-13_high，2025-11）
- `openai:gpt-5-1-codex-max:base`（GPT-5.1-Codex-Max，2025-11）
- `openai:gpt-5-2-codex:base`（GPT-5.2 Codex，2025-12）
- `openai:gpt-5-2:base`（GPT-5.2，2025-12）
- `openai:gpt-5-3-codex:base`（GPT-5.3 Codex，2026-02）
- `openai:gpt-5-4-2026-03-05-none:base`（gpt-5.4-2026-03-05_none，2026-03）
- `openai:gpt-5-4-mini:base`（GPT-5.4 Mini，2026-03）
- `openai:gpt-5-4-pro-2026-03-05-xhigh:base`（gpt-5.4-pro-2026-03-05_xhigh，2026-03）
- `openai:gpt-5-5-pre-release-xhigh:base`（gpt-5.5-pre-release_xhigh，2026-04）
- `openai:gpt-5-6-luna-max:base`（gpt-5.6-luna_max，2026-07）
- `openai:gpt-5-6-sol-max:base`（gpt-5.6-sol_max，2026-07）
- `openai:gpt-5-6-terra-max:base`（gpt-5.6-terra_max，2026-07）
- `openai:gpt-realtime-2-1-mini:base`（GPT-Realtime-2.1-Mini，2026-07）
- `[to_add]` `openai:gpt-4.1-mini:base`（GPT-4.1 mini）

### anthropic（in_v1 21，to_add 1）

- `anthropic:claude-2:base`（Claude 2，2023-07）
- `anthropic:claude-instant-1-2:base`（claude-instant-1.2，2023-08）
- `anthropic:claude-2-1:base`（Claude 2.1，2023-11）
- `anthropic:claude-3-opus:20240229`（claude-3-opus-20240229，2024-02）
- `anthropic:claude-3-haiku:base`（Claude 3 Haiku，2024-03）
- `anthropic:claude-3-5-sonnet:20240620`（claude-3-5-sonnet-20240620，2024-06）
- `anthropic:claude-3-5-haiku:base`（Claude 3.5 Haiku，2024-10）
- `anthropic:claude-3-5-sonnet:20241022`（claude-3-5-sonnet-20241022，2024-10）
- `anthropic:claude-3-7-sonnet:20250219`（claude-3-7-sonnet-20250219，2025-02）
- `anthropic:claude-opus-4:20250514`（claude-opus-4-20250514，2025-05）
- `anthropic:claude-sonnet-4-20250514-32k:base`（claude-sonnet-4-20250514_32K，2025-05）
- `anthropic:claude-gov:base`（Claude Gov，2025-06）
- `anthropic:claude-opus-4-1:20250805`（claude-opus-4-1-20250805，2025-08）
- `anthropic:claude-sonnet-4-5:20250929`（claude-sonnet-4-5-20250929，2025-09）
- `anthropic:claude-haiku-4-5:base`（Claude Haiku 4.5，2025-10）
- `anthropic:claude-opus-4-5:20251101`（claude-opus-4-5-20251101，2025-11）
- `anthropic:claude-opus-4-6-max:base`（claude-opus-4-6_max，2026-02）
- `anthropic:claude-opus-4-7:base`（Claude Opus 4.7，2026-04）
- `anthropic:claude-opus-4-8:base`（Claude Opus 4.8，2026-05）
- `anthropic:claude-fable-5-max:base`（claude-fable-5_max，2026-06）
- `anthropic:claude-opus-5-max:base`（claude-opus-5_max，2026-07）
- `[to_add]` `anthropic:claude-3-sonnet:base`（Claude 3 Sonnet）

### google（in_v1 33，to_add 3）

- `google:palm-2-l:base`（PaLM 2-L，2023-05）
- `google:palm-2-m:base`（PaLM 2-M，2023-05）
- `google:palm-2-s:base`（PaLM 2-S，2023-05）
- `google:palm-2:base`（PaLM 2，2023-05）
- `google:gemini-1-0-pro-001:base`（gemini-1.0-pro-001，2023-12）
- `google:gemini-1-5-pro-001-feb24:base`（gemini-1.5-pro-001-feb24，2024-02）
- `google:gemma-1-1-7b-instruct:base`（Gemma 1.1 7B Instruct，2024-02）
- `google:gemma-2b:base`（Gemma 2B，2024-02）
- `google:gemma-7b:base`（Gemma 7B，2024-02）
- `google:gemini-1-5-flash:0514`（gemini-1.5-flash-0514，2024-05）
- `google:gemini-1-5-pro-001:base`（gemini-1.5-pro-001，2024-05）
- `google:gemma-2-27b:base`（Gemma 2 27B，2024-06）
- `google:gemma-2-2b:base`（Gemma 2 2B，2024-06）
- `google:gemma-2-9b:base`（Gemma 2 9B，2024-06）
- `google:gemini-1-5-pro-002:base`（gemini-1.5-pro-002，2024-09）
- `google:gemini-1-5-flash-8b-001:base`（gemini-1.5-flash-8b-001，2024-10）
- `google:gemini-exp:1114`（Gemini-Exp-1114，2024-11）
- `google:gemini-2-0-pro-exp-02-05:base`（gemini-2.0-pro-exp-02-05，2025-02）
- `google:gemini-2-5-pro-exp-03-25:base`（gemini-2.5-pro-exp-03-25，2025-03）
- `google:gemma-3-1b:base`（Gemma 3 1B，2025-03）
- `google:gemma-3-27b-it:base`（gemma-3-27b-it，2025-03）
- `google:gemini-2-5-flash-preview-05-20:base`（gemini-2.5-flash-preview-05-20，2025-05）
- `google:gemini-2-5-pro:base`（gemini-2.5-pro，2025-06）
- `google:gemma-3-270m:base`（Gemma 3 270M，2025-08）
- `google:gemini-3-flash:base`（Gemini 3 Flash，2025-12）
- `google:gemini-3-1-pro-preview-high:base`（gemini-3.1-pro-preview_high，2026-02）
- `google:gemini-3-0-flash-lite:base`（Gemini 3.0 Flash-lite，2026-03）
- `google:gemini-3-1-flash-lite-minimal:base`（gemini-3.1-flash-lite_minimal，2026-03）
- `google:gemma-4-26b-a4b:base`（Gemma 4 26B A4B，2026-04）
- `google:gemma-4-31b-it:base`（Gemma 4 31B IT，2026-04）
- `google:gemini-3-5-flash-high:base`（gemini-3.5-flash_high，2026-05）
- `google:gemini-3-6-flash-high:base`（gemini-3.6-flash_high，2026-07）
- `google:gemini-3-7-flash-high:base`（gemini-3.7-flash_high，2026-08）
- `[to_add]` `google:gemini-1.0-ultra:base`（Gemini 1.0 Ultra）
- `[to_add]` `google:gemini-2.0-flash:base`（Gemini 2.0 Flash）
- `[to_add]` `google:gemini-3-pro:base`（Gemini 3 Pro）

### meta（in_v1 22，to_add 1）

- `meta:llama-2-13b:base`（Llama 2-13B，2023-07）
- `meta:llama-2-34b:base`（Llama 2-34B，2023-07）
- `meta:llama-2-70b-chat-hf:base`（Llama-2-70b-chat-hf，2023-07）
- `meta:llama-2-70b:base`（Llama 2-70B，2023-07）
- `meta:llama-2-7b:base`（Llama 2-7B，2023-07）
- `meta:code-llama-70b:base`（Code Llama-70B，2024-01）
- `meta:llama-3-70b:base`（Llama 3-70B，2024-04）
- `meta:llama-3-8b:base`（Llama 3-8B，2024-04）
- `meta:meta-llama-3-70b-instruct:base`（Meta-Llama-3-70B-Instruct，2024-04）
- `meta:meta-llama-3-8b-instruct:base`（Meta-Llama-3-8B-Instruct，2024-04）
- `meta:llama-3-1-405b:base`（Llama 3.1-405B，2024-07）
- `meta:llama-3-1-70b:base`（Llama 3.1-70B，2024-07）
- `meta:llama-3-1-8b:base`（Llama 3.1-8B，2024-07）
- `meta:llama-3-2-11b-vision-instruct:base`（Llama-3.2-11B-Vision-Instruct，2024-09）
- `meta:llama-3-2-1b:base`（Llama 3.2 1B，2024-09）
- `meta:llama-3-2-3b:base`（Llama 3.2 3B，2024-09）
- `meta:llama-3-2-90b-vision-instruct:base`（Llama-3.2-90B-Vision-Instruct，2024-09）
- `meta:llama-3-3-70b:base`（Llama 3.3 70B，2024-12）
- `meta:llama-4-scout-17b-16e-instruct:base`（Llama-4-Scout-17B-16E-Instruct，2025-04）
- `meta:muse-spark:base`（muse-spark，2026-04）
- `meta:muse-spark-1-1:base`（Muse Spark 1.1，2026-07）
- `meta:muse-spark-1-2:base`（Muse Spark 1.2，2026-08）
- `[to_add]` `meta:llama-4-maverick:base`（Llama 4 Maverick）

### xai（in_v1 14，to_add 2）

- `xai:grok-1-5:base`（Grok-1.5，2024-03）
- `xai:grok-2:1212`（grok-2-1212，2024-12）
- `xai:grok-3-mini:base`（Grok-3 mini，2025-02）
- `xai:grok-4-heavy:base`（Grok 4 Heavy，2025-07）
- `xai:grok-4:0709`（grok-4-0709，2025-07）
- `xai:grok-code-fast-1:base`（Grok Code Fast 1，2025-08）
- `xai:grok-4-fast:base`（Grok 4 Fast，2025-09）
- `xai:grok-4-1-fast:base`（Grok 4.1 Fast，2025-11）
- `xai:grok-4-1:base`（Grok 4.1，2025-11）
- `xai:grok-4-20:base`（Grok 4.20，2026-02）
- `xai:grok-4-3-high:base`（grok-4.3_high，2026-04）
- `xai:grok-build-0-1:base`（Grok Build 0.1，2026-05）
- `xai:grok-4-5:base`（Grok 4.5，2026-07）
- `xai:grok-4-6-high:base`（grok-4.6_high，2026-08）
- `[to_add]` `xai:grok-1:base`（Grok-1）
- `[to_add]` `xai:grok-3:base`（Grok 3）

### mistral（in_v1 36，to_add 1）

- `mistral:mistral-7b-v0-1:base`（Mistral-7B-v0.1，2023-09）
- `mistral:open-mistral-7b:base`（open-mistral-7b，2023-09）
- `mistral:mistral-7b-instruct-v0-2:base`（Mistral-7B-Instruct-v0.2，2023-12）
- `mistral:mixtral-8x7b-instruct-v0-1:base`（Mixtral-8x7B-Instruct-v0.1，2023-12）
- `mistral:open-mixtral-8x7b:base`（open-mixtral-8x7b，2023-12）
- `mistral:mistral-large:base`（Mistral Large，2024-02）
- `mistral:mixtral-8x22b-v0-1:base`（Mixtral-8x22B-v0.1，2024-04）
- `mistral:mixtral-8x22b:base`（Mixtral 8x22B，2024-04）
- `mistral:open-mixtral-8x22b:base`（open-mixtral-8x22b，2024-04）
- `mistral:codestral:base`（Codestral，2024-05）
- `mistral:mistral-7b-instruct-v0-3:base`（Mistral-7B-Instruct-v0.3，2024-05）
- `mistral:codestral-mamba:base`（Codestral Mamba，2024-07）
- `mistral:mistral-large-2:base`（Mistral Large 2，2024-07）
- `mistral:mistral-nemo-base:2407`（Mistral-Nemo-Base-2407，2024-07）
- `mistral:mistral-nemo:base`（Mistral NeMo，2024-07）
- `mistral:open-mistral-nemo:2407`（open-mistral-nemo-2407，2024-07）
- `mistral:mistral-small-v24-09:base`（Mistral Small v24.09，2024-09）
- `mistral:ministral-3b:base`（Ministral 3B，2024-10）
- `mistral:ministral-8b:base`（Ministral 8B，2024-10）
- `mistral:mistral-large-2-1:base`（Mistral Large 2.1，2024-11）
- `mistral:mistral-moderation:base`（Mistral Moderation，2024-11）
- `mistral:mistral-small:2501`（mistral-small-2501，2025-01）
- `mistral:mistral-saba:base`（Mistral Saba，2025-02）
- `mistral:mistral-small:2503`（mistral-small-2503，2025-03）
- `mistral:codestral-embed:base`（Codestral Embed，2025-05）
- `mistral:mistral-medium:2505`（mistral-medium-2505，2025-05）
- `mistral:magistral-small-1-0:base`（Magistral Small 1.0，2025-06）
- `mistral:magistral-small:2506`（magistral-small-2506，2025-06）
- `mistral:magistral-small-1-1:base`（Magistral Small 1.1，2025-07）
- `mistral:mistral-medium-3-1:base`（Mistral Medium 3.1，2025-08）
- `mistral:magistral-medium-1-2:base`（Magistral Medium 1.2，2025-09）
- `mistral:devstral-2:base`（Devstral 2 (123B)，2025-12）
- `mistral:ministral-3-14b:base`（Ministral 3 14B，2025-12）
- `mistral:ministral-3-3b:base`（Ministral 3 3B，2025-12）
- `mistral:ministral-3-8b:base`（Ministral 3 8B，2025-12）
- `mistral:mistral-large-3:base`（Mistral Large 3，2025-12）
- `[to_add]` `mistral:mistral-medium:base`（Mistral Medium）

### cohere（in_v1 2，to_add 2）

- `cohere:cohere-command-a:base`（Cohere Command A，2025-03）
- `cohere:north-mini-code:base`（North Mini Code，2026-06）
- `[to_add]` `cohere:command-r:base`（Command R）
- `[to_add]` `cohere:command-r-plus:base`（Command R+）

### inflection（in_v1 3，to_add 1）

- `inflection:inflection-1:base`（Inflection-1，2023-06）
- `inflection:inflection-2:base`（Inflection-2，2023-11）
- `inflection:inflection-2-5:base`（Inflection-2.5，2024-03）
- `[to_add]` `inflection:inflection-3:base`（Inflection-3）

### aleph-alpha（in_v1 1，to_add 0）

- `aleph-alpha:pharia-1-llm-7b:base`（Pharia-1-LLM-7B，2024-08）

### microsoft（in_v1 15，to_add 1）

- `microsoft:phi-1-5:base`（Phi-1.5，2023-09）
- `microsoft:phi-2:base`（Phi-2，2023-12）
- `microsoft:phi-3-5-mini:base`（Phi-3.5-mini，2024-04）
- `microsoft:phi-3-5-moe:base`（Phi-3.5-MoE，2024-04）
- `microsoft:phi-3-medium-14b:base`（phi-3-medium 14B，2024-04）
- `microsoft:phi-3-mini-3-8b:base`（phi-3-mini 3.8B，2024-04）
- `microsoft:phi-3-small-7-4b:base`（phi-3-small 7.4B，2024-04）
- `microsoft:wizardlm-2-70b:base`（WizardLM-2 70B，2024-04）
- `microsoft:wizardlm-2-7b:base`（WizardLM-2 7B，2024-04）
- `microsoft:wizardlm-2-8x22b:base`（WizardLM-2 8x22B，2024-04）
- `microsoft:phi-4-mini:base`（Phi-4 Mini，2025-03）
- `microsoft:mai-ds-r1:base`（MAI-DS-R1，2025-04）
- `microsoft:phi-4-reasoning:base`（Phi-4-Reasoning，2025-04）
- `microsoft:mai-code-1-flash:base`（MAI-Code-1-Flash，2026-06）
- `microsoft:mai-thinking-1:base`（MAI-Thinking-1，2026-06）
- `[to_add]` `microsoft:phi-4:base`（Phi-4）

### nvidia（in_v1 20，to_add 0）

- `nvidia:nemotron-4-15b:base`（Nemotron-4 15B，2024-02）
- `nvidia:nemotron-4-340b:base`（Nemotron-4 340B，2024-06）
- `nvidia:llama-3-1-minitron-4b:base`（Llama-3.1-Minitron-4B，2024-11）
- `nvidia:minitron-4b:base`（Minitron 4B，2024-11）
- `nvidia:minitron-8b:base`（Minitron 8B，2024-11）
- `nvidia:llama-nemotron-nano-8b:base`（Llama Nemotron Nano 8B，2025-03）
- `nvidia:llama-nemotron-super-49b:base`（Llama Nemotron Super 49B，2025-03）
- `nvidia:llama-nemotron-ultra-253b:base`（Llama Nemotron Ultra 253B，2025-03）
- `nvidia:nemotron-h-47b:base`（Nemotron-H 47B，2025-04）
- `nvidia:nemotron-h-56b:base`（Nemotron-H 56B，2025-04）
- `nvidia:nemotron-h-8b:base`（Nemotron-H 8B，2025-04）
- `nvidia:llama-nemotron-super-v1-5:base`（Llama Nemotron Super v1.5，2025-07）
- `nvidia:openreasoning-nemotron-32b:base`（OpenReasoning-Nemotron-32B，2025-07）
- `nvidia:nvidia-nemotron-nano-12b-v2:base`（NVIDIA-Nemotron-Nano-12B-v2，2025-08）
- `nvidia:nvidia-nemotron-nano-9b-v2:base`（NVIDIA-Nemotron-Nano-9B-v2，2025-08）
- `nvidia:nemotron-3-nano-30b-a3b:base`（Nemotron 3-Nano-30B-A3B，2025-12）
- `nvidia:nemotron-cascade-14b:base`（Nemotron-Cascade 14B，2025-12）
- `nvidia:nemotron-3-super:base`（Nemotron 3 Super，2026-03）
- `nvidia:nemotron-3-ultra:base`（Nemotron 3 Ultra，2026-06）
- `nvidia:nemotron-3-5-lightning:base`（Nemotron 3.5 Lightning，2026-08）

### databricks（in_v1 1，to_add 0）

- `databricks:dbrx:base`（DBRX，2024-03）

### cognition（in_v1 3，to_add 0）

- `cognition:swe-1-5:base`（SWE-1.5，2025-10）
- `cognition:swe-1-6:base`（SWE-1.6，2026-04）
- `cognition:swe-1-7:base`（SWE-1.7，2026-07）

### alibaba（in_v1 67，to_add 1）

- `alibaba:qwen-14b:base`（Qwen-14B，2023-09）
- `alibaba:qwen-7b:base`（Qwen-7B，2023-09）
- `alibaba:qwen-1-8b:base`（Qwen-1_8B，2023-11）
- `alibaba:qwen-plus:base`（Qwen Plus，2024-02）
- `alibaba:qwen1-5-14b:base`（Qwen1.5-14B，2024-02）
- `alibaba:qwen1-5-32b:base`（Qwen1.5-32B，2024-02）
- `alibaba:qwen1-5-72b:base`（Qwen1.5-72B，2024-02）
- `alibaba:qwen1-5-7b:base`（Qwen1.5-7B，2024-02）
- `alibaba:codeqwen1-5-7b:base`（CodeQwen1.5-7B，2024-04）
- `alibaba:qwen1-5-110b:base`（Qwen1.5-110B，2024-04）
- `alibaba:qwen2-0-5b:base`（Qwen2-0.5B，2024-06）
- `alibaba:qwen2-1-5b:base`（Qwen2-1.5B，2024-06）
- `alibaba:qwen2-57b-a14b:base`（Qwen2-57B-A14B，2024-06）
- `alibaba:qwen2-72b:base`（Qwen2-72B，2024-06）
- `alibaba:qwen2-7b:base`（Qwen2-7B，2024-06）
- `alibaba:qwen2-math-1-5b:base`（Qwen2-Math-1.5B，2024-08）
- `alibaba:qwen2-math-72b:base`（Qwen2-Math-72B，2024-08）
- `alibaba:qwen2-math-7b:base`（Qwen2-Math-7B，2024-08）
- `alibaba:qwen2-5-1-5b:base`（Qwen2.5-1.5B，2024-09）
- `alibaba:qwen2-5-14b:base`（Qwen2.5-14B，2024-09）
- `alibaba:qwen2-5-32b:base`（Qwen2.5-32B，2024-09）
- `alibaba:qwen2-5-3b:base`（Qwen2.5-3B，2024-09）
- `alibaba:qwen2-5-72b:base`（Qwen2.5-72B，2024-09）
- `alibaba:qwen2-5-7b:base`（Qwen2.5-7B，2024-09）
- `alibaba:qwen2-5-coder-0-5b:base`（Qwen2.5-Coder-0.5B，2024-09）
- `alibaba:qwen2-5-coder-1-5b:base`（Qwen2.5-Coder-1.5B，2024-09）
- `alibaba:qwen2-5-coder-14b:base`（Qwen2.5-Coder-14B，2024-09）
- `alibaba:qwen2-5-coder-32b:base`（Qwen2.5-Coder-32B，2024-09）
- `alibaba:qwen2-5-coder-7b:base`（Qwen2.5-Coder-7B，2024-09）
- `alibaba:qwen2-5-math-1-5b:base`（Qwen2.5-Math-1.5B，2024-09）
- `alibaba:qwen2-5-math-7b-base:base`（Qwen2.5-Math-7B-Base，2024-09）
- `alibaba:qwen-turbo-2024-11-01:base`（qwen-turbo-2024-11-01，2024-11）
- `alibaba:qwen2-5-coder-3b-instruct:base`（Qwen2.5-Coder-3B-Instruct，2024-11）
- `alibaba:qwen2-5-coder:base`（Qwen2.5-Coder (32B)，2024-11）
- `alibaba:qwen-max-2025-01-25:base`（qwen-max-2025-01-25，2025-01）
- `alibaba:qwen2-5-max:base`（Qwen2.5-Max，2025-01）
- `alibaba:qwq-32b:base`（QwQ-32B，2025-03）
- `alibaba:qwen3-0-6b:base`（Qwen3-0.6B，2025-04）
- `alibaba:qwen3-1-7b:base`（Qwen3-1.7B，2025-04）
- `alibaba:qwen3-14b:base`（Qwen3-14B，2025-04）
- `alibaba:qwen3-30b-a3b:base`（Qwen3-30B-A3B，2025-04）
- `alibaba:qwen3-32b:base`（Qwen3-32B，2025-04）
- `alibaba:qwen3-4b:base`（Qwen3-4B，2025-04）
- `alibaba:qwen3-8b:base`（Qwen3-8B，2025-04）
- `alibaba:qwq-plus:base`（QWQ-Plus，2025-04）
- `alibaba:qwen3-235b-a22b-thinking:base`（Qwen3-235B-A22B-Thinking (Jul 2025)，2025-07）
- `alibaba:qwen3-coder-480b-a35b:base`（Qwen3-Coder-480B-A35B，2025-07）
- `alibaba:qwen3-max-2025-09-23:base`（qwen3-max-2025-09-23，2025-09）
- `alibaba:qwen3-next-80b-a3b:base`（Qwen3-Next-80B-A3B，2025-09）
- `alibaba:qwen3-max-thinking:base`（Qwen3-Max-Thinking，2026-01）
- `alibaba:qwen-3-5-flash:base`（Qwen 3.5 Flash (hosted 35B-A3B)，2026-02）
- `alibaba:qwen3-5-0-8b:base`（Qwen3.5-0.8B，2026-02）
- `alibaba:qwen3-5-122b-a10b:base`（Qwen3.5-122B-A10B，2026-02）
- `alibaba:qwen3-5-27b:base`（Qwen3.5-27B，2026-02）
- `alibaba:qwen3-5-2b:base`（Qwen3.5-2B，2026-02）
- `alibaba:qwen3-5-35b-a3b:base`（Qwen3.5-35B-A3B，2026-02）
- `alibaba:qwen3-5-397b-a17b:base`（qwen3.5-397b-a17b，2026-02）
- `alibaba:qwen3-5-4b:base`（Qwen3.5-4B，2026-02）
- `alibaba:qwen3-5-9b:base`（Qwen3.5-9B，2026-02）
- `alibaba:qwen3-coder-next:base`（Qwen3-Coder-Next，2026-02）
- `alibaba:qwen3-6-plus:base`（qwen3.6-plus，2026-03）
- `alibaba:qwen-3-6-27b:base`（Qwen 3.6-27B，2026-04）
- `alibaba:qwen3-6-27b-none:base`（qwen3.6-27b_none，2026-04）
- `alibaba:qwen3-6-35b-a3b:base`（qwen3.6-35b-a3b，2026-04）
- `alibaba:qwen3-7-plus-none:base`（qwen3.7-plus_none，2026-06）
- `alibaba:qwen-3-8-max:base`（Qwen 3.8 Max，2026-07）
- `alibaba:qwen3-7-flash:base`（Qwen3.7 Flash，2026-07）
- `[to_add]` `alibaba:qwen3-235b-a22b:base`（Qwen3-235B-A22B）

### deepseek（in_v1 18，to_add 0）

- `deepseek:deepseek-llm-1-3b-base:base`（DeepSeek-LLM-1.3b-base，2024-01）
- `deepseek:deepseek-llm-67b:base`（DeepSeek LLM 67B，2024-01）
- `deepseek:deepseek-llm-7b:base`（DeepSeek LLM 7B，2024-01）
- `deepseek:deepseekmoe-16b:base`（DeepSeekMoE-16B，2024-01）
- `deepseek:deepseek-v2:base`（DeepSeek-V2 (MoE-236B)，2024-05）
- `deepseek:deepseek-coder-v2-236b:base`（DeepSeek-Coder-V2 236B，2024-06）
- `deepseek:deepseek-coder-v2-lite-base:base`（DeepSeek-Coder-V2-Lite-Base，2024-06）
- `deepseek:deepseek-v2-5:base`（DeepSeek-V2.5，2024-09）
- `deepseek:deepseek-r1-zero:base`（DeepSeek-R1-Zero，2025-01）
- `deepseek:deepseek-v3:base`（DeepSeek-V3 (Mar 2025)，2025-03）
- `deepseek:deepseek-r1:base`（DeepSeek-R1 (May 2025)，2025-05）
- `deepseek:deepseek-v3-1:base`（DeepSeek-V3.1，2025-08）
- `deepseek:deepseek-v3-1-terminus:base`（DeepSeek-V3.1-Terminus，2025-09）
- `deepseek:deepseek-chat:base`（deepseek-chat，2025-12）
- `deepseek:deepseek-reasoner:base`（deepseek-reasoner，2025-12）
- `deepseek:deepseek-v3-2:base`（DeepSeek-V3.2，2025-12）
- `deepseek:deepseek-v4-pro:base`（DeepSeek-V4-Pro，2026-04）
- `deepseek:deepseek-v4-flash:0731`（DeepSeek V4 Flash 0731，2026-07）

### bytedance（in_v1 4，to_add 0）

- `bytedance:doubao-pro:base`（Doubao-pro，2024-10）
- `bytedance:doubao-1-5-pro:base`（Doubao-1.5-pro，2025-01）
- `bytedance:seed-coder:base`（Seed-Coder，2025-06）
- `bytedance:seed-oss-36b-base:base`（Seed-OSS-36B-Base，2025-08）

### baidu（in_v1 4，to_add 2）

- `baidu:ernie-4-5-0-3b:base`（ERNIE-4.5-0.3B，2025-06）
- `baidu:ernie-4-5-21b-a3b:base`（ERNIE-4.5-21B-A3B，2025-06）
- `baidu:ernie-4-5-300b-a47b:base`（ERNIE-4.5-300B-A47B，2025-06）
- `baidu:ernie-5-1:base`（ERNIE 5.1，2026-05）
- `[to_add]` `baidu:ernie-4.0:base`（ERNIE 4.0）
- `[to_add]` `baidu:ernie-x1:base`（ERNIE X1）

### zhipu（in_v1 7，to_add 3）

- `zhipu:chatglm2-6b:base`（chatglm2-6b，2023-06）
- `zhipu:glm-4-plus:base`（GLM-4-Plus，2024-08）
- `zhipu:glm-4-7-flash:base`（GLM 4.7 Flash，2026-01）
- `zhipu:glm-5:base`（GLM-5，2026-02）
- `zhipu:glm-5-1:base`（GLM-5.1，2026-04）
- `zhipu:glm-5-2:base`（GLM-5.2，2026-06）
- `zhipu:glm-5-3:base`（GLM-5.3，2026-08）
- `[to_add]` `zhipu:glm-4:base`（GLM-4）
- `[to_add]` `zhipu:glm-4.5:base`（GLM-4.5）
- `[to_add]` `zhipu:glm-4.6:base`（GLM-4.6）

### moonshot（in_v1 9，to_add 1）

- `moonshot:moonshot-v1:base`（Moonshot-v1，2024-09）
- `moonshot:kimi-1-6:base`（Kimi 1.6，2025-02）
- `moonshot:kimi-dev-72b:base`（Kimi Dev 72b，2025-06）
- `moonshot:kimi-linear:base`（Kimi Linear，2025-10）
- `moonshot:kimi-k2-thinking:base`（Kimi K2 Thinking，2025-11）
- `moonshot:kimi-k2-5:base`（Kimi K2.5，2026-02）
- `moonshot:kimi-k2-6:base`（Kimi K2.6，2026-04）
- `moonshot:kimi-k2-7-code:base`（kimi-k2.7-code，2026-06）
- `moonshot:kimi-k3-max:base`（kimi-k3_max，2026-07）
- `[to_add]` `moonshot:kimi-k2:base`（Kimi K2）

### iflytek（in_v1 1，to_add 1）

- `iflytek:spark-4-0:base`（Spark 4.0，2024-09）
- `[to_add]` `iflytek:spark-x1:base`（讯飞星火 X1）

### baichuan（in_v1 5，to_add 0）

- `baichuan:baichuan-7b:base`（Baichuan-7B，2023-06）
- `baichuan:baichuan-13b-base:base`（Baichuan-13B-Base，2023-07）
- `baichuan:baichuan-2-7b:base`（Baichuan 2-7B，2023-09）
- `baichuan:baichuan2-13b:base`（Baichuan2-13B，2023-09）
- `baichuan:baichuan4:base`（Baichuan4，2024-05）

### tencent（in_v1 3，to_add 2）

- `tencent:hunyuan-large:base`（Hunyuan-Large，2024-11）
- `tencent:hunyuan-turbos:base`（Hunyuan-TurboS，2025-03）
- `tencent:tencent-hy3:base`（Tencent Hy3，2026-07）
- `[to_add]` `tencent:hunyuan-t1:base`（Hunyuan-T1）
- `[to_add]` `tencent:hunyuan-a13b:base`（Hunyuan-A13B）

### huawei（in_v1 3，to_add 0）

- `huawei:pangu-5-0:base`（Pangu 5.0，2024-06）
- `huawei:pangu-ultra:base`（Pangu Ultra，2025-04）
- `huawei:pangu-pro-moe:base`（Pangu Pro MoE，2025-05）

### meituan（in_v1 0，to_add 1）

- `[to_add]` `meituan:longcat-flash:base`（LongCat-Flash）

### xiaomi（in_v1 1，to_add 1）

- `xiaomi:super-xiaoai:base`（Super XiaoAI，2024-10）
- `[to_add]` `xiaomi:mimo-7b:base`（MiMo-7B）

### zero-one（in_v1 7，to_add 0）

- `zero-one:yi-34b:base`（Yi-34B，2023-11）
- `zero-one:yi-6b:base`（Yi 6B，2023-11）
- `zero-one:yi-9b:base`（Yi-9B，2024-03）
- `zero-one:yi-1-5-34b:base`（Yi-1.5-34B，2024-05）
- `zero-one:yi-1-5-9b:base`（Yi-1.5-9B，2024-05）
- `zero-one:yi-large:base`（Yi-Large，2024-05）
- `zero-one:yi-lightning:base`（Yi-Lightning，2024-10）

### modelbest（in_v1 0，to_add 1）

- `[to_add]` `modelbest:minicpm-4:base`（MiniCPM 4）

### aispeech（in_v1 0，to_add 0）


