# 阶段 3 质检报告（model_data v2）

> 执行者：`workbuddy-05`（本机采集主 agent）
> 执行时间：2026-08-29
> 依据：`multi_agent_plan.md` §5「阶段 3 · 质检与验收」、`COLLECTION_PLAN_v2.md` §6 验收标准、`WORKBUDDY_AGENT_GUIDE.md`
> 统计口径脚本：`scripts/qa_stats.py`（填充率）、`scripts/diff_incoming_db.py`（差异/冲突）

> **【同日补记 2026-08-29 · 整改轮 D1–D7】** 本报告的质检结论之后，同日又跑了一轮整改，读本文时注意六处时效性：
> 1. §1 的 **ERROR 0 是在旧门禁下取得的**——旧门禁不查 `pricing.confidence` 枚举、不查 `knowledge_cutoff` 格式、
>    不查 `source_type` 与价格值是否自相矛盾，也不查「无价却填了币种」。四项补齐后，当前主库仍为
>    **ERROR 0 / WARN 689 / 结构漂移 0**。
> 2. §3.2 第 2 点与 §5-6 关于「开源权重却有定价」的判定**已被推翻**，红线 5 同日改按
>    「厂商有无自有官方 API 刊例价」判定，详见 `multi_platform_subagent_guide.md` §5 红线 5 与 `WORKBUDDY_AGENT_GUIDE.md` §16。
> 3. 门禁现行口径以 `scripts/validate_model_data.py` 为准，**本文与规范文档都只是它的说明，不是判据本身**。
> 4. **主库记录数已变：950 → 940**。采集人在 `meta.verification_status` 标了 `存疑` 的 10 条经逐条复核确认查无依据，
>    经用户拍板全部移出主库，原样存 `docs/unconfirmed_models.jsonl`，对应采集文件移入 `incoming/models/_quarantine/`
>    （机制见 `WORKBUDDY_AGENT_GUIDE.md` §17）。花名册口径因此重基线为 **主库 692 + 隔离档 10 + 缺失 0**，
>    这 10 条**不是漏采、不要重采**。本文正文所有 950 / 678 一类计数均为整改前快照，未回填。
> 5. **本文 §3 / §3.1 的 `independent` 与 `arena_elo` 两行是「破坏后」快照**：本轮「补合并 277 条」用
>    `--on-array replace` 静默抹掉了 81 条记录 / 215 个已采集跑分条目，把这两个维度的填充率打了下来。
>    **D8 已回补并结案**：累计净回补 **82 条记录 / 207 个条目**（`independent` 178 + `arena_elo` 29；另 9 条
>    `self_reported` 经核对属合法 schema 升级，不计损失），回补后花名册 `independent` 18.2% → **28.3%**、
>    `Arena Elo` 6.4% → **7.8%**，全库 `independent>0` 33.8%。详见 §3.2 第 4 点与 `WORKBUDDY_AGENT_GUIDE.md` §18。
> 6. **`pricing.currency` 口径已拍板并归一（D7）**：无价即无币种，六价键全 null 的 323 条已统一为 `null`，
>    门禁新增规则 4.3 防回归；§6.2 里「currency 口径未定」一行已结。根因是 `prompt.md` 原文写着
>    「`currency` 默认 `"USD"`」，该字段说明与三处采集侧文档同日一并改正。

---

## 0. 一句话结论

**数据层完好，但合并层此前存在系统性缺口：702 条花名册记录中 303 条（43.2%）从未合并采集成果，主库里躺的是 08-24 的 HF 骨架快照。本轮已补合并 277 条，缺口从 303 降到 26。**

采集工作本身是完成的（305/305 批次 submitted、702 个 model_id 全部存在），问题出在"合并"这一步没被验证——此前判定"0 缺失"用的是 `model_id 是否存在于主库`，而骨架早已预填，所以 `model_id 存在 ≠ 数据已合并`。

---

## 1. 全量校验结果

