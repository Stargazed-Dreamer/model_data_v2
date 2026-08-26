# 大模型静态数据集 · 多 Agent 协作与合并方案（v1）

> 配套文件：`prompt.md`（采集规范）、`执行细则.md`（十项执行细则）、`model_data_tool.py`（读写/合并工具）、`build_model_data.py`（v1 生成脚本）
> 当前基线：`model_data_v1_clean.jsonl`（924 条，已清洗）
> 文档定位：多 agent 任务拆分、分工、输入输出契约、合并策略与质检标准的唯一真源。任何采集/合并动作以本文档为准。

## 进度总览（更新于 2026-08-24）

| 阶段 | 状态 | 产物 |
|------|------|------|
| 阶段 0 · 地基 | ✅ 完成 | `model_data_v1_clean.jsonl`、`roster.jsonl`/`roster.md`、`validate_model_data.py` + `validation_v1_baseline.md`、`clean_v1.py`/`gen_roster.py` |
| TEST_REPORT 问题处置 | ✅ 完成 | P1/P2/P3/P4/P5 已修（详见 `TEST_REPORT.md` 第六节），P6 设计内承接 |
| 阶段 1 · 并行采集 | ⬜ 待启动 | 以花名册分组表（第 3.1 节）分片 |
| 阶段 2 · 合并 | ⬜ 待启动 | — |
| 阶段 3 · 质检 | ⬜ 待启动 | — |

---

## 0. 现状诊断（决定拆法的三个事实）

对 `model_data_v1.jsonl` 的逐维度填充率统计（924 条）：

| 维度 | 填充情况 | 结论 |
|---|---|---|
| 基础身份 / 参数量 | 基本齐全（源：Epoch AI） | 无需重采，仅需校验 |
| 独立跑分 `independent` | 297/924（32%，均 Epoch 聚合，T1） | 部分有，需补强 |
| 上下文窗口 `context_window_tokens` | 21/924（2%） | 大面积缺失 |
| 自报跑分 `self_reported` | 0 | 全空，需联网采集 |
| Arena Elo `arena_elo` | 0 | 全空，需联网采集 |
| 定价 `pricing.input` 等 | 0 | 全空，需联网采集 |
| 多模态 `modality` | 0 | 全空，需联网采集 |

**三个关键判断：**

1. **v1 只完成「身份+参数」骨架。** 定价、多模态、自报跑分、Arena 四块整体空白，且都依赖联网采集——这是多 agent 并行的主战场。
2. **范围未对齐。** 924 条混入大量社区微调 / 论文模型（SEA-LION、Smaug、360Zhinao、mGTE 等），而 `prompt.md` 的范围是 **28 家厂商的旗舰 + 主线模型**。不先裁剪，采集会在范围外模型上大量空耗。
3. **v1 存在数据 bug，须在合并前修复**，否则会污染后续合并：
   - 部分 `meta.source_urls` 数组元素内嵌换行符（多条 URL 粘进同一字符串）；
   - 45 条 `vendor` 字段经 slug 化后为 `unknown`；
   - 个别厂商 slug 映射异常（如学术机构被当作厂商）。

---

## 1. 总体架构：四阶段

```
阶段0 地基(串行)  →  阶段1 并行采集(8 agent)  →  阶段2 合并(串行,主agent独占)  →  阶段3 质检与验收
```

- **串行环节**（阶段 0、2、3）只由**主 agent** 操作，保证花名册唯一、主库无写冲突。
- **并行环节**（阶段 1）的 8 个采集 agent 各自只写自己的 `incoming/` 分片文件，**绝不直接写主库**。
- 合并统一走 `model_data_tool.py`，默认 dry-run，显式声明全部合并策略。

---

## 2. 阶段 0 · 地基（串行，✅ 已完成 2026-08-24）

**目标**：产出「花名册 + 校验脚本 + 修复后的 v1」，作为并行采集不打架的锚点。

### 2.1 修复 v1 数据 bug（✅ 完成）
脚本：`clean_v1.py`。修复项：
- 清洗 `meta.source_urls`：内嵌换行拆分为独立 URL 并去重（65 条受影响）；
- 归一 `vendor`：`unknown` 前缀按模型官方出处修正（16 条，如 PaLM→google、Qwen→alibaba、盘古→huawei）；
- 产出 `model_data_v1_clean.jsonl`（保留原文件不覆盖），清洗日志 `clean_v1_log.md`。

### 2.2 生成花名册（✅ 完成）
脚本：`gen_roster.py`。对 28 家厂商逐一过范围，产出 `roster.jsonl`（机器可读）与 `roster.md`（人读）。

