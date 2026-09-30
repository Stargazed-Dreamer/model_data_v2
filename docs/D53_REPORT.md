# D53 轮次报告：D 类 12 条真候选采集入库 + 私榜（atmeplz）对标分析

> 日期：2026-10-01。触发方式：用户（原话「这几个待条件全要。另外这里有一个私榜【https://atmeplz.github.io/ai-test-prompt/】，我认为可信度较高，请你**假设它是权威信源**，上面的模型都是最值得关注的热门前沿模型，和我们的数据对比一下，看看有多大的偏差。包括**收录情况和能力排行评分情况**。」）
> 记录数 **982 → 993（+11）**，门禁 **ERROR 0 / WARN 0**；qa_outliers 终态 **r1=0 / r2=0**，硬错为既有存量 `o1=4` / `c4=2`。
> 上轮：D52（2026-10-01）D51 三遗留清账 + S0 口径升级 + 体检器扩容（977 → 982）。本轮消费 D52 C1 反推出的 **D 类 12 条真候选**，并完成用户指定的**私榜对标**。

## 一、本轮工作集

| 组 | 内容 | 状态 |
|---|---|---|
| ① | D 类 **12 条真候选**采集入库（`b349w1`，**11 行 + 1 项不立行裁定**） | ✅ |
| ② | 私榜 `atmeplz.github.io/ai-test-prompt` 对标（收录对齐 + 能力排行偏差） | ✅ |

---

## 二、D 类 12 条：逐条裁定与落库

**来源**：D52 §五 C1 的「Arena 榜单全量反推 ⇒ 四分类」中的 **D 类真候选 12 条**（快照 2026-09-25，明细 `temp/d52/arena_gap_candidates.jsonl`）。本批落盘 `incoming/models/b349w1__*.jsonl`，**全部为新增行**（与主库零并存，故 merge 走 `add_record`）。

| # | model_id | 关键取值 | 身份/口径裁定 |
|---|---|---|---|
| 1 | `openai:gpt-5.3:base` | rd 2026-03-03 · ctx 128K · **$1.75/$14/$0.175** · elo text 1450/coding 1498/math 1431 · **已过期** | 「Chat / Instant」为**服务档后缀**，不进 `model_id`（沿用 `openai:gpt-5.2:base` 先例）；官方弃用页 2026-05-08 弃用、**2026-08-10 关停**（替代 `gpt-5.6-sol`） |
| 2 | `openai:gpt-5-pro:base` | rd 2025-08-07 · ctx 400K · **$15/$120**，batch $7.5/$60，cache 均 null · elo text 1435 · **已过期** | 官方标 Deprecated（计划退役 2026-12-11、API 仍可调）⇒ 按执行细则 §8 记「已过期」；定价 T1（官方域 CF 拦截，OR × modelpricing.ai **两源交叉一致**） |
| 3 | `baidu:ernie-5.0:base` | rd 2025-11-13 · **MoE 2.4T** · ctx 128K · **$0.89/$3.56**（¥ 刊例折算） · elo text 1449 | 命名**归一去 Preview 后缀**（沿用 D52 对 `ERNIE-5.1-Preview` 的先例）；定价 T0 官方定价页 |
| 4 | `zhipu:glm-5v-turbo:base` | rd 2026-04-02 · ctx 200K · **$0.7418/$3.2641/$0.178** · elo text 1433/coding 1488/math 1437 | 定价**跟库内主流走国内刊例折算**（国际 Z.ai $1.2/$4.0 留痕）；license `Proprietary`+`open_weights=false` ——**本批经 HF 官方组织直查确认**（见 §四.2） |
| 5 | `amazon:nova-2-lite:base` | rd 2025-12-02 · ctx **1M** · **$0.33/$2.75/$0.0825**，batch $0.165/$1.38 · elo text 1335/coding 1393/math 1332 | 取 **us-east-1 In-Region** 价（与库内 amazon 家族口径一致；global CRIS $0.30/$2.50 留痕）；GA 非 Preview |
| 6 | `stepfun:step-1o-turbo:base` | full_name `Step-1o Turbo Vision` · rd 2025-02-14 · ctx 32768 · **$0.3709/$1.1869/$0.0742** · elo text 1320 | 命名**不挂 `-vision`**（与库内 stepfun 主名口径一致、榜单提交名同形）；`sub_benchmark=text` 确认 |
| 7 | `reka:reka-core-20240904:base` | rd 2024-09 · ctx 128K · **$2/$6** · elo text 1288/coding 1316/math 1246 · **已过期** | **闭源**（Reka 开放权重始于 2025 年 Flash 3 系）；**已退役**（官方 Gateway 目录下架 + AA 明示 deprecated） |
| 8 | `reka:reka-flash-20240904:base` | rd 2024-10 · **21B Dense** · ctx 128K · **$0.8/$2** · elo text 1272/coding 1292/math 1232 · **已过期** | 同上；⚠ AA 另记 $0.20/$0.80（差 4×）→ 按「定价优先官方页」口径取官方值、冲突留痕 |
| 9 | `reka:reka-flash-21b-20240226:base` | rd 2024-02-26 · 21B Dense · ctx 128K · **$0.8/$2** · elo text 1227 · **已过期** | 首次立 **`reka` 厂商节点**（Reka AI） |
| 10 | ~~`reka:reka-flash-21b-20240226-online:base`~~ | **不立行** | 裁定为**同一模型的「联网检索 / 在线服务」配置**（服务档），非独立发布模型 ⇒ 只进 #9 的 `meta.notes` 防重（详见 §三） |
| 11 | `cohere:aya-vision-32b:base` | rd 2025-03-04 · **32B Dense** · ctx 16K · pricing 全 null · elo text 1267 | `open_weights=True`；license **CC-BY-NC 4.0（含 Cohere Labs 可接受使用政策）** |
| 12 | `cohere:aya-vision-8b:base` | rd 2025-03-04 · **8B Dense** · ctx 16K · pricing 全 null · elo text 1223 | 同上 |

