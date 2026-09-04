# model_data 采集 Pipeline 测试报告

> 测试时间：2026-08-24
> 测试对象：`prompt.md`(v2 采集 prompt) + `model_data_tool.py`(读写/合并工具) + `model_data_v1.jsonl`(第一版数据库，924 条)
> 测试方法：模拟"遵循 prompt.md 的采集 agent"，联网调研 **Anthropic** 与 **Zhipu(智谱 GLM)** 两家公司的旗舰/主线模型，产出符合 schema 1.1 的 JSONL，再用 `model_data_tool.py` 合并进数据库（先在 **副本** `model_data_v1_test.jsonl` 上 dry-run + apply，原始 v1 未改动）。
> 测试产物：`test_collected_anthropic_zhipu.jsonl`(7 条) / `test_enrich_existing.jsonl`(1 条) / `gen_test_records.py` / `model_data_v1_test.jsonl`(929 条，沙箱副本)

---

## 一、结论速览

| 严重度 | 问题 | 一句话 |
|--------|------|--------|
| 🔴 高 | P1 model_id 命名规范冲突 | build 脚本用连字符+`:base`，prompt 用点号+营销代号 → 合并时**新建重复记录而非富集** |
| 🔴 高 | P2 newer_wins 同日平局静默保旧 | `collected_at` 同为当天时，所有"双方都有值且不同"的字段（release_date/vendor/open_weights/notes）**被静默丢弃更新** |
| 🟡 中 | P3 官方域可达性判定过粗 | 同一厂商子域可达性不一致（anthropic.com/pricing 直连失败，docs.anthropic.com 可达且价格同源），决策1 的"官方域不可访问"触发是厂商级开关，粒度不对 |
| 🟡 中 | P4 汇率来源/校验未规定 | 人民币→USD 折算（执行细则#10）只要求"记录汇率日期"，未规定汇率从哪取、是否需实时核实 → 我用假设汇率 7.13，存在错误风险 |
| 🟡 中 | P5 缺记录级校验器 | 工具的 11 项自查清单（执行细则#11）无代码强制；非合规记录（错 confidence、漏 meta.notes 声明）工具不会拦截 |
| 🟢 低 | P6 跑分依赖特定站点 | 完整跑分需命中 Artificial Analysis / LMArena 等站，WebSearch 摘要往往不含 → 实际采集成本高、易留空 |
| 🟢 低 | P7 富集路径 null 填充正常 | 正向：已有记录的 null 字段（pricing/modality）被 take_source 正确填充（非问题，仅记录以区分 P2） |

---

## 二、逐条问题详述

### P1（高）model_id 命名规范冲突 → 重复而非合并

- **现象**：第一版库由 `build_model_data.py` 生成，ID 形如 `zhipu:glm-5-3:base`、`anthropic:claude-opus-4-7:base`（连字符 family + 默认 `:base` / 快照日期）。
- **prompt.md 决策6** 要求三段式 `vendor:family:variant`，family 含主版本、variant 放营销代号，示例用**点号**：`anthropic:claude-opus:4.7`、`deepseek:deepseek-v4-pro:2026-06`。
- **结果**：用 prompt 规范采集 `zhipu:glm-5.3:base` 合并进库时，因库里是 `zhipu:glm-5-3:base`（连字符），**两者不等 → 被当成新记录 add_record**。库中最终同时存在两条指向同一模型的记录（验证：`glm-5.3 -> ['zhipu:glm-5.3:base']`，`glm-5-3 -> ['zhipu:glm-5-3:base']`），DB 由 924 涨到 929（净增 5 条重复）。
- **影响**：全量采集时，按 prompt 规范产出的记录几乎不会命中 build 脚本的任何 ID，**第一版库无法被"富集"，只会无脑追加**，数据冗余且横向对比会分裂。
- **根因**：两套 ID 生成逻辑没有统一来源（一个在 build 脚本的 `build_model_id()`，一个在 prompt 文本）。

### P2（高）newer_wins 同日 collected_at 平局 → 静默保留旧值

- **现象**：合并策略 `on_both=newer_wins` + `recency=meta.collected_at`。第一版库记录的 `collected_at` 是 `2026-08-24`（build 脚本写死的当天），本次采集记录也是 `2026-08-24` → `_compare_recency` 判定"相等/无法判定" → 走"保留目标(old)"分支。
- **后果**（enrichment 测试 `zhipu:glm-5-3:base` 实锤）：
  - `basic_info.access.open_weights`：目标 `false` → 来源 `true`，**被跳过，保留错误的 `false`**；
  - `basic_info.release_date`：目标 `2026-02` → 来源 `2026-04`，保留旧的 `2026-02`；
  - 所有 `notes`（architecture / pricing / modality / meta）：**全部保留 Epoch 旧文本，丢弃本次更新的更准文本**；
  - `vendor` 也保留旧的 `Z.ai (Zhipu AI)`。
