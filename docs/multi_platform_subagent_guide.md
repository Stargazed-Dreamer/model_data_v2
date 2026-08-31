# 多平台并发 subagent 采集指南（model_data v2）

> **用途**：你（agent）读完本文档 + 给定的共享上下文 `_m_context.md`，就能开工。本文档负责：①批次认领、②派发本平台 subagent、③单文件门禁、④落盘到指定目录。**不负责合并入库**——所有平台采集完后由高端模型统一合并 + 错漏重跑。
>
> **跨平台同步**：所有平台读写同一份 `batch_claim_ledger.jsonl`（认领表）。每个平台靠"读-改-写-提交"原子抢批次。详见 §2。
>
> **目标产出**：每个 model_id 一个 `<batch_id>__<vendor>__<model>__<variant>.jsonl` 单行压缩 JSON 文件，落到 `incoming/models/` 目录。
>
> **不要做的事**：①不要合并主库 `model_data_v2.jsonl`；②不要伪造 T0；③不要修改 `_m_context.md` / `batch_claim_ledger.jsonl` 以外的共享文件；④不要跨批次抢工（一次只认领本平台能完成的最大并发数）。
>
> **路径约定**：本指南所有路径都相对于**仓库根目录**（即包含 `model_data_v2.jsonl` / `docs/` / `incoming/` / `scripts/` 的那个目录）。各平台 clone 后此根目录可能是 `D:\model_data` / `~/model_data` / `f:\...\workspace\model_data` 等，路径不同但相对结构一致。下文 `<REPO>` 即仓库根目录占位符，调用时替换为实际绝对路径。

## 0. 一次读完即可开工的最小步骤

```
1. 读 本指南 §1-§7 全文（约 5 分钟）
2. 读 <REPO>/incoming/models/_m_context.md（红线 + 字段口径，约 2 分钟）
3. 读 <REPO>/docs/batch_claim_ledger.jsonl（认领表，找 status=pending 的批次）
4. 按本指南 §2 协议认领 N 个 pending 批次（N=本平台可同时开的 subagent 数）
5. 按本指南 §3 模板，为每个 model_id 派发一个 subagent（在 subagent 任务书里把本指南 §4-§5 复制进去）
6. 每个 subagent 完成后，主 agent 用 validate_model_data.py 跑单文件门禁，ERROR 必须=0
7. 把通过门禁的文件落盘到 <REPO>/incoming/models/，按文件命名规范 §4.3
8. 更新认领表：把对应批次 status 改为 submitted，填 submitted_files
9. 全部认领批次完成后，主 agent 退出，不合并
```

---

## 1. 角色与边界

| 角色 | 职责 | 不做的事 |
|---|---|---|
| 主 agent（你） | 读指南→认领批次→派发 subagent→单文件门禁→落盘→更新认领表 | 合并主库、跨平台协调、错漏重跑 |
| subagent | 单模型 WebSearch 采集→写单行 JSON→自跑单文件门禁 | 改主库、改认领表、跨模型 |
| 高端合并 agent（最后阶段，不在本指南范围） | 扫描 incoming/models/→按 batch_id 顺序合并→全库门禁→错漏重跑→归档 | 单模型采集 |

**核心原则**：你只对**单文件门禁通过 + 落盘 + 认领表更新**负责。合并、修复跨文件冲突、回滚都由最后的合并 agent 干。**不要试图合并**——本指南要求你不碰主库 `model_data_v2.jsonl`。

---

## 2. 批次认领表与跨平台同步

### 2.1 表文件

路径：`<REPO>/docs/batch_claim_ledger.jsonl`

每行一个批次记录（JSONL，单行压缩，UTF-8 无 BOM）：

```json
{"batch_id":"b9w1-openai","vendor":"openai","wave":1,"models":["openai:ada:base","openai:babbage:base","openai:curie:base","openai:davinci:base","openai:text-ada-001:base"],"status":"pending","claimed_by":null,"claimed_at":null,"submitted_at":null,"submitted_files":[],"notes":""}
```

字段说明：

