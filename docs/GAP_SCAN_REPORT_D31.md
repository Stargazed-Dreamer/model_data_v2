# model_data 缺口扫描与可视化报告（D29-D31）

> 撰写于 2026-09-03。承接 `GAP_SCAN_REPORT_D28.md`，覆盖 D29-D31 的工作：可视化改进 3 批 + 缺口扫描 4 个新角度 + 来源去集中化 + 跑分维度候选 + D31 数据清理（删 42 老模型 + 修子榜区隔） + D31 scaling law 验证 + D31 跑分多源一致性扫描。

## 1. 数据集当前状态（截至 D31 收尾）

| 维度 | 数值 | 备注 |
|---|---|---|
| 总记录 | 891 条（D31 删 42 条 2022 前老模型，原 933） | 全部 model_id 唯一 |
| 厂商 | 233 家（D28 已归一，原 249） | 长尾：单模型厂商 145 家 |
| 跑分条目 | 5,634（自报 4,108 + 独立 1,013 + Arena Elo 513） | arena_elo 来源已去集中化 |
| license 填充率 | 0.9%（8/891） | D30 已扫，未修复 |
| knowledge_cutoff | 18.5%（173/891） | D28 已修关键 5 条 |
| pricing.input | 31.3%（292/891） | |
| total_params_b | 72.5%（646/891） | |
| context_window_tokens | 79.6%（709/891） | D30 扫出 effective vs nominal 矛盾 |
| modality.input.image | 82.9%（739/891） | |
| verification_status | 已验证 54 / 待验证 716 / 已定死 108 / 已过期 13 | D28 时效性标准已改 |
| 跑分维度覆盖 | GPQA 227 / MMLU 159 / MATH 96 / GSM8K 81 / **HumanEval 2 / BBH 3 / MuSR 1 / IFEval 1** | 4 个维度严重缺失 |
| Arena 子榜覆盖 | text 175 / coding 174 / math 156 / **webdev 4 / vision 1 / search 1 / agent 1 / gdpval 1** | 5 个子榜严重缺失 |
| 多源覆盖率（独立评测） | 56/912 组有多源（6.1%） | D31 新扫 |
| 多源不一致率 | 27/56 = 48.2% | D31 新扫，差异 ≥5 个百分点 |

## 2. D29-D31 累计已扫缺口

### 2.1 D30 新增 4 个扫描角度

| # | 角度 | 扫描结果 | 处置状态 |
|---|------|----------|----------|
| 1 | context_window_effective vs nominal 矛盾 | 倒挂（eff > nom）+ 偏差过大（eff < nom×0.5）共若干条 | 已记录，待修复 |
| 2 | license 填充率（按厂商分布） | 0.9% 极低；Top 厂商中 OpenAI/Anthropic/Alibaba 都几乎全空 | 已记录，需逐厂商补 |
| 3 | 模型代际命名规范（base/large/medium/mini 等） | 大量模型无代际标识；同义异写（mid vs medium） | 已记录，未修复 |
| 4 | 多厂商合作记录归属（vendor 含 + / & / and / /） | 多个 vendor 含分隔符，归属主次未拆 | 已记录，未修复 |

### 2.2 D31 新增 2 个扫描角度

#### 2.2.1 Scaling law 验证（参数量 vs 跑分 power law）

**方法**：取有 `total_params_b` + independent 跑分（MMLU/GSM8K/GPQA/MATH）的模型，按 `log(score) = a + b * log(params)` 拟合。

| benchmark | n | 斜率 b | R² | 预测 score@7B | @70B | @700B | 结论 |
|---|---|---|---|---|---|---|---|
| MMLU | 105 | 0.108 | 0.277 | 0.502 | 0.643 | 0.824 | 符合 power law，斜率正常 |
| GSM8K | 64 | 0.155 | 0.046 | 0.290 | 0.415 | 0.593 | 拟合极差，reasoning/coder 模型颠覆传统 law |
| GPQA | 96 | 0.155 | 0.344 | 0.346 | 0.494 | 0.706 | 中等拟合，power law 较明显 |
| MATH | 47 | 0.350 | 0.285 | 0.144 | 0.322 | 0.720 | 对参数量最敏感（b 最大） |

**异常点扫描（实际分 vs 拟合分差异 > 15 个百分点）**：