**判定结果**：目标厂商记录 480 条 → `in_v1` **333** / `to_add` **26** / `out_of_scope` **147**。

三态定义与处置：

| 状态 | 含义 | 后续动作 |
|---|---|---|
| `in_v1` | v1 已有，且属于旗舰/主线 | 沿用原 `model_id`，只补缺失维度 |
| `to_add` | 范围内但 v1 缺失 | 用花名册分配的新 `model_id`，全量采集 |
| `out_of_scope` | 研究项目 / 配置变体 / 蒸馏 / 量化 / 早于 2023-03 | 不采集，保留在 clean 库中，采集阶段跳过 |

**「主线」判定标准（已采纳）**——满足其一即可：
1. 厂商官方主推过（官网/定价页/发布会列为旗舰或主力）；
2. 有独立官方定价页或正式技术报告 / Model Card；
3. 属于厂商公开的产品线主干迭代（含已退役 / 已下线的历史旗舰与主力，按决策 5 全量保留）。

**去重逻辑**（`gen_roster.py` 词干分组）：同一模型的配置变体（`_high/_none/_max` 等）、上下文变体（`-16k/-32k`）、快照日期变体（`-2024-05-13`）归为同一词干组，组内只保留一条代表记录（优先锚点记录 → `:base` → 独立跑分最多 → 发布最近），其余标 `config_dup`。`mistral-small`/`mistral-medium`/`claude-3-5-sonnet` 因日期后缀代表真实版本发布而豁免合并。

### 2.3 编写校验脚本（✅ 完成）
脚本：`validate_model_data.py`。把执行细则第 11 节自查机械化，ERROR/WARN 分级，退出码可作门禁（0=无 ERROR，1=有 ERROR，2=读取失败）。

**基线结果**：`model_data_v1_clean.jsonl` 924 条 → **0 ERROR / 0 WARN**（见 `validation_v1_baseline.md`）。负向测试（故意违规记录）命中 23 ERROR，确认检测有效。

检查项：

- [x] 顶层必备键齐全（`schema_version` / `model_id` / `basic_info` / `architecture` / `benchmarks` / `pricing` / `modality` / `meta`）
- [x] 参数量未披露 → `total_params_b`/`active_params_b` 为 `null` 且 `notes` 含「官方未披露」
- [x] 上下文：标称填 `context_window_tokens`；有效未测为 `null` + notes「标称值，有效上下文待测」
- [x] 多模态布尔：`false`=官方明确不支持，`null`=未提及/模糊，严禁用 `false` 代「没查到」
- [x] 定价四必采字段（`cached_input`/`cache_write`/`batch_input`/`batch_output`）必须出现，即使全 `null`
- [x] `positioning` 必须是数组，且标签在枚举内（旗舰/中端/轻量/推理增强/多模态/工具调用增强）
- [x] `confidence` 与 `source_type` 自洽（转述来源不得配 `T0`/`T0-自报`）
- [x] 跑分 `score` 为 0–1 小数（百分制须转小数 + notes）
- [x] 日期符合 ISO 8601；`pricing.currency` 为 `USD`
- [x] `meta.source_urls` 无内嵌换行符

---

## 3. 阶段 1 · 并行采集（8 个 agent）

**分组原则**：按厂商分组，避免两个 agent 同时写同一 `model_id`。平台类数据（Arena、跨厂商独立评测）因数据源天然跨厂商，单列为平台 agent，避免按厂商拆导致重复爬同一站点。

### 3.1 厂商采集 agent（6 组）

分片以花名册分组表为准（格式：in_v1 数 / to_add 数）：

| 组 | 厂商 | 工作量 |
|---|---|---|
| G1 | openai（33/1）、anthropic（21/1） | 56 条，先跑做样板 |
| G2 | google（33/3）、meta（22/1）、xai（14/2） | 75 条 |
| G3 | mistral（36/1）、cohere（2/2）、inflection（3/1）、aleph-alpha（1/0）、microsoft（15/1）、nvidia（20/0）、databricks（1/0）、cognition（3/0） | 84 条 |
| G4 | alibaba（67/1）、deepseek（18/0）、bytedance（4/0） | 90 条，最重 |
| G5 | baidu（4/2）、zhipu（7/3）、moonshot（9/1）、tencent（3/2）、iflytek（1/1） | 32 条 |
| G6 | baichuan（5/0）、huawei（3/0）、meituan（0/1）、xiaomi（1/1）、zero-one（7/0）、modelbest（0/1）、aispeech（0/0） | 18 条 |