| 字段 | 类型 | 含义 |
|---|---|---|
| `batch_id` | string | 全局唯一，格式 `b<批次号>w<波次号>-<vendor>` 或 `b<批次号>w<波次号>-<vendor>-<子标识>` |
| `vendor` | string | 主厂商名（model_id 首段） |
| `wave` | int | 本平台第几波（1 起，每平台独立计数） |
| `models` | array | model_id 列表，3-10 个为宜 |
| `status` | enum | `pending` / `claimed` / `submitted` / `verified` / `failed` |
| `claimed_by` | string\|null | 平台 ID，如 `trae-cn-glmm` / `claude-opus` / `codex-cli` |
| `claimed_at` | ISO8601\|null | 认领时间戳 |
| `submitted_at` | ISO8601\|null | 落盘完成时间戳 |
| `submitted_files` | array | 实际落盘的文件名列表（含路径） |
| `notes` | string | 留痕（失败原因、特殊情况等） |

### 2.2 认领协议（CAS - Compare And Swap）

**没有真正的文件锁**。我们用 git 作为仲裁：所有平台共享一个 git 仓库（或云盘同步目录），通过 `git pull → 改本地副本 → git commit → git push`，push 失败即视为被抢，pull 重试。

操作步骤（每次认领前都执行）：

```bash
# 1. 同步远程最新
git pull --rebase

# 2. 在本地副本里找 N 个 status=pending 的批次
#    （用 Python 读 ledger，过滤 status==pending，取前 N 个）

# 3. 把这 N 个批次的 status 改为 claimed，claimed_by=<本平台ID>，claimed_at=<now ISO8601>
#    （只改本地副本，不动远程）

# 4. 提交并推送
git add docs/batch_claim_ledger.jsonl
git commit -m "claim: <batch_id列表> by <本平台ID>"
git push

# 5. 如果 push 失败（远程已有新 commit）：
git pull --rebase
# 检查自己 claim 的批次是否被别人抢了：
#   - 如果别人已经把同批次的 status 改为 claimed，则放弃该批次，重试步骤 2 取下一批 pending
#   - 如果自己抢到了（status 仍为自己写的 claimed），继续执行采集

# 6. 全部 subagent 完成 + 文件落盘后，再次更新认领表：
#    把对应批次 status 改为 submitted，submitted_at=<now>，submitted_files=[...]
git add docs/batch_claim_ledger.jsonl incoming/models/*.jsonl
git commit -m "submit: <batch_id列表> by <本平台ID>"
git push
```

**没有 git 怎么办**：如果用云盘（OneDrive/Dropbox/坚果云）同步，则没有仲裁机制，必须用**预分配模式**：

- 在 ledger 创建时就给每个批次预填 `claimed_by` 字段（按平台编号轮流分配），各平台只跑分配给自己的批次
- 缺点：某平台宕机时其批次无法被其他平台接管
- 补救：每个批次加 `claimed_at`，超过 24h 未变 `submitted` 视为 stale，其他平台可重新认领（把 `claimed_by` 改成新平台 ID 并在 notes 留痕"接管原平台 X 超时未交"）

### 2.3 平台 ID 命名

格式：`<平台名>-<模型名>`，如 `trae-cn-glmm` / `claude-opus-4-5` / `codex-cli-gpt5` / `cursor-claude`。每个平台主 agent 启动时自己取一个唯一 ID，写到认领表。

### 2.4 批次大小建议

- 单批次 3-10 个 model_id（推荐 5 个）
- 同一 vendor 的模型尽量在同批次（同源数据便于 subagent 复用搜索结果）
- 跨 vendor 拆批次时按 fill_score 优先级：score=0 优先 > score=1 > score=2

---

## 3. 单模型 subagent 任务书模板

**每次派发 subagent 时，把以下模板复制一份，填入具体值**。模板包含本指南 §4-§5 的全部红线，subagent 读完就能开工，无需再读本指南。

