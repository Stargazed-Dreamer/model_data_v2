# D59 报告 · 增量更新（S0 双轨扫描 + S1 拍板 + S2 采 15 条）

> **轮次**：D59 ｜ **日期**：2026-11-11
> **触发**：用户「`F:\project_temp\localAgent\workspace\model_data` 看一下更新最新的模型情况」（Qoder 会话 `29afb6cb` 05:20）
> **接手**：Qoder 06:32 报错 145 断在 **S2 准备阶段**；WorkBuddy 按 `qoder-takeover` skill 导包接手，补跑 S2→S5（本报告 §1）
> **基线**：主库 **1028 条** / 门禁 **ERROR 0 / WARN 0** / `independent` 2197（D58 收官）
> **结果**：**1028 → 1043（+15）**；门禁 **ERROR 0 / WARN 0**；`r1=0 / r2=0`；丙类 4 条字段更新已落库；批次 `b353w1`
> **窗口**：2026-10-31 → 2026-11-11（主库 max release_date 10-27 / max collected_at 10-31）

---

## 0. 一句话结论

用户前两轮 `AskUserQuestion` 已把范围定死为**「采 15 条 + 丙类 4 条字段更新，四条全落、边界项都不要、preview→正式版按官方是否同 checkpoint 逐个判」**；
Qoder 完成 S0（29 条候选）、S1 拍板、丙类 4 条落库后断在 S2 门口，本会话接手把 **15 条完整 schema 1.1 记录**产出并合并，主库 +15 行、门禁与重复硬基线全部守住。
两条 preview→GA 判定均为**立独立行**；`LongCat-2.5 GA` 因发布日三口径冲突留 `null`，是本轮唯一新增的 `o1` 硬错，属知情保留。

---

## 1. 接手背景（断在哪、接了什么）

