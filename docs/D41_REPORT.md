# D41 轮次报告 · 2026-09-10

> 用户触发。D40 报告 §七 五项遗留一次裁定并执行：**① 移除 arena 段位错置条目 ② `dola-seed` 保留 ③ vendor 命名统一为首字母大写 ④ Qwen 3 世代命名统一为 `qwen-3-*` ⑤ license 缺口留档**
>
> 用户原文：`1. 移除 2. 保留 3. 统一首字母大写 4. 统一qwen-3 5. 留档后续再做`
>
> 主库 **937 条不变**（本轮零增删记录，全部是字段级整改），门禁 **ERROR 0 / WARN 0**。

---

## 一、结论速览

| 项 | 裁定 | 落地结果 |
|---|---|---|
| ① arena 段位错置 | **移除** | 删除 **4 条**非标准段位条目（D40 报告标题写「5 条」系笔误，实际 4 条） |
| ② `dola-seed` | **保留** | 记录保留；**附带发现**其 arena 分值原本只在 `meta.notes` 散文里、`arena_elo` 为空，已结构化补录 3 条 |
| ③ vendor 命名 | **统一首字母大写** | `basic_info.vendor` 改 **261 条 / 86 种源值**；取值 **229 → 198 种**；首字母小写 **62 → 2 种** |
| ④ Qwen 命名 | **统一 qwen-3** | `qwen3-*` → `qwen-3-*`，改 **40 条 / 39 个 family** |
| ⑤ license 46 条 | **留档后续再做** | 新建 `docs/LICENSE_GAP_BACKLOG.md`（A 类 46 条 + B 类 16 条 + 补采方法） |

**顺带修正**（③ 范围内）：

- `model_id` 前缀归一为小写 slug **56 条**（前 **207 种 → 192 种**，首字母大写前缀 **14 → 0**）
- 修正语义错误前缀 **1 处**：`unknown:yue-ai:base` → `ireader-technology:yue-ai:base`

**改动面（本轮零记录增删、零跑分/定价改动）**：仅 `basic_info.vendor`、`model_id`、`meta.notes`、`benchmarks.arena_elo` 四处。

---

## 二、第 ③ 项：vendor 命名统一（本轮工作量最大）

### 2.1 先厘清一个规范冲突

动手前查了既有规范，发现两处规定**只管 `model_id` 段、不管 `basic_info.vendor`**：

- `docs/prompt.md` 决策表第 6 项：「三段式 `vendor:family:variant`：**vendor 小写 slug**」
- `docs/prompt.md` §6.4：「`vendor`：厂商小写 slug，如 `openai` / `anthropic` / `google`…」

而实际数据是**两头都不统一**：

| 字段 | 现状 |
|---|---|
| `model_id` 前缀 | 小写 slug **885 条**（符合 §6.4）；**大写 14 种 / 52 条**（`Alibaba`13、`Google`8、`Cohere`6…），另 `xAI` 3 条 |
| `basic_info.vendor` | 首字母大写 **750 条**（80%）；**首字母小写 62 种 / 187 条**（`allenai`、`lg`、`sha-ai-lab`、`tii`…） |

「统一首字母大写」若落到 `model_id` 前缀上要改 **885 条主键**、且与 §6.4 规范相反，因此先确认了范围（见 §2.2 三问），用户选：**只改 `basic_info.vendor` 显示字段** + 前缀归一回小写 slug + **保留品牌惯用写法** + **合并同厂多写法**。

### 2.2 执行规则

**规则一 · 同厂多写法合并**（消除「按厂商聚合漏计」的根因）：

