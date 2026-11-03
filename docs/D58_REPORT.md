# D58 报告 · 接入「致知」小众榜（llm2014/llm_benchmark）

> **轮次**：D58 ｜ **日期**：2026-11-04
> **触发**：用户「看一下这个网址 `https://llm2014.github.io/llm_benchmark/`，适配到 model_data 工作区作为小众榜」→ S1 拍板「**入库 + 榜单页**」「取**最新一期三榜**」
> **基线**：主库 `model_data_v2.jsonl` = **1028 条**（D57 收官），`independent` 条目 **2159**
> **结果**：新增 benchmark 两个（致知·逻辑榜 / 致知·视觉榜）、**38 个模型各 +1 条跑分**（2159 → 2197）；新增可视化页「小众榜」；门禁 **ERROR 0 / WARN 0** 不变

---

## 0. 一句话结论

「致知」是被测者自建私有题库的**个人长期追踪榜**（28 题 / 每月滚动 / 三榜：逻辑、代码 v3、视觉），**能入库、但只能按 T3 记**：
它发布的是数值分（逻辑/视觉）与任务级评级（代码），题不公开、无法复核 ⇒ 分数可作**横向位次参考**，不可当权威真值。
最新一期 78 行里 **62 行匹配到库内 model_id（79.5%）**，入库 38 个模型；**16 行是真缺口**，其中 3 个（openPangu-2.0、LongCat-2.0、Spark X2.6）属 2026 年新模型、值得进 S0，其余 13 个是 2025 年的老视觉/非主线型号，**不在本库采集口径内**。

---

## 1. 站点口径（先摸清）

| 项 | 值 |
|---|---|
| 站点 | 「致知」大模型智力长期追踪榜（个人性质，非机构） |
| 代码/数据 | `github.com/llm2014/llm_benchmark`，页面在 `docs/`（GitHub Pages），静态托管 |
| 题目 | **私有题库，长期维持 28 题 / ≤270 用例**，**全部非公开**；每月滚动增减，故同一模型跨月有 ±3 分波动 |
| 计分 | 每题若干得分点，得分 ÷ 得分点总数 × 10；**同题测 3 遍**；「极限分数」= 3 次中最高，「中位分数」= 3 次中位 |
| 榜单 | **logic**（2024-04 起逐月，最新 2026-11）、**code_v3**（2026-01/05/07/08/09/10/11，7 期）、**vision**（2025-05/07/09/11，4 期）；旧 `code` 榜站点已隐藏 |
| 数据形态 | `docs/data/datasets.json` 清单 + 每期一个 CSV；主站另有「测试成本 / 平均耗时 / Token 效率」三个纵轴 |
| 代码榜特性 | **只发任务级评级**（`Pass` / `4/A+(341.72)` / `Failed` / `Skip`），**站点自身不出合成分**（`benchmark-domain.js` 只有排序用的等级序，没有加权总分） |

> 站点自述「不够权威，不够全面，仅从一个侧面观察长期趋势；不可盲信任何评测」——与我们的 T3 定级一致。

---

## 2. 接入方式（两条腿，各有边界）

### 2.1 主库跑分（logic / vision 两榜）

- benchmark 名：**`致知·逻辑榜`** / **`致知·视觉榜`**（viz 里归入新分组 **小众榜**）
- score：站点主用轴 **中位分数 ÷ 100**（0-1，符合库内 `independent` 口径）；**极限分数写进 notes**
- config：`<榜期> 月榜 · <站点档位>`（如 `2026-11 月榜 · xhigh`）——档位是**测量配置**，不是型号身份
- date：榜期（logic/code_v3 = `2026-11`，vision = `2025-11`，**vision 站点最后一期是 2025-11，不能写成 2026-11**）
- source_type：`独立第三方评测（其它）`（落在 `independent` 段受控枚举内）
- confidence：**T3**（个人评测、题库不公开、不可复核；与 D53 对 atmeplz 私榜的结论同向——**第三方私榜不构成立行依据，也不得升 T0**）

**同模型多行的处理**：榜内同一型号会按 effort 档 / `w/ refuse` 各占一行（如 Opus 5.5 有 `xhigh` 与 `xhigh w/ refuse`）。
规则：同一 model_id **取中位分最高的一行**，被丢弃行的档位仍在站点原始 CSV 里可查（快照入库）。