**落库结果**：`scripts/model_data_tool.py merge`（dry-run 见计划 → `--apply`），**982 → 993**，11 条全部入库、`model_id` 零重复；全库门禁 **ERROR 0 / WARN 0**；体检器 **r1=0 / r2=0**。

---

## 三、`-online` 变体身份裁定（本批唯一「不立行」项）

**问题**：D52 反推线索中，Arena 榜上同时存在 `reka-flash-21b-20240226`（text r327 elo 1227）与 `reka-flash-21b-20240226-online`（r322 elo 1234），**两条各有独立 elo**。按项目「一行一个独立测量身份」口径，是否有独立 elo 即须立行？

**结论：不立行**。判据（口径来自 D51/D52）：

- D51 立行判据的**适用边界**是「**effort 档**（max/high/xhigh，改变模型行为）有独立 elo ⇒ 立行」；**服务档**（`-pro` / `:batch` / `-ultraspeed`，自述同一底层模型）⇒ 只进 `notes`。
- `-online` **不是 effort 档**，而是**同一底层模型的在线/检索服务配置**：

| 证据 | 内容 |
|---|---|
| ① LMSYS/LMArena 原始榜表（`leaderboard_table_20240422.csv`） | `-online` 行「知识截止」列写的是 **`Online`**（而非年月），且来源链指向 `docs.reka.ai/http-api.html#generation` |
| ② Reka 官方 HTTP API 文档（§四.1 已复核） | 联网是**同一模型 `reka-flash` 的请求级布尔参数**：逐字 `use_search_engine: Optional, boolean, whether to use a search engine.`；官方模型列表中**不存在** `-online` 独立 model id，**无独立定价 / 无独立 model card** |
| ③ 第三方独立源（explainx.ai） | 该条官网链同样指向 `docs.reka.ai/http-api.html#generation`，与 ① 吻合 |

⇒ 两种读法（「联网检索配置」或「API 托管版」）**同属服务档**，结论一致：**并入 #9 记录、只在 `meta.notes` 留痕双档 elo（base 327/1227 vs online 322/1234），不另立行、不写文件**。

---

## 四、本批复核中独立确认/修正的项

### 1. Reka 的 `use_search_engine`（官方域直读）

复核时官方旧文档页 `docs.reka.ai/http-api.html` 已 404（迁移），改取**同域版本化路径** `v0.docs.reka.ai/http-api.html` 直读成功，逐字确认 `use_search_engine` 参数存在、示例 `model_name: "reka-flash"` ⇒ §三 证据②成立。

### 2. `glm-5v-turbo` 的「无开放权重」经 HF 官方组织直查（**修正一条降级声明**）

采集 agent 当时 `curl huggingface.co` 返 **HTTP 000**，标注「HF 不可达、未能逐仓核验是否托管权重」，`open_weights=false` 系**推定**。本轮复核时该网络问题消失（000 系**代理未清**，`unset` 后正常）：

| 查询 | 结果 |
|---|---|
| `huggingface.co/api/models?search=GLM-5V-Turbo` / `5V-Turbo` / `glm-5v` | **均命中 0 个官方仓库**（仅一个无关第三方 `gatilin/GLM5ViT`） |
| 官方组织 `zai-org`（原 THUDM）GLM-5 系仓库 | 仅 `GLM-5` / `GLM-5.1` / `GLM-5.2` / `GLM-5.3`（+`-Flash`/`-BF16`/`-FP8`）与 `GLM-4.6V`、`GLM-4.1V-9B-Thinking`、`glm-edge-v-5b` 等 |

