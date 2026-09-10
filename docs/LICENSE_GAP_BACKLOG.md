# license 空白留档（D41 第 5 项，用户裁定「留档后续再做」）

> 生成时间：2026-09-10（D41）｜数据源：`model_data_v2.jsonl`（937 条）
> 触发：D40 报告 §七.5「license 仍有 46 条空白」，用户 D41 裁定 **留档后续再做**，本轮不补。

## 一、口径说明

「license 空白」**不是**指全库 412 条 `basic_info.license` 为空的记录——其中绝大多数是闭源商业模型（`access.open_weights=false`），本就没有开源许可证可言。
有采集意义的缺口只有两类：

| 类别 | 条数 | 含义 |
|---|---|---|
| **A 类：`open_weights=true` 但 license 空** | **46** | 开放权重模型却查不到许可证，属真实缺口 |
| B 类：`open_weights=null` 且 license 空 | 16 | 是否开源本身未确认，先确认开源再谈许可证 |
| （参考）`open_weights=false` 且 license 空 | 350 | 闭源，无采集意义 |

## 二、A 类：开放权重但 license 空白（46 条，本轮留档）

| # | model_id | vendor | verification_status | 源链接数 | 源链接中的 HF repo | 备注 |
|---|---|---|---|---|---|---|
| 1 | `beijing-orionstar-technology-co-ltd:orion-star:base` | Beijing OrionStar Technology Co., Ltd. | 已定死 | 4 | OrionStarAI/Orion-14B-Base |  |
| 2 | `cerebras-systems:cerebras-gpt-13b:base` | Cerebras Systems | 已定死 | 8 | cerebras/Cerebras-GPT-13B |  |
| 3 | `china-mobile:jiutian-139moe:base` | 中国移动（China Mobile）—— 中国移动九天研究院（CMCC Jiutian / 中移九天） | 待验证 | 6 | — | **无 HF repo 线索，需人工定点** |
| 4 | `cisco:foundation-sec-8b:base` | Cisco | 待验证 | 4 | fdtn-ai/Foundation-Sec-8B |  |
| 5 | `deep-cogito:cogito-v2-1:base` | Deep Cogito | 已验证 | 8 | deepcogito/cogito-671b-v2.1 |  |
| 6 | `g42:jais-70b:base` | G42 | 待验证 | 7 | — | **无 HF repo 线索，需人工定点** |
| 7 | `indosat-tech-mahindra-ai-singapore-goto:gemma2-9b-cpt-sahabat-ai:base` | Indosat Ooredoo Hutchison / Tech Mahindra / AI Singapore / GoTo Group | 待验证 | 4 | GoToCompany/gemma2-9b-cpt-sahabatai-v1-base<br>GoToCompany/gemma2-9b-cpt-sahabatai-v1-instruct |  |
| 8 | `johannes-kepler-university-linz:xlstm-1-4b:base` | Johannes Kepler University Linz (JKU) / NX-AI | 待验证 | 7 | NX-AI/xlstm_scaling_laws<br>NX-AI/xLSTM-7b |  |
| 9 | `lmsys:vicuna-13b-v1-3:base` | LMSYS | 已定死 | 5 | lmsys/vicuna-13b-v1.3 |  |
| 10 | `massachusetts-institute-of-technology-mit:linoss:base` | Massachusetts Institute of Technology (MIT) | 已验证 | 7 | — | **无 HF repo 线索，需人工定点** |
| 11 | `motif-technologies:motif-3:base` | Motif Technologies | 待验证 | 6 | — | **无 HF repo 线索，需人工定点** |
| 12 | `nanbeige-llm-lab:nanbeige2-16b-chat:base` | Nanbeige Lab | 待验证 | 6 | Nanbeige/Nanbeige2-16B-Chat |  |
| 13 | `nstc-taiwan:llama-3-taide-lx-8b-chat-alpha1:base` | NSTC (Taiwan, China) | 待验证 | 11 | taide/Llama3-TAIDE-LX-8B-Chat-Alpha1 |  |
| 14 | `nstc-taiwan:taide-lx-7b:base` | NSTC (Taiwan, China) | 待验证 | 13 | taide/TAIDE-LX-7B-Chat<br>ZoneTwelve/TAIDE-LX-7B-GGUF |  |
| 15 | `nexusflow:athene-v2:base` | NexusFlow | 待验证 | 9 | Nexusflow/Athene-V2-Chat<br>Nexusflow/Athene-V2-Chat-72B |  |
| 16 | `opengpt-x-fraunhofer-institute-for-algorithms-and-scientific-computing-forschungszentrum-julich-technische-universit-t-dresden:teuken-7b:base` | OpenGPT-X Consortium (Fraunhofer IAIS / Fraunhofer IIS / Forschungszentrum Jülich / TU Dresden / DFKI / IONOS / Aleph Alpha 等) | 待验证 | 4 | openGPT-X/Teuken-7B-base-v0.6 |  |
| 17 | `prime-intellect:intellect-3:base` | Prime Intellect | 待验证 | 7 | PrimeIntellect/INTELLECT-3<br>PrimeIntellect/INTELLECT-3-FP8 |  |
| 18 | `prime-intellect:opendiloco-1-1b:base` | Prime Intellect | 待验证 | 7 | PrimeIntellect/llama-1b-fresh |  |
| 19 | `prime-intellect:opendiloco-150m:base` | Prime Intellect | 待验证 | 6 | PrimeIntellect/llama-150m-fresh |  |
| 20 | `princeton:mamba-2-2-7b:base` | Princeton University | 待验证 | 6 | state-spaces/mamba2-2.7b |  |
| 21 | `princeton:simpo:base` | Princeton University | 待验证 | 3 | — | **无 HF repo 线索，需人工定点** |
| 22 | `salesforce:xgen-7b-8k-base:base` | Salesforce | 已定死 | 7 | Salesforce/xgen-7b-8k-base |  |
| 23 | `saltlux:luxia-21-4b-alignment:base` | Saltlux | 待验证 | 6 | saltlux/Ko-Llama3-Luxia-8B |  |
| 24 | `sambanova:sambalingo-thai-chat-70b:base` | SambaNova | 待验证 | 8 | sambanovasystems/SambaLingo-Thai-Chat-70B<br>sambanova/sambalingo-thai-chat-70b |  |
| 25 | `sambanova:sambalingo-thai-chat:base` | SambaNova | 待验证 | 7 | sambanova/sambalingo-thai-chat |  |
| 26 | `sea-ai-lab:sailor-7b-chat:base` | Sea AI Lab | 待验证 | 4 | sail/Sailor-7B-Chat |  |
| 27 | `shanghai-kuanyu-digital-technology-co-ltd-bilibili:index-1-9b:base` | Bilibili（上海宽娱数码科技有限公司） | 待验证 | 3 | — | **无 HF repo 线索，需人工定点** |
| 28 | `sk-telecom:a-x-k1:base` | SK Telecom | 待验证 | 7 | skt/A.X-K1 |  |
| 29 | `sk-telecom:a-x-k2:base` | SK Telecom | 待验证 | 8 | skt/A.X-K2 |  |
| 30 | `snowflake:arctic:base` | Snowflake | 待验证 | 9 | Snowflake/snowflake-arctic-base<br>Snowflake/snowflake-arctic-instruct |  |
| 31 | `speakleash-cyfronet-agh:bielik-11b-v2:base` | SpeakLeash / Cyfronet AGH | 待验证 | 6 | speakleash/Bielik-11B-v2 |  |
| 32 | `speakleash-cyfronet-agh:bielik-7b:base` | SpeakLeash / Cyfronet AGH | 待验证 | 5 | — | **无 HF repo 线索，需人工定点** |
| 33 | `t-bank:t-pro-2-0:base` | T-Bank | 待验证 | 5 | — | **无 HF repo 线索，需人工定点** |
| 34 | `kotoba-technologies:fugaku-llm:base` | Kotoba Technologies | 待验证 | 6 | Fugaku-LLM/Fugaku-LLM-13B |  |
| 35 | `tokyo-institute-of-technology:swallow:base` | Tokyo Institute of Technology | 已定死 | 11 | tokyotech-llm/Swallow-7B<br>tokyotech-llm/Swallow-13B<br>tokyotech-llm/Swallow-70B |  |
| 36 | `trend-micro:llama-primus-nemotron-70b:base` | Trend Micro | 待验证 | 5 | — | **无 HF repo 线索，需人工定点** |
| 37 | `trillion-labs:tri-21b:base` | Trillion Labs | 已验证 | 4 | trillionlabs/Tri-21B |  |
| 38 | `deep-cogito:cogito-1-series:base` | Deep Cogito | 已验证 | 8 | — | **无 HF repo 线索，需人工定点** |
| 39 | `migtissera:llama-3-70b-synthia-v3-5:base` | Mig Tissera | 待验证 | 5 | migtissera/Llama-3-70B-Synthia-v3.5 |  |
| 40 | `jondurbin:llama-3-airoboros-70b-3-3:base` | Jondurbin | 待验证 | 6 | jondurbin/airoboros-70b-3.3<br>jondurbin/llama-3-airoboros-70b-3.3 |  |
| 41 | `lmsys:vicuna-13b-v1-1:base` | LMSYS | 已定死 | 4 | lmsys/vicuna-13b-v1.1 |  |
| 42 | `upstage:solar-open-100b:base` | Upstage | 待验证 | 8 | upstage/Solar-Open-100B |  |
| 43 | `upstage:solar-open2-250b:base` | Upstage | 待验证 | 9 | upstage/Solar-Open2-250B |  |
| 44 | `tencent:hy-mt2-1-8b:base` | Tencent | 已验证 | 3 | tencent/Hy-MT2-1.8B |  |
| 45 | `tencent:hy-mt2-30b-a3b:base` | Tencent | 已验证 | 3 | tencent/Hy-MT2-30B-A3B |  |
| 46 | `tencent:hy-mt2-7b:base` | Tencent | 已验证 | 3 | tencent/Hy-MT2-7B |  |