- **本质**：天级粒度的 `collected_at` 无法区分"同一天内的两次采集谁更新"；平局默认保旧，导致**重采集（更新已有记录）在同日几乎必然失败**。
- **影响**：这是"重采集修正/补全"工作流的核心阻塞点。

### P3（中）官方域可达性判定过粗

- **实测**：
  - `https://www.anthropic.com/pricing` 直连 **fetch failed（不可达）**；
  - `https://docs.anthropic.com/.../models/overview`（同属官方域）**可达**，且含**同源同价**的定价；
  - `https://open.bigmodel.cn/pricing`（智谱官方）**可达**，但只列 GLM-4 系列，GLM-5.3 价格只存在于 OpenRouter（T1 独立追踪）。
- **问题**：决策1 的"官方域沙盒不可访问 → 降级"是**厂商级**开关，但真实情况是**子域级**：主定价页挂了、docs 没挂；或官方页可达但缺最新模型。prompt 没说清"以哪个 URL 为准"，采集 agent 只能自行判断，易误标/漏标降级声明。
- **连带**：Anthropic 价格我最终标了 `source_type=官方定价页 / confidence=T0`（取自 docs 概览），但主定价页其实没直连成功——是否该降级为 T3，规范含糊。

### P4（中）汇率来源与校验未规定

- 执行细则#10 要求非 USD 价按采集日汇率折算为 USD 并在 notes 记"原始货币+汇率日期"。
- **缺口**：没规定汇率从哪取、是否需实时核实。本次 GLM-4-Plus 官方人民币价（¥5/百万 token）我按**假设汇率 7.13（未实时核实）**折算成 $0.70 写入——若汇率偏差，全部人民币计价模型的价格都会系统性偏移。
- 建议：明确汇率取数源（如当天公开汇率 API/页面）并写入 `meta` 或 `pricing.notes` 的"汇率日期+来源"。

### P5（中）缺少记录级校验器（linter）

- `model_data_tool.py` 只做"读写/合并"，**不做 schema/合规校验**。
- 执行细则#11 的 11 项自查（参数量未披露填 null、多模态 true/false/null 区分、降级记录 meta.notes 声明、百分制转小数…）目前只能靠采集 agent 自律。
- **风险**：非合规记录（如把"没查到"写成 `false` 而非 `null`、降级记录漏写"官方域沙盒不可访问…"声明、confidence 与 source_type 不自洽）能直接进库且工具不报错。
- 建议：加一个 `validate` 子命令，对单条/批量 JSONL 跑 11 项检查并输出违规清单。

### P6（低）跑分需依赖特定站点，采集成本高

- prompt 推荐 GPQA / SWE-bench / AIME / MMMU 等，并强调"自报+独立双源"。
- 实测 WebSearch 摘要通常不含这些具体分数；要拿全需命中 Artificial Analysis、LMArena、OpenCompass 等站。本次 Anthropic 模型我**未采集到具体跑分**（留空数组 + notes 说明），只有 Zhipu GLM-5 从第三方博客拿到 SWE-bench 0.778 / AIME 2026 0.927（已标 T3）。
- 含义：完整跑分采集是个重活，且依赖外部站点可达性；轻量测试可只填架构/定价/多模态。

---

## 三、工具表现良好的部分（正向确认）

1. **安全机制到位**：默认 dry-run，apply 前自动 `.bak` 备份，原子写（`os.replace`）。原始 v1 全程未动。
2. **null 填充正确**：`on_null=take_source` 对已有记录的空字段（pricing.input/output、modality.*、architecture.context_window_tokens）正确补全。
3. **数组按主键合并**：`positioning` / `benchmarks.independent` / `meta.source_urls` 用 UNION_BY_KEY 正确去重追加，未丢数据。
4. **schema 版本一致**：双方均为 1.1，`on_schema=upgrade` 无触发、无意外升级。
5. **CLI 策略强校验**：缺 `--recency` 时 `newer_wins` 会立即报错，杜绝隐藏默认。
6. **注释行兼容**：JSONL 的 `//` 注释行被 `_load` 正确跳过。

---

## 四、修复建议（按优先级）

