# D51 轮次报告：17 天窗口全量 S0 + G1/G2 采集入库（960 → 977）

> 日期：2026-09-30。触发方式：用户（原话「看一下这个任务是不是该更新了」）。
> 记录数 **960 → 977（+17）**，门禁 **ERROR 0 / WARN 0**，qa_outliers 终态：硬错全 0、o1=4、c4=2、**r1=0、r2=0**（与 D50 持平，17 条新行未触发任何体检项）。
> 距上轮 D50（2026-09-14）16 天，主库最新 `release_date` 原为 2026-09-13，**09-14→09-30 的发布窗口此前完全未扫**。

## 一、用户拍板的两条口径

1. **采集范围**：G1（国际旗舰新代际）+ G2（国产/亚洲新档）= 18 条候选进 S2；G3 新厂商 7 条、G4 组件并入 2 条本轮不做；G5 舍。
2. **变体口径 = 按「独立测量身份」分判**：Arena 榜上有独立 elo 条目的 effort 档（max/high/xhigh）⇒ 独立成行（沿用库内 `gpt-5.6-sol-max`、`claude-opus-5-max`、`grok-4.6-high` 先例）；OpenRouter 自述 `same underlying model` / `same checkpoint` 的服务档（-pro / :batch / -ultraspeed）⇒ 不立行，只写 notes 防重（沿用 D50 `gpt-6-astra-pro` 判例）。

落地结果：**10 条新型号行 + 7 条 effort 档行 = 17 行**；7 项服务档进 notes 不立行。

## 二、S0 四源实测（A 层重抓 + B/C 层台账与榜单）

| 源 | 本轮（2026-09-30） | 对比 09-14 基线（已存 `temp/d51_baseline/`） |
|---|---|---|
| OpenRouter | 464 模型，36 条上架 ≥09-14 | leads 520→539，**35 条新线索** |
| ModelScope | 27 条候选 | 8→27，**22 条新仓库**（13 条 `NCP_ArchPreview` 训练 checkpoint） |
| Arena / DataLearner | 快照 09-25，text 409 行 | 09-11/400 行，**9 个榜上新名字** |
| Artificial Analysis | 735 条，max releaseDate 09-07 | **md5 逐字节一致 ⇒ 零新增**（收录滞后约 3 周） |
| 阿里云台账 | 141 行带日期 | 逐行一致 → 0 新增（**但见下节：这是 TC 语言页滞后的假结论**） |
| DeepSeek | sitemap 枚举最新 `news260910` | 09-14 后无官方发布（**D50 遗留已解**） |

S0 汇总候选 56 条 → `candidate_diff.py` 分档 **NEW 37 / CHECK_VARIANT 16 / EXISTS 3**（`temp/d51_candidates.jsonl`、`temp/d51_diff_out.txt`）。

## 三、本轮挖出的两个源侧坑（已写回 `跟踪源清单.md`）

1. **DeepSeek news 入口失效的真实机制**：`/news/` 与任意 `/news/newsXXXXXX`（包括不存在的路径）都返回**同一份 48 KB Docusaurus 客户端壳**，title 恒为 "Your First API Call"，**HTTP 200 完全不能当"页面存在"用**。替代入口 = `api-docs.deepseek.com/sitemap.xml` 枚举 + 单篇详情页取正文（单篇页确有服务端内容，`news260910` 可直读）。
2. **阿里台账的语言页滞后**：S0 用 `/help/tc/`（繁体）页扫出「0 新增」，b345 采集时重抓发现 **TC 页 725 行不含 `qwen3.8-omni-flash`，而 zh（1,776 行）/ en 页都有且带 09-17 日期** ⇒ 差点漏采一个 T0 官方条目。**S0 扫阿里系必须用 zh 或 en 页**，`跟踪源清单.md` §B2 已改写并标注。
3. （顺带）xAI / Meta 官方域 09-30 复测仍全 000，OpenAI 新增两条 403 样本 ⇒ 已记入 §B2 复测结果。

## 四、S2 采集（6 批次 / 17 行，并发≤3 三波）