## 三、B 类：开源状态未确认且 license 空（16 条，前置条件未满足）

| # | model_id | vendor | verification_status | 源链接数 |
|---|---|---|---|---|
| 1 | `4paradigm:zhiyan:base` | 4Paradigm | 待验证 | 6 |
| 2 | `allenai:atlantes:base` | Allen Institute for AI | 待验证 | 3 |
| 3 | `beijing-58-information-technology:chatling:base` | Beijing 58 Information Technology | 待验证 | 6 |
| 4 | `beijing-beida-software-engineering-co-ltd:beiruan:base` | Beijing Beida Software Engineering Co., Ltd. | 待验证 | 7 |
| 5 | `beijing-bitauto-interactive-advertising-company-limited:lantu:base` | Beijing Bitauto Interactive Advertising Company Limited | 待验证 | 5 |
| 6 | `beijing-yuanshi-technology-co-ltd:yuanshi:base` | 北京元始科技有限公司 | 待验证 | 5 |
| 7 | `unicom:yuanjing-llm:base` | China Unicom | 待验证 | 6 |
| 8 | `creditease:mili:base` | CreditEase | 待验证 | 4 |
| 9 | `google:datarater-test-model:base` | Google | 待验证 | 2 |
| 10 | `guangzhou-lingju-information-technology-co-ltd:lingju-lingnao:base` | Guangzhou Lingju Information Technology Co., Ltd. | 待验证 | 8 |
| 11 | `shanghai-digivio-information-technology-co-ltd:digivio:base` | 上海数聚威信息科技有限公司（Shanghai Digivio Information Technology Co., Ltd.） | 待验证 | 0 |
| 12 | `shanghai-shuheng-information-technology-co-ltd:mingzhi-guwen:base` | 上海书珩信息技术有限公司 (Shanghai Shuheng Information Technology Co., Ltd.) | 待验证 | 3 |
| 13 | `tencent:tencent-search-llm:base` | Tencent | 待验证 | 5 |
| 14 | `unisound:unigpt-mmed:base` | Unisound | 待验证 | 7 |
| 15 | `xiaomi:xiaomi-edge-side-text:base` | Xiaomi | 待验证 | 6 |
| 16 | `inclusionai:ling-3-0-flash-sante:base` | InclusionAI | 待验证 | 2 |

