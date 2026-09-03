# model_data 缺口扫描报告（D32）

> 撰写于 2026-09-03。承接 `GAP_SCAN_REPORT_D31.md`，覆盖 D32 第一批 5 个未深探方向扫描（高 ROI 方向 1-5）。

## 0. 数据集当前状态（D32 起）

| 维度 | 数值 |
|---|---|
| 总记录 | 891 条（D31 删 42 条 2022 前，933 → 891） |
| 厂商 | 233 家 |
| 跑分条目 | 5,634（self_reported 4,023 + independent 1,004 + arena_elo 513）— D28 之前算 4,108 + 1,013 + 513 |
| license 填充率 | **0.9%**（8/891）⚠️ 极低 |
| knowledge_cutoff | 18.5%（173/891） |
| pricing.input | 32.3%（288/891） |
| open_weights | T 521 (58.5%) / F 316 (35.5%) / null 54 (6.1%) |
| api_access | T 654 (73.4%) / F 161 (18.1%) / null 76 (8.5%) |
| local_deployment | T 535 (60.0%) / F 234 (26.3%) / null 122 (13.7%) |

## 1. D32 扫描的 5 个方向

### 1.1 价格历史变迁（缺口 1）

**问题**：当前 schema 每模型只有 1 个 `pricing` 对象，无 `pricing_history` 数组设计，**无法扫同模型价格历史变迁**。

**可扫的替代**：同厂商代际价格变化。Top 10 厂商价格时间线已列出（OpenAI 57 价 / Anthropic 44 / Alibaba 32 / Mistral 30 / Google DeepMind 22 / xAI 15 / DeepSeek 11 / MiniMax 8 / Google 6 / Cohere 5）。

**pricing 字段填充率**：

| 字段 | 填充数 | 占比 |
|---|---|---|
| pricing.input | 288 | 32.3% |
| pricing.output | 273 | 30.6% |
| pricing.cached_input | 159 | 17.8% |
| pricing.batch_input | 93 | 10.4% |
| pricing.effective_date | 883 | 99.1% |

**effective_date 月份分布异常**：

| 月份 | 数量 |
|---|---|
| 2026-08 | 653（绝大多数） |
| 2025-04 | 15 |
| 2024-04 | 10 |

**问题**：653 条 effective_date 都是 2026-08（采集月份），不反映真实定价月份——批量采集时默认填了当前月。需数据采集时补真实定价月份。

**结论**：

- 缺口 A：schema 缺 `pricing_history` 字段，无法追溯同模型价格变化
- 缺口 B：653 条 effective_date 是采集月份而非真实定价月份（数据质量问题）

### 1.2 API 可用性 × 厂商矩阵（缺口 2）

**全库三态分布**：

| 字段 | True | False | null |
|---|---|---|---|
| open_weights | 521 (58.5%) | 316 (35.5%) | **54 (6.1%)** |
| api_access | 654 (73.4%) | 161 (18.1%) | **76 (8.5%)** |
| local_deployment | 535 (60.0%) | 234 (26.3%) | **122 (13.7%)** |

**厂商维度 Top 15 矩阵**：

| vendor | n | ow_t | ow_null | api_t | api_null | ld_t | ld_null |
|---|---|---|---|---|---|---|---|
| Alibaba | 80 | 70 | 0 | 73 | 2 | 67 | 3 |
| OpenAI | 64 | 3 | **21** | 40 | **21** | 1 | **33** |
| Anthropic | 44 | 0 | **9** | 33 | **9** | 0 | **15** |
| Mistral AI | 41 | 29 | 0 | 40 | 0 | 31 | 1 |
| Google DeepMind | 37 | 11 | **5** | 29 | 3 | 11 | 6 |
| DeepSeek | 27 | 27 | 0 | 24 | 0 | 24 | 3 |
| NVIDIA | 25 | 24 | 0 | 21 | 0 | 23 | 2 |
| Microsoft | 23 | 17 | 0 | 21 | 0 | 17 | 4 |
| xAI | 19 | 1 | 0 | 17 | 0 | 1 | 2 |
| Meta | 18 | 14 | 0 | 5 | 0 | 14 | 1 |

**矛盾清单**：

1. **open_weights=null 但 api=true** 共 4 条（应改 ow=false 因为 API-only）：
   - Google DeepMind | gemini-3.6-flash_high
   - kunlun | 天工大模型 4.0
   - unisound | Shanhai 2.0
   - Inflection AI | Inflection 3.0