| 项 | 结果 |
|---|---|
| 主库记录 | **950 条**（花名册 702 + v1 遗留 248） |
| 门禁 ERROR | **0** ✅（验收标准 1 达标） |
| 门禁 WARN | 678（不阻塞） |
| schema | 全部 1.1 |
| 重复 model_id | 0 |

> **整改后现值（读表时替换使用）**：主库 **940 条**（花名册 692 + v1 遗留 248）、ERROR **0**、WARN **689**、
> 结构漂移 0；另有 10 条存疑记录移出主库、原样存 `docs/unconfirmed_models.jsonl`。见文首补记第 4 点。

### WARN 678 的构成（按类型）

| 数量 | 类型 | 性质 |
|---|---|---|
| 123 | 填了有效上下文但 notes 未注明独立测试方法与来源 | 规范性提醒，可后置补写 |
| 105 | 有标称上下文但有效上下文为空，notes 未标「标称值，有效上下文待测」 | 同上（对应 §14 踩点 3） |
| ~220 | 自报跑分 `source_type` 未体现「自报」字样 | 规范性提醒，多为骨架残留条目 |
| 10 | 参数量全空但 notes 未声明「官方未披露」/「待补」 | 对应 §14 踩点 2 |
| 其余 | 散布的字段口径提醒 | — |

> 上下文窗口相关的两类合计 228 条，占 WARN 的 34%，是"notes 补写"这一项的主要工作量。

### 验收标准逐条对照

| # | 验收标准（COLLECTION_PLAN_v2 §6） | 结论 |
|---|---|---|
| 1 | 全量 ERROR = 0 | ✅ 0 |
| 2 | 逐维度填充率较 v1 显著提升 | ✅ 见 §3（定位 / 多模态 / 自报跑分 / 上下文均提升） |
| 3 | `verification_status` 全部诚实 | ✅ 本轮修掉 3 条「已验证但无 verified_at」，现为 0 |
| 4 | `collected_at` 为真实采集日 | ✅ 分布见下，符合"不同模型不同日"的正确状态 |
| 5 | 占位符 notes 占比从 98.4% 降下来 | ✅ **5.6%**（53/950） |

`collected_at` 分布：`08-24: 82` / `08-25: 2` / `08-26: 193` / `08-27: 163` / `08-28: 359` / `08-29: 151`
（`08-24` 的 82 条 = 26 条待重采花名册 + 56 条无采集任务的 v1 遗留）

---

## 2. 🔴 重大发现：277 个采集文件从未合并进主库

### 2.1 怎么发现的

阶段 3 要求做"冲突裁决清单"，于是逐个比对 `incoming/models/*.jsonl`（采集产出）与主库同 `model_id` 记录：

- 319 个采集文件中，只有 **5 个**与主库完全一致，226 个有 21–50 处字段差异
- 按 `meta.collected_at` 判定方向：**279 个文件的采集日晚于主库，0 个早于主库**
  → 差异不是"主库后来更新了"，而是"采集成果根本没进去"

### 2.2 根因

主库 950 条中，702 条花名册模型的**骨架早已由 HF API 快照预填**（`WORKBUDDY_AGENT_GUIDE.md` §13）。
因此 `model_id 存在` 是一个**恒真**的判据——用它来验收"是否入库"，必然得出 0 缺失的假象。

真正的验收判据应为 `meta.collected_at` 是否已从骨架快照日（`2026-08-24`）推进到实际采集日。

### 2.3 处置

1. 生成待合并清单：`intermediate/merge_todo.txt`（277 个文件，全部预先跑过门禁 ERROR=0）
2. 用文档 §13 的既有策略一次性合并：

```bash
python scripts/model_data_tool.py merge \
  --file model_data_v2.jsonl \
  --incoming @intermediate/merge_todo.txt \
  --on-null take_source --on-both source_wins \
  --on-array replace --on-schema upgrade --tie-breaker keep_target --apply
```

3. 结果：**记录数仍 950（填骨架不加记录，符合预期），ERROR 仍 0，WARN 684 → 678**

