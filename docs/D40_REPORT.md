# D40 轮次报告 · 2026-09-10

> 用户触发。四项拍板一次执行：**① arena 快照瘦身 ② D40 候选开采 ③ Artificial Analysis 独立跑分接入 ④ A 类历史缺口 + B 类增量采集并行**
>
> 用户原文：`1.是 2.是 3.看看能不能浏览器去连 4. AB的采集也可以一起做了`
>
> 主库 **915 → 937 条**（+22），门禁 **ERROR 0 / WARN 0**（合并前基线同为 0/0）。

---

## 一、结论速览

| 项 | 结果 |
|---|---|
| 记录数 | 900 → 915（D38）→ **937**（D40 +22） |
| `independent` 覆盖 | 340（37.2%）→ **450（48.0%）**，条目 1,050 → **2,011** |
| `arena_elo` 条目 | 809 → **662**（瘦身 -147、新增 +29） |
| `release_date` 到日 | 665 → **709**；缺失 5 → 6（新增 1 条无信源） |
| `license` 填充率 | 51.0% → **56.0%**（+36 条 HF 权威补全） |
| 完全无跑分 | 232 → **210** |
| 采集件门禁 | 22 个文件：**7 个曾报错 → 全部 ERROR 0 / WARN 0** |

---

## 二、第 ③ 项：Artificial Analysis「浏览器去连」——**实测不需要浏览器**

用户拍板原话是"看看能不能浏览器去连"。探查结论：

| 路径 | 结果 |
|---|---|
| 官方 API `/api/v2/data/llms/models` | **HTTP 401，需 key**（与 D39 判断一致） |
| 榜单页 `artificialanalysis.ai/leaderboards/models` | **HTTP 200 / 2.75 MB**，644 个模型的全部评测字段内嵌在 Next.js flight 流里 |
| agent-browser | **未安装**（需 ≈500 MB Chromium），且**用不上** |

**做法**：沿用 D39 已验证的 flight 流提取法（`self.__next_f.push([1,"…"])` → 按括号平衡切 `{"slug":…}` 对象 → 按 slug join 两类对象），`curl --ssl-no-revoke` 直读。生产脚本固化 `scripts/d40_fetch_artificial_analysis.py`。

**导入口径（保守，已定死）**：

| 规则 | 原因 |
|---|---|
| **仅精确匹配**（270 对） | 模糊匹配曾把 `command-a-plus` 误配到 `qwen-plus`——根因是把 `command` 当 vendor 前缀剥掉留下 `a-plus` 残渣。`gemma`/`gemini`/`phi`/`olmo`/`jamba`/`nemotron`/`lfm` 同理是**系列名不是厂牌** |
| 仅补空值 | 只对 `independent` 为空的记录写入 |
| 复合指数一律不导 | `intelligenceIndex` / `omniscience` 量程 3.75–53.37，**不是 0–1 准确率**，混入会污染跨模型对比 |
| `releaseDate` 只做精化 | 仅当主库月级 + AA 同 `YYYY-MM` 的日级时才改，不凭空造日期 |

**产出**：99 条记录 / **+913 条 independent 条目**，43 条 `release_date` 精化到日；185 条 AA 模型无对应主库记录（`gpt-5-4` / `agnes-2-5-pro-beta` / `deepseek v4-flash-vision` / `kimi k3-low` 等），已留作下一轮漏采线索。

---

## 三、第 ④ 项 B：Wave-1 增量采集 22 条

4 个批次全部 submitted，22 文件单文件门禁 ERROR 0：

| 批次 | 条数 | 模型 |
|---|---|---|
| `b329w1-openai` | 6 | GPT-5.5 Instant · GPT-4.1 Nano · GPT-5 Nano · Claude Mythos 5.1（Wave-1 遗留）· Gemini Advanced 0514 · Gemini Pro Dev API |
| `b330w1-alibaba` | 5 | Qwen3.5/3.6/3.7-Max-Preview · Qwen3.6-Plus-Preview · QwQ-32B-Preview |
| `b331w1-tencent` | 5 | Hunyuan-Standard-256K · Hunyuan-Standard-20250210 · Hunyuan-Turbo-0110 · Hunyuan-Vision-1.5-Thinking · Hunyuan-Large-Vision |
| `b332w1-deepseek` | 6 | DeepSeek-V4-Flash/Pro-High-Preview · MiMo-V2-Flash · MiMo-V2-Omni · LongCat-Flash-Chat-2602-Exp · DOLA Seed 2.0 Pro |