**每个厂商 agent 的输入**：
1. `prompt.md` + `执行细则.md`（采集规范）
2. 花名册中本组分片（`roster.jsonl` 按 vendor 过滤，含 `in_v1` / `to_add` 清单与每个模型的 `model_id`）
3. 本组模型在 v1 的现状切片（从 `model_data_v1_clean.jsonl` 提取，已有字段 + 待补字段）
4. `sample_openai_deepseek.jsonl`（输出格式样例）

**每个厂商 agent 的输出契约**：
- 文件：`incoming/agent_<组号>.jsonl`（如 `incoming/agent_g1.jsonl`），UTF-8 无 BOM，每行单条压缩 JSON
- 对 `in_v1` 模型：**已有字段原样保留，只填原本为 `null` 的字段**（保证合并时 `on_both` 不刷屏）
- 对 `to_add` 模型：按 `prompt.md` schema 1.1 全量填写
- 五大维度空缺补齐优先级：**定价 > 多模态 > 自报跑分 > 上下文窗口 > Arena**（Arena 由平台 agent 负责，厂商 agent 可跳过）
- `meta.notes` 若为降级采集，须声明「官方域沙盒不可访问，数据经媒体转述间接核实」（执行细则第 6 条）
- 严守：不伪造 `T0`、空字段填 `null`、发现冲突标注不自行取舍

### 3.2 平台采集 agent（2 组）

| 组 | 职责 | 数据源 | 写入字段 |
|---|---|---|---|
| P1 Arena | 采集 LMArena 各子榜快照 | lmarena.ai | `benchmarks.arena_elo` |
| P2 独立跑分 | 采集跨厂商独立评测分 | OpenCompass、Artificial Analysis | `benchmarks.independent` |

- 平台 agent 产出同样写 `incoming/agent_p1.jsonl` / `incoming/agent_p2.jsonl`
- 平台数据与 v1 已有的 Epoch 聚合记录**按主键合并、不覆盖**（见阶段 2 数组主键）
- 同一 benchmark 多平台记录**全部保留，不取平均**（执行细则第 5 条）

---

## 4. 阶段 2 · 合并（串行，主 agent 独占）

### 4.1 无写冲突架构
- 所有采集 agent 只写自己的 `incoming/*.jsonl`，**谁也不直接动主库**。
- 合并由主 agent 逐个来源执行 `model_data_tool.py merge`，每次先 `dry-run` 看计划，审完再 `--apply`（自动备份 `.bak`）。

### 4.2 推荐合并策略（固定参数，所有来源一致）

```
model_data_tool.py merge \
  --file model_data_v2.jsonl \
  --incoming incoming/agent_g1.jsonl \
  --on-null take_source \
  --on-both conflict \
  --on-array union_by_key \
  --array-key benchmark config date \
  --array-key-override benchmarks.arena_elo:sub_benchmark,date \
  --on-schema upgrade
```

| 维度 | 策略 | 理由 |
|---|---|---|
| `on_null` | `take_source` | 目标为空 → 用来源填充，这是补缺主语义 |
| `on_both` | `conflict` | 双写不一致一律报冲突留人工。配合「保留+补缺」契约，报出来的都是真分歧，不会刷屏 |
| `on_array` | `union_by_key` | 跑分数组按主键合并，异键追加、同键递归 |
| 数组主键（默认） | `benchmark` + `config` + `date` | 独立/自报跑分的唯一性标识 |
| 数组主键（Arena 覆盖） | `sub_benchmark` + `date` | Arena 按子榜 + 快照日期去重 |
| `on_schema` | `upgrade` | 以较高 schema 版本为准并规范化结构 |

**平局裁决（tie_breaker，P2 修复）**：合并工具新增 `--tie-breaker` 参数。`on_both=newer_wins` 且 recency 相等/缺失（天级 `collected_at` 无法区分同日两次采集）时**必填**，可选 `keep_target` / `source_wins` / `conflict`，禁止静默保旧。本管线主策略固定 `on_both=conflict`（双写不一致一律留人工），故标准合并命令无需 `--tie-breaker`；仅当某来源改用 `newer_wins` 时才须显式声明，例如：

```
model_data_tool.py merge ... --on-both newer_wins --recency meta.collected_at --tie-breaker source_wins
```

### 4.3 合并顺序建议
1. 先合并平台 agent（P1/P2）——纯数组追加，风险最低，验证合并链路；
2. 再合并信息最全的 G1（OpenAI/Anthropic）做样板，人工复核计划质量；
3. 确认无误后批量合并 G2–G6；
4. 每次 `--apply` 前检查 `.bak` 已生成。

---

## 5. 阶段 3 · 质检与验收

