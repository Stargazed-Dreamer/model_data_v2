# D55 报告 · 两个新私榜接入（arenaofbias / galbands）+ 新模型缺口盘点

> **轮次**：D55 ｜ **日期**：2026-10-10 ｜ **触发**：用户「更新一下最近的新模型情况。我又找到两个私榜：`https://gallery.arenaofbias.icu/#/leaderboard`、`https://benchmark.galbands.com/`，也可以作为来源」
> **基线**：主库 `model_data_v2.jsonl` = **995 条**（D54 收官）
> **产物**：`temp/d55/`（两榜快照 + 比对脚本 + 候选清单）；本文档；`docs/跟踪源清单.md` 新增 C-3/C-4 两条源

---

## 0. 一句话结论

两个新私榜**都能作为 S0 发现源接入**，且**互补**：`arenaofbias` 是**策展式前沿榜**（59 个模型，全是当下最热前沿，命中率 67.8%），`galbands` 是 **OpenRouter 全量目录镜像**（396 个模型，命中的是「谁被拿来 PK」）。

**检出真缺口约 20 个前沿模型**，集中在 **ByteDance Seed 2.1 系、Google Gemini 4 系 / Claude Haiku 5.5、Cognition SWE-2、Meituan LongCat 2.x、腾讯 HY、新厂商 China Telecom / Poolside / Liquid**。另有一批匿名代号（space-bunny / omen-alpha / pixel-canary）与别名（hy3 / gpt-4o / solar-pro-4）**不入库**。

---

## 1. 两个新源的数据结构（实测 2026-10-10）

### 1.1 arenaofbias（亿模亿样 · 模型效果对比）

首页是 SPA，真数据在**独立 API 域**：

| 项 | 值 |
|---|---|
| API base | `https://api.arenaofbias.icu/`（前端 `runtime-config.js` 的 `SAME_PROMPT_CONFIG.apiBaseUrl` 明文给出） |
| 免鉴权端点 | `GET /api/bootstrap`（**978 KB**，含 `works` / `questions` / `arena` / `featured` / `domains` / `site`） |
| 规模 | **927 个作品（works）/ 59 个模型 / 60 道题 / 26 个领域 / 8,309 票 / 215 投票人** |
| 每作品的字段 | `model`（id）、`modelName`（显示名）、`vendor`、`effort`（`Low/Medium/High/XHigh/Max/Ultra/Ultracode`）、`provider`（official/unofficial）、`task`、`title` |
| 计分口径 | Bradley–Terry 模型估偏好强度 → 折 Elo 刻度（**1000 = 平均水平**，+400 ≈ 偏好概率高 10 倍）；比较 <30 次标「暂定」 |
| 性质 | **策展前沿榜**——59 个模型是站方挑的前沿代表，正是「最值得关注」的那批 |

> ⚠ `bootstrap` 只含 `arena` 的**每任务计数**（works/entries），**不含票矩阵**，故**无法离线复算 Elo**（Elo 由前端 `leaderboard.js` 依票实时算）。⇒ arenaofbias 只作**发现源**（谁在榜=谁新），不作排行源。

### 1.2 galbands（RP 竞技场）

| 项 | 值 |
|---|---|
| 端点 | `GET /api/leaderboard`（**4.1 MB**）、`GET /api/models`（396 条，带 `openrouter_id`）、`GET /api/bootstrap`（stats） |
| 规模 | **396 个模型 / 3,932 个条目 / 12,066 票 / 44 个类目**；`updatedAt = 2026-10-10 13:13` |
| 五个榜 | **综合评分 / 同人 / 原创 / 长程 / 翻译**（行数 124 / 116 / 119 / 39 / 98） |
| 行字段 | `name`（"Vendor: Model"）、`openrouter_id`（★关键——可直接映射 OpenRouter）、`score`(=elo)、`eloLow/High`、`winrate`、`votes`、`uniqueVoters` |
| 性质 | **OpenRouter 目录镜像**：只要上了 OpenRouter 就可能进 galbands。好处是**带 openrouter_id**（可交叉到 A 层）；坏处是**混入大量非前沿**（老模型 / 别名 / 聚合器路由） |

