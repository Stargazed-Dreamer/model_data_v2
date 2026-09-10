# D39 报告 · arena 跑分补全与榜单反推漏采线索

生成于 2026-09-10。主库仍 **915 条**，门禁 **ERROR 0 / WARN 0**。本轮主目标是用户指出的"arena 是最大的一块低垂果实"。

---

## 1. 结论摘要

| 指标 | D39 前 | D39 后 | 变化 |
|---|---|---|---|
| 有 `arena_elo` 的记录 | 172（19.1%） | **215（23.5%）** | +43 |
| `arena_elo` 条目数 | 513 | **809** | +296 |
| 其中此前**完全没有** arena 的记录 | — | **43 条** | 新增覆盖 |
| `independent` | 340（37.2%） | 340（37.2%） | 本轮未动 |
| 完全无任何跑分 | 238（26.0%） | **232（25.4%）** | −6 |

一句话：**arena 覆盖率提升 4.4 个百分点，43 个模型从零到有；同时意外挖出 84 条疑似漏采模型**。

---

## 2. 数据源：DataLearner 镜像的 LM Arena 榜单

lmarena.ai（一手）在本机 **HTTP 000 不可达**，故沿用库内既有做法走 DataLearner 镜像。

| 榜单 | 路径 | 条数 |
|---|---|---|
| text | `/leaderboards/external/text-generation` | 400 |
| coding | `/leaderboards/external/text-generation-coding` | 395 |
| math | `/leaderboards/external/text-generation-math` | 383 |

- 快照：三榜统一 `versionTime = 2026-09-02`，text 榜总票数 1,162 万。
- 抓取要点已固化进 `docs/跟踪源清单.md` §C-1（主榜有 JSON API，端点藏在页面 ld+json 的 `contentUrl`；分类榜无 API，走 Next.js flight 流）。

---

## 3. 补入逻辑（保守优先，宁缺勿错）

**变体口径**：主库 model_id 无 `thinking/think/reasoning` 标记 ⇒ 只取榜单「无变体标记」条目；有标记才取 `(thinking)/(high)/(xhigh)` 条目。

**三道过滤**（歧义一律跳过，不猜）：

| 过滤 | 触发条件 | 跳过 | 举例 |
|---|---|---|---|
| 榜单重名 | 同类别下有多条同名「无变体标记」条目 | 33 | `Claude 3.5 Sonnet` 同榜 1374 / 1343 两条 |
| 版本差异 | 同一榜单条目被多个主库记录引用且非仅上下文差异 | 63 | `GPT-4` 被 0314/0613/1106/0125 四个快照共用；共用分数等同伪造 |
| ✅ 放行：仅上下文差异 | 去掉 `-32k/-64k` 后完全相同 | 6 | `claude-opus-4-6-32k` 与 `-64k` 同模型不同窗口 |

**追加而非覆盖**：沿用库内先例（`alibaba:qwen-3-8-max` 已有两个旧快照），同 `sub_benchmark` 保留多快照序列，靠 `date` 区分。

> ⚠ **待决策**：条目数 513 → 809。若认为历史快照冗余，可另起一轮做快照瘦身（只保留每模型每 sub_benchmark 最新一条）。

---

## 4. 榜单反推的漏采线索（本轮最有价值的副产品）

榜单 236 条未被主库命中 → **84 条疑似真漏采**（另 152 条疑似"库内已有但命名不同"，但 difflib 模糊判定不可尽信，例如 `Claude Opus 5` 被错配到 `claude-opus-4-5-...`，已标注 `similar_in_db` 供人工复核）。

**高价值漏采（按 text 榜名次）**：