1. **跑校验脚本**：`validate_model_data.py` 全量检查 `model_data_v2.jsonl`，输出不合规清单。
2. **填充率对比报告**：v2 vs v1 逐维度填充率对比，确认定价/多模态/自报跑分/Arena 已从 0 提升。
3. **冲突裁决清单**：汇总所有 `on_both=conflict` 产生的冲突，按 `prompt.md` 5.4 可信度规则（官方 > 独立评测 > 媒体）逐条裁决。
4. **已知风险声明**（对照执行细则附录 A，须在分析端显著声明）：
   - 官方域不可访问属环境限制，大量记录可信度低于严格 T0/T1；
   - 社区异常信号（如某模型特定榜单骤降）不入规范基准，仅 `notes` 保留风险提示；
   - 定价频繁变动，`pricing.effective_date` 须精确到日，采集 30 天后需复核。

---

## 6. 协作不破的三个关键点

1. **model_id 预先协调**：花名册是唯一 ID 分配依据。`in_v1` 模型必须沿用 v1 的 `model_id`，`to_add` 模型按三段式命名（`厂商:模型:版本`）。这是避免合并时产生重复记录的根本。
2. **「保留 + 补缺」而非重写**：给每个采集 agent 附上其负责模型的 v1 现状，要求已有字段原样保留、只填 `null`。这样 `on_both=conflict` 不会因无意义覆盖而刷屏。
3. **无写冲突架构**：采集 agent 只写自己的 `incoming` 分片；合并工具默认 dry-run + 强制显式策略 + 自动备份，主库安全。

---

## 7. 拍板记录（决策结论，更新于 2026-08-24）

### 7.1 规划待拍板项（用户已按默认拍板）
原始提示词第 1 条：「拍板决策全按默认走」。

| # | 事项 | 拍板结论（默认） |
|---|---|---|
| 1 | 「主线」判定尺度（第 2.2 节三条标准是否采纳） | ✅ 采纳三条标准 |
| 2 | 范围外模型处置：归档隔离 vs 直接删除 | ✅ 归档隔离（`archive/` 目录），不删除 |
| 3 | Arena 历史快照：多日期 vs 仅最新一期 | ✅ 先采最新一期，历史按需补 |
| 4 | 定价非 USD 的汇率口径（执行细则第 10 条） | ✅ 按 `collected_at` 当日汇率，入 notes |

### 7.2 TEST_REPORT 问题处置结论（P1–P7）
抓取测试 + `TEST_REPORT.md` 复盘结论，详见 `TEST_REPORT.md` 第六节。P1–P5 已修（代码/文档已落地），P6 设计内承接，P7 无需动作；无需要 agent 自行拍板的问题。

| # | 问题 | 严重度 | 拍板结论 | 处置方式 |
|---|---|---|---|---|
| P1 | model_id 命名冲突 | 高 | 用户拍板 | 花名册（roster）成为 model_id 唯一权威；存量记录沿用 v1 ID，新模型才按三段式命名规则生成 → 从流程上根除「采集 ID ≠ 库内 ID」 |
| P2 | newer_wins 同日平局 | 高 | 用户拍板 | 合并工具新增显式 `--tie-breaker`（平局策略必填，符合「无隐藏默认」哲学）；本管线主策略固定 `on_both=conflict`，双保险 |
| P3 | 官方域判定粒度 | 中 | 用户拍板 | 决策 1 细化为「按实际使用的 `source_url` 逐条判定」：官方子域可达且同源 → 仍算 T0（已落 `prompt.md` 决策 1 + 5.4） |
| P4 | 汇率来源 | 中 | 用户拍板 | 执行细则补充「汇率必须有可查来源，禁止假设值」（已落 `执行细则.md` #10） |
| P5 | 缺校验器 | 中 | 直接建 | 阶段 0 本来就要建，已落地 `validate_model_data.py`（基线 0 ERROR/0 WARN） |
| P6 | 跑分采集成本高 | 低 | 不修 | 计划已有平台 agent（P1/P2）承接；补一句「建议用浏览器抓取」 |
| P7 | 正向确认 | — | 无需动作 | — |

---

## 8. 产出文件清单（预期）

| 文件 | 产出方 | 说明 |
|---|---|---|
| `model_data_v1_clean.jsonl` | 阶段 0 | 修复 bug 后的 v1 |
| `roster.md` / `roster.jsonl` | 阶段 0 | 28 厂商花名册（三态标记） |
| `validate_model_data.py` | 阶段 0 | 校验脚本 |
| `incoming/agent_g1..g6.jsonl`、`agent_p1/p2.jsonl` | 阶段 1 | 各采集 agent 分片 |
| `model_data_v2.jsonl` | 阶段 2 | 合并后主库 |
| `qa_report.md` | 阶段 3 | 填充率对比 + 冲突裁决 + 风险声明 |