> ★ galbands 的 `openrouter_id` 让它天然可与 A 层（OpenRouter）联表；且有五个**方向榜**（同人/原创/长程/翻译），比 atmeplz 的四方向更细。

---

## 2. 收录对齐：两榜 vs 库内 995 条

匹配口径：源名剥厂商前缀 → 归一化（去非字母数字+小写）→ 对库内 `model_id` 第 2 段（family）与 `full_name` 做 **精确 / 前缀族 / 子串** 匹配（脚本 `temp/d55/d55_leaderboard_match.py`、`d55_consolidate_gap.py`）。

| 源 | 榜内模型数 | 库内已收 | 覆盖率 | 未匹配 |
|---|---:|---:|---:|---:|
| **arenaofbias**（策展前沿） | 59 | **40** | **67.8%** | 19 |
| **galbands · 综合评分榜**（受测集） | 124 | **98** | **79.0%** | 26 |
| galbands · 全目录 `/api/models` | 396 | 261 | 65.9% | 135（多为非前沿/别名） |

**读法**：
- arenaofbias 的 67.8% 与 D53 atmeplz 的 76.7% 同量级 ⇒ **我们对该榜的收录是健康的**，漏的 19 个里还有 3 个不可采（匿名/别名）。
- galbands 全目录 65.9% 的低覆盖**不是缺陷**——它把 OpenRouter 上所有老开源模型（hermes / phi / gemma-3 / granite…）都算进来了，本就不在采集口径内。**要看的是「排行榜前段」**：综合评分榜 79.0% 才是真指标。

---

## 3. 真缺口候选（★建议采）

### 3.1 前沿新模型（两榜交叉命中，优先级高）