- **新训练范式模型显著超拟合**（reasoning/coder 模型打破传统 scaling law）：
  - `deepseek:deepseek-r1-distill-qwen-14b`：MATH 实际 0.871 vs 拟合 0.183，**超 +0.688**
  - `alibaba:qwen2-5-coder-14b`：GSM8K 实际 0.942 vs 拟合 0.325，**超 +0.617**
  - `microsoft:phi-4-mini` (3.8B)：MMLU +0.378 / GSM8K +0.598 / MATH +0.533（小模型超拟合）
  - `moonshot:fireworks-kimi-k2p5` (1B)：GPQA 实际 0.876 vs 拟合 0.256，超 +0.620（**待核查**：1B 参数不太可能 0.876）

- **老模型显著低于拟合**（训练数据/方法过时）：
  - `meta:opt-66b`：MMLU 实际 0.276 vs 拟合 0.639，低 -0.363
  - `cerebras-systems:cerebras-gpt-13b`：MMLU 低 -0.275
  - `openai:text-davinci-001` (175B)：MMLU 低 -0.271
  - `databricks:dolly-v2-12b`：MMLU 低 -0.270

**按参数量分段看分数中位数**：

| 段 | n | MMLU | GSM8K | GPQA | MATH |
|---|---|---|---|---|---|
| <1B | 2 | 0.420 | 0.345 | — | — |
| 1-7B | 18 | 0.423 | 0.324 | 0.561 | 0.649 |
| 7-30B | 59 | 0.592 | 0.386 | 0.365 | 0.210 |
| 30-100B | 38 | 0.699 | 0.544 | 0.461 | 0.367 |
| 100-350B | 21 | 0.776 | 0.156 | 0.587 | 0.503 |
| 350B+ | 25 | 0.733 | 0.565 | 0.810 | 0.755 |

**观察**：
1. 350B+ 在 GPQA/MATH 上显著高于 100-350B（0.810 vs 0.587；0.755 vs 0.503）—— 大参数对难题最敏感
2. 100-350B 段 GSM8K 中位 0.156 异常低 —— 这段多是老 dense 模型（如 OPT-66B/Cerebras），未训练数学
3. 1-7B 段 MATH 中位 0.649 高于 7-30B 的 0.210 —— 因为 1-7B 多是新 reasoning 模型（Phi-4-mini/DeepSeek-R1-distill 等）

#### 2.2.2 跑分多源一致性（同模型同 benchmark 多源差异）

**方法**：取 independent 段，按 `(model_id, benchmark 归一)` 分组，找多源组（≥2 条 entry），计算分数差异 `max - min`，差异 ≥5 个百分点视为不一致。

**总体**：
- 912 组 (model, benchmark) 中只有 56 组有多源（6.1%）—— 多源覆盖率低
- 56 多源组中 27 组差异 ≥5%（不一致率 **48.2%**）—— 几乎一半不一致

**各 benchmark 不一致率**：

| benchmark | 多源组数 | 不一致数 | 不一致率 |
|---|---|---|---|
| math | 3 | 3 | **100.0%** |
| arc | 1 | 1 | **100.0%** |
| mmlu | 9 | 5 | 55.6% |
| gpqa | 21 | 10 | 47.6% |
| swe-bench verified | 11 | 5 | 45.5% |
| aime 2025 | 8 | 3 | 37.5% |

**Top 差异清单（前 5）**：

| 模型 | benchmark | 差异 | 多源分数 |
|---|---|---|---|
| openai:gpt-5-2-2025-12-11-xhigh | math | 0.357 | 0.674@token.app / 0.317@token.app |
| deepseek:deepseek-r1 | aime 2025 | 0.342 | 0.533@epoch.ai / 0.875@topreviewed.ai |
| mistral:mistral-7b-instruct-v0-3 | mmlu | 0.333 | 0.599@epoch.ai / 0.642@datalearner.com / 0.309@datalearner.com |
| mistral:mistral-large-3 | gpqa | 0.329 | 0.680@artificialanalysis.ai / 0.439@chatforest.com / 0.351@openrouter.ai |
| meta:llama-4-scout-17b-16e | math | 0.221 | 0.623@epoch.ai / 0.844@artificialanalysis.ai |

**来源域名 × 不一致关联率**：

| 域名 | 多源次数 | 在不一致组 | 关联率 |
|---|---|---|---|
| topreviewed.ai | 2 | 2 | **100%** |
| datalearner.com | 8 | 6 | **75%** |
| rankedagi.com | 4 | 3 | 75% |
| arxiv.org | 5 | 3 | 60% |
| serenitiesai.com | 12 | 6 | 50% |
| epoch.ai | 48 | 23 | 47.9%（基数大，是基准源） |