| 合并前 | 条数 | 合并后 |
|---|---|---|
| `Google` 37 + `Google DeepMind` 36 | 73 | **`Google`** |
| `Alibaba` 88 + `Alibaba (阿里通义千问 Qwen Team)` 5 + `Alibaba (Qwen Team)` / `Alibaba (Tongyi Lab)` / `Alibaba Cloud` / `Alibaba Tongyi Lab (通义实验室)` / `Alibaba (Alibaba International Digital Commerce, MarcoPolo Team, AIDC-AI)` 各 1 | 98 | **`Alibaba`** |
| `DeepSeek` 29 + `DeepSeek（深度求索）` 8 | 37 | **`DeepSeek`** |
| `Meta` 19 + `Meta AI` 12 + `Meta (Meta AI)` 1 | 32 | **`Meta`** |
| `Mistral AI` 41 + `mistral` 1 | 42 | **`Mistral AI`** |
| `Zhipu AI` 7 + `Zhipu AI (Z.ai internationally)` 3 + `Zhipu AI (北京智谱华章科技股份有限公司)` 2 + `Z.ai (Zhipu AI)` 1 + `z-ai-zhipu-ai-tsinghua-university` 3 | 16 | **`Zhipu AI`** |
| `allenai` 13 + `allen-institute-for-ai` 6 | 19 | **`Allen Institute for AI`** |
| `ByteDance` 5 + `ByteDance Seed Team` 5 + `ByteDance (字节跳动)` 1 + `ByteDance Seed` 1 | 12 | **`ByteDance`** |
| `Sber（…）` 三种括号写法 | 3 | **`Sber`** |
| `Moonshot AI` 7 + `Moonshot` 3 + `Moonshot AI (月之暗面)` 2 | 12 | **`Moonshot AI`** |
| `Huawei` / `huawei` / `华为（华为云 Huawei Cloud）` / `华为（… 昇腾 Ascend … 诺亚方舟实验室）` | 7 | **`Huawei`** |
| `Xiaomi` / `xiaomi`；`Meituan` / `meituan`；`tsinghua` / `tsinghua-university`；`ModelBest` 四种写法；`qihoo-360` 两种；`4paradigm` / `4Paradigm` | 各自合并 | `Xiaomi` / `Meituan` / `Tsinghua University` / `ModelBest` / `Qihoo 360` / `4Paradigm` |

**规则二 · 首字母大写（品牌惯用写法，非机械首字母）**：`lg`→`LG`、`tii`→`TII`、`sdaia`→`SDAIA`、`mbzuai`→`MBZUAI`、`lmsys`→`LMSYS`、`iflytek`→`iFlytek`、`stepfun`→`StepFun`、`sambanova`→`SambaNova`、`lighton`→`LightOn`、`nexusflow`→`NexusFlow`、`character-ai`→`Character.AI`、`sha-ai-lab`→`Shanghai AI Laboratory`、`nous`→`Nous Research`、`kunlun`→`Kunlun Tech`、`singapore-ai`→`AI Singapore`、`stability`→`Stability AI`、`voyage`→`Voyage AI`、`princeton`→`Princeton University`、`sk-telecom`→`SK Telecom`、`unicom`→`China Unicom`、`nstc-taiwan`→`NSTC (Taiwan, China)` 等。

**规则三 · 不动的两类**：

- **品牌自身即小写首字母**：`xAI` 保持 `xAI`（用户选「保留品牌惯用写法」）。
- **多主体联合串不合并**：含 `+` / `/` / `,` 的联合研发串（`Microsoft + NVIDIA（联合开发）`、`RWKV Foundation / EleutherAI / …`、`Contextual AI,The University of Hong Kong,Microsoft` 等）视为「研发主体描述」而非厂商，保持原文本；`Cognition AI + Stanford University`、`Mistral AI + All Hands AI`、`Zhipu AI / Tsinghua University (THUDM)`、`Prime Intellect + Arcee AI` 同理。

### 2.3 两道护栏（都真实拦下过问题）

1. **覆盖率断言**：任何首字母小写的 `vendor` 值若无显式映射即报错，**不留静默兜底**。
   → 拦下漏配的 `huawei`、`salesforce`，以及映射不一致的 `qihoo-360`（兜底会产出 `Qihoo-360`，与合并目标 `Qihoo 360` 打架）。
2. **重命名碰撞预检**：先算改后 `model_id` 全量，检测组内重复。→ **0 组碰撞**。

### 2.4 效果