### 2.2 为什么 `code_v3` 不入主库

站点代码榜给的是**每项工程任务的评级**（8 个任务：Simple Model / iOS+Server / Animation / Data Process / Metal / Science / Rust App / Debug），
排序靠用户点列头按单项排，**站点自己不算总分**。若我们自造一个「等级指数」写进 `independent`：
① 库里会出现一个**没有任何第三方出处**的数值分，违反「跑分必须可溯源」；
② 该指数与 MMLU/GPQA 等百分比口径相差一个语义层，会被下游当成同尺度比较。

⇒ **只在「小众榜」页呈现任务级评级**（Pass/Fail/Skip + 等级色标），不写主库。若日后站点发布合成分，再按 §2.1 补录。

### 2.3 身份粒度规则（沿用 D53/§21 的教训）

第三方榜的 effort 档**不构成新立行依据**：一律落到该型号的 **base 记录**，档位进 `config`。
唯一例外：库内**没有 base 记录**时落已有档位记录（本次 1 例：`GPT-5.6 Luna (max)` → `openai:gpt-5.6-luna-max:base`，该家族只有 `-max` / `-none` 两条）。

---

## 3. 匹配与覆盖（最新一期三榜，实跑）

| 榜 | 站点行数 | 匹配到 model_id | 覆盖率 | 去重后入库模型 |
|---|---:|---:|---:|---:|
| logic（2026-11） | 39 | 35 | 89.7% | 31 |
| code_v3（2026-11） | 19 | **19** | **100%** | 19（仅页面，不入库） |
| vision（2025-11） | 20 | 8 | 40.0% | 7 |
| **合计** | **78** | **62** | **79.5%** | **38（入库）** |

- 匹配方式：显式裁定表（57 条，逐条写依据）+ 归一化模糊匹配（阈值 0.86）；**不做同族外推**。
  ⚠ 模糊匹配本次抓到 1 个误配（`Gemini 3.7 Flash` 撞 `gemini-3.8-flash` 0.94），已改为显式裁定 `google:gemini-3.7-flash-high:base`。
  这正是 D53 的教训：**高分不等于正确，别名表必须逐条过目**。
- logic 覆盖 89.7%，说明前沿主线收录健康；vision 40% 的低覆盖**不是缺陷**——见下。

### 3.1 真缺口 16 行（站点有 / 库内无）

| 站点行 | 判定 | 说明 |
|---|---|---|
| `openPangu-2.0-Pro` / `-Flash` | **S0 候选** | 库内只有 `pangu-5.0` / `pangu-ultra` / `pangu-pro-moe`，openPangu 开源系整条线未采 |
| `LongCat-2.0` | **S0 候选** | 库内 LongCat 只有 flash 系与 `longcat-2.5-preview` |
| `Spark X2.6` | **S0 候选** | 库内讯飞只有 `spark-4.0` / `spark-x1` |
| `Seed-1.6` / `-vision` / `-vision (Think)` / `-thinking-0715` | 口径外 | 字节 Seed 系库内从 2.0 起；1.6 属 2025 老型号 |
| `GLM-4.5V` | 口径外 | 库内只有 GLM-4.5 文本版，无 V 视觉版 |
| `Step-3` | 口径外 | 库内 stepfun 有 3.5/3.7-flash、5-preview，无 step-3 |
| `Qwen-vl-max-2025-08-13` | 口径外 | 库内 Qwen-VL 只有 Qwen3-VL 开源系，无商用 `qwen-vl-max` 线 |
| `hunyuan-t1-vision 0619` / `-turbos-vision 0619` | 口径外 | 库内腾讯视觉只有 `hunyuan-vision-1.5-thinking` / `large-vision` |
| `SenseNova-V6-Pro` / `-Reasoner` | 口径外 | 库内商汤只有 U1 / 6.8-flash-lite |
| `ERNIE 4.5 Turbo VL 0829` | 口径外 | 库内文心只有 4.5 开源三尺寸 / 4.0 |

> 结论：视觉榜是 **2025 年的老榜**（最后一期 2025-11），其覆盖缺口与我们「只收主线 + 前沿」的口径天然不重叠，
> **不建议为对齐这个榜单去补采老视觉型号**；真正要跟进的是 logic 榜照出的 3 个 2026 新模型。