| 指标 | 补合并前 | 补合并后 |
|---|---|---|
| 花名册中仍是骨架快照（`collected_at=08-24`） | **303** | **26** |
| 花名册已合并采集成果 | 399（56.8%） | **676（96.3%）** |

> 合并工具原本只支持 `--incoming` 单个文件，277 次调用意味着 277 次全库重写。
> 本轮给它加了**多文件 / 目录 / `@清单文件`** 三种传入方式（在内存中依次合并，最后只落盘一次、只备份一次），
> `@清单` 是专为规避 Windows 命令行长度上限（277 个路径约 16KB，超限）而加。

---

## 3. 填充率对比（花名册 692 vs v1 遗留 248）

统计脚本：`scripts/qa_stats.py`；填充判定 = 非 null / 非空串 / 非空数组 / 非全 null 对象。

> 口径已两次变更，下表为 **D6 隔离 + D8 回补之后**的现值：分母从 702 变成 **692**（10 条存疑记录移出主库，见 banner 第 4 点），
> `独立评测` 与 `Arena Elo` 两行含 D8 找回的 207 个跑分条目（见 banner 第 5 点）。本节初版表格（702 / 破坏后）已作废。

| 维度 | 花名册(692) | v1 遗留(248) | 差值 |
|---|---:|---:|---:|
| 发布日期 | 100.0% | 100.0% | 0.0 |
| **定位标签** | **90.3%** | 81.9% | **+8.4** |
| 开放权重 | 95.1% | 87.1% | +8.0 |
| API 可用 | 92.5% | 85.5% | +7.0 |
| 本地部署 | 89.3% | 75.4% | +13.9 |
| **总参数量** | **74.3%** | 56.0% | **+18.3** |
| 激活参数量 | 50.0% | 48.4% | +1.6 |
| **上下文窗口** | **67.6%** | 97.2% | −29.6 |
| 有效上下文 | 17.2% | 35.9% | −18.7 |
| 知识截止 | 16.6% | 25.4% | −8.8 |
| **多模态输入** | **83.5%** | 94.4% | −10.9 |
| 原生多模态 | 80.6% | 89.1% | −8.5 |
| **自报跑分** | **56.5%** | 66.1% | −9.6 |
| 独立评测 | **28.3%** | 49.2% | −20.9 |
| Arena Elo | 7.8% | 47.6% | −39.8 |
| 定价-输入 | 21.4% | 59.3% | −37.9 |
| 定价-输出 | 19.5% | 58.5% | −39.0 |
| 定价-生效日 | 100.0% | 96.8% | +3.2 |
| 来源 URL | 99.7% | 99.6% | +0.1 |

### 3.1 补合并带来的提升（同口径对比）

| 维度 | 补合并前 | 补合并后（D8 回补后现值） |
|---|---:|---:|
| 定位标签 | 57.5% | **90.3%** |
| 上下文窗口 | 44.6% | **67.6%** |
| 自报跑分 | 34.3% | **56.5%** |
| 多模态输入 | 52.4% | **83.5%** |
| 原生多模态 | 48.4% | **80.6%** |

> `独立评测` / `Arena Elo` 未列入本表：它们同时受「补合并提升」与「replace 破坏」两股反向作用影响，
> 拆分前的补合并前基线已不可单独归因，只在 §3 给出终值。

### 3.2 为什么部分维度花名册反而低于 v1 遗留（口径说明）

**这不是 v2 采集质量差，是样本构成不同：**

1. **v1 遗留的 248 条是早年投入充分的主流模型**（Qwen 全系、GPT、Claude 等），数据天然齐全；
   而 v2 花名册 702 条里 **406 条是开源权重模型**、含大量长尾/学术模型（如 `brain2qwerty`、`rnnsearch-50`、
   `nplm`、`digivio`、Bengio 2003 NPLM），这些模型公开信息本就稀少。