| # | 建议 model_id | 源名 / 证据 | 关键点 |
|---|---|---|---|
| 1 | `anthropic:claude-haiku-5.5` | arenaofbias（32 works，含 Ultracode 档） | 库内只有 haiku-4.5，5.5 代缺失 |
| 2 | `openai:gpt-6-chat` | galbands #5 综合评分 65.4 | 库内只有 astra/luna/sol，无 gpt-6 base/chat |
| 3 | `google:gemini-4-0930` | arenaofbias `gemini-4.x`(18) + galbands `Gemini 4 0930`(#3) | 两榜交叉，Gemini 4 系首发 |
| 4 | `cognition:swe-2` | arenaofbias `swe-2`(10) | 库内只有 swe-1.5/1.6/1.7 |
| 5 | `meituan:longcat-2.5` | arenaofbias `longcat-2.5`(8) + galbands `LongCat-2.5-Preview`(#48) | 库内只有 longcat-flash 系 |
| 6 | `stepfun:step-5-preview` | arenaofbias `step-5-preview`(8) + galbands(#61) | 库内到 step-3.7-flash |
| 7 | `bytedance:seed-2.1-pro` | arenaofbias(8) + galbands `Doubao Seed 2.1 Pro`(#20) | 库内只有 seed-2.1-turbo |
| 8 | `bytedance:seed-2.1-lite` | arenaofbias(5) + galbands(#94) | 同上 |
| 9 | `bytedance:doubao-seed-evolving` | arenaofbias(3) + galbands `Doubao Seed Evolving`(#14) | 豆包进化版 |
| 10 | `alibaba:qwen-3.5-plus` | arenaofbias(1) | 库内有 qwen-3.5-flash/27b 等，**无 plus** |
| 11 | `sensetime:sensenova-6.8-flash-lite` | arenaofbias(3) | 库内 SenseNova 到 U1 / SenseChat 5.0 |
| 12 | `inclusionai:ling-3.1-flash` | arenaofbias(6) + galbands(#?) | 库内到 ling-3.0-flash 系 |
| 13 | `nvidia:nemotron-3-nano-omni-30b-a3b` | galbands(#124) | 库内无 omni 变体 |
| 14 | `google:gemini-3.5-flash-lite` | galbands(#70) | 库内无 3.5-flash-lite |
| 15 | `poolside:laguna-xs-2.1` / `laguna-s-2.1` | galbands(#113/#118) | 库内只有 poolside-malibu |
| 16 | `liquid:lfm2.5-8b-a1b` / `lfm2.5-vl-3b` | galbands(#111/#121) | 库内 LFM 到 2.5-2.6b |
| 17 | `bytedance:seed-2.0-lite` / `seed-2.0-mini` | galbands(#108/#94) | 库内有 seed-2.0-code，无 lite/mini |
| 18 | ★新厂商 | `xing4.0-29b-a4b`(arenaofbias, vendor=**China Telecom**) | 库内无运营商节点（待核真伪） |
| 19 | ★新厂商 | `atria-dawn-preview`(arenaofbias vendor=Shanghai AI Lab；galbands) | 「Atria」系列，库内 0 命中 |

> 说明：#3/#5/#6/#7/#8/#9/#12 在两榜**同时命中**，交叉验证充分；#1/#4/#11 在 arenaofbias 高频（32/10/3 works）；#15/#16 是新厂商面。`Hy4 preview`（galbands #72）经核**＝库内 `hunyuan-hy4-preview`**，非缺口（见 §3.2）。

### 3.2 别名 / 已覆盖（不入库，仅建映射）

| 源名 | 库内对应 | 判据 |
|---|---|---|
| `hy3`（arenaofbias/galbands） | `tencent:tencent-hy3:base` | 库内已有 |
| `Hy4 preview` | `tencent:hunyuan-hy4-preview:base` | 命名差 `hunyuan-` 前缀（D55 复核确认为同一模型） |
| `GPT-4o` | `openai:gpt-4o-2024-*` 系列 | 库内无裸 base，仅有日期变体 |
| `GPT-5.5` / `GPT-5.4` | `openai:gpt-5.5-*` / `gpt-5.4-*` 变体 | **有变体无 base**，可考虑补 base 行 |
| `Solar Pro 4` | `upstage:solar-pro4:base` | 连字符差异 |
| `Dots3-Note` | `dots-studio:dots3-note-preview:base` | 同族 preview |
| `Doubao Seed 2.1 Turbo` | `bytedance:seed-2.1-turbo:base` | 已有 |
| `Nano Banana Pro` | `google/gemini-3-pro-image`（OpenRouter）| 谷歌图像模型代号（图像类，按库口径评估） |

### 3.3 匿名 / 非模型（不采）

- **匿名代号**：`space-bunny`（galbands orid=`stealth/space-bunny-alpha`，官方保密模型）、`omen-alpha`、`pixel-canary`（Google 代号）、`qwen-latest-series-invite-2609`（阿里邀请制代号）
- **非模型**：`Codex Auto Review`（OpenAI 服务）、`openrouter/auto`、`openrouter/free`、`Body Builder`

---

## 4. 建议动作

1. **登记源**（本文档已完成）：把 arenaofbias / galbands 写入 `docs/跟踪源清单.md` §C 层（C-3 / C-4），固化端点与判据。
2. **补采**：对 §3.1 的 ~20 个前沿模型按 S1→S5 采集入库（口径不变：官方源定档、`pricing` 四键、查不到=null）。
3. **建别名映射**：§3.2 的 8 条写入别名表（供本地管家/消费方），无需新建记录。
4. **不采**：§3.3 匿名/非模型，按 D45/D52 先例排除。

## 5. 待议 / 不确定

- `atria-dawn-preview` 的 vendor「Shanghai AI Lab」存疑（galbands 未给 vendor，arenaofbias 标 Shanghai AI Lab）——需回官方核。
- `xing4.0-29b-a4b`（China Telecom）疑为特定用途模型，需核是否入采集口径。
- galbands 分数（`score`）与库内 LMArena elo 的**相关性未测**（本轮以收录为主）；如需能力偏差分析可另起一轮。
- arenaofbias 的 `bootstrap` 不含票矩阵 ⇒ **无法取该榜 Elo**，只能作发现源。

---

*脚本：`temp/d55/d55_src_match.py`（初版）、`d55_leaderboard_match.py`（榜单比对）、`d55_consolidate_gap.py`（合并分类）。快照：`temp/d55/{aob_bootstrap.json, gb_leaderboard.json, gb_models.json, gb_bootstrap.json}`。*