2. **OpenAI/Anthropic 等 API-only 厂商大量 ow=null**：OpenAI 21 条 ow=null（应是 false）、Anthropic 9 条 ow=null、Google DeepMind 5 条——这些厂商明确闭源，ow 应统一标 false

3. **open_weights=null 共 54 条 + api_access=null 76 条 + local_deployment=null 122 条**：缺三态的记录需逐条补

### 1.3 置信度 × 厂商分布（缺口 3）

**三段 confidence 分布**：

| 段 | 总条数 | Top 类型 |
|---|---|---|
| self_reported | 4,023 | T0-自报 49.4% / T0-自报-转述 19.9% / **空 17.1%** / T3 12.8% |
| independent | 1,004 | T1 83.0% / T3 14.4% / T2 1.3% |
| arena_elo | 513 | T1 97.1% / T3 2.1% |

**缺口 A**：self_reported 段 **686 条 confidence 为空**，需补。

**厂商自报率 Top 15**（跑分条目 ≥ 5 的厂商中 100% 自报无独立验证）：

| vendor | total | self | indep | arena |
|---|---|---|---|---|
| qihoo-360 | 26 | 26 | 0 | 0 |
| Abacus AI | 15 | 15 | 0 | 0 |
| aleph-alpha | 13 | 13 | 0 | 0 |
| Alibaba (Tongyi Lab) | 11 | 11 | 0 | 0 |
| Alibaba (Qwen Team) | 6 | 6 | 0 | 0 |
| **Apple** | 28 | 28 | 0 | 0 |
| Beijing OrionStar | 7 | 7 | 0 | 0 |
| **ByteDance Seed Team** | 11 | 11 | 0 | 0 |
| mbzuai | 7 | 7 | 0 | 0 |
| 中国移动 | 5 | 5 | 0 | 0 |
| unicom | 5 | 5 | 0 | 0 |
| **Cognition** | 6 | 6 | 0 | 0 |
| **Cursor** | 9 | 9 | 0 | 0 |
| Deci AI | 7 | 7 | 0 | 0 |
| Fujitsu+Cohere | 8 | 8 | 0 | 0 |

**厂商独立验证率 Top 10**：

| vendor | total | indep | arena | rate |
|---|---|---|---|---|
| Naver | 12 | 12 | 0 | 100% |
| Mig Tissera | 6 | 6 | 0 | 100% |
| Z.ai (Zhipu AI) | 18 | 13 | 3 | 88.9% |
| Databricks | 14 | 9 | 3 | 85.7% |
| Baidu | 18 | 10 | 4 | 77.8% |
| Moonshot | 16 | 9 | 3 | 75.0% |
| OpenAI | 407 | 198 | 70 | 65.8% |
| Zhipu AI (国际) | 15 | 4 | 5 | 60.0% |
| Zhipu AI (北京智谱) | 5 | 2 | 1 | 60.0% |
| Anthropic | 345 | 144 | 60 | 59.1% |

**观察**：

- Apple / ByteDance / Cognition / Cursor / 中国移动 等大公司**100% 自报**——这些厂商其实有独立评测数据可补，是数据缺失
- self_reported 段 17.1% confidence 空，需补
- 部分厂商变体（Alibaba 有 3 种 vendor 写法：Alibaba / Alibaba Tongyi Lab / Alibaba Qwen Team）—— D28 已部分归一但仍有

### 1.4 source_type 跨段错位（缺口 4）

**期望**：

- self_reported 段 source_type 应含「自报」「官方」「GitHub」「技术报告」
- independent 段 source_type 应含「独立」「评测」「平台」「epoch.ai」「artificialanalysis」
- arena_elo 段 source_type 应含「竞技场」「Arena」「lmarena」「LMArena 镜像」

**扫描结果**：

| 段 | 错位条数 |
|---|---|
| self_reported | 0 ✓ |
| independent | 0 ✓ |
| **arena_elo** | **14** ⚠️ |

**arena_elo 段错位 14 条**（source_type 标"独立评测平台"应改"LMArena 镜像"）：

- Alibaba: text / coding / vision 子榜分 3 条
- Baidu: search 子榜分 1 条
- Google DeepMind: text / webdev 子榜分共 4 条
- 其余厂商 6 条

**全库 source_type Top 20**：

| source_type | 条数 |
|---|---|
| (空) | 1,301 |
| 独立评测平台 | 840 |
| 官方 Model Card（自报） | 727 |
| 行业媒体聚合官方发布（自报分转述） | 491 |
| LMArena 镜像（DataLearner），原始来源 LM Arena | 480 |
| 官方技术报告（自报） | 470 |
| 官方自报（其它） | 252 |