2. **定价必须按分型看**，但分型依据不是「是否开源权重」。开源与否不决定有没有官方价——
   DeepSeek / 阿里 Qwen / Moonshot Kimi / 智谱 GLM / MiniMax / Mistral / Cohere 都是**既开源权重、又公布自有官方 API 刊例价**，
   这类模型的定价本该照采。判定基准见 `multi_platform_subagent_guide.md` §5 红线 5（2026-08-29 由「是否开源权重」修订）。
   混在一起统计仍会严重低估真实覆盖：

   | 分组 | 定价填充率 |
   |---|---:|
   | 花名册 / 商业 API（191 条） | **50.3%** |
   | 花名册 / 开源权重（406 条） | 12.6%（**应接近 0，属正常**） |
   | 花名册 / 未知或混合（105 条） | 7.6% |
   | v1 遗留 / 商业 API（83 条） | 86.7% |
   | v1 遗留 / 开源权重（131 条） | 32.8% |

   → 真实的同比口径是 **50.3% vs 86.7%**（同为商业 API 模型），差距仍在，
   主因是花名册里的商业 API 模型有大量长尾厂商（如区域小厂），定价页难找或不存在。

   > **【本报告初稿结论已更正】** 初稿依旧红线 5 把这 32.8%（43 条）判为「疑似违规、建议核查后置 null」。
   > 逐条复核来源后该结论**不成立**：43 条中 **40 条 `source_type` 即厂商自家官方定价页/发布页且标 T0**
   > （含 14 条「已下架」模型的历史官方价），另 3 条为如实标注的媒体转述 T3，
   > **没有一条是拿第三方托管商（OpenRouter / 云厂商）报价冒充官方价的**。
   > 若照初稿建议执行，将直接删掉 40 条真实的官方刊例价——是口径错误导致的破坏性「整改」。

3. **Arena Elo 7.8% 属正常**：只有上过 LMArena 榜的模型才有该字段，长尾模型本就没有。

4. > **【重要更正 · 本文 §3 / §3.1 的 independent 与 arena_elo 两行是「破坏后」快照，现已回补】**
   > 本轮自己的「补合并 277 条」用了 `--on-array replace`，而采集分片普遍只填 `self_reported`、
   > `independent` / `arena_elo` 留空 `[]` —— **空数组把目标里已有的条目整组抹掉了**：
   > 按主键比对 **81 条记录 / 215 个条目**（`independent` 177、`arena_elo` 29、`self_reported` 9），
   > 丢的是前几轮人工采集的真数据（如 `cohere:cohere-command-a` 的三条 Arena Elo）。
   > 反常证据：从未被合并触碰的 08-24 骨架记录 `independent` 覆盖 **72%**（59/82），
   > 而被合并过的记录只有 **22%**（191/858）——同源于 Epoch/公开榜单的数据不可能差三倍。
   > 所以这两个维度的「花名册低于 v1 遗留」**不是样本构成差异，是本轮合并造成的破坏**；
   > 取证与恢复方法见 `WORKBUDDY_AGENT_GUIDE.md` §18。
   > 教训：**「记录数不变 + ERROR 0」这套验收口径看不见字段级破坏**，且合并后 WARN 由 684 降到 678
   > 当时被当成成绩记录——那 6 条正是被删掉的跑分带走的 WARN。
   >
   > **【D8 处置结果】** 已按主键「只回补不覆盖」找回，累计净回补 **82 条记录 / 207 个条目**：
   > 其中 `self_reported` 的 9 条经逐条核对**不算损失**（`nvidia:llama-nemotron-ultra-253b:base` 的旧
   > `name`/`mode` 写法被后来的 canonical 写法取代，属合法 schema 升级，已撤回），故不计入。
   > 另有 1 条 `independent` 早在恢复基线（943b6f2）之前就已丢失、按单一基线扫不出来，
   > 回补后复跑全历史取证才发现并一并找回 —— 这就是「回补完必须用全历史最大长度复扫」的理由。
   > 回补后 `independent>0` 全库 22% → **33.8%**。
   > **新开待拍板项**：主键 `(benchmark, config)` 认不出 legacy `name` 写法，回补后 207 条里有
   > 2 条与既有条目同名同分、3 条同名不同分（例如 `openai:gpt-5-2-2025-12-11-xhigh:base` 的
   > GPQA Diamond 0.914 同时存在 T1 直连与 T3 转述两条）。两条都带完整来源，未自动删，
   > 需与「全库 1291 条 legacy `name` 条目是否归一化」一并定口径。