---

## 4. 与库内既有尺子的关系（读法提醒）

1. **不可与 MMLU/GPQA 同尺度**：致知是「私有题库 + 每题 10 分制 + 3 次取中位」，与标准化基准的题目分布、评分粒度都不同。
2. **不可当 T0**：题库不公开、无法复核；连站点作者自述「不可盲信」。T3 是本库能给的上限。
3. **成本/耗时可当独立信息**：站点记录了每次测量的**测试成本（¥）、平均耗时（s）、Token**，这是库内 `pricing` 之外的**实测开销**，本次原样写进 notes，未进结构化字段（避免与刊例价混为一谈）。
4. **档位漂移**：站点同一模型跨月会因题目增删出现 ±3 分波动，**逐月趋势比单月快照更有意义**。本期按拍板只入最新一期；历史月度 CSV（logic 32 期、code 8 期、code_v3 7 期、vision 4 期）未取，需要趋势线时再扩。

---

## 5. 产物清单

| 类型 | 路径 | 说明 |
|---|---|---|
| 数据快照 | `viz/data/niche/zhizhi/2026-11/{logic,code_v3,vision}.csv` | 站点原始 CSV（含成本/耗时/Token/档位列），随仓库入库 |
| 导入脚本 | `scripts/d58_zhizhi_import.py` | 解析 → 别名裁定 → 生成补丁 + 页面数据；`--apply` 才写补丁 |
| 主库补丁 | `incoming/models/d58_zhizhi_202611.jsonl` | 38 条记录（仅 `benchmarks.independent`），`merge -f` 入库 |
| 页面数据 | `viz/data/niche/zhizhi.json` | 三榜全字段 + model_id 匹配结果 + 缺口原因 |
| 可视化 | `viz/viz_index.html` 新增「小众榜」页 | 三榜切换、成本×分数散点、收录覆盖、缺口清单；模型名可点开档案 |
| 接口 | `scripts/viz_server.py` `GET /api/niche` | 读上面的 JSON |
| 榜单分组 | `scripts/viz_transform.py` `bench_meta` | 新增两条 `group="小众榜"`，跑分排行下拉自动出现 |

---

## 6. 复核命令

```bash
# 1) 重算匹配与页面数据（不写主库）
PYTHONUTF8=1 python scripts/d58_zhizhi_import.py

# 2) 合并（dry-run 先看计划，应为 38 条 merge_array）
PYTHONUTF8=1 python scripts/model_data_tool.py merge --file model_data_v2.jsonl \
  --incoming incoming/models/d58_zhizhi_202611.jsonl \
  --on-null take_source --on-both source_wins --on-array union_by_key \
  --array-key benchmark config date \
  --array-key-override "benchmarks.independent:benchmark,config,date" \
  --on-schema upgrade --tie-breaker keep_target

# 3) 门禁（基线：1028 条 / ERROR 0 / WARN 0）
PYTHONUTF8=1 python scripts/validate_model_data.py model_data_v2.jsonl

# 4) 页面（127.0.0.1:8620 → 跑分深度 / 小众榜）
PYTHONUTF8=1 python scripts/viz_server.py
```

实测结果：合并前后记录数 **1028 → 1028**（不新增模型行），`independent` 条目 **2159 → 2197（+38）**，
门禁 **ERROR 0 / WARN 0** 与基线一致。

---

## 7. 后续建议

1. **月度刷新**：站点每月底归档，建议按「用户触发」节奏（不设定时）重跑 `d58_zhizhi_import.py`，改 `SNAP` 目录为该月 + `cfg["month"]`，`union_by_key` 主键已含 `config`（月份），**不会与上期撞键**。
2. **3 个新模型进 S0**：`openPangu-2.0`（Pro/Flash）、`LongCat-2.0`、`Spark X2.6`——本榜是目前唯一见到它们的源，可作为「榜单反推漏采」的一条线索（与 D39/D52 的双轨口径一致）。
3. **不要拿 vision 榜的 40% 覆盖率当质量指标**：它是 2025 年老榜，缺口 13 个全在口径外。
4. 若用户希望把 **code_v3** 也纳入主库，需要先定「等级 → 分数」的换算口径并单独拍板（本报告 §2.2 已说明为何暂不自动做）。
