# D43 轮次报告：D42 四项遗留拍板落地 + 台账漂移一次归位

> 日期：2026-09-11。用户拍板（四项全选推荐项）：s1 家族=版本+参数式；olmo/luxia 都改；minicpm 按官方名对齐；zhipu 别名统一为 `zhipu`。
> 门禁 **ERROR 0 / WARN 0**；记录数 **937 → 935**（合并 2 条重复档案）；台账 models 改写 **186 处**。

## 一、四项拍板落改

| # | 拍板 | 落改 | 证据 |
|---|---|---|---|
| 1 | s1 家族 → **版本+参数式** | `s1-1` → `allen-institute-for-ai:s1.1-1.5b:base`；`s1-32b` → `s1.1-32b`；`s1` 保持 | full_name `s1.1-1.5B` / `s1.1-32B`，与全库「family 编码版本+参数」惯例一致，三条互不冲突 |
| 2 | olmo/luxia **都改** | `olmo-3-32b-instruct` → `olmo-3.1-32b-instruct`；`luxia-21-4b-alignment` → `luxia-2.1-4b-alignment` | 前者 version 字段明写 `3.1`（HF `allenai/Olmo-3.1-32B-Instruct`）；后者 full_name 明写 `Luxia 2.1`（21 是数字串内缺小数点，D42 连字符规则管不到的「缺位」类） |
| 3 | minicpm **按官方名对齐** | `minicpm-1-2b` → `minicpm-1b`；`minicpm-2-4b` → `minicpm-2b` | 官方 HF 名即 MiniCPM-1B/2B；精确参数量**本来就在** `architecture.total_params_b`（1.2B / 2.7B，注记含非嵌入 2.4B），改名注记中指回，无新造数据 |
| 4 | vendor 别名 → **统一 zhipu** | 长前缀 `z-ai-zhipu-ai-tsinghua-university` 3 条改挂 `zhipu:`；其中 `glm-4.5`/`glm-4.6` 与 zhipu 侧档案**合并**（见 §二） | 主键 vendor 段归并后 family 重名消除 |

## 二、glm-4.5 / glm-4.6 重复档案合并

两侧是**各自独立采集**的档案（非复制），深度 diff 后以 **zhipu 侧为主档**（benchmark 条目带 config/date，完整度更高）：

- **glm-4.5**：两侧 14 条 self_reported **同名同分**全部对上（同一官方来源），0 并入 0 冲突；补值 2 处（`pricing.effective_date`、`pricing.unit`，仅长前缀侧有值）；source_urls 并集（长前缀侧多 2 条 epoch.ai 来源）。
- **glm-4.6**：长前缀侧独有 2 条并入（CC-Bench 对 Sonnet 4 胜率 0.486、Token 效率相对指标），主档 8 条 OCR 基准保留，合并后 self_reported 10 条；补值 2 处；冲突 0。
- 标量冲突（license、modality 细节等两侧表述不同处）**一律保留主档值**，差异点写入 `meta.notes` 留痕；并入的 benchmark 条目 notes 均标注 `【D43 合并】`。

## 三、台账 models 数组一次归位（本轮最大收益）

排查 `b60w1` 前缀漂移时发现漂移是**系统性的**：多平台 agent 按批次原始 vendor 串登记，主库则经 D41 归并（ant-group→alibaba、allen-institute-for-ai→allenai、mosaicml→databricks 等）。台账 758 个 model 槽位中：

| 归位方式 | 条数 | 例 |
|---|---|---|
| 已在主库（含 D42 改写后命中） | 506 | — |
| A. family+variant 唯一命中（vendor 漂移） | 131 | `ant-group:ling-1t:base` → `alibaba:ling-1t:base` |
| B. family 经 D42/D43 映射后唯一命中（连缀漂移） | 53 | `lg-ai-research:exaone-3-5-2-4b:base` → `lg:exaone-3.5-2.4b:base` |
| C. 同 vendor 下 family 唯一（variant 漂移） | 2 | `anthropic:claude-3-haiku:20240307` → `anthropic:claude-3-haiku:base` |
| 未归位（保留原登记） | 66 | 见 §四 |

- **改写 186 处、覆盖 86 个批次**；每条映射均要求**唯一命中**（0 歧义才落笔）。
- `status` / `submitted_files` / 批次 `vendor` 字段**逐字段核验零改动**（对照 `backups/batch_claim_ledger.pre-d43-20260911-222110.jsonl`）。
- 66 条未归位 = **真实历史**：远古批未合并（b9/b10 的 openai ada/davinci、google t5/gnmt/switch 等）、被拒候选（`cohere:parse-v5-0`）、以及**库内真实缺口**（见 §四）。台账记「采集过什么」、主库记「收了什么」，本就不必相等。

## 四、台账暴露的库内真实缺口（下一轮候选，非本轮范围）

- `google:gemma-4-31b:base`（库内只有 `-it` / `-it-minimal`，基座缺）
- `lg-ai-research:exaone-3-5-r-2-4b:base`（R 系列 2.4B 缺，32b/7.8b 在库）
- `google:gemini-3-6-flash-cyber:base`（3.5 有 cyber、3.6 缺）
- `meituan-inc:longcat-flash:base`（库内只有 `:20250831`/`:20250901` 日期 variant，且二选一歧义）
- `t-bank:t-pro:base`（库内只有 `t-pro-2.0`，是否同模型需查证）
- `tsinghua-university:jetfire:base`、`allen-institute-for-ai:codescientist`、`naver:hyperclova-204b`、`inspur:yuan-1-0` 等

## 五、核验

- 门禁 `validate_model_data.py`：935 条，**ERROR 0 / WARN 0**。
- 主库：model_id 唯一；9 个旧 id 0 残留；`z-ai-zhipu` 前缀 0 残留；glm-4.6 合并后 self_reported 10 条含 CC-Bench+AIME25。
- 台账：行数一致；非 models 字段零改动；models 改写 186；未归位保留 66/758。
- D42 §6 遗留四类（s1/luxia/olmo/minicpm）全部落改，`CHANGELOG.md` 顶部 D42 待拍板行结清。

## 六、产物

| 类型 | 文件 |
|---|---|
| 脚本 | `scripts/d43_struct_fix.py`（改名+合并）、`scripts/d43_ledger_sync.py`（台账归位，解析链 A/B/C） |
| 留痕 | 7 条改名记录与 2 条合并主档的 `meta.notes`（`【D43 结构改名】`/`【D43 合并】`） |
| 备份 | `backups/model_data_v2.pre-d43-struct-20260911-222109.jsonl`、`backups/batch_claim_ledger.pre-d43-20260911-222110.jsonl` |
| 日志 | `CHANGELOG.md` [D43] |