### 3.3 占位符 notes 的口径修正

`COLLECTION_PLAN_v2` §6-5 原文口径是「待补/未含」。但若把"官方未披露""待实测"也算作占位符，
会把**真实采集结论**（查过了，官方确实没公布）误判成烂尾记录——长尾模型参数量普遍未公开，必然被误伤。

本轮把口径收窄为「待补 / 未含 / 需另行采集 / 待采集 / 未采集 / 待核实」，
并单独统计「确认官方未披露」类：

| 口径 | 数量 | 占比 |
|---|---:|---:|
| 真占位符 notes（未采到） | 53 | **5.6%** |
| 确认官方未披露（有效采集结论） | 243 | — |

---

## 4. 冲突裁决清单

### 4.1 结论：无需要裁决的冲突

本轮合并策略为 `--on-both source_wins --on-null take_source --on-array replace`
（依据 `WORKBUDDY_AGENT_GUIDE.md` §13：主库是预填骨架，合并是"填骨架"不是"加记录"）。
因此**没有产生 `on_both=conflict` 条目**，冲突裁决清单为空。

按 `prompt.md` 5.4 的可信度规则，实际生效的是一条**统一的优先级裁决**：
**人工实采值 > HF API 骨架快照值**。理由：骨架来自自动化快照推导，实采经过官方源直验。

### 4.2 合并前后的实质差异（等价于"被裁决掉的冲突"）

`scripts/diff_incoming_db.py` 的扫描结果（补合并前）：

- 采集文件与主库存在值差异的字段 **7804 处**
- 差异最多的字段：`pricing.source_type`(289)、`architecture.notes`(279)、`pricing.notes`(279)、
  `modality.*.notes`(各 278)、`basic_info.access.notes`(258)、`basic_info.release_date`(253)
- 骨架独有、合并时被保留的字段：`pricing.promotions`(103)、`pricing.long_context`(89)、`pricing.free_tier`(72)

典型裁决案例（骨架值 → 实采值）：

| model_id | 字段 | 骨架值 | 实采值（胜出） |
|---|---|---|---|
| `aleph-alpha:pharia-1-llm-7b:base` | `basic_info.full_name` | `Pharia-1-LLM-7B` | `Aleph Alpha Pharia-1 LLM 7B` |
| `aleph-alpha:pharia-1-llm-7b:base` | `architecture.architecture_type` | `Unknown` | `Dense Transformer` |
| `aleph-alpha:pharia-1-llm-7b:base` | `architecture.context_window_tokens` | null | 8192 |
| `google:datagemma:base` | `meta.notes` | Epoch AI 数据集转述 | 实采 T0 说明（arXiv 2409.13741） |
| `fugaku-llm`（§13 已记录） | `access.api` | `true`（HF 快照推导） | 实查无官方 API |

### 4.3 越界 positioning 的静默丢弃（已知未修项）

合并工具对**受控词表外的 positioning 标签**是静默丢弃的，
导致源文件合规但主库落成 `[]`，而主库校验仍是 ERROR 0。
`workbuddy-03` 已修源文件（`b168w1`/`b258w1`/`b259w1`），主库未回填，留给本阶段。

本轮补合并后花名册定位填充率已达 **89.5%**，剩余空 `positioning` 多为"确无适用标签"的历史模型
（如 Bengio 2003 NPLM，六个标签无一适用，记 `[]` 并说明是正确做法）。

---

## 5. 已知风险声明（分析端须显著标注）