| 项 | 值 |
|---|---|
| 原会话 | `29afb6cb-c44b-4a12-91fa-da323e827973`（QoderCN，`F--project-temp-localAgent`） |
| 断点 | 2026-11-11 06:32，`The request could not be completed. Please try again.`（报错 `145`×1） |
| 断点前最后一句 | 「丙类落库完成：**1028 / ERROR 0 / WARN 0**，git diff 恰好 4 增 4 删。现在准备 S2，先查批次号、厂商前缀与那两条待判身份的记录。」 |
| 断点前已做 | 查明 `Next batch = b353w1 / round D59`、厂商前缀（`ricursive`/`moondream` 为 0 条新厂商）、Anthropic 命名惯例、`_m_context.md` 与样板、`prompt.md` model_id 规则 |
| 断点前**未做** | 无任何 S2 产物（`incoming/models/` 里没有 `b353w1__*`），未写台账、未派 subagent |
| 接手包 | `F:\project_temp\localAgent\temp\qoder_takeover\2026-11-11\29afb6cb\`（HANDOFF / tail_full / chat_full / source.jsonl / PROMPT） |

**没有遗留待拍板的问题**：S1 四问全部由用户在 06:20 / 06:21 答完（见下表），所以按「直接接着做」执行，未重新采访用户。

| 拍板点 | 用户选择 | 落到的结果 |
|---|---|---|
| ①采哪些 | 甲+乙 全采 18 条（推荐） | 与 ③ 相交后 16 条 |
| ②丙类 4 条 | 四条全落（推荐） | Qoder 已落库 |
| ③边界项勾选 | **都不要** | 剔除 Particle-1 / Recursive Flint / PrismML Ternary Bonsai |
| ④preview→正式版口径 | **按官方是否同 checkpoint 逐个判**（推荐） | Hy4 GA、LongCat-2.5 GA 逐个判定（§3.2） |
| 追加一轮（Elorian Glimpse） | 否 | 16 → **15 条** |

> 与既有判例对齐：D52 的 `b348w1` 早就把 `prism-ml:ternary-bonsai-2-27b` 判为「非范围未立行」，本轮「都不要」不是新口径。

---

## 2. S0 盘点（Qoder 已完成，本会话复用）

窗口 **10-31 → 11-11**，双轨：

- **S0-a 差集**：OpenRouter 469 模型，窗口内新上架 23 项 → 候选 15；
- **S0-b 榜单全量反推**（必做）：Arena 11-08 快照，`real_gap 52 / naming_diff 129`，逐条人工复核；
- **上轮遗留与承诺兑现复查**：`moonshotai/Kimi-K3.1-Pro` 96 个 safetensors、`stepfun-ai/Step-5-Preview` 28 个，两条承诺兑现。

产物 `temp/d59/d59_s0_candidates.jsonl` **29 条**，分四类：甲 7（本轮新发布）/ 乙 11（上轮漏采）/ 丙 4（只改字段不立行）/ 丁 7（剔除或退回观察）。
`candidate_diff` 对甲乙 18 条判定 NEW 8 / CHECK_VARIANT 9 / EXISTS 1。

**两条只有「非差集」路径才捞得到**（D52 立规的直接收益）：

| 模型 | 为什么差集捞不到 | 怎么捞到的 |
|---|---|---|
| **Gemini 4 Carbon** | 发布 10-28，早于上轮 10-31 截止 | Arena 文本榜 **#1 / elo 1527**；反推工具把它误归入 naming_diff（错配 `gemini-4-argon`），人工翻前 60 条提出 |
| **LongCat-2.0** | 6-30 发布、OR 7-20 就上架，不落在任何近轮差集窗口 | D38 已查证存在却一直没采，本轮由榜单全量反推照出 |

**两条退回观察**（防止把基座规格安到变体头上）：`ERNIE-5.5-Flash-Preview`（官方 release 页只列 Base，HF baidu 组织也只有 Base + Base-BF16；OR 的「280B」疑抄自 Base）、`Nex-N2.6`（仅 orcarouter 博客侧栏一处 T3，HF 搜索 No results，「321B」只能追到基座 GLM-5.3-Flash）。

**两家名字易撞已分清**：`Ricursive Intelligence`（ricursive**.com**，Ripple-65B，65B dense）≠ `Recursive`（Recursive Flint，40B/2.5B MoE，Richard Socher）；`Particle AI`（particle.ai）≠ Particle.news。

---

## 3. S2 采集（本会话补跑）

### 3.1 15 条清单

批次 **`b353w1`**（`docs/batch_claim_ledger.jsonl` 355 → 356 条），产物落 `incoming/models/b353w1__<vendor>__<model>__<variant>.jsonl`。
15 个 `model_id` 合并前逐一验过，**与主库零撞键**；merge dry-run = `add_record=15`，无覆盖、无冲突。

| # | model_id | 厂商 | release_date | 定级 | 关键判定 |
|---|---|---|---|---|---|
| 1 | `anthropic:claude-fable-5.2:base` | Anthropic | 2026-11-09 | T0 | 官方新闻稿 $8/$40（较 5.1 降 20%），OR 独立条目 |
| 2 | `anthropic:claude-mythos-5.2:base` | Anthropic | 2026-11-09 | T0 / 定价 T3 | 与 Fable 5.2 同底层、仅安全限制不同；**按库内 mythos-5.1 独立行先例立行**；不在 OR，靠 news 台账补漏 |
| 3 | `tencent:hunyuan-hy4:base` | Tencent | 2026-11-04 | T0 | **不同 checkpoint → 立行**；GA 权重未放出 ⇒ `open_weights=false`，不照抄 preview 的 Apache-2.0 |
| 4 | `meta:muse-ember:base` | Meta | 2026-11-09 | T2/T3 | Meta 全域 000 不可达，走中文转述 + OR 交叉；「11-10」是报道日不是发布日 |
| 5 | `ricursive:ripple-65b-preview:base` | Ricursive Intelligence | 2026-11-04 | T0 | **新厂商首条**；HF API 200 / 16 safetensors / apache-2.0 / 65B Dense Transformer |
| 6 | `baidu:ernie-5.5-flash-base:base` | Baidu | 2026-11-05 | T0 | **台账补漏**（OR 只有 Preview，Base 才是开放权重那个）；280B/14B、43 层、33.5T tokens |
| 7 | `meituan:longcat-2.5:base` | Meituan | **null**（待二查） | T0 | **立独立行**；HF GA 权重仓 11-04；三口径冲突按铁律不硬填 |
| 8 | `google:gemini-4-carbon:base` | Google | 2026-10-28 | T1 | 官方「complements rather than replaces Argon」⇒ 与 argon **同代并列档**，非后继 |
| 9 | `liquid:lfm3-1.7b:base` | Liquid AI | 2026-10-27 | T0 | 1.73B / 256K / tri-hybrid 24 层；⚠ 架构不是 CfC；本轮只采文本版 |
| 10 | `zhipu:glm-5.3-flashx-legal:base` | Zhipu AI | 2026-10-12（待二查） | T0 | 法律域后训练变体、独立 model code；母体 FlashX 是速度档**不立行** |
| 11 | `iflytek:spark-x2.6:base` | iFlytek | 2026-10-22 | T0 | 采云端版 293B-A30B；4B 开源版 / Preview 版留痕不立行 |
| 12 | `huawei:openpangu-2.0-pro:base` | Huawei | 2026-07-31 | T0 | 505B/18B、512K、MLA+DSA+SWA；与 Flash **分立两行** |
| 13 | `huawei:openpangu-2.0-flash:base` | Huawei | 2026-06-30 | T0 | 92B/6B；独立 HF 仓 + 独立参数档 ⇒ 独立测量身份 |
| 14 | `meituan:longcat-2.0:base` | Meituan | 2026-06-30 | T0 | D38 查证却漏采至今；1.6T/48B、MIT、$0.30/$1.20；⛔ 未照抄 D38 无法复现的「ScMoE + 零计算专家」 |
| 15 | `moondream:moondream-3.1:base` | Moondream | **2026-07-07**（本轮修正） | T0 | **新厂商首条**；原以为 10 月，OR 10-15 只是上架日 ⇒ 属 7 月缺口 |

### 3.2 两条 preview→GA 的 checkpoint 判定（用户拍板点④）

| 模型 | 判定 | 依据 |
|---|---|---|
| **Hy4 GA** | **立独立行** | ①OR 独立条目 `tencent/hy4`（created 11-04）与 `tencent/hy4-preview` 并存，描述原文「official release ... comprehensive and substantial improvements over Hy4 Preview」；②官方独立发布页；③preview 开放权重而 GA 权重未放出。三者共同指向不同 checkpoint，非同一模型服务档 |
| **LongCat-2.5 GA** | **立独立行**（留痕待复核） | ①HF 独立 GA 权重仓（createdAt 11-04）+ `-W4A4`；②OR 无 GA 条目，排除服务档；③preview 行明确 `open_weights=false` 且 notes 写「承诺另行开源」⇒ 权重兑现是实质产物差异。⚠ 官方**未逐字声明**是否同 checkpoint，按「独立权重仓 + 独立许可口径」立行并在 `meta.notes` 留痕；若官方明确同 checkpoint，应合并回 preview 行并归零 `r1/r2` |

### 3.3 执行方式与证据口径（与标准 S2 的差异，如实记录）

标准 S2 是「每模型派一个 subagent、并发 ≤3」。本轮**由接手会话集中生成**（脚本 `temp/d59/apply_d59_s2.py`），原因：

- S0 阶段三路 subagent 已把一手证据**全部本地化**到 `temp/d59/`（约 50 个官方页 / HF API 回显 / `or_verify.json` 469 模型快照），不需要重新联网「研究」；
- 集中生成可让每条记录的每个字段都挂到明确出处，便于逐条跑门禁与事后审计；
- 产物仍严格按 S2 的目录、命名（`b353w1__*`）、schema 1.1 与单文件门禁口径，台账 `notes` 里也已写明这一差异。

**红线执行**：

| 红线 | 本轮做法 |
|---|---|
| 没查到 = `null` | 参数量、许可、max_output、knowledge_cutoff、待二查发布日一律 `null`；不用 `false`/`0`/`""` 冒充 |
| 不伪造 T0 | Meta 全域 000 ⇒ Muse Ember 标 T2/T3；Gemini 4 Carbon 官方域不可达 ⇒ 日期标 T1；Mythos 5.2 沿用推定价标 **T3** |
| **OR 转售价不冒充官方刊例价** | 15 条里 **9 条定价六键 + `currency` 全 `null`**，OR 挂牌数值只写进 `pricing.notes` 留痕；仅 Fable 5.2 / LongCat-2.0 有官方一手价填 T0，Muse Ember / Mythos 5.2 / Gemini 4 Carbon 按媒体转述或交叉印证填 T3/T1 |
| 日期铁律 | OR `created` / HF `createdAt` 一律不当发布日；LongCat-2.0 取新华网 06-30（HF 07-05 / 开源公告 07-12 / OR 07-20 均留痕）；LongCat-2.5 GA 三口径冲突 ⇒ `null` |
| 参数量未披露须声明 | 所有 `total/active` 为 `null` 的记录，`architecture.notes` 统一含「官方未披露参数量」（门禁规则 1） |
| 不照抄兄弟条目 | D38 的旧架构措辞、preview 的许可/定价/模态、母体的 320B-A18B 规格，均未移植到新行 |

### 3.4 丙类 4 条（Qoder 已落库，本会话验收）

`zhipu:glm-5.3-flash:base`（补 FlashX 防重，升级为 T0 官方 Model Code 依据）、`stepfun:step-5-preview:base`（权重兑现；许可文件实为 `LICENSE.txt` 而非 `LICENSE`；**`release_date` 继续留 null**）、`openai:gpt-6.1-terra:base`（terra-pro 服务档防重）、`moonshot:kimi-k3.1-pro:base`（权重兑现）。
落库后 1028 条 / ERROR 0 / WARN 0，`git diff` 恰好 4 增 4 删；本会话合并后再次逐字节比对确认这 4 条是**唯一**发生变化的既有行。

---

## 4. S3 / S4 验收数字

| 检查 | 结果 |
|---|---|
| 单文件门禁（15 个 `b353w1__*`） | **15/15 ERROR 0 / WARN 0**（一次通过） |
| 合并计划 | dry-run `add_record=15`，无覆盖 / 无撞键 |
| 合并后全库门禁 | **1043 条 / ERROR 0 / WARN 0**（基线 1028 / 0 / 0） |
| 既有行未动取证 | 与 `git show HEAD:model_data_v2.jsonl` 逐条比对：**1024 行逐字节未动**；变化的 4 条恰为丙类字段更新；新增 15 条 |
| 数组缩水取证 | 既有 1028 行 `benchmarks` 三数组长度变化 **0 条** |
| `qa_outliers.py`（31 项） | **`r1=0 / r2=0`**（硬基线守住）；`o2/o4/o5/o6/c1/c2/c3/c6 = 0` |
| 硬错变化 | `o1 9→10`、`c4 2→2`，合计 **11→12**；+1 全部来自本轮新入库的 `meituan:longcat-2.5:base`（发布日待二查留 `null`），**既有 1028 条无一条新增硬错** |
| `candidate_diff` 复跑 18 条甲乙候选 | **NEW 3**（恰为用户剔除的 Particle-1 / Recursive Flint / Elorian Glimpse）、**EXISTS 14**、**CHECK_VARIANT 1** |
| 台账 | `b353w1` 已登记，355 → 356 条，`submitted_files` 15 个 |

⚠ `CHECK_VARIANT 1` = `Hy4 (正式版 GA)`，工具按名模糊匹配到 `tencent:hunyuan-hy4-preview:base`（overlap 0.5），**不是漏采**：本轮已立 `tencent:hunyuan-hy4:base`。与 D38 的 `Qwen3.8 Flash` 判 EXISTS 属同类按名误判，凡「同家族不同档位/版本」的结论必须人工复核。

**关于 `o1` +1**：工作流 §5 的判读规则要求「硬错总数不增 / 新增命中都属新入库记录」。本轮 `o1` 从 9 到 10，唯一新增即 `LongCat-2.5 GA`；备选做法是硬填一个发布日让数字不变，但三个候选日期（11-02 发布 / 11-04 HF createdAt / 11-10 开源）互相冲突，按「OR created / HF createdAt 不是发布日」铁律与「查不到不硬填」红线，**留 `null` 是正确处置**。库内已有 9 条同性质存量（均为官方未公告发布日），此处如实记账不掩饰。

---

## 5. 文档修订（S0 结论写回 + 一处复验驳回）

| 文件 | 改动 |
|---|---|
| `docs/增量更新工作流.md` 第 182 行 | Wave-1 遗留里「`Claude Mythos 5.1`（P1 NEW）未入库」**已过时**（库内实有 `anthropic:claude-mythos-5.1:base`，rd=2026-09）⇒ 保留历史原文并加 D59 更正注，不再作为待办 |
| `docs/跟踪源清单.md` B2 表 + 新增 D59 复测段 | ①腾讯混元官网 **200 但只回 6,893 B SPA 壳**（`pg_010aa44a.html` / `hy_sitemap.xml` / `tx_33cd9a.html` 三个不同 URL 同壳）⇒ 不能当台账定 T0，Hy4 GA 发布日改走官方发布页；②新增 `www.minimax.cn/news`（55,228 B 带正文）替代 404 的 `platform.minimaxi.com/document/`；③新增 `docs.bigmodel.cn/sitemap.xml`（38,222 B 真 `urlset`）补 Zhipu 更新日志子页枚举空白；④Anthropic `anthropic.com/news` 本轮 200 且正文完整（含 11-09 Fable/Mythos 5.2 官方稿），可直读定 T0 |

**★ 复验驳回一条**：S0 结论里「`docs.anthropic.com/en/release-notes/api` 从 200 退化为地区封锁跳转」**未写回**。
理由：`temp/d59/` 中找不到该 URL 的对应快照；`anthropic_news.html` 里 28 处 `region` 全是 HTML `role="region"` 属性，`country` 3 处，无任何「not available in your region」类文案，页面 title = `Newsroom \ Anthropic` 且正文完整。
⇒ 该结论无法复验，表格第 99 行状态**保持原样**，文档里记「下轮 S0 前单独复测一次再定」。接手方不把没有快照的观测当事实写进常驻文档。

---

## 6. 产物清单

| 类型 | 路径 | 说明 |
|---|---|---|
| 主库 | `model_data_v2.jsonl` | 1028 → **1043** |
| 采集产物 | `incoming/models/b353w1__*.jsonl` | 15 个，各 1 条完整 schema 1.1；`.gitignore:32` 默认忽略，按历史 474 个产物的惯例 `git add -f` 入库（台账 `submitted_files` 引用了这些路径） |
| 生成器 | `scripts/d59_s2_build.py` | 15 条事实表 → 记录 + 台账登记（可重跑覆盖）；按 `scripts/dNN_*.py` 轮次脚本惯例**随仓库入库**，避免脚本随 `temp/` 清理丢失。原始副本在 `temp/d59/apply_d59_s2.py`（不入库） |
| 台账 | `docs/batch_claim_ledger.jsonl` | `b353w1`，355 → 356 |
| 报告 | `docs/D59_REPORT.md` | 本文件 |
| 文档 | `docs/跟踪源清单.md` / `docs/增量更新工作流.md` | §5 四项修订 |
| S0 材料（未入库） | `temp/d59/` | 29 条候选、Arena 反推、469 模型 OR 快照、官方页/HF API 回显、`apply_bing.py` / `verify_bing.py` |
| 质检报告 | `temp/d59/outliers_report.txt` | `qa_outliers.py` 31 项结果 |
| 接手包 | `F:\project_temp\localAgent\temp\qoder_takeover\2026-11-11\29afb6cb\` | Qoder 原会话全量导出 |

---

## 7. 复核命令

```bash
cd "F:/project_temp/localAgent/workspace/model_data"