| 指标 | D41 前 | D41 后 |
|---|---|---|
| `basic_info.vendor` 取值种数 | 229 | **198** |
| 其中首字母小写 | 62 | **2**（`xAI`、`iFlytek`，均为品牌自身写法） |
| `model_id` 前缀种数 | 207 | **192** |
| 其中首字母大写 | 14 | **0** |

全 261 条改动记录的 `basic_info.notes` 均追加 `【D41 vendor 归一】原 vendor: X→Y`（沿用 D28 留痕惯例）。

---

## 三、第 ④ 项：Qwen 3 世代命名统一

### 3.1 裁定方向与我的既往处置相反，需明确留痕

数据现状：`qwen3-*` **39 个 family / 40 条** vs `qwen-3-*` **3 个 family**（`qwen-3-5-flash` / `qwen-3-6-27b` / `qwen-3-8-max`）。

D40 时我按「紧贴式是多数（36:3）」的惯例，把新入库的 `qwen-3-6-plus-preview` **归一成了紧贴式** `qwen3-6-plus-preview`。本轮用户裁定「统一 qwen-3」，即改为**连字符式**，因此这 1 条随本轮一并改回。

> ⚠ **这是对 D40 处置的反转**，已在 CHANGELOG 显著标注。若原意是紧贴式，反向重命名同样是一条约命令的事。

### 3.2 改动

`qwen3-*` → `qwen-3-*` 共 **40 条 / 39 个 family**，例如：

- `qwen3-235b-a22b` → `qwen-3-235b-a22b`（含 `:2507` 与 `:base` 两个 variant）
- `qwen3-5-max-preview` → `qwen-3-5-max-preview`、`qwen3-6-max-preview`、`qwen3-7-max-preview`
- `qwen3-coder-480b-a35b` → `qwen-3-coder-480b-a35b`、`qwen3-coder-next` → `qwen-3-coder-next`
- `qwen3-embedding` / `qwen3-reranker` → `qwen-3-embedding` / `qwen-3-reranker`
- `qwen3-next-80b-a3b`、`qwen3-max-thinking`、`qwen3-max-2025-09-23` 等

**碰撞核验**：转换后与既有 3 例无冲突（`qwen3-6-27b-none` → `qwen-3-6-27b-none` 与既有 `qwen-3-6-27b` 是不同 family 串，不撞）。

**按裁定范围未动的世代**：`qwen-*`（原始 Qwen：`qwen-7b` / `qwen-1-8b` / `qwen-plus` / `qwen-turbo-2024-11-01`）、`qwen1-5-*`、`qwen2-*` / `qwen2-5-*` / `qwen2-math-*`、`codeqwen1-5-7b`。

> 📌 **一个值得下一轮注意的遗留**：改成连字符式后，`qwen3-1-7b`（Qwen3-1.7B）会变成 `qwen-3-1-7b`，与 `qwen-3-5-*`（Qwen3.5）在字面结构上产生新的歧义读法。这不是本轮引入的数据错误（原 id 本身就把点号写成了连字符），但**统一命名时值得一次性定清楚点号口径**。

---

## 四、第 ① 项：arena 段位错置条目移除

用户裁定「移除」。实际条目 **4 条**（D40 报告 §七.1 标题写「5 条」是笔误，正文表格与说明均为 4 条）：

| model_id | 被删 sub_benchmark | score | 删除理由 |
|---|---|---|---|
| `baidu:ernie-5-1:base` | `search` | 1223 | 官方博客转述 Arena Search 榜，非库内标准段位 |
| `google:gemini-3-1-pro-preview-high:base` | `LiveCodeBench Pro` | 2887 | 第三方竞赛级编程榜，非 arena 榜 |
| `meta:muse-spark:base` | `gdpval` | 1444 | GDPval 办公任务评估，非 arena 榜 |
| `zhipu:glm-5-2-none:base` | `agent` | 1524 | 媒体博客转述，未经 LMArena 直证；删后该记录 `arena_elo` 为空 |

每条 `meta.notes` 均写有 `【D41 arena 段位错置移除】`，并注明「如为独立榜单应迁 independent 段，本轮按裁定直接移除未迁移」。