1. **官方域不可访问属环境限制**。`docs.claude.com` / `platform.openai.com` 等官方域直连不可达，
   大量记录只能取 WebSearch 摘要，按红线降级标 `T3` / `T0-自报-转述`。
   **相当比例的记录可信度低于严格 T0/T1**——全库 `confidence` 分布：
   `T0-自报` 1546、`T1` 1145、`null` 1111、`T0-自报-转述` 799、`pricing:T0` 783、`T3` 725、`T0` 122、`T2` 13。

2. **Arena 数据来自镜像源**。原始 `arena.ai` 被 Cloudflare 拦截，
   442 条记录的 `source_type` 标注为「LMArena 镜像(DataLearner)」，非一手来源。

3. **定价需定期复核**。`pricing.effective_date` 有 854/942 条精确到日；
   **定价采集 30 天后应复核**（本轮主要集中在 2026-08-27 ~ 08-29）。

4. **社区异常信号不入规范基准**。某模型特定榜单骤降等信号，仅在 `notes` 保留风险提示，不进 `benchmarks`。

5. **骨架残留字段未经实采复核**。主库保留的 `pricing.promotions` / `long_context` / `free_tier`
   等骨架独有字段（共约 264 处）来自 HF 快照，未经本轮实采验证。

6. **~~v1 遗留记录的开源权重定价可疑~~ → 已更正，判定不成立（见 §3.2 更正框）**。
   131 条中 43 条有定价，初判「与红线 5 冲突、疑似第三方云转售价」；逐条复核来源后 40 条出自厂商自家官方定价页（T0）、
   3 条为如实标注的媒体转述（T3），**无一例转售冒充**。红线 5 的判定基准已于同日改为「厂商有无自有官方 API 刊例价」。
   → 这轮回扫真正查出的缺陷是另一类，且此前门禁完全不查：**`pricing.source_type` 声称查无官方价、价格键却仍挂着值**。
   全库 7 条，其中 4 条已按记录自身证据整改（D5：3 条剔 null + `aya-expanse-32b` 更正标签），
   余 3 条（`meta:muse-spark-1-1` / `muse-spark-1-2` / `microsoft:mai-code-1-flash`）价格取自头条号 UGC、
   需外部核实方能定方向，**已保留为 WARN 并登记待拍板，未靠猜测改动数据**。

---

## 6. 剩余待办

### 6.1 26 个花名册模型未合并（需重采）

补合并后仍有 26 条花名册记录停留在骨架快照日，**全部是"磁盘无采集文件"**——
对应早期 pilot 批次（OpenAI / Anthropic / Google / Meta / Mistral），文件在合并后未保留。

```
anthropic:claude-opus-4-1-20250805-16k / -27k
anthropic:claude-opus-4-20250514-16k / -27k
anthropic:claude-opus-4-5-20251101-16k
apple:openelm-270m
google:gemini-3-6-flash-minimal / gemini-embedding / gemma-4-31b-it-minimal / glam
meta:meta-llama-3-70b-instruct / meta-llama-3-8b-instruct
meta:muse-spark / muse-spark-1-1 / muse-spark-1-2
mistral:mistral-large:2411 / mistral-medium:2505 / mistral-moderation
mistral:mistral-nemo-base:2407 / mistral-saba
openai:babbage / babbage-002 / chatgpt-agent / code-davinci-002 / gpt-3-5-turbo:1106
technology-innovation-institute:falcon-arabic
```

重采后按 §2.3 的合并命令入库即可（清单可复用 `intermediate/merge_todo.txt` 的形式）。

### 6.2 其他