```
你是 model_data v2 数据集的 M 型采集 subagent。

## 任务
为模型 `<model_id>` 产出单模型深度档案，写盘到 `<REPO>/incoming/models/<batch_id>__<sanitized_model_id>.jsonl`。

## 步骤

1. 读共享上下文 `<REPO>/incoming/models/_m_context.md`（红线规则、字段口径、JSON 格式规范都在里面）
2. 读一个已完成样板 `<REPO>/incoming/models/_samples/sample_google_gemini-3-5-flash-minimal.jsonl`（学格式，照抄顶层键顺序和骨架）
3. WebSearch 查 `<model 显示名> technical report`、`<model 显示名> model card`、`<model 显示名> pricing`、`<model 显示名> context window`
4. 数据优先级：官方定价页 > 官方 Model Card / 技术报告 (arxiv) > 官方文档博客 > 第三方媒体聚合
5. 重点字段（按 M 型优先级）：
   - basic_info.positioning：数组（受控词表：旗舰/中端/轻量/推理增强/多模态/工具调用增强）
   - basic_info.release_date：YYYY-MM-DD
   - architecture.context_window_tokens / context_window_effective_tokens / knowledge_cutoff / total_params_b / active_params_b
   - modality.input.{text,image,audio,video} / output.{text,image} / native_multimodal（布尔三态 true/false/null）
   - pricing：USD/M tokens（官方源 T0，媒体转述 T3）；**厂商无自有官方 API 刊例价时六价键全 null + notes 注明**（判定基准见下方「硬性红线」定价条目，不是「是否开源权重」）
   - access.{open_weights, api, local_deployment}
   - benchmarks.self_reported：官方自报跑分，score 一律 0-1 小数（百分制 ÷100 并在 notes 注明），每条带 source_url，source_type 必须含「自报」字样，confidence 用 "T0-自报-转述"

## 硬性红线
- 查不到 = null，严禁 false/0/空串冒充"没查到"
- 不伪造 T0：搜索结果转述的官方数据 → source_type="行业媒体聚合官方发布"，confidence="T3"
- **定价填 null 的判定基准 = 「厂商是否公布自有官方 API 刊例价」，不是「是否开源权重」**。
  厂商自己运营 API 且有刊例价 → 照常填 T0（DeepSeek / Moonshot / 阿里 Qwen / 智谱 GLM / MiniMax / Mistral 均属此类，虽也开源权重）；
  查遍官方渠道确认无自有刊例价 → 六价键全 null **且 `currency` 也置 null（无价即无币种，别留 `"USD"` 默认值，门禁规则 4.3 会 WARN）**，
  `source_type="开源权重模型核对（无官方 API 价）"`、`confidence="T0"`
  （此处 T0 指「已核对官方渠道、确认其无公开 API 价」这一核实动作的可信度，**不是**给不存在的价格贴 T0，不算伪造）。
  闭源但官方页查不到价用 `"官方定价页核对（无公开定价）"`，已下架用 `"官方定价页核对（已下架）"`。
  **严禁把第三方托管商报价（OpenRouter / NVIDIA hub / 云厂商转售）当官方价填进去。**
- 每个 benchmarks.* 条目必须带 source_url
- meta.collected_at = "YYYY-MM-DD"（今天），meta.verification_status = "待验证"
- 文件 = 单行压缩 JSON，schema 1.1，**8 个顶层键**（schema_version/model_id/basic_info/architecture/benchmarks/pricing/modality/meta），禁止删键，**禁止把 access 提为顶层键**（access 嵌套在 basic_info.access 内，见样板）
- 禁止改动 model_data_v2.jsonl 主库（合并由主 agent 统一执行）
- 禁止改动 batch_claim_ledger.jsonl 认领表

## 文件命名
<batch_id>__<sanitized_model_id>.jsonl
其中 sanitized_model_id 把 `:` 替换为 `__`，例如：
  model_id = "google:gemini-3-5-flash-minimal:base"
  文件名 = "b9w1-google__google__gemini-3-5-flash-minimal__base.jsonl"
  JSON 内 model_id 保持原样三段式

## 完成后自检
写盘后用以下命令跑单文件门禁（Windows PowerShell；Linux/macOS 把 $env 改为 export）：
$env:PYTHONUTF8='1'
python <REPO>/scripts/validate_model_data.py <REPO>/incoming/models/<你的文件名>.jsonl
目标：ERROR=0。若 ERROR>0，按报错修复后重跑直到 ERROR=0。WARN 可接受。

## 报告
完成后报告：文件路径 + 字节数 + 门禁 ERROR/WARN 数 + self_reported 条数。
```

**填模板时的关键提示**：