1. **【P1 必须】统一 model_id 生成器**：把 `build_model_data.py` 的 `build_model_id()` 与 prompt 决策6 对齐（点号 family + 营销 variant，去掉 `:base` 默认，缺失 variant 才用日期）。或反过来：在 prompt 里明确"与 build 脚本一致用连字符 + `:base`/快照"。**两处必须收敛到同一实现**，否则全量采集 = 纯追加。
2. **【P2 必须】recency 平局策略可配**：`MergeStrategy` 增加 `tie_breaker`（keep_target / source_wins / conflict），并在 `newer_wins` 且日期相等时走该策略；或把 `collected_at` 提为**带时分秒**的时间戳以区分同日采集。重采集场景建议默认 `source_wins`（新采集覆盖旧）。
3. **【P3】官方可达性细化到 URL**：prompt 决策1 改为"按具体 source_url 的可达性逐条判定降级"，并给出"docs 子域可达且价格同源时是否算 T0"的明确口径。
4. **【P4】汇率取数规范化**：在 prompt/细则里指定汇率来源与"必须记录来源+日期"，禁止用假设值。
5. **【P5】新增 validate 子命令**：实现执行细则#11 的自动化检查（null 合规、多模态三态、降级声明、confidence 与 source_type 自洽、百分制转小数、定价四必采字段存在），CI/采集后门禁。
6. **【P6】跑分采集脚本化**：提供 AA/LMArena/OpenCompass 的抓取模板，降低单模型采集成本。

---

## 五、测试产物清单（均在 `workspace/model_data/`）

| 文件 | 说明 |
|------|------|
| `test_collected_anthropic_zhipu.jsonl` | 模拟采集输出：7 条（Anthropic 3 + Zhipu 4），prompt 规范 ID |
| `test_enrich_existing.jsonl` | 富集测试：1 条，故意复用库已有 ID `zhipu:glm-5-3:base` |
| `gen_test_records.py` | 上述 JSONL 的生成脚本（保证 schema 合法、可复用） |
| `model_data_v1_test.jsonl` | 沙箱副本（929 条），已 apply 两次合并；**可随时删除，不影响原始 v1** |
| `TEST_REPORT.md` | 本报告 |

> 复现命令（在 `workspace/model_data/`）：
> ```bash
> python gen_test_records.py
> python model_data_tool.py merge --file model_data_v1_test.jsonl --incoming test_collected_anthropic_zhipu.jsonl \
>   --on-null take_source --on-both newer_wins --recency meta.collected_at --tie-breaker source_wins \
>   --on-array union_by_key --on-schema upgrade \
>   --array-key benchmark config date --array-key-override benchmarks.arena_elo:sub_benchmark,date --apply
> ```
> 注：`--tie-breaker` 为 P2 修复后新增的必填参数（on_both=newer_wins 时），缺失会立即报错。

---

## 六、问题处置记录（2026-08-24）

| 问题 | 处置 | 落地物 |
|------|------|--------|
| P1 model_id 命名冲突 | 已修：`roster.jsonl`/`roster.md` 花名册为 model_id 唯一权威；`prompt.md` 6.4 节新增执行约束（in_v1 沿用 v1 风格 ID，to_add 用花名册分配 ID，禁止自行发明/重命名） | `gen_roster.py`、`roster.*`、`prompt.md` |
| P2 newer_wins 平局 | 已修：`model_data_tool.py` 新增 `TieBreakerRule`（keep_target/source_wins/conflict），on_both=newer_wins 时 `tie_breaker` 必填，平局不再静默保旧；已用 `test_enrich_existing.jsonl` 回归验证（8 个字段更新正确生效） | `model_data_tool.py` |
| P3 可达性判定过粗 | 已修：`prompt.md` 决策1 细化为按具体 `source_url` 逐条判定；官方注册子域可达且同源 → 仍按官方域计（可标 T0）；官方页可达但缺该模型 → 按实际来源降级 | `prompt.md`（0 节摘要 + 5.4 表格） |
| P4 汇率来源 | 已修：`执行细则.md` #10 补「汇率必须有可查来源、注明出处与日期，禁止假设值；查不到则保留原币入 notes、USD 填 null」 | `执行细则.md` |
| P5 缺校验器 | 已修：`validate_model_data.py`（11 项自查机械化，ERROR/WARN 分级，退出码可作门禁）；基线结果：`model_data_v1_clean.jsonl` 924 条 0 ERROR 0 WARN；负向测试命中 23 ERROR | `validate_model_data.py`、`validation_v1_baseline.md` |
| P6 跑分采集成本高 | 不修（设计内）：阶段 1 由 P1/P2 平台 agent 专职抓取，建议优先浏览器直连而非搜索摘要 | 见 `multi_agent_plan.md` 阶段 1 |
| P7 null 填充正常 | 无需动作（正向确认） | — |