| batch | 行数 | 定档质量 |
|---|---|---|
| b341w1 OpenAI | gpt-6-sol / -sol-max / gpt-6-luna / -luna-max / gpt-6.1-sol | 官方域 403 ⇒ **T2**（媒体转述 + OR 同日上架互证），全部 `待验证` |
| b342w1 Anthropic | claude-opus-5.5 / -opus-5.5-high / claude-sonnet-5.5 | **T0**：官方 news 页 + `claude.com/pricing` 直读（sonnet-5.5 公告详情页实测 404，已记降级点） |
| b343w1 xAI | grok-4.7 / grok-4.7-xhigh | **T3**：官方域全 000，媒体多源一致 09-21 |
| b344w1 Xiaomi | mimo-v2.6-pro / -flash（开源权重） | **T0**：HF 卡片+技术报告 PDF+`platform.xiaomimimo.com/api/v1/models` 官方刊例；pro=1.02T/42B、flash=309B/15B（报告写 310B，取权重卡口径并记分歧） |
| b345w1 Upstage+Alibaba | solar-mini4 / qwen-3.8-omni-flash | **T0**：Upstage Console 模型史 `solar-mini4-260922` + 阿里 zh/en 台账 09-17 |
| b346w1 补档 | claude-fable-5-high / muse-spark-1.3-max / deepseek-v4.1-flash-max | **T0**：官方 news260910 直读；三族榜上 `modelCode=null` + `thinkingMode` 有值 ⇒ 独立测量身份判据落地 |

服务档不立行、已 notes 留痕 7 项：`glm-5.3-prime`、`glm-5.3-flashx`、`qwen3.8-max-prime`（→ 主库既有 3 行）、`gpt-6-sol-pro`、`gpt-6-luna-pro`、`gpt-6.1-sol-pro`、`mimo-v2.6-pro-ultraspeed`（→ 新行 notes）、另 `qwen3.8-27b:free` 仅 notes 留痕。
`qwen3.8-max-prime` 的判据是硬证据：阿里云《Prime 模式》文档正文两处「模型支持的能力、使用限制与原版模型相同」，且台账 538 个 model ID 里**无** `qwen3.8-max-prime`，计费表把 Prime 与「Batch 半价/缓存折扣」并列在同注记 ⇒ 计费模式非型号身份。

## 五、S3/S4 合并与质检

- 合并 17 文件全为 `add_record`（零字段冲突），命令沿用 `增量更新工作流.md` §4 口径（`--on-null take_source --on-both source_wins --on-array replace --on-schema upgrade --tie-breaker keep_target`）；改前基线另存 `temp/d51_premerge_model_data_v2.jsonl`。
- Arena elo 导入：`d39_import_arena_elo.py --apply` 写入 **33 条**涉及 12 条记录（幂等；含 `solar-pro4`、`granite-4.2-*` 等旧行首次补上 elo）。
- **本轮自引入并已修复的一处回归**：b343 把基准名写成 `GDPVal`，而库内 37 条（D40 AA 导入批）统一 `GDPval` ⇒ `r2` 由 0 变 1。已按「少数服从库内主流写法」归一（`temp/d51_fix_gdpval_case.py`，带逐行断言），复检 `r2=0`。

## 六、遗留与待裁决（3 项，均已 notes 留痕，未擅自处理）

1. **xAI 已更名 SpaceXAI（2026-07 官宣）**：OR 与 Arena 均标 SpaceXAI，`docs.x.ai` 页面标题亦为 "Grok 4.7 | SpaceXAI Docs"。按红线 §3.2 新行仍用 `xai:` 前缀 / vendor `xAI`，库内 19 条 grok 全部挂 xAI ⇒ **是否做一轮 vendor 归一待用户拍板**。
2. **`meta:muse-spark-1.3` 家族行定价可疑**：官方域不可达无法复验；库内该家族行 $0.10/$0.20 恰等于 OpenRouter 上 `muse-spark-1.3-contributor` 报价，而 AA/OR 对 `-max` 观测为 $1.25/$4.25（差 12.5×）⇒ 疑当年把 contributor 刊例误读成 base 刊例。新行按 T1 观测价填并写明冲突，**待官方域可达时一并改判**。另 `-max` 在 Meta 文档里是独立 model ID，但 OR 无端点、AA 只当档名 ⇒ 身份边界标「未判定」。
3. **`glm-5.3-max` 漏项**：Arena 09-25 榜有独立 elo（text r24 1480 / coding r29 1522 / math r16 1497，`thinkingMode=max`），库内无该行；它 09-11 就在榜上 ⇒ 不属「新面孔」，本轮差集式 S0 捞不到。**按本轮已定口径它应立行**。同类风险：凡「基线期已上榜但未采」的条目都不会被差集发现（D39 曾用「榜单反推漏采 84 条」的全量式扫法覆盖此类）。

## 七、下一步

- 上述 3 项待用户点单；
- D50 遗留的「qa_outliers 扩容至 31 项」仍未排期；
- G3（Perceptron Mk1.5 / Fireworks Ember-1 / PrismML Ternary-Bonsai-2-27B / BAAI AREX-2 / Realtime-Venus / Unbiased Pareto）与 G4（Nex-N2.5 DSpark 组件并入）留作下一轮候选，明细在 `temp/d51_candidates.jsonl`。
