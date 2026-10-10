# D56 报告 · 前沿缺口全量补采（承接 D55 的两个新私榜）

> **轮次**：D56 ｜ **日期**：2026-10-11 ｜ **触发**：用户「全部采」（对 D55 §3.1 的 ~22 条前沿缺口候选全量采集）
> **基线**：主库 `model_data_v2.jsonl` = **995 条**（D54 收官）｜**门禁** ERROR 0 / WARN 0｜**体检器** r1=0 / r2=0 / o1=5
> **结果**：**20 条立行入库 → 1015 条**；2 条判为别名不立行；门禁 ERROR 0 / WARN 0，r1=r2=0，o1 5→9（4 条官方未标注发布日，按红线留 null）

---

## 0. 一句话结论

D55 检出的前沿缺口**全部处置完毕**：22 条候选里 **20 条是真模型**（含 2 条存疑项核属实），**2 条是别名**（`gpt-6-chat`、`doubao-seed-evolving`）。
主库 995 → **1015（+20）**，覆盖 14 家厂商，其中 **Google Gemini 4 系首发、ByteDance Seed 2.1 系、Cognition SWE-2、中国电信星辰 Xing4.0、上海 AI Lab Atria Dawn** 五条是本轮最有信息量的新增。

**副作用可控**：`o1` 5→9（4 条官方未公告发布日，属该检查项的定义内命中）；`c5` 19→20（`ling-3.1-flash` 轻量定位配 560B 总参，稀疏 MoE，与同族 `ling-3.0-flash-fin/sante` 同款疑点，非硬错）。

---

## 1. 入库 20 条（按厂商）

| # | model_id | 关键规格 | 定价（USD/1M，in / out / cached_in） | 许可 | 可信度 |
|---|---|---|---|---:|---|
| 1 | `google:gemini-4-argon:base` | rd 2026-09-30、ctx 1,000,000、max_out 1,000,000 | 2.00 / 10.00 / 0.10（推广价，恢复后 4/20） | 闭源 API | T1 |
| 2 | `google:gemini-3.5-flash-lite:base` | rd 2026-07-21、ctx 1,048,576、max_out 65,536 | 0.30 / 2.50 / 0.03（batch 0.15 / 1.25） | 闭源 API | 价 T1 / 规格 T3 |
| 3 | `bytedance:seed-2.1-pro:base` | rd 2026-06（月）、ctx 1,048,576、max_out 256,000 | 0.8911 / 4.4557 / 0.1782（¥6 / ¥30 / ¥1.2 折算） | 闭源 API | T1 |
| 4 | `bytedance:seed-2.1-lite:base` | rd null、ctx 1,048,576、max_out 256,000 | 0.1188 / 0.4010 / 0.0238（¥0.8 / ¥2.7 / ¥0.16） | 闭源 API | T1 |
| 5 | `bytedance:seed-2.0-lite:base` | rd null、ctx 262,144、max_out 128,000 | 0.0891 / 0.5347 / 0.0178（¥0.6 / ¥3.6 / ¥0.12，最低档） | 闭源 API | T1 |
| 6 | `bytedance:seed-2.0-mini:base` | rd null、ctx 262,144、max_out 128,000 | 0.0297 / 0.2970 / 0.0059（¥0.2 / ¥2.0 / ¥0.04，最低档） | 闭源 API | T1 |
| 7 | `meituan:longcat-2.5-preview:base` | rd 2026-09-25、ctx 1,048,576（官方 `/v1/models`） | 0.30 / 1.20 / 0.006（官方页自带 USD 栏，限时折扣价） | 闭源 API | **T0** |
| 8 | `stepfun:step-5-preview:base` | rd null、ctx 1,000,000、max_out 64,000 | 1.00 / 2.70 / 0.10 | null（未公布） | **T0** |
| 9 | `alibaba:qwen-3.5-plus:base` | rd 2026-02-15、ctx 1,000,000、max_out 65,536、思维链 81,920 | 0.115 / 0.688 / 0.0115（+ cache_write 0.14375、batch 0.0575/0.345） | 闭源 API | **T0** |
| 10 | `sensetime:sensenova-6.8-flash-lite:base` | rd 2026-08-11、ctx null、max_out null | 全 null（官方付费档「即将上线」） | null | **T0** |
| 11 | `inclusionai:ling-3.1-flash:base` | rd 2026-09-30、ctx 1,000,000（体验期 262,144）、max_out 32,768、560B/A25B | 0.30 / 0.90 / 0.06 | null（称计划开源） | T1 |
| 12 | `cognition:swe-2:base` | rd 2026-09-10、ctx null、2.8T（基座 Kimi K3） | 3.00 / 15.00 / 0.30 | 闭源 proprietary | **T0** |
| 13 | `nvidia:nemotron-3-nano-omni-30b-a3b:base` | rd 2026-04-28、ctx 262,144、31B/A3B、原生视听文 | 无官方托管 API 价 | NVIDIA Open Model License | **T0** |
| 14 | `poolside:laguna-xs-2.1:base` | rd 2026-07-02、ctx 262,144、33B/A3B | 0.10 / 0.20 / 0.05 | OpenMDW-1.1 | **T0** |
| 15 | `poolside:laguna-s-2.1:base` | rd 2026-07-21、ctx 1,048,576、118B/A8B | 0.10 / 0.20 / 0.01 | OpenMDW-1.1 | **T0** |
| 16 | `liquid:lfm2.5-8b-a1b:base` | rd 2026-05-28、ctx 131,072、8B/A1.5B | 无官方托管 API 价 | LFM Open License 1.0 | **T0** |
| 17 | `liquid:lfm2.5-vl-3b:base` | rd 2026-08-12、ctx 32,768、3.1B（dense VLM） | 无官方托管 API 价 | LFM Open License 1.0 | **T0** |
| 18 | `china-telecom:xing4.0-29b-a4b:base` | rd 2026-09-17、ctx 262,144（可扩 512K）、29B/A4B | 无官方托管 API 价 | Apache-2.0 | **T0**（跑分 T1） |
| 19 | `sha-ai-lab:atria-dawn-preview:base` | rd 2026-09-11、ctx 256,000、744B/A40B（GLM-5.2 后训练） | 无官方托管 API 价 | MIT | **T0**（跑分 T1） |
| 20 | `anthropic:claude-haiku-5.5:base` | rd 2026-10-07、ctx 1,000,000、max_out 128,000 | 0.10 / 0.50 / 0.01（>100K 档 0.50/2.50/0.05） | 闭源 API | T1 |