合并计划：`add_record=22`（无 fill_null / 无 conflict），无重复 `model_id`，与主库 915 条零碰撞。

### 采集件归一（7 个文件曾未过门禁，全部修复）

| 类 | 处数 | 问题 | 处置 |
|---|---|---|---|
| `source_type` 枚举违规 | 25 | agent 自造 `官方发布页（自报）` / `行业媒体转述官方发布` / `LMArena`，不在 D26 受控枚举内 | 按库内惯例归正（`T0-自报-转述` 主流配对 `行业媒体转述官方发布（自报）`，169 例） |
| arena 段来源虚假 | 5 组 | `source_url` 指向新闻站（news.qq.com / ithome.com）或上游 `arena.ai`；`rank`/`votes`/`ci` 被塞进 `notes` 文本 | **整段以 DataLearner 本地快照（2026-09-02）权威值重建**，补齐独立字段 |
| 日期格式 | 1 | `gemini-pro-dev-api` 的 `release_date='2024'` | 查证 Google 开发者博客（Gemini API 面向开发者开放 **2023-12-13**）→ 精确到日，状态改「已定死」 |
| 键名漂移 | 1 | `pricing.long_context` 用 `input_multiplier`/`output_multiplier` | 改规范键绝对价（$2.00 / $12.00 per M） |
| 定价生效日缺失 | 6 | 有定价无 `pricing.effective_date`（库内基线 298/298 全有） | 锚定官方发布/版本标签日；**仅知月用 `YYYY-MM` + notes 注明周期，不伪造到日** |
| 命名漂移 | 1 | `qwen-3-6-plus-preview` 与同族 `qwen3-6-plus` 不一致 | 归一为 `qwen3-6-plus-preview`（库内 `qwen3-*` 紧贴式 36 : 连字符式 3） |

### ⚠ 关键发现：采集 agent 写的 arena 分值与真值有偏差

| 模型 | 档位 | agent 记（新闻转述） | DataLearner 权威值 |
|---|---|---|---|
| `qwen3-7-max-preview` | coding | 1526 | **1525** |
| `qwen3-5-max-preview` | text | 1464 | **1466** |

核对后才写入，**未沿用新闻口径**。这印证了"榜单分数必须以镜像站结构化数据为准，新闻转述只做线索"。

---

## 四、第 ① 项：arena 快照瘦身

- 条目 **809 → 633**：同 `(model_id, sub_benchmark)` 只保留最新 `date` 一条，历史快照移除（D39 遗留副作用就此清账）。
- 归一 `is_primary`：**仅 `text` 为 `true`**，其余 `false`。初版脚本曾把所有缺失值置 `true`，与库内惯例（text 266 True / coding·math 全 False）不符，已修正。
- 删除前全量快照：`backups/model_data_v2.pre-d40-arena-slim-20260910-152340.jsonl`。

---

## 五、第 ④ 项 A：A 类历史缺口治理

D32 遗留 5 项，逐项核查后确认：

| # | 项 | 状态 |
|---|---|---|
| 2 / 3 / 4 | 已在 D33–D37 修完 | 现库 0 / 0 / 1 条 |
| 5 | `license` 缺失 | **本轮治理**：82 条缺口 → 补 36 条，余 46 条 |

**license 补全改走 HuggingFace API 作权威源**（`huggingface.co/api/models/{repo}` 的 `tags` 里读 `license:` 标签），取代此前从 notes 正则抽文本的做法（正则曾把 `HF`、`Under the MIT` 误判为许可证名）。

配套**同尺寸一致性校验**（repo 与记录的参数规模 token 取交集，空则拒写），成功拦下 `g42:jais-70b` ← `inception42/jais-13b` 这类错配。结果：写入 36 / 尺寸不符拒写 3 / repo 无 license 标签 11 / 无 repo 可定位 32。

---

## 六、合并后收尾三自检（项目强制项）