- `<model_id>` 用三段式原样，如 `google:gemini-3-5-flash-minimal:base`
- `<batch_id>` 来自认领表，如 `b9w1-google`
- `<sanitized_model_id>` 把 `:` 替换为 `__`
- `<model 显示名>` 用人类可读名，如 `Gemini 3.5 Flash minimal`，给 subagent 搜索用
- 平台差异：Windows 路径用 `\`，Linux/macOS 用 `/`，subagent 任务书里**统一用 Windows 路径**（除非本平台跑在 Linux 上则改用 Linux 路径）

---

## 4. subagent 派发与验收

### 4.1 并发数建议

- 单平台同时开 3-5 个 subagent（多了上下文管理成本激增）
- 每波次完成后立即更新认领表（提交 push），不要等所有批次都跑完才提交（避免其他平台以为你这批没人在做）
- 单 subagent 重试上限 5 次：第 1 次失败大概率是网络/工具调用问题，第 2-3 次重试换搜索关键词；第 4-5 次仍失败则把批次 status 改回 `pending` 并在 notes 标注"subagent 5 次未交卷"，让其他平台接管

### 4.2 验收 checklist（主 agent 对每个 subagent 产出必做）

- [ ] 文件确实落盘到 `incoming/models/<batch_id>__*.jsonl`（先查磁盘，再信 subagent 报告）
- [ ] 单文件门禁 ERROR=0（用 `validate_model_data.py` 跑过）
- [ ] JSON 是单行压缩、UTF-8 无 BOM、行尾有 `\n`
- [ ] **8 个顶层键齐全**（schema_version / model_id / basic_info / architecture / benchmarks / pricing / modality / meta）；**access 必须嵌在 basic_info.access 内，不是顶层键**
- [ ] model_id 三段式保留（含 `:`），文件名 sanitize 后用 `__`
- [ ] meta.collected_at 是今天的日期
- [ ] 至少 1 条 self_reported（除非该模型确实无公开跑分——如已下线/学术模型——此时空数组合规，但需在 meta.notes 注明原因）
- [ ] 不含主库字段（subagent 不应触碰主库，所以 incoming 文件应该是独立完整的）

### 4.3 文件命名规范（跨平台不冲突）

**关键**：所有平台共享 `incoming/models/` 目录，所以**文件名必须含 batch_id 前缀**避免重名覆盖：

```
incoming/models/<batch_id>__<sanitized_model_id>.jsonl
```

示例：
- `b9w1-google__google__gemini-3-7-flash-high__base.jsonl` （注意 batch_id 里的 `google` 和 model_id 首段 `google` 会重复，这是正常的）
- `b9w2-openai__openai__ada__base.jsonl`
- `b9w3-anthropic__anthropic__claude-1-3__base.jsonl`

**合并阶段会按 batch_id 顺序处理，文件名前缀会被合并工具识别为批次标记**。

### 4.4 失败处理

| 失败模式 | 处理 |
|---|---|
| subagent 5 次未交卷 | 把批次 status 改回 `pending`，notes 标注"5 次未交卷"，让其他平台接管或高端合并阶段重跑 |
| 单文件门禁 ERROR>0 且 subagent 无法修复 | 主 agent 手工修复（按报错信息），仍失败则 status 改 `failed`，高端合并阶段处理 |
| 模型实际不存在（如 gemini-3-0-flash-lite Google 官方目录无此命名） | 仍写一个"占位记录"（vendor + access + 占位 positioning + 其他字段全 null + meta.notes 标注"模型命名在官方目录中不存在"），落盘 + 门禁通过 + 更新认领表为 submitted，高端合并阶段决定改指或删除 |
| 网络问题导致所有 WebSearch 都失败 | 把批次 status 改回 `pending`，notes 标注"网络异常"，下次再认领 |

---

## 5. 红线（subagent 任务书必附）

1. **查不到 = null**，严禁 false/0/空串冒充"没查到"
2. **不伪造 T0**：直接来自官方源的标 `T0` 或 `T0-自报`；经媒体转述的官方数据标 `T3`，source_type="行业媒体聚合官方发布"
3. **每个 benchmarks.* 条目必须带 source_url**
   - **条目键名**：`self_reported` / `independent` 的基准名只写 `benchmark`，`arena_elo` 只写 `sub_benchmark`，
     **禁止 `name` / `benchmark_name` / `metric_name`**（`arena_elo` 也不得写 `benchmark`）；
     2026-08-30 的 D9 + D10 已把存量的 1293 + 57 条非 canonical 写法全部归一（门禁规则 6.1 现对任何缺 canonical 主键的条目报 WARN）；
     合并去重主键分别是 `(benchmark, config, date)` 与 `(sub_benchmark, date)`，认不出非 canonical 写法，同一次测量会静默并存两份
   - **主键必须能唯一标识一次测量**：同一基准并存多个测量时（shot 数 / prompting 方法 / 脚手架与 turn 预算 /
     单次 vs 投票 / pass@k / 一条记录里的多个发布变体），**区别必须写进 `config`**，全留 `null` 就会撞车、合并时无从裁决；
     同一基准的**子任务**各成一条并把子任务写进 `benchmark` 名（如 `Russian SuperGLUE (RSG) – MuSeRC`）。
     **`config` 里禁止写来源名**（如 `default（benched.ai）`）—— 来源站填 `source_site`（仅 `independent` 用，
     `independent` 的主键是 `(benchmark, config, source_site, date)`；`self_reported` 不填，来源由 `source_url` / `source_type` 表达）。
     门禁规则 6.2 会对「同主键挂着多个不同分数」报 WARN（口径见 `WORKBUDDY_AGENT_GUIDE.md` §20、§21）
4. **跑分 score 一律 0-1 小数**（百分制 ÷100 并在 notes 注明"原值 X 分，÷100 转小数"）；非百分制跑分（如 Elo / Perplexity）按红线置 score=null，原始值保留在 notes
5. **定价 null 的判定基准 = 厂商有无自有官方 API 刊例价**（2026-08-29 修订）。
   - 厂商自己运营 API 并公布刊例价 → **无论是否开源权重**，按官方定价页正常填，`confidence="T0"`
   - 查遍官方渠道确认厂商无自有刊例价（纯开源权重 / 仅提供权重不自营 API）→ pricing 六价格键全 null，
     **`currency` 一并置 null（无价即无币种；留 `"USD"` 会被读成「已按美元核实、确认无价」，门禁规则 4.3 报 WARN）**，
     `source_type="开源权重模型核对（无官方 API 价）"` + `confidence="T0"`，notes 注明「可经 HuggingFace/ModelScope 自托管或经第三方云厂商调用」
   - 闭源但官方定价页查不到 → 同上全 null，`source_type="官方定价页核对（无公开定价）"`；模型已下架 → `"官方定价页核对（已下架）"`
   - **严禁用第三方托管商报价（OpenRouter / NVIDIA hub / 云厂商转售）冒充官方价**；发现已误填的，剔为 null 并在 notes 保留原观测值留痕
   - `access.open_weights` / `access.api` / `access.local_deployment` 三者**互相独立、按事实各填**：`api` 只表示**厂商自营官方 API**，
     第三方云托管不算 true。不得由「开源」推出「有官方 API」，也不得由「有云托管」推出「api=true」
   > 旧版写作「开源权重模型 pricing 全 null」，已废弃：该口径把「开源权重」当成了判定条件，
   > 而 DeepSeek / 阿里 Qwen / Moonshot Kimi / 智谱 GLM / MiniMax / Mistral 都是**既开源权重、又有自有官方 API 刊例价**的模型，
   > 按旧口径会被错误置 null（数据丢失），或迫使采集者改写口径绕过红线。
6. **positioning 受控词表**：`["旗舰", "中端", "轻量", "推理增强", "多模态", "工具调用增强"]`，越界标签会被门禁拒
7. **文件 = 单行压缩 JSON**，schema 1.1，**8 个顶层键**（schema_version / model_id / basic_info / architecture / benchmarks / pricing / modality / meta），禁止删键，**禁止把 access 提为顶层键**（access 嵌套在 basic_info.access 内，与主库一致；如果 subagent 把 access 提到顶层，主 agent 修复时把它移回 basic_info.access）
8. **文件名 sanitize**：model_id 中 `:` → `__`，JSON 内容里 model_id 保持三段式原样
9. **meta.collected_at = "YYYY-MM-DD"**（今天的日期），meta.verification_status = "待验证"
10. **禁止改动主库 `model_data_v2.jsonl`**（合并由合并 agent 统一执行）
11. **禁止改动认领表 `batch_claim_ledger.jsonl` 中其他平台的批次**（只改自己 claim 的批次）
12. **arxiv ID 必须先核对**：任务书给的 arxiv ID 可能是错的（如 Gemma 3 任务书给 2503.19711 实为无关论文，正确是 2503.19786）；subagent 经 WebFetch 直验后用正确 ID 并在 meta.notes 标注纠错
13. **只采模型本体**（2026-08-31 拍板，D14）：agent 系统、训练/编排框架、推理基础设施、数据管线**不建条目**，即使厂商正式发布。
    发现派发错了，**回报主 agent 走 §23 非范围处置，不得硬填一条全 `null` 的记录**——这类记录占花名册名额、让完成率虚高，
    且没有任何一个字段是"这个模型"的属性。存量 7 条已移出至 `docs/non_model_records.jsonl`

---

## 6. 自检清单（主 agent 完成所有认领批次后）

- [ ] 所有认领的批次 status 都已更新为 `submitted` 或 `failed`
- [ ] 所有 submitted 批次的 submitted_files 字段填了实际文件路径列表
- [ ] 所有 submitted 文件都通过单文件门禁 ERROR=0
- [ ] 所有 submitted 文件命名符合 §4.3 规范（含 batch_id 前缀）
- [ ] 认领表已 `git push` 到远程
- [ ] incoming/models/ 下没有遗漏的文件（即认领表里 submitted_files 列表和磁盘文件一一对应）
- [ ] 没有改动主库 `model_data_v2.jsonl`（diff 应为空）
- [ ] 没有改动 `_m_context.md` / `agent_prompt_per_model.md` 等共享文件

完成后向用户报告：本平台共认领 X 批次 / Y 模型，全部 submitted。退出，不合并。

---

## 7. 高端合并 agent 的入口（参考，不在本指南执行范围）

最后阶段的高端合并 agent 读到这里即可知道本指南的产出形态：

- 入口目录：`<REPO>/incoming/models/`
- 文件命名：`<batch_id>__<sanitized_model_id>.jsonl`，含 batch_id 前缀
- 已通过单文件门禁 ERROR=0（合并 agent 仍需全库门禁复核）
- 认领表 `<REPO>/docs/batch_claim_ledger.jsonl` 中 status=`submitted` 的批次就是要合并的；status=`failed` 的需要重跑
- 合并工具：`python <REPO>/scripts/model_data_tool.py merge --file <REPO>/model_data_v2.jsonl --incoming <file> --on-null take_source --on-both conflict --on-both-override meta.collected_at:source_wins --on-array union_by_key --array-key benchmark config date --array-key-override benchmarks.arena_elo:sub_benchmark,date benchmarks.independent:benchmark,config,source_site,date --on-schema upgrade --apply`
- 合并顺序：按 batch_id 字母序，同 batch_id 内按文件名字母序
- 全库门禁：`python <REPO>/scripts/validate_model_data.py <REPO>/model_data_v2.jsonl --report <path.md>`
- 错漏重跑：对 status=`failed` 或合并后 fill_score 仍极低的模型，重新派发 subagent 采集

---

## 8. 经验教训（从前 8 批次提炼）

### 8.1 subagent 派发

1. **任务书要详尽**：模型能力差异大，模板里说"看官方源"不够，要给具体 URL 提示（如 `ai.google.dev/gemini-api/docs/pricing`）+ 数据优先级 + 红线全文。前 8 批次凡是任务书写得简略的，subagent 经常跑偏。
2. **每模型 5 次重试上限**：约 5-10% 的 subagent 因网络/工具调用问题失败，第 1 次失败大概率是网络抖动，重试即可；4-5 次仍失败通常是模型本身搜索难度大（如已下线模型），放弃让其他平台或合并阶段处理。
3. **Windows GBK 控制台崩溃**：所有 Python 命令必须加 `$env:PYTHONUTF8='1'` 前缀，否则合并工具的 emoji 输出会让 GBK 控制台崩。Linux/macOS 无此问题。
4. **Task 结果丢失率约 40%**：subagent 返回"toolcall_result is missing"或空，但文件实际可能已写盘。**先查磁盘再决定是否重派**。
5. **subagent 落盘前先读样板**：给 subagent 一个已完成样板文件路径（如 `incoming/models/_samples/sample_google_gemini-3-5-flash-minimal.jsonl`），让它照抄顶层键顺序和骨架，能省 80% 的格式问题。
### 8.2 数据采集

6. **arxiv ID 经常错**：任务书给的 arxiv ID 约有 5-10% 是错的（如 2408.01847 实为天文学论文，2503.19711 实为写作论文）。subagent 必须经 WebFetch 直验后再采用，并在 meta.notes 标注纠错。
7. **定价 null 判定见 §5 红线 5**：基准是「厂商有无自有官方 API 刊例价」，**不是「是否开源权重」**。两个实测反向坑：① DeepSeek / Qwen / Kimi / GLM / MiniMax / Mistral 开源权重但自营 API 有刊例价，按「开源即 null」会把真价丢掉；② 反过来拿 OpenRouter / NVIDIA hub / 云厂商转售价冒充官方价填进去，是伪 T0。
8. **CNY 定价折算**：中国厂商（百度/阿里/智谱/月之暗面等）官方定价常以 CNY 给出，需按可查汇率折算 USD（PBOC 中间价 + 日期留痕）。汇率查询优先用中国外汇交易中心 chinamoney.com.cn 官方源。
9. **positioning 受控词表**：`["旗舰", "中端", "轻量", "推理增强", "多模态", "工具调用增强"]` 六值枚举，越界标签（如"端侧"、"代码专用"、"开源权重"、"高推理深度预览"）会被门禁拒。映射规则：轻量高速→轻量；高性价比→中端；智能体系列/计算机使用/编码系列→工具调用增强；混合推理/前沿推理→推理增强。删除而非映射：纯场景描述（"专业工作"、"知识工作"）。
10. **非百分制跑分**：Elo / CFEval / Perplexity / Bits-per-char 等非 0-1 量纲的跑分，按红线置 score=null，原始值保留在 notes。Codeforces Elo=2386 / CFEval=2134 等不能直接进 self_reported.score。

### 8.3 跨平台协调

11. **批次大小 5 个为宜**：太小（1-2 个）认领表频繁更新开销大；太大（>10 个）单平台卡住影响整体进度。前 8 批次每波 4-6 个并发效果最好。
12. **同厂商同批次**：同一 vendor 的模型尽量在同批次，subagent 搜索结果可复用（如 Qwen 系列的技术报告 arxiv ID 一次找到多个模型通用）。
13. **认领后立即 push**：不要等所有 subagent 都完成才更新认领表，每波次完成立即 push，避免其他平台重复认领。
14. **占位记录合规**：模型实际不存在（如 gemini-3-0-flash-lite）仍要写一个占位记录（vendor + access + 占位 positioning + 其他全 null + meta.notes 标注），落盘 + 门禁通过 + 更新认领表。**不要留空**，否则合并阶段无法追踪。
15. **失败批次回退**：5 次未交卷的批次 status 改回 `pending` 而非 `failed`，让其他平台有机会接管。只有"模型命名在官方目录中不存在"这种确认无解的才标 `failed`。

---

## 9. 附录：环境差异速查

| 环境 | 命令前缀 | 路径分隔符 | 备注 |
|---|---|---|---|
| Windows PowerShell | `$env:PYTHONUTF8='1';` | `\` | GBK 控制台必须加 UTF8 前缀 |
| Windows cmd | `set PYTHONUTF8=1 &&` | `\` | 同上 |
| Linux/macOS | `export PYTHONUTF8=1;` | `/` | 无 GBK 问题，但加 UTF8 前缀也无害 |
| Git Bash (Windows) | `PYTHONUTF8=1` | `/` 或 `\`（混合） | 路径建议用 `/` |

Python 路径在脚本里用 raw string + 双反斜杠：`r'f:\project_temp\localAgent\workspace\model_data\...'`，跨平台脚本建议用 `os.path.join()` 或 `pathlib.Path`。

---

## 10. 附录：本指南的维护

- 本指南维护者：主 agent（你）
- 修改场景：发现新的 subagent 派发陷阱、红线补充、环境差异修正
- 修改原则：**只增不删**（除非确认某条已失效），所有修改在文末留痕
- 版本：v1（2026-08-26 首发，基于 Batch1-8 经验提炼）

---

**全文完。读完即可开工。祝采集顺利。**
