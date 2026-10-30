# D57 报告 · D56 以来的新主线模型补采

> **轮次**：D57 ｜ **日期**：2026-10-31（采集）｜ **触发**：用户「看一下 model_data 工作区，更新一下上次更新以来新的主线模型的情况」→ S1 拍板「9 条全采 + Qwen3-VL 只补两个 MoE 尺寸」
> **基线**：主库 1015 条（D56 收官 2026-10-11）｜门禁 ERROR 0 / WARN 0｜r1=0 / r2=0
> **结果**：**13 条立行入库 → 1028 条**；另 3 条变体挂现有记录 notes；门禁 ERROR 0 / WARN 0，r1=r2=0，硬错零增长

---

## 0. 一句话结论

19 天窗口（10-11 → 10-30）内的新主线模型全部采集入库：**海外 8 条**（Muse Wonder / GPT-6.1 Terra / Kimi K3.1 Pro / Mistral Large 4 / Nemotron 3.5 Super VL / Mercury 3 / Beam 1.0）+ **国内 2 条**（MiniMax M3.1 Flash / DeepSeek V4.1 Flash 1017）+ **存量缺口 4 条**（Qwen3-VL 235B-A22B 与 30B-A3B 各 Instruct/Thinking）。

四条源（OpenRouter / Arena 三榜 / 阿里云百炼台账 / ModelScope）对这批模型的指向一致，无单源孤证。

---

## 1. 入库 13 条（batch `b352w1`）

| # | model_id | 厂商 | release_date | 关键规格 | 定价 $/1M | 许可 | 可信度 | 自报跑分 |
|---|---|---|---|---|---|---|---|---:|
| 1 | `meta:muse-wonder:base` | Meta | 2026-10-12 | ctx 1,048,576；参数量官方未披露 | 4.00 / 20.00 / cached 0.20 | 闭源 API | T3（官方定价页不可达） | 10 |
| 2 | `openai:gpt-6.1-terra:base` | OpenAI | 2026-10-26 | ctx 1,050,000；max_out 128K | 1.00 / 5.00 / cached 0.05 / batch 0.5-2.5 | 闭源 API | T1 | 12 |
| 3 | `moonshot:kimi-k3.1-pro:base` | Moonshot AI | 2026-10-23 | 2800B 总 / 104B 激活 MoE；ctx 1,048,576 | 2.00 / 10.00 / cached 0.20；cache_write 5m 2.00、1h 4.00 | 未公布 | **T0** | 33 |
| 4 | `mistral:mistral-large-4:base` | Mistral AI | 2026-10-27 | 1050B 总 / 49B 激活 MoE；ctx 1,000,000 | 0.70 / 2.10 / cached 0.07 | Mistral Ecosystem Open-Weight License（modified MIT） | T1 | 2 |
| 5 | `minimax:minimax-m3.1-flash:base` | MiniMax | 2026-10-19 | 428B 总 / 23B 激活 MoE；ctx 1,000,000 | 0.15 / 0.60 / cached 0.015 | MiniMax Community License | **T0** | 14 |
| 6 | `deepseek:deepseek-v4.1-flash:1017` | DeepSeek | 2026-10-17 | 552B 总 / 16B 激活；ctx 1,048,576；max_out 393,216 | 0.30 / 1.20 / cached 0.006（空闲时段减半 0.15/0.60） | MIT | **T0** | 12 |
| 7 | `nvidia:nemotron-3.5-super-vl:base` | NVIDIA | 2026-10-15 | 120B 总 / 12B 激活 MoE；ctx 1,000,000 | 0.15 / 0.50 / cached 0.02 | OpenMDW-1.1 | T1（官方刊例） | 36 |
| 8 | `inception-labs:mercury-3:base` | Inception Labs | 2026-10-19 | diffusion-based LM；参数量未披露；ctx 1,000,000 | 0.20 / 0.70 / cached 0.02（首发 5 折促销 0.10/0.35） | 闭源 API | **T0** | 12 |
| 9 | `reflection:beam-1.0-501b-a23b:base` | Reflection AI | 2026-10-16 | 501.3B 总 / 23.4B 激活 MoE；ctx 1,048,576 | 全 null（官方 API 免费公测，无刊例价；OpenRouter $0.25/$1.00 仅第三方） | Apache-2.0 | **T0** | 22 |
| 10 | `alibaba:qwen-3-vl-235b-a22b:instruct` | Alibaba | 2025-09-23 | 235B / 22B；ctx 1,000,000（256K 原生 + 扩展） | 0.40 / 1.60 | Apache-2.0 | **T0** | 21 |
| 11 | `alibaba:qwen-3-vl-235b-a22b:thinking` | Alibaba | 2025-09-23 | 同上，思考档 | 0.40 / 4.00 | Apache-2.0 | **T0** | 21 |
| 12 | `alibaba:qwen-3-vl-30b-a3b:instruct` | Alibaba | 2025-10-04 | 30B / 3B；ctx 1,000,000 | 0.20 / 0.80 | Apache-2.0 | **T0** | 20 |
| 13 | `alibaba:qwen-3-vl-30b-a3b:thinking` | Alibaba | 2025-10-04 | 同上，思考档 | 0.20 / 2.40 | Apache-2.0 | **T0** | 20 |