| 检查 | 结果 |
|---|---|
| 数组缩水取证 | 915 条老记录 × 5 个数组字段 → **无缩水** ✓ |
| 撞键分类 | 22 条新记录，`self_reported`(benchmark,config,date) / `independent`(+source_site) / `arena_elo`(sub_benchmark,date) → **无重复键** ✓ |
| WARN 基线差值 | 0 → **0**，未上涨 ✓ |
| model_id 唯一性 | 937 条 **无重复** ✓ |

备份：`backups/model_data_v2.pre-d40-wave1-merge-20260910-160906.jsonl`

---

## 七、遗留待拍板（需用户裁定）

### 1. 5 条 arena `sub_benchmark` 段位错置 ⚠ 需裁定

| 取值 | 条数 | 问题 |
|---|---|---|
| `search` | 1 | 不在库内主流枚举（text/coding/math/vision/webdev） |
| `LiveCodeBench Pro` | 1 | 这不是 arena 榜段位，像是把独立跑分错标进 arena 段 |
| `gdpval` | 1 | 同上 |
| `agent` | 1 | 同上 |

这 4 条的 `source_type` 标为 `LMArena 镜像（DataLearner），原始来源 LM Arena`，但实际来源存疑（语义矛盾）。**属跨段位迁移还是移除，需用户裁定，本轮未自动处置。**

### 2. `bytedance:dola-seed-2-0-pro:base` 信息过薄

仅 arena 数据（text 1456 / coding 1513 / math 1451），无 `release_date`、无定价、无架构——AA 与 OpenRouter 均无此模型，采集 agent 自评"可信度偏低，建议主 agent 复核"。**是否保留待定。**

### 3. vendor 大小写混乱

库内并存 `Google` / `google`、`Alibaba` / `Alibaba Cloud` / `Alibaba (Qwen Team)` 等写法，`model_id` 前缀与 `basic_info.vendor` 脱钩（D34 扫描 A7：85 条），会导致按厂商聚合时漏计/错分。**未批量整改**（牵动已入库记录，需单独一轮）。

### 4. Qwen 命名双轨

`qwen3-*`（36）vs `qwen-3-*`（3：`qwen-3-5-flash` / `qwen-3-6-27b` / `qwen-3-8-max`）。本轮只归一了新入库的 1 条，老记录未动。**建议下一轮统一。**

### 5. license 仍有 46 条空白

其中 32 条无 HF repo 可定位（官方站多为沙盒不可达或纯闭源商业模型），需人工定点补。

---

## 八、环境坑（已写入 `docs/跟踪源清单.md` §C-2）

1. **AA 的 API 401 不代表数据拿不到**——榜单页 flight 流里就是完整评测矩阵，`curl --ssl-no-revoke` 直读，无需装浏览器。
2. **DataLearner 的 coding / math 榜没有独立 API**——对应端点返 HTML 而非 JSON（`json.load` 报 `Expecting value: line 1 column 1`），须存 `.html` 再解析表格；且**模型名可能只出现在 `<a href>` / `aria-label` 属性里**（如 Qwen3.6-Max-Preview 行），按可见文本匹配会整行漏掉。

---

## 九、本轮产出文件

| 类别 | 文件 |
|---|---|
| 数据 | `model_data_v2.jsonl`（937 条） |
| 台账 | `docs/batch_claim_ledger.jsonl`（b329w1~b332w1 置 submitted） |
| 变更日志 | `CHANGELOG.md`（[D40] 条目） |
| 源清单 | `docs/跟踪源清单.md`（C 层新增 AA 接入 + C-2 小节） |
| 生产脚本 | `scripts/d40_fetch_artificial_analysis.py` · `scripts/d40_aa_import.py` · `scripts/d40_license_hf.py` · `scripts/d40_postcheck.py` |
| 备份 | `backups/model_data_v2.pre-d40-arena-slim-20260910-152340.jsonl`（快照瘦身前）<br>`backups/model_data_v2.pre-d40-licensehf-20260910-153408.jsonl`<br>`backups/model_data_v2.pre-d40-aa-20260910-153931.jsonl`<br>`backups/model_data_v2.pre-d40-wave1-merge-20260910-160906.jsonl`（合并前） |
| 中间产物 | `temp/d40_aa_models.json` · `temp/d40_incoming_orig/`（采集原件留档） |

---

_报告生成于 D40 收尾，主库门禁 ERROR 0 / WARN 0。_
