# v2 数据补全与任务分配方案

> 制定日期：2026-08-25 ｜ 依据：927 条实测缺口矩阵（见附录）
> 原则：**准确 > 速度**。宁可字段空着标"待采"，不许编造。

---

## 0. 当前状态（本轮已完成的程序化补全）

- ✅ **ERROR 0 / WARN 0**（历史首次全绿；从 184 ERROR → 0）
- 删除 6 条不可溯源的 independent 跑分（wiki.hugogu / aiwiki 无 URL，T3 且无法核实 = 垃圾，删）
- 77 条有标称上下文的记录补「标称值，有效上下文待测」诚实标注
- 22 条自报跑分的 source_type 补「(自报)」属性
- 全库过 normalize_record 确认骨架完整（0 条需修）

## 1. 缺口现实（不回避）

| 字段 | 已填 | 填充率 | 结论 |
|------|------|-------:|------|
| pricing.input/output | 51 | 5% | 几乎全空 |
| modality 多模态 | 44 | 5% | 几乎全空 |
| positioning | 3 | 0.3% | 实质为空 |
| context_window | 77+ | 8% | 大部分空 |
| self_reported 跑分 | 12 | 1% | 几乎全空 |
| arena_elo | 170 | 18% | 有底子，需统一快照 |
| independent 跑分 | 302 | 33% | 最大存量，但来源混杂 |

**873/927（94%）是四项内容全空的壳。** 补全的主体只能是重新采集，程序补不了。

## 2. 核心决策：先分层，再分配

不是所有模型都该采同样的字段。按「获取方式」把 927 条分成两层：

### A 层：API 模型（483 条）→ 需要定价
闭源/商用 API 模型。必采：**定价全套、多模态、positioning、context window、自报跑分、官方文档 URL**。
（openai 68 / google 49 / anthropic 44 / alibaba 26 / mistral 26 / xai 17 / meta 12 …）

### B 层：开放权重模型（444 条）→ 不需要定价，需要 HF/GitHub
开源模型没有 API 定价这回事（硬填就是编数据）。必采改为：**HuggingFace 链接、license、参数量确认、模态、positioning、上下文长度**。
（360zhinao、smaug、各大学联合体模型等）

> `unknown` 厂商 24 条在 A 层——这些 model_id 本身可疑，先做归属鉴定再采集。

## 3. 任务分配：谁独立抓，谁聚合抓

```
                    ┌─ 独立深采（一模型一 subagent）──┐
                    │  A层 483 条：官方定价页/模型卡   │
                    │  B层 444 条：HF 页/官方 repo    │
                    └───────────────┬────────────────┘
                                    │ 合并
                    ┌─ 聚合快照（中心化 agent）────────┐
                    │  Arena ELO ← lmarena.ai 一次抓   │
                    │  独立跑分 ← Artificial Analysis  │
                    │  （同一天同一快照，保证可比性）    │
                    └─────────────────────────────────┘
```

### 3.1 独立抓（一模型一 subagent）——占工作量 ~85%

每条记录一个 subagent，只服务这一个模型。产出走 `incoming/models/<vendor>__<model>__base.jsonl`（文件名冒号换 `__`），用修复后的 merge 工具合并。

**批次划分（A 层，按厂商聚类=同一定价页，效率高且一致）：**

| 批次 | 厂商 | 数量 | 数据源入口 |
|-----|------|-----:|-----------|
| A1 | openai | 68 | platform.openai.com/docs/pricing + 模型页 |
| A2 | google | 49 | ai.google.dev/gemini-api/docs/pricing |
| A3 | anthropic | 44 | docs.anthropic.com pricing |
| A4 | alibaba(阿里系 API) | 26 | 阿里云百炼定价页 |
| A5 | mistral | 26 | mistral.ai/pricing |
| A6 | xai + meta(API) | 29 | docs.x.ai / llama.com |
| A7 | deepseek+microsoft+ant+bytedance+moonshot+zhipu | 38 | 各家官网定价页 |
| A8 | 其余小厂商 API（amazon/cohere/perplexity 等） | ~205 | 各家官网 |

**批次划分（B 层，按 HF 组织聚类）：**

| 批次 | 内容 | 数量 | 数据源入口 |
|-----|------|-----:|-----------|
| B1 | 国内大厂开源（Qwen/Llama 中文生态/DeepSeek 开源版/GLM…） | ~120 | HF org 页 |
| B2 | Llama/Mistral/Gemma 西方开源 | ~90 | HF org 页 |
| B3 | 研究机构/社区模型（AI2/BAAI/各大学） | ~234 | HF 搜索逐个定位 |

**单模型 agent 提示词模板：`agent_prompt_per_model.md`（已有，直接派发）。**

### 3.2 聚合抓（中心化平台 agent）——占工作量 ~15%，但必须集中做

| 任务 | 来源 | 为什么聚合 |
|------|------|-----------|
| Arena ELO（170 条已有 + 缺口） | lmarena.ai leaderboard | 同一天一次抓 → 所有分数同一快照日期，跨模型可比；分散抓会日期漂移 |
| 独立跑分基准线 | artificialanalysis.ai | 同上；且避免 N 个 agent 打同一站点触发限流 |
| vendor 归属鉴定（unknown 24 条 + 大学超长名归一） | HF API / 官网 | 一次性清洗任务，产出厂商别名映射表 |

**执行要求：** 聚合抓取必须在一天内完成全部模型的该类数据（快照一致性）；结果以补丁形式合并，`date` 字段统一写快照日。

## 4. 执行顺序（准确优先）

1. **第 0 步（半天）**：vendor 清洗 —— unknown 归属鉴定 + 别名表（alibaba vs qwen、google-deepmind-google vs google 等）
2. **第 1 步（聚合先行）**：Arena ELO 快照 + Artificial Analysis 快照（1 天内完成）
3. **第 2 步**：A1–A3 三大批（openai/google/anthropic，161 条，覆盖最常用模型）
4. **第 3 步**：B1+B2 主流开源（210 条）
5. **第 4 步**：A4–A8 剩余 API + B3 长尾研究模型
6. **每批验收标准**：该批记录合并后校验 ERROR 0；抽样 10% 人工核对定价数字；positioning/modality/pricing 三块填充率 ≥95%（真无此项的显式 null+notes 说明，不算缺）

## 5. 验收红线（防再退化）

- 新增/更新记录必须过修复后的 merge 工具（骨架自动完整）
- 任何数值字段必须有 source_url + source_type + confidence
- verification_status 只允许：待验证/已验证（verified_at 必须非空才可"已验证"）
- 每批合并前重跑 `validate_model_data.py`，ERROR>0 即退回

## 附录：本轮程序化补全明细

- 备份链：`model_data_v2.jsonl.preclean.bak` → `.fix2.bak` → 当前
- 删除的 6 条不可溯源跑分：qwq-32b ×4（wiki.hugogu）、grok-4:0709 ×2（aiwiki）
- WARN 清零路径：77 上下文标注 + 22 自报标注 + 2 定价日期格式