| 项 | 说明 | 建议 |
|---|---|---|
| WARN 678 → **689** | 现值按规则实测构成：自报分 `source_type` 未含「自报」440、有效上下文缺测试方法说明 127、标称上下文缺「待测」标注 105、`knowledge_cutoff` 格式 9、参数量缺未披露声明 4、`source_type` 与价格值矛盾 3、缺 `source_url` 1 | 前三项占 97.5%，均属 notes 补写轮性质的采集工作；后三项为本轮新增检查照出的存量 |
| v1 遗留开源权重定价 | ~~131 条中 43 条有定价，疑似违规~~ **初判不成立，已撤销**：40 条本就有厂商官方刊例价 | **不得按旧红线 5 置 null**，见 §3.2 更正框 |
| 定价矛盾待核实 3 条 | `muse-spark-1-1` / `muse-spark-1-2` / `mai-code-1-flash`：标签称无官方价、值却挂着 UGC 转述价 | 需回厂商官方价目页逐条核实后定方向（属重采范畴，待拍板） |
| ~~采集人标 `存疑` 的 10 条~~ **已处置（D6）** | `meta.verification_status == "存疑"` 逐条复核均查无立得住的依据，经用户拍板**全部移出主库**（950 → 940），原样存 `docs/unconfirmed_models.jsonl`，4 个对应采集文件移入 `incoming/models/_quarantine/` | 已结。这 10 个 model_id 不再计入花名册完成率（692/702 + 隔离 10），**不得当「漏采」重派**；重新入库须先拿到官方证据，流程见 `WORKBUDDY_AGENT_GUIDE.md` §17.5 |
| ~~`pricing.currency` 口径未定~~ **已拍板并归一（D7）** | 六价键全 null 的 645 条里 USD 323 / null 318 / 连 unit 也 null 4，接近对半。**根因是 `prompt.md` 字段说明原文写「`currency` 默认 `"USD"`」**——照文档写就会产出「有币种无价格」的记录 | 已按「无价即无币种」把 323 条归一为 null，门禁新增规则 4.3 防回归，采集侧三处文档同日改正。`unit` 保持 `per_million_tokens` 不动（量纲声明，不携带「已核实」语义） |
| ✅ **本轮补合并造成的跑分条目丢失（D8 已回补结案）** | `85b9fae` 用 `--on-array replace` 把 81 条记录 / 215 个**已采集**跑分条目覆盖成空（independent 177 / arena_elo 29 / self_reported 9），丢的是前几轮人工成果而非骨架填充值 | 见 §3.2 第 4 点与指南 §18。工具已加空数组保护（默认不覆盖，需 `--allow-empty-replace` 显式放行）并经 `temp/d8_verify_empty_array_guard.py` 验证；恢复脚本 `temp/d8_restore_benchmarks.py --apply` 已执行，再由 `temp/d8_fix_over_restore.py` 撤回 9 条属合法升级的 legacy `self_reported`、`temp/d8_restore_eurus_independent.py` 找回 1 条早于恢复基线丢失的条目，**累计净回补 82 条 / 207 个条目**，复检 940 条 ERROR 0。遗留项转为「同名基准冲突与 1291 条 legacy `name` 条目归一化口径」，由 `temp/d8_check_restore_conflicts.py` 出清单 |
| 主库 positioning 空值 | 补合并后花名册填充率 89.5%，剩余多属确无适用标签 | 抽样复核即可 |
| 可视化发布 | `viz/viz_index.html` 需按最终库重新生成 | 合并定版后执行 |
| 交付 push | 主库已定版待推 | 用 `C:\Program Files\Git\cmd\git`（system credential.helper=manager，静默通过） |

---

## 7. 本轮产出与变更

| 文件 | 变更 |
|---|---|
| `model_data_v2.jsonl` | 补合并 277 条采集成果；修 3 条 `meta.verified_at` |
| `scripts/qa_stats.py` | **新增**：阶段 3 填充率统计器（含分型定价、占位符口径修正） |
| `scripts/diff_incoming_db.py` | **新增**：incoming vs 主库差异扫描器（冲突裁决清单输入） |
| `scripts/model_data_tool.py` | `_save()` 加重试退避（修 Windows 瞬时锁定）；`merge --incoming` 支持多文件/目录/`@清单` |
| `intermediate/qa_stats.json` | 质检统计明细 |
| `intermediate/conflicts.json` | 差异扫描明细 |
| `intermediate/merge_todo.txt` | 277 个待合并文件清单 |
| `backups/model_data_v2.jsonl.wb05-pre-qa-20260829-192705` | 合并前主库备份 |

---

*维护者：`workbuddy-05` ｜ 生成时间：2026-08-29*