> 汇率口径：人民币定价统一按 **1 USD = 6.7330 CNY**（中国外汇交易中心 2026-10-09 中间价）折算，原始人民币价已写入各条 `pricing.notes`，未静默改单位。

---

## 2. 裁定为别名 / 不立行（2 条）

| 源名 | 指向 | 判据（官方原文） |
|---|---|---|
| `gpt-6-chat`（galbands #5，65.4 分） | `openai:gpt-6-sol:base`（库内已有） | OpenAI 官方发布说明：「**Plus, Pro, Business, and Enterprise use GPT‑6 Sol; Free and Go use GPT‑6 Luna**」——ChatGPT 侧的「GPT-6」不是独立模型，由 Sol/Luna 两个端点承载；`chat-latest` 是滚动别名。库内 `gpt-6-astra / luna / sol / 6.1-sol` 已覆盖，**不建空壳 base 行**。<br>⚠ 反证处置：techpulse.press 称 2026-10-08 发布 plain `gpt-6`（10M 上下文、$5/$25），但该文含伪造 API 参数且与官方时间线冲突，**未采**。 |
| `Doubao Seed Evolving`（arenaofbias + galbands #14） | `bytedance:seed-2.1-pro:base`（本轮新建） | 火山方舟官方原文：「版本升级**自动生效**，通过**统一 Model ID** `doubao-seed-evolving` 调用即可获取**最新版本的模型服务**」；官方模型列表标为「快速迭代模型」，控制台明示 2.1-pro-260915 是「9 月 9 日更新的 doubao-seed-evolving **同款模型**」；价格与 2.1-pro 完全同轴。**滚动入口，非独立 checkpoint**。 |

---