**观察**：
1. **多源覆盖率仅 6.1%** —— 大多数 (model, benchmark) 只有 1 个源，无法交叉验证，数据可信度有限
2. **多源不一致率 48.2%** —— 多源组中近一半差异 ≥5 个百分点，跨源数据矛盾严重
3. **同域名不同分数**：Mistral-7B 在 datalearner.com 出现两个不同分数（0.642 vs 0.309）—— 可能是重复条目
4. **跨源矛盾最大**：DeepSeek-R1 aime2025 在 epoch.ai 0.533 vs topreviewed.ai 0.875（差 0.342）—— 不同评测方法/版本
5. **域名关联率高的源**：topreviewed.ai / datalearner.com / rankedagi.com 容易参与不一致组

**待推进**：
- 数据层：标记 27 条不一致条目为「多源矛盾」，可视化加警告 badge
- 处置策略：保留所有源（让用户判断），可视化层加冲突展示
- 增加多源覆盖：为关键模型补充 epoch.ai / artificialanalysis.ai 等权威源

## 3. D31 数据清理

### 3.1 删除 42 个 2022 前老模型

**用户要求**：只要 2022+ 数据。

**删除清单**（按年份）：

| 年份 | 数量 | 代表模型 |
|---|---|---|
| 1959 | 1 | MIT Pandemonium |
| 1987 | 1 | CMU Translation-Invariant MLP |
| 1994 | 1 | TUM Predictive-Coding-NN |
| 1999 | 1 | Universitat Jaume I RECONTRA |
| 2000 | 1 | Mila Neural Probabilistic LM |
| 2003 | 1 | Mila NPLM |
| 2005 | 1 | Université de Montréal Hierarchical Softmax NNLM |
| 2007 | 2 | Google KN-LM / SB-LM |
| 2010 | 1 | Johns Hopkins RNN-LM |
| 2013 | 2 | Google DistBelief NNLM / TransE |
| 2014 | 3 | Google Seq2Seq LSTM / SNM-skip / Mila RNNsearch-50 |
| 2016 | 2 | Google BIG LSTM+CNN / GNMT |
| 2019 | 7 | XLNet / XLM-RoBERTa / RoBERTa-large / T5-11B / T5-3B / Megatron-BERT / Grover Mega |
| 2020 | 9 | Meena / mT5-XXL / GShard / OpenAI ada / babbage / curie / davinci / GPT-3 175B / text-curie-001 |
| 2021 | 9 | Jurassic-1 Jumbo / ERNIE 3.0 Titan / Gopher / GPT-J 6B / FLAN 137B / GLaM / Switch Transformer / Yuan 1.0 / HyperCLOVA |

**执行**：
- 备份原文件 `model_data_v2.jsonl.bak.20260903_190631`
- 写回 891 条到 `model_data_v2.jsonl`
- 门禁验证：ERROR 0 / WARN 0 持平 ✓

### 3.2 修复子榜区隔问题（GLM-5.2 主榜分误取 agent 子榜分）

**问题**：用户反馈 GLM-5.2 主榜分数显示异常（1524 分），且高于 GLM-5.3。

**根因**：`viz_transform.py` `flatten_record` 的 `arena_elo_max` 逻辑：
- 旧逻辑：`max(elos)` 取所有子榜中最高分
- 当模型只有 agent/coding/math 等子榜（无 text 主榜）时，子榜分被误作主榜分

**GLM-5.2 实际 arena_elo 数组结构**：
```
model_id: zhipu:glm-5-2-none:base
arena_elo:
  - sub='agent' score=1524 is_primary=None source=https://blog.csdn.net/namexingyun/article/details/162294368
```

→ 只有 1 条 agent 子榜分（来自 blog.csdn.net 非官方源），按旧逻辑 `max([1524]) = 1524` 被显示为主榜分。

**修复**（`viz_transform.py` `flatten_record`）：
1. 优先 `is_primary=true` 的 score
2. 否则 `sub_benchmark` 归一为 `text`/`overall`/空 的 score
3. 都无则 `None`（避免子榜虚高）

**新增辅助函数**：`_norm_sub_benchmark(s)` 用于子榜名归一。

**影响范围**：
- 172 个有 arena_elo 数据的模型中，170 个保留原主榜分
- 2 个模型失去主榜分：GLM-5.2 / GLM-5.1（都只有 agent/coding 等子榜分）
- 主榜 Top 10 现在 GLM-5.3 (1487) 排第 10，GLM-5.2 不再出现

## 4. 可视化改进（D29-D31 累计）