⇒ `open_weights=false` 与 license「无开放权重」**成立**；已把该结论作为**【后续独立复核】**追加进该条 `meta.notes`（原降级声明保留 + 注明「在本项上已可撤销」，符合留痕惯例）。

### 3. 格式与门禁级修正（3 类 4 处）

| 项 | 问题 | 处理 |
|---|---|---|
| `reka-core-20240904` / `reka-flash-20240904` | 有定价但缺 `pricing.effective_date`（门禁 **WARN 1**） | 官方页未标价生效日 ⇒ 按库内惯例（D47）取**采集核对日 2026-10-01**，与同厂商 `reka-flash-21b` 条目同口径 |
| `reka-flash-21b-20240226` | 基准名 `MT-bench` / `Perception-test` 与库内主流 `MT-Bench` / `Perception-Test` 构成「仅大小写异写」簇（引入 qa `r2` 回归 0→2） | 归一为 **`MT-Bench`**（库内 24 条一律大写 B）/ **`Perception-Test`**（同源同分的 `reka-core/-flash 20240904` 用此写法，同为 arXiv:2404.12387 Table 5） |

修正后复跑：门禁 **WARN 0**、体检器 **r2 归零**。

---

## 五、私榜对标分析（用户任务②）

> 完整分析见 `temp/d53/D53_私榜对标分析.md`；本节为正式结论。数据源：静态站真数据 `data/site.json`（68.9 KB，快照 `temp/d53/atmeplz_site.json`），站点版本 `EDITION/UPDATED 2026-09-11`。

### 5.0 站点口径（先摸清，再谈偏差）

- **7 题 × 4 方向**（TEXT / FRONTEND / BACKEND / KNOWLEDGE），**31 条完整测评 = 30 个基础模型**（同模型不同 `platform` 各算一条，`glm-5.3` 出现 2 次），满分 400，归一 `= 原始分 ÷ 该题冻结基准 × 100`（可 >100）。
- ⚠ **口径关键差异**：私榜测的是「**模型在某客户端/effort 档上的端到端工程产出**」（含前端页、后端 MES、体素建模），库内 `arena_elo` 是 **LMArena 人类偏好 elo** ⇒ 两者**测的不是同一件事**，偏差**不应解读为「谁错」**，而是「同一批模型在两套尺子下的相对位次是否稳定」。

### 5.1 收录对齐：30 个基础模型，库内**已收 23 个（76.7%）**

**未匹配 7 条，逐条裁定后**：

| 私榜名 | 裁定 | 依据 |
|---|---|---|
| `DSV4F0731` | 实为**已收录** | 即库内 `deepseek:deepseek-v4-flash:0731`（DSV4F = 缩写），脚本因缩写未命中 |
| `DSV4F-VE-ocgo` | **同族已有** | 库内有 `deepseek:deepseek-v4-flash-vision-exp:base`；`ocgo` = opencode 平台档 |
| `gpt-5.6-sol-0829` | **待核** | 库内有 `gpt-5.6-sol-max`/`-none`（rd 2026-07-09），无 0829 版 |
| `seed-2.1-pro` | **同族变体未采** | 库内有 `bytedance:seed-2.1-turbo:base`，无 pro |
| `gpt-5.6-cyber` | **同族变体未采** | 库内 gpt-5.6 仅 luna/sol/terra 三支，无 cyber |
| `ox-alpha` / `omen-alpha` | **匿名实验模型**（`vendor=stealth`） | 无厂商归属，库内 0 条 stealth 记录 ⇒ **本就不在采集口径内** |

⇒ **真实收录缺口仅 2–3 条**（`gpt-5.6-cyber`、`seed-2.1-pro`，外加热门度更高的待核项 `gpt-5.6-sol-0829`）。

### 5.2 能力排行偏差：**方向高度一致（ρ=+0.77）**，位次抖动小

可比样本 = 私榜 30 个模型中库内**同时有 LMArena `text` elo** 的 **14 个**（46.7%）：

| 私榜# | elo# | ΔR | 模型 | 私榜 total | 库内 text elo |
|---:|---:|---:|---|---:|---:|
| 1 | 1 | 0 | claude-fable-5 | 381.7 | 1508 |
| 2 | 3 | +1 | claude-opus-5 | 378.3 | 1493 |
| 3 | 6 | +3 | glm-5.3 | 351.0 | 1480 |
| 4 | 9 | **+5** | glm-5.3-flash | 334.1 | 1474 |
| 5 | 4 | −1 | gemini-3.7-flash | 321.6 | 1491 |
| 6 | 7 | +1 | qwen3.8-max | 319.2 | 1480 |
| 7 | 5 | −2 | gpt-5.6-sol-0829 | 319.0 | 1481 |
| 8 | 2 | **−6** | muse-spark-1.2-contributor | 313.3 | 1498 |
| 9 | 13 | +4 | DSV4F0731 | 311.0 | 1436 |
| 10 | 10 | 0 | grok-4.6 | 308.8 | 1461 |
| 11 | 8 | −3 | gemini-3.6-flash | 280.5 | 1480 |
| 12 | 12 | 0 | minimax-m3-thinking | 279.8 | 1443 |
| 13 | 11 | −2 | hy3 | 237.5 | 1455 |
| 14 | 14 | 0 | gpt-4o | 83.3 | 1346 |