# 1) 单文件门禁（15/15 应全部 ERROR 0 / WARN 0）
for f in incoming/models/b353w1__*.jsonl; do PYTHONUTF8=1 python scripts/validate_model_data.py "$f" | tail -1; done

# 2) 全库门禁（1043 条 / ERROR 0 / WARN 0）
PYTHONUTF8=1 python scripts/validate_model_data.py model_data_v2.jsonl

# 3) 合并计划重放（应为 add_record=15，DRY-RUN 不改文件）
PYTHONUTF8=1 python scripts/model_data_tool.py merge --file model_data_v2.jsonl \
  --incoming incoming/models/b353w1__*.jsonl \
  --on-null take_source --on-both source_wins --on-array replace \
  --on-schema upgrade --tie-breaker keep_target

# 4) 31 项体检（r1/r2 必须 0）
PYTHONUTF8=1 python scripts/qa_outliers.py --out temp/d59/outliers_report.txt

# 5) 候选复跑（NEW 应只剩 3 条已剔除项）
PYTHONUTF8=1 python scripts/candidate_diff.py temp/d59/d59_wave1_diff_input.jsonl
```

> 注：3) 在当前已合并的主库上重放会报 `on_both` 覆盖计划，只看重放前的 dry-run 输出即可；要完全复现请先把主库回退到 `git show HEAD:model_data_v2.jsonl`（但那样会丢掉丙类 4 条已落库改动）。

---

## 8. 遗留 / 待二查（本轮未闭环，不掩饰）

1. **`meituan:longcat-2.5:base` 发布日**：11-02 发布 / 11-04 HF createdAt / 11-10 开源三口径冲突 ⇒ `release_date=null`，是当前唯一新增 `o1`；官方给准日后可直接补，硬错即归零。
2. **`zhipu:glm-5.3-flashx-legal:base` 发布日 10-12**：出自 `z.ai/blog/assets/glm-legal-C520yt-y.js`（200），另一路核查未复现 ⇒ 待二查；开放权重口径亦冲突（HF zai-org 无 Legal 仓 / Vals AI 标 open-weight），故 `open_weights=null`。
3. **`iflytek:spark-x2.6:base` 定价**：二手一致「限时 输入 0.9 / 缓存命中 0.08 / 输出 3.6 元每 M」，官方 MaaS 页 JS 壳未取证 ⇒ 六价键全 null；且为 CNY，需可查汇率才能折算。
4. **Anthropic `release-notes/api` 地区封锁退化**：§5 已说明未复验，下轮 S0 前单独复测。
5. **丁类未闭环**：`ERNIE-Light-DT-1.0-intl`（OR 单处、基座版本/参数全未查到）、`ERNIE-5.5-Flash-Preview` 与 `Nex-N2.6`（退回观察）、`PrismML Ternary Bonsai` 系（按用户「都不要」剔除，与 D52 判例一致）。
6. **Meta / Google 官方域不可达**：Muse Ember（T2/T3）、Gemini 4 Carbon（T1）的规格与定价均非 T0 直读，官方域恢复后应重采升级定级。
7. **Hy4 GA 权重放出后**：需重采 `access` / `license`，并重新裁定是否与 preview 合并。