## 四、后续补采方法（D40 已验证有效，本轮未执行）

1. **权威源**：`https://huggingface.co/api/models/{repo}` 返回的 `tags` 数组里读 `license:X`。
   - 比从页面/README 正则抽文本可靠得多（D40 实测正则把 `HF`、`Under the MIT` 误判为许可证名）。
   - 现成脚本：`scripts/d40_license_hf.py`（含 `repo_matches_model()` 同尺寸一致性校验）。
2. **必配一致性校验**：从记录文本抽 repo id 时可能抽错仓库。做法是把 repo 名与记录里的参数量 token 取**交集，空则拒写**（别要求全等，`mamba-2-2-7b` ↔ `mamba2-2.7b` 这类写法差异会被误拒）。D40 实测拦下 `g42:jais-70b` ← `inception42/jais-13b` 的错配。
3. **无 HF repo 线索的**：需人工定点（官方 Model Card / 权重下载页 / GitHub 仓库 LICENSE）。D40 曾统计 A 类中约 32 条属此类；本轮按更严格的 HF **模型库**正则口径（排除 `api/models/*`、`papers/*` 等非模型路径）复核为 **10 条**，差异来自口径而非数据变化，以本轮 10 条为准。
4. **闭源商业模型不要强补**：`open_weights=false` 时 license 留空是本库既有惯例，不是缺口。

## 五、D40 已完成的填充（本轮基线）

D40 通过 HF API 写入 36 条（含一致性校验拒绝 3 条、无 license tag 11 条、无 repo 线索 32 条），`license` 填充率 51.0% → 56.0%。本轮（D41）**未新增填充**，仅留档。