| 名次 | 模型 | 厂商 | Elo |
|---|---|---|---|
| 26 | GPT-5.2 Chat | OpenAI | 1476 |
| 31 | GPT-5.5 Instant | OpenAI | 1474 |
| 32 | Qwen3.7-Max-Preview | Alibaba | 1474 |
| 34 | Opus 4.5 | Anthropic | 1473 |
| 42 | ERNIE-5.1-Preview | Baidu | 1468 |
| 45 | Qwen3.5 Max Preview | Alibaba | 1466 |
| 47 | Grok 4.1 Thinking | xAI | 1465 |
| 51 | Qwen3.6-Max-Preview | Alibaba | 1460 |
| 59 | DOLA Seed 2.0 Pro | ByteDance Seed Team | 1456 |
| 69 | GPT-5.3 Chat | OpenAI | 1449 |
| 70 | ERNIE 5.0 Preview | Baidu | 1449 |
| 95 | GLM-5V-Turbo | Zhipu | 1433 |
| 98 | Kimi K2.5 Instant | Moonshot | 1431 |
| 152 | hunyuan-vision-1.5-thinking | Tencent | 1395 |
| 157 | mimo-v2-flash | Xiaomi | 1392 |
| — | amazon-nova-experimental-chat-26-02-10 等 3 条 | Amazon | — |

已转成 S0 格式：**`temp/d40_wave1_candidates.jsonl`**（84 条），S1 分档结果 **NEW 59 / CHECK_VARIANT 11 / EXISTS 14**。

> ⚠ **不可直接采**：榜单含匿名 / 实验版代号（如 `amazon-nova-experimental-chat-26-02-10`、`GPT-5-Pro`），且老社区模型（`vicuna-13b` / `alpaca-13b` / `oasst-pythia-12b` / `GPT4All 13B` 等）虽在榜且主库无，但**未必符合本库"主流大模型"收录口径**——须过 S0/S1 核实并人工筛除。

---

## 5. 未解决 / 待决策

| # | 事项 | 说明 |
|---|---|---|
| 1 | arena 快照瘦身 | 条目 513 → 809，是否只保留每 sub_benchmark 最新快照 |
| 2 | `independent` 补分仍停在 37.2% | 覆盖最差：IBM 13% / Microsoft 13% / Google 17% / NVIDIA 28%；Artificial Analysis API 需 key（401），OpenCompass 待验证 |
| 3 | D40 候选 84 条需人工筛 | 榜单代号 + 老社区模型不宜直接采 |
| 4 | 图像/视频榜未采 | 已探到 4 个路径（image-edit / text-to-image / image-to-video / video-generation） |

---

## 6. 本轮脚本与数据留档

| 文件 | 用途 |
|---|---|
| **`scripts/d39_fetch_arena_leaderboard.py`** | **生产脚本①：抓取三榜 → `temp/d39_arena_raw.json`**（固化自 temp，避免 temp 清理后丢失） |
| **`scripts/d39_import_arena_elo.py`** | **生产脚本②：导入主库**（含三道过滤；`--apply` 才写库；**幂等**，重跑写入 0 条） |
| `temp/d39_dl_tables.py` | 从 HTML flight 流提取 `"data"` 表的独立工具（调试用） |
| `temp/d39_arena_match_probe.py` / `d39_arena_match2.py` | 主库 ↔ 榜单匹配探针（v1/v2，调试用） |
| `temp/d39_arena_audit_1ton.py` | 一对多审计（同一榜单条目被多记录引用，调试用） |
| `temp/d39_gap_from_arena.py` | 榜单反推漏采 → `temp/d40_arena_gap_raw.json` |
| `temp/d39_make_d40_candidates.py` | 转 S0 格式 → `temp/d40_wave1_candidates.jsonl` |
| `temp/d39_finalize_cohere.py` | Cohere Parse 5 终裁结论写入隔离档 |
| `backups/model_data_v2.pre-d39-arena-20260910-151430.jsonl` | 导入前全量备份 |

---

## 7. 附：Cohere Parse 5 终裁留痕

用户 D39 终裁 **维持移除**，理由：**计费方式与主流不符**（按页计价 $1.50/1,000 页，`pricing` token 六键全 null、unit 置 null），不像常规模型。

归档说明：D37 二查的「2.3B 文档 VLM＝真模型」结论针对"是否存在/是否为模型"，与"是否符合本库收录口径"是**两个层次**的问题，不构成保留依据。回滚脚本 `temp/d38_restore_cohere_parse.py` 已标注 **VOID 作废**；终裁结论已写入 `docs/non_model_records.jsonl` 第 8 条 `meta.notes`。