**缺口**：

- arena_elo 段 14 条 source_type 错位需归一为 "LMArena 镜像"
- 全库 1,301 条 source_type 为空，需补

### 1.5 license × open_weights 一致性（缺口 5）

**license 填充率：0.9%（8/891）** ⚠️ 极低，仅 5 种 license 写法：

| license | 数量 |
|---|---|
| (空) | 883 |
| 闭源 API (proprietary, API-only) | 4 |
| MIT (code) + DeepSeek Model License | 1 |
| Model License (DeepSeek Model Agreement) + MIT (Code) | 1 |
| 闭源 API，无公开权重或许可 | 1 |
| NVIDIA Open Model License + Llama 3.1 Community License | 1 |

**矛盾清单**：

| 矛盾类型 | 条数 | 说明 |
|---|---|---|
| ow=true 但 license 空 | **518** | 开源权重模型缺协议字段 ⚠️ |
| ow=true 但 license 是闭源 | 0 | 无 |
| ow=false 但 license 是开源协议 | 0 | 无 |
| ow=null 但 license 有值 | 4 | gemini-1.5-pro×2 / gemini-2.5-pro-exp / Moonshot-v1 |

**缺口 A**：518 条 open_weights=true 但 license 空，需逐条补 license 字段（开源权重必有协议，这是严重缺失）。

**缺口 B**：4 条 ow=null 但 license="闭源 API"（gemini-1.5-pro/Moonshot-v1）—— ow 应改 false。

## 2. D32 扫描发现的数据问题清单

| # | 问题 | 影响条数 | 优先级 | 修复方式 |
|---|---|---|---|---|
| 1 | arena_elo 段 source_type 错位（"独立评测平台"→"LMArena 镜像"） | 14 | 高 | 机械修 |
| 2 | open_weights=null 但 api=true | 4 | 高 | ow 改 false |
| 3 | ow=null 但 license="闭源 API" | 4 | 高 | ow 改 false |
| 4 | API-only 厂商大量 ow=null（OpenAI 21 / Anthropic 9 / Google DeepMind 5） | ~35 | 中 | 厂商维度的 ow 改 false |
| 5 | open_weights=true 但 license 空 | 518 | 高 | 需批量补 license（按 vendor 推断协议：DeepSeek/Alibaba/Llama 系等） |
| 6 | self_reported 段 confidence 空 | 686 | 中 | 按 source_type 推断 confidence |
| 7 | 全库 source_type 空 | 1,301 | 中 | 按 source_url 推断 |
| 8 | pricing.effective_date 653 条是采集月份非真实定价月份 | 653 | 低 | 数据质量问题，需补真实定价月份 |
| 9 | schema 缺 pricing_history 字段 | — | 低 | schema 设计缺陷，当前无法扫同模型价格变迁 |

## 3. 仍待推进的方向

### 3.1 数据修复（高优先级 4 项）

1. arena_elo 段 14 条 source_type 错位机械修
2. open_weights=null 但 api=true 4 条 + ow=null 但 license="闭源 API" 4 条 → ow 改 false
3. API-only 厂商 ow=null 改 false（OpenAI/Anthropic/Google DeepMind 等）
4. 518 条 ow=true 但 license 空的批量补 license

### 3.2 数据修复（中优先级 3 项）

5. self_reported 段 686 条 confidence 空 → 按 source_type 推断
6. 全库 1,301 条 source_type 空 → 按 source_url 推断
7. pricing.effective_date 653 条采集月份 → 补真实定价月份

### 3.3 可视化改进（A + B 方向）

- **方向 B**：6 张高价值图表（B1 排行总榜 / B2 scaling law / B6 可信度仪表盘 后端就绪直接渲染；B3 价格瀑布 / B4 Pareto / B5 同代际横评 需新写前端）
- **方向 A**：架构重组（总览 Dashboard 重构 + 模型档案路由 + 厂商档案页 + Ctrl+K 搜索）

### 3.4 未深探的剩余方向（11-20）

- benchmark × score_type 配对合理性
- release_date vs knowledge_cutoff 矛盾
- 价格合理性分布
- modality 组合频次
- vendor 命名稳定性
- derivative_of 派生关系
- Arena 子榜分数合理性
- 跨厂商同 benchmark 排名一致性
- collected_at 与 verification_status 一致性
- vendor 中英文混用
- 同 benchmark 不同 score_type 度量方式混用