## 3. 质量闸门

| 检查 | 基线（D54 后） | D56 后 | 判读 |
|---|---:|---:|---|
| 主库记录数 | 995 | **1015** | +20 全为 `add_record`，无覆盖 |
| 门禁 ERROR / WARN | 0 / 0 | **0 / 0** | 通过 |
| 源文件门禁（20 个） | — | **20/20 ERROR 0 / WARN 0** | 通过 |
| 体检器 r1（同厂商同 full_name 重复） | 0 | **0** | 通过 |
| 体检器 r2（基准名大小写异写） | 0 | **0** | 通过（本轮修 4 处，见下） |
| 体检器 o1（release_date 缺失） | 5 | **9** | +4 = `seed-2.1-lite` / `seed-2.0-lite` / `seed-2.0-mini` / `step-5-preview`，官方未标注 → 按红线留 null，**非数据缺陷** |
| 体检器 c5（定位与参数量级不匹配·疑点） | 19 | **20** | +1 = `ling-3.1-flash`（轻量 + 560B 总参，稀疏 MoE），同族先例同类，疑点级非硬错 |

**本轮顺手修的 4 处基准名异写**（否则 r2 会从 0 变 3）：

- `SWE-bench Pro` → `SWE-Bench Pro`（`sha-ai-lab:atria-dawn-preview`）
- `Tau3-Bench` → `TAU3-Bench`（`china-telecom:xing4.0-29b-a4b`）
- `BFCL V4` / `BFCL v4` → `BFCLv4`（`liquid:lfm2.5-vl-3b`、`sha-ai-lab:atria-dawn-preview`）

主库与 `incoming/` 源文件**同步修改**，保证源库一致。

---

## 4. 待复核 / 遗留（下轮可接）

1. **`gemini-4-argon` 的型号名待一手确认**：本环境 `ai.google.dev` / `cloud.google.com` 均 fetch failed，「Argon」来自官方博客公告标题的第三方转述 + 多家家族目录交叉，已在 `meta.notes` 留痕。若一手页确认正式名不含 Argon，family 段应改 `gemini-4`（其余字段不受影响）。
2. **`qwen-3.5-plus` 的 release_date 是推导值**（2026-02-15）：官方未单列稳定版首发日，据最早快照 `qwen3.5-plus-2026-02-15` + 官方「稳定版功能等同该快照」推定，notes 已注明。查到官方独立首发日应改。
3. **库内 `alibaba:qwen-3.5-flash:base` 疑似历史错配**：其 Epoch AI 三条跑分（AIME/GPQA/SimpleQA）的 `原始 Model version` 实为 `qwen3.5-plus`，本轮未复制这些分数到新记录，**建议另案核查该记录**。
4. **`cognition:swe-2` 的 `context_window` / `max_output` 留 null**：官方博客与 Devin / Windsurf 官方文档的模型表只列价格，未给窗口数值。
5. **`stepfun:step-5-preview` 权重承诺**：媒体称承诺 2026-10-15 释放权重，本轮按未兑现记 `open_weights=false`；若兑现需重采 `access` / `license`。
6. **`sensetime:sensenova-6.8-flash-lite` 定价全 null**：官方付费档「即将上线」，上线后补 `pricing` 六键。
7. **`bytedance` 4 条只能定 T1**：火山方舟文档页正文 JS 渲染，WebFetch 只取到标题，数值经官方页检索摘要取得。
8. **arenaofbias / galbands 的能力偏差分析未做**：D55 只做了收录对齐，本轮以采集为主。两榜分数与库内 LMArena Elo 的相关性可另起一轮（D55 §5 已列）。

---

*采集文件：`incoming/models/b351w1__*.jsonl`（20 个）｜台账：`docs/batch_claim_ledger.jsonl` 第 354 行（`batch_id=b351w1`，`round=D56`，`claimed_by=workbuddy-03`）｜合并参数：`--on-null take_source --on-both source_wins --on-array union_by_key --array-key-override benchmarks.arena_elo:sub_benchmark,date benchmarks.self_reported:benchmark,config benchmarks.independent:benchmark,config --on-schema upgrade --tie-breaker keep_target`*