- 私榜 `total` 排名 vs LMArena `text` elo：**Spearman ρ = +0.767**
- 私榜 `text 方向分` vs LMArena `text` elo（**同测文字能力**，理论更可比）：**ρ = +0.653**

**读法**：方向**完全一致**（14 个无一处符号反转）；**11/14 位移 ≤3 位**、最大 6 位。两处结构性差异来自**尺子差异**而非数据错误：

1. `muse-spark-1.2-contributor` 私榜 #8 / elo #2（**私榜低估 6 位**）—— 与 D52 B2 结论呼应：私榜可能测的是**不同档位**；
2. `glm-5.3-flash` 私榜 #4 / elo #9（**私榜高估 5 位**）—— 私榜**工程题（前端/后端）权重高**，该模型后端分 81.0 高于其纯文字位次。

### 5.3 厂商覆盖：私榜 17 个 vendor，库内**已有 16 个节点**

计数按 `model_id` 前缀（`dots` 特例 `dots-studio`，基线 993 条）：alibaba 104 / openai 75 / google 73 / anthropic 48 / deepseek 40 / meta 34 / xai 21 / zhipu 17 / tencent 15 / bytedance 13 / moonshot 12 / minimax 10 / sensetime 5 / cursor 4 / dots 1 / thinking-machines 1，**`stealth` 0（匿名，非采）**。⇒ 私榜厂商面**完全被库内覆盖**。

### 5.4 结论（一句话版）

1. **收录高度对齐**：实收 **23/30 = 76.7%**；未收 7 条中 2 条为匿名代号（非采）、2 条经识别实为已收（缩写/同族），**真缺口仅 2–3 条**。
2. **排行偏差小且同向**：ρ=+0.77（同测文字能力 ρ=+0.65），11/14 位移 ≤3 位 ⇒ 两套尺子判断一致。
3. **偏差集中在「工程题 vs 偏好 elo」的口径差**：后端强的被抬高、纯对话强的被压低，属尺子差异。
4. **库内短板被照出**：私榜 30 个模型我们只有 14 个（46.7%）有 elo；**全库 elo 覆盖率仅 256/993 = 25.8%**（`arena_elo` 共 740 条：text 256 / coding 245 / math 234 / webdev 4 / vision 1）。私榜可作**「该补榜数据」的外部 drive 清单**。

> **口径提醒**：私榜按 `platform × effort` 拆条，属**第三方评测分档**，**不构成立行依据**（非官方发布），最多作 `notes` 留痕；其又未公开每题原始分与冻结基准的样本定义，**不可反向提升为本库的 T0**。

---

## 六、本轮新发现 / 待议项

1. **门禁盲点（新）**：`scripts/validate_model_data.py` **不校验** `benchmarks.arena_elo[].sub_benchmark` 的**枚举值**。实测把 `sub_benchmark` 写成 `"LMArena text"`（非枚举内的 `text`）仍回 **ERROR 0**（本批 aya-vision 两处即靠人工复核 + 自建抽查脚本才发现，已改正）。建议下轮把该枚举纳入门禁。
2. **`open_weights` 核验依赖网络可达（新）**：本批 `glm-5v-turbo` 的 HF 不可达系**代理未清**所致的**假阴性**（HTTP 000）。建议把「核验 HF 权重前先 `unset HTTP_PROXY HTTPS_PROXY` 并自证 curl 返回码」写进采集提示词，避免把假阴性写成降级声明。
3. **`gpt-5-pro` 的 `verification_status` 口径偏严（存疑留痕）**：官方仅标 **Deprecated（计划退役 2026-12-11）**、API 仍可调用，按执行细则 §8 记「已过期」。若项目希望把「仅弃用未退役」单列，需新增枚举，本轮不动。

---

## 七、收尾

- 合并前手动备份 `backups/model_data_v2.d53pre.<ts>.jsonl`；`--apply` 时工具亦自动备份。
- 收尾同步：`CHANGELOG.md` 追加 `## [D53] - 2026-10-01`；本报告落 `docs/D53_REPORT.md`。
- 采集产物 `incoming/models/b349w1__*.jsonl` 以 `git add -f` 入库（`.gitignore:32` 整类排除 `/incoming/models/*.jsonl`）。