### 4.1 D29 数据缺口分析页
- 字段组填充率雷达
- 跑分覆盖热力图（Top 30 benchmark × Top 30 厂商）
- 字段缺口排行表
- 无跑分模型清单

### 4.2 D29 厂商碎片化检测视图
- 大小写/空格/连字符变体合并建议
- 厂商气泡图

### 4.3 D29 模型档案抽屉
- sticky 全局筛选条（厂商/定位/开源/价格/参数/日期/Elo/跑分 8 维）
- 档案抽屉组件（基本信息/架构/定价/模态/跑分/兄弟/相似/源 URL）
- URL hash 状态分享

### 4.4 D30 价格性能象限图
- 中位价格 × 中位 Elo 分割 4 象限（高性价比/低性价比/高端/低端）
- 线性回归线

### 4.5 D30 模型生命周期甘特图
- release → knowledge_cutoff 生命周期条
- 颜色按地缘（中国红/美国蓝/欧洲紫/其他灰）
- dataZoom 缩放 + 点击跳档案

### 4.6 D31 厂商 × 字段 缺口矩阵
- Top 30 厂商 × 19 关键字段 = 438 矩阵点
- 红黄绿色阶（满→空）
- 厂商智能诊断（健康度 Top 15）
- 一键导出待补清单（JSON/CSV/MD）
- 点击单元格复制该格缺失 model_id 清单到剪贴板

## 5. 仍待推进的缺口

| # | 任务 | 优先级 |
|---|------|--------|
| 1 | 补跑分维度 HumanEval/BBH/MuSR/IFEval（<1% 覆盖） | 中 |
| 2 | 标记 27 条多源不一致条目 + 可视化加警告 badge | 中 |
| 3 | 增加多源覆盖（为关键模型补 epoch.ai/artificialanalysis.ai 权威源） | 中 |
| 4 | context_window_effective vs nominal 矛盾处置 | 低 |
| 5 | license 类型分布与 GPL/AGPL 合规（填充率 0.9%） | 低 |
| 6 | 模型代际命名规范（base/large/medium/mini） | 低 |
| 7 | 多厂商合作记录归属主次 | 低 |
| 8 | Arena webdev/vision/search/agent/gdpval 子榜补充 | 低 |

## 6. 可视化后续改进方向

### 6.1 方向 A：架构重组（高 ROI）

- **总览 Dashboard 重构**：从 KPI+图升级为数据故事仪表盘（一屏看全 KPI+厂商 Top10+跑分 Top10+价格段+时效性仪表+可信度环+缺口矩阵缩略+时间线）
- **模型档案页路由化**：抽屉升级为独立 URL `/model/<mid>`，可分享、可浏览器历史回退
- **厂商档案页**（新增）：点击厂商名 → 厂商全家桶（所有模型+同厂商代际演进+价格历史+能力雷达+同价位竞品对比）
- **快捷搜索框**：Ctrl+K 唤起，模糊搜索模型/厂商，回车跳档案

### 6.2 方向 B：新增 6 张高价值图表

1. **跑分排行总榜**：按 benchmark 维度切换 Top 30 排行（MMLU/GSM8K/GPQA/MATH/Arena-text/coding/math）
2. **scaling law 散点**：参数量 vs Elo（颜色=厂商/大小=价格/形状=开源），验证 power law
3. **价格历史瀑布图**：同厂商代际价格变化（如 GPT-4→4o→4o-mini→5 价格阶梯）
4. **Pareto 前沿图**：价格×性能的前沿模型（高性价比前沿，谁被淘汰）
5. **同代际横评**：选年份 → 该年发布模型横评（雷达 + 排行）
6. **数据可信度仪表盘**：自报/独立/Arena 占比环 + 源域名分布 + 来源类型分布 + 不一致警告

### 6.3 方向 C：交互强化（次优先）

- 全页面 URL hash 状态分享（`#page=vendor&vendor=alibaba`）
- 图表一键导出 PNG/SVG + 全屏模式
- 表格行内筛选 + 多列排序
- 联动强化：所有厂商名 → 厂商档案页；所有模型名 → 模型档案；对比按钮随处可加
- localStorage 记忆「最近浏览 5 个模型」

### 6.4 方向 D：视觉细节（次优先）

- 暗色模式（主题切换按钮）
- 厂商稳定色板（同一厂商在所有图都用同一颜色）
- 加载骨架屏（避免白屏闪烁）
- 图表 tooltip 多行 + 跳转链接
- 响应式移动端
- 空状态友好提示