> **Qwen3-VL 日期更正**：S0 阶段据媒体推测为 2026-10 补尺寸，回官方 GitHub News 核实后确认两个 MoE 尺寸的首发日是 **2025-09-23 / 2025-10-04**。2026-10 的开源只是 Dense 4B/8B/2B/32B 补尺寸，不改变 MoE 主线的发布日。

---

## 2. 挂现有记录留痕（3 条，不立行）

用户裁决「挂现有」，已写入对应记录的 `basic_info.notes`（追加 `【D57 变体留痕】` 段）：

| 变体 | 挂到 | 留痕要点 |
|---|---|---|
| Muse Spark Open（10-15） | `meta:muse-spark:base` | 开源权重、agentic coding 专用；OR id `meta/muse-spark-open`、ctx 1,048,576、$1.25/$4.25；权重是否同 checkpoint 待核 |
| LFM2.5-24B-A2B（10-13） | `liquid:lfm2.5-8b-a1b:base` | 24B 总 / 2.45B 激活 MoE、128K ctx、$0.05/$0.70；LFM2.5 家族新尺寸档 |
| Ling-3.1-flash-1019（10-27） | `inclusionai:ling-3.1-flash:base` | 560B MoE、1M ctx；ModelScope 仓库 10-27 / 媒体 10-28；迭代快照 |

---

## 3. 质量闸门

| 检查 | 基线（D56 后） | D57 后 | 判读 |
|---|---:|---:|---|
| 主库记录数 | 1015 | **1028** | +13 全为 `add_record`，无覆盖 |
| 门禁 ERROR / WARN（全库） | 0 / 0 | **0 / 0** | 通过 |
| 源文件门禁（13 个） | — | **13/13 ERROR 0 / WARN 0** | 通过 |
| 体检器硬错（o1-o6 / c1-c4） | o1=9 / c4=2，其余 0 | **同左** | **零增长** |
| 体检器 r1 / r2 | 0 / 0 | **0 / 0** | 通过（本轮修 9 处基准名异写） |
| 体检器 c5 | 20 | 22 | +2（`muse-wonder` 与 `kimi-k3.1-pro` 的定位/参数量级疑点，属新记录） |
| 体检器 a7 / a8b | 434 / 93 | 446 / 96 | +12 / +3（新记录 version 冗余与 license 未分类，属既有口径） |
| a6 同厂同代系指纹簇 | 17 | 20 | +3（`qwen-3-vl-*` 两档 + 一条新厂商簇） |

**验证方法**：把 13 条新记录从当前库扣除后重跑体检，30 项指标与合并前备份**逐项完全相等** ⇒ 合并未触碰任何既有记录，全部增量都来自本批。

**本轮修的 9 处基准名大小写异写**（否则 r2 由 0 变 9）：`SWE-bench Pro`→`SWE-Bench Pro`、`tau2-bench telecom`→`Tau2-bench Telecom`、`CharXiv reasoning`→`CharXiv Reasoning`、`AA-Omniscience accuracy`→`AA-Omniscience Accuracy`（以上 nemotron-3.5-super-vl）；`GDP.pdf`→`GDP.PDF`、`MMMU-Pro (w/ python)`→`MMMU-Pro (w/ Python)`、`CharXiv (RQ, w/ python)`→`CharXiv (RQ, w/ Python)`（以上 kimi-k3.1-pro）；`Vals Finance Agent V2`→`Vals Finance Agent v2`（muse-wonder）；`τ³-bench Banking`→`τ³-Bench Banking`（mercury-3）。主库与 `incoming/` 源文件同步修改。