> 库内标准段位为 `text` / `coding` / `math` / `vision` / `webdev`（`webdev` 4 条、`vision` 1 条属正常，未动）。

arena 条目总数：**662 → 658**（-4），另补 3 条（见 §五），**终态 661**。

---

## 五、第 ② 项：`dola-seed` 保留 + 一处勘误

用户裁定「保留」。但核对时发现 **D40 报告 §七.2 的描述不准确**：

> 原文：「仅 arena 数据（text 1456 / coding 1513 / math 1451）」

**实际**：D40 采集 agent 把这 3 个 Elo 值**只写进了 `meta.notes` 散文**，`benchmarks.arena_elo` 是**空数组**，`self_reported` / `independent` 亦均为空——即该记录当时**没有任何结构化跑分**。

处理：既然用户是基于「它有 arena 数据」做保留决定，且散落的事实已具备权威来源，本轮按同一快照结构化落地 3 条：

| sub_benchmark | score | rank | ci_95 | votes | is_primary |
|---|---|---|---|---|---|
| text | 1456.0 | 59 | ±3 | 74,277 | true |
| coding | 1513.0 | 43 | ±6 | 20,711 | false |
| math | 1451.0 | 66 | ±10 | 4,083 | false |

- **来源**：DataLearner 镜像 LM Arena，快照 `versionTime=2026-09-02`，`confidence=T1`，URL 用库内既有惯例（`/leaderboards/external/text-generation{,-coding,-math}`）。
- **核验**：三项数值已与 `temp/dl_pg_{text,coding,math}.html` 逐项比对，**与采集时写入 notes 的散文值完全一致**——本轮**无新增事实，仅是已有事实的结构化落地**。
- `meta.notes` 追加 `【D41 结构化补录】` 说明来源与该勘误。

> 该记录仍**信息过薄**：无 `release_date`（AA 与 OpenRouter 均无此模型）、无定价、无架构。本轮未补，保持留痕待后续信源。

---

## 六、第 ⑤ 项：license 缺口留档

新建 **`docs/LICENSE_GAP_BACKLOG.md`**，用户裁定「留档后续再做」，本轮**未新增任何 license 填充**。

文档先把口径钉死——这是最容易误判的地方：

> 「license 空白」**不是**全库 412 条 `basic_info.license` 为空（其中绝大多数是**闭源商业模型**，本就没有开源许可证可言）。

真实缺口只有两类：

| 类别 | 条数 | 含义 |
|---|---|---|
| **A 类：`open_weights=true` 但 license 空** | **46** | 开放权重模型却查不到许可证，**真实缺口** |
| B 类：`open_weights=null` 且 license 空 | 16 | 是否开源本身未确认，前置条件未满足 |
| （参考）`open_weights=false` 且 license 空 | 350 | 闭源，无采集意义 |

文档含：46 条逐条 `model_id` / `vendor` / `verification_status` / 源链接中的 HF repo；后续补采方法（HF API `tags` 读 `license:` + 同尺寸一致性校验）；以及一个**口径修正**——D40 曾统计「约 32 条无 HF repo 线索」，本轮按更严格的 HF **模型库**正则（排除 `api/models/*`、`papers/*` 等非模型路径）复核为 **10 条**，差异来自口径而非数据变化。

---

## 七、收尾自检（`scripts/d41_postcheck.py`，六项全过）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | `vendor` 首字母小写残留（白名单：品牌自身写法） | 无 |
| 2 | `model_id` 前缀非小写 slug | 无 |
| 3 | `qwen3-*` family 残留 | 无 |
| 4 | arena 非标准段位 | 无 |
| 5 | 重复 `model_id` / 非三段式 | 无 / 无 |
| 6 | 数组缩水（对照 `pre-d41-normalize` 备份，937 条 × 3 个 benchmarks 数组） | **0** |

- 全库门禁：**ERROR 0 / WARN 0**
- 备份：`backups/model_data_v2.pre-d41-normalize-20260910-164933.jsonl`、`backups/model_data_v2.pre-d41-dola-20260910-165029.jsonl`