---

## 4. 待复核 / 遗留（下轮可接）

1. **`meta:muse-wonder` 定价为 T3**：官方定价页不可达，$4/$20 取 OpenRouter（Meta 官方端点）；`cached_input` 0.20 同样来自 OR。拿到 Meta 官方定价页后应升 T0。
2. **`reflection:beam-1.0` 定价全 null**：官方 API 处于免费公测、无刊例价；OpenRouter 的 $0.25/$1.00 为第三方渠道价，按红线未写入 `pricing`。
3. **`mistral:mistral-large-4` 参数量三口径**：模型卡 1T、AA 1.1T、激活 49B（含 embedding/输出层 52B）；已按 1050B / 49B 入库并在 notes 留三口径。
4. **`inception-labs:mercury-3` 发布日 10-19 vs OpenRouter 10-16**：取官方博客页脚日期 10-19，OR 预登记日差异写 notes。
5. **Qwen3-VL 定价是国际部署口径**：0.40/1.60 等取自百炼国际站美元价；内地人民币价与托管侧 131,072 上下文限制已写 notes。
6. **`kimi-k3.1-pro` 的 open_weights=false（采集时未放权重）**：官方承诺 2026-11-04 前释出，兑现后需重采 `access` / `license`。
7. **`stepfun:step-5-preview` 的权重承诺日（2026-10-15）已过**：D56 遗留项，本轮未复核，建议下次一并核。
8. **智谱 GLM-5.4 / 5.5 未发布**：10-22 官方海报预告，截至 10-30 无发布公告；下轮 S0 优先复扫。

---

## 5. 观察清单（本轮不采）

| 项 | 理由 |
|---|---|
| Unbiased Pareto 26.9 / 26.10 | 疑为聚合/路由产品，需先确认是否自有权重 |
| Particle-1 | 基于 DeepSeek V4.1 Flash 后训练，属衍生模型 |
| Elorian Glimpse | 新厂商，规模与权重未知 |
| Moondream 3.1 9B-A2B | 小型视觉模型，非主线 |
| Recursive Flint v1.0 | 仅 free 档，信息不足 |
| PrismML Ternary Bonsai 2 9B | 基于 Qwen3.5 的社区派生 |
| 智谱 GLM-5.4 / 5.5 | 未发布 |
| 小米新模型 / Qwen4-27B | DataLearner 预告日期，未核实到官方发布 |

---

## 6. S0 源覆盖

| 源 | 状态 | 命中 |
|---|---|---|
| OpenRouter | HTTP 200 / 456 模型 | 10-11 后新上架 28 条（去 batch/free 后 20 条） |
| Arena（DataLearner 镜像） | 快照 2026-10-22，text 418 / coding 413 / math 404 | 三榜未命中真新面孔 3 条（Muse Wonder / Beam 1.0 / Nemotron 3.5 Super VL） |
| arenaofbias | works 2,707 / entries 275 | 真新面孔 1 条（Beam）+ 1 条待查（Sonus） |
| galbands | 更新至 10-29，综合榜 139 行 | 0 条（唯一未匹配是 Hy3，命名差异） |
| ModelScope | 22 个官方组织 | 10-01 后新仓库 22 条，主线 2 条 |
| 阿里云百炼台账 | 10-29 更新 | 10-11 后 13 个去重型号，主线 2 条 |
| DeepSeek sitemap | 最新 news261017 | 1 条 |
| Artificial Analysis | 快照 735 条，max releaseDate 2026-09-07 | **滞后期约 7 周，本轮未用作发现源** |

---

*采集文件：`incoming/models/b352w1__*.jsonl`（13 个）｜台账：`docs/batch_claim_ledger.jsonl`（`batch_id=b352w1`，`round=D57`）｜合并参数：`--on-null take_source --on-both source_wins --on-array union_by_key --array-key-override benchmarks.arena_elo:sub_benchmark,date benchmarks.self_reported:benchmark,config benchmarks.independent:benchmark,config --on-schema upgrade --tie-breaker keep_target`*