---

## 八、台账与活文档同步

- `docs/batch_claim_ledger.jsonl`：7 个批次（b15w2 / b15w3 / b50w1 / b307w1 / b318w1 / b319w2 / b330w1）的 `models` 数组按新 `model_id` 同步，共 **15 处**（14 处 `qwen3-*`→`qwen-3-*` + 1 处 `unknown:yue-ai`→`ireader-technology:yue-ai`）。
  **`submitted_files` 保持历史文件名不改写**——那是历史提交物，改写等于伪造提交记录。
- `docs/WORKBUDDY_AGENT_GUIDE.md` §20 案例中的 `alibaba:qwen3-coder-480b-a35b` 加注 D41 改名后的新 id（保留当时原文）。
- `docs/D40_REPORT.md` §七 加 D41 处置结论 + 两处勘误。
- **`docs/archive/**` 与 `CHANGELOG.md` 历史条目中的旧 `model_id` 一律不回改**——归档反映当时状态，grep 旧 id 命中属预期。
- **`incoming/models/**` 提交快照文件一律不改写**（内容与文件名都保留提交当时状态）：它们记录「提交时是什么」，主库才是当前真相。因此 grep 到 `incoming/models/` 下 8 个 `*qwen3-*.jsonl` 文件名属**预期**，不是残留；`submitted_files` 与之保持对应。

---

## 九、本轮产出文件

| 文件 | 说明 |
|---|---|
| `CHANGELOG.md` | 新增 `[D41]`（Added / Changed / Removed / Docs / Notes） |
| `docs/D41_REPORT.md` | 本报告 |
| `docs/LICENSE_GAP_BACKLOG.md` | **新建**，license 缺口留档（第 ⑤ 项产物） |
| `docs/D40_REPORT.md` | §七 加 D41 处置结论与两处勘误 |
| `docs/README.md` | 索引补 D41 报告与 license 留档 |
| `docs/batch_claim_ledger.jsonl` | 7 批次 `models` 同步 |
| `docs/WORKBUDDY_AGENT_GUIDE.md` | §20 旧 id 加注 |
| `scripts/d41_normalize.py` | 三项归一（vendor / 前缀 / Qwen），含覆盖率断言与碰撞预检 |
| `scripts/d41_dola_arena.py` | dola-seed arena 结构化补录 |
| `scripts/d41_ledger_sync.py` | 台账 model_id 同步 |
| `scripts/d41_license_backlog.py` | 生成 license 留档文档 |
| `scripts/d41_postcheck.py` | 收尾六项自检 |
| `model_data_v2.jsonl` | 261 条 vendor + 56 条前缀 + 40 条 Qwen + 4 条 arena 删除 + 3 条 arena 新增 |

---

## 十、下一轮建议

1. **点号口径统一**（见 §3.2 遗留）：`qwen-3-1-7b`（Qwen3-1.7B）vs `qwen-3-5-*`（Qwen3.5）字面歧义，建议一次性定清「点号→连字符」的转换规则。→ **已于 D42 落地**：不是「点号→连字符」，而是反向——**小数一律写 `.`**（`qwen-3-1.7b` / `qwen-3.5-max-preview`），判据为 `full_name`/`version` 原文含 `a.b` 才转换；定额 314 family / 317 条，见 `docs/D42_REPORT.md`。
2. **license A 类 46 条**：其中 10 条无 HF repo 线索需人工定点，36 条可用 `scripts/d41_license_backlog.py` 配套方法批量补。
3. **`bytedance:dola-seed-2-0-pro:base`**：仍缺 `release_date` / 定价 / 架构，AA 与 OpenRouter 均无，需换信源。
4. **arena `vision` / `webdev` 段位**：库内仅 5 条，覆盖极低；`LiveCodeBench Pro` / `gdpval` 这类「Elo 量纲但非 arena 榜」的跑分，若后续要收，应明确落到 `independent` 段的哪个基准名下（本轮按裁定直接移除，未迁）。
