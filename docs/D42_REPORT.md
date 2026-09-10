# D42 轮次报告：model_id 点号口径统一（小数用 `.`）

> 轮次日期：2026-09-10 ｜ 触发：用户「点号问题有什么解决方案吗，你设计一下然后一起改了」
> 主库：**937 条不变**（零增删）｜ 门禁：**ERROR 0 / WARN 0** ｜ 改名：**317 条记录 / 314 个 family**

---

## 一、结论摘要

| 项目 | 结果 |
|---|---|
| 规范 | `family` / `variant` 段中**官方名称里的小数点一律写 `.`**，`-` 只作 token 分隔符 |
| 判据 | **证据驱动**——仅当字面串 `a.b` 出现在该记录 `full_name` 或 `version` 原文中才转换 |
| 改名 | 314 family / 317 记录（占全库 33.8%） |
| 证据来源 | `full_name` 94 ／ `version` 10 ／ 两者兼有 206 ／ 亲缘继承 3 ／ 人工补录 1 |
| 碰撞 | **0**（含跨 family 组内撞名预检） |
| 未改（无小数证据） | 120 family（日期、整数参数量、模型名内嵌数字——本就不该有点号） |
| 显式排除 | 1 family（`s1-1`，属结构问题非点号问题，见 §六） |
| 收尾自检 | 5 项 **ALL PASS**（仅点号位变化、无缩水、无重名、无残留） |
| 规范同步 | `docs/prompt.md` §6.4 新增点号条款，并**废止**与之冲突的 P1 禁令 |
| 台账 | `models` 数组同步 **156 处**（`submitted_files` 保持历史文件名不改写） |

---

## 二、问题定义：为什么必须修

`model_id` 的 `family` 段里，小数点长期被写成连字符，与 token 分隔符**共用同一字符**，导致数字连串**无法机械切分**：

| 现状 | 两种读法 | 哪个对 |
|---|---|---|
| `qwen-3-1-7b` | Qwen3 + 1.7B ／ Qwen3.1 + 7B | 前者（Qwen3-1.7B） |
| `qwen-3-5-max-preview` | Qwen3.5 ／ Qwen3 + 5B？ | 前者（Qwen3.5 Max） |
| `exaone-3-5-2-4b` | 3.5+2.4B ／ 3+5.24B ／ 3.5.2+4B | 第一种（EXAONE 3.5 2.4B） |
| `llama-3-1-typhoon-2-70b` | Llama3.1 + Typhoon2 + 70B | 唯一合理读法，但无法从字面判定 |
| `sea-lion-v3-llama3-1-70b` | Llama 3.1 70B（**不是** 1.70B） | 需领域知识才能切 |

关键反证：**纯连字符风格无法用任何正则/启发式可靠解析**。以 `qwen1-5-7b`（Qwen1.5-7B）与 `qwen2-5-1-5b`（Qwen2.5-1.5B）为例，两者都是「数字-数字-数字」结构，但前者的 7B 是整数量纲、后者末两位 `1-5b` 是小数参数量——任何「取末两位为参数量」的规则都会在其中一个上出错。

因此这是**数据可解析性缺陷**，不是风格偏好；必须引入与分隔符不同的小数点字符。

---

## 三、规范设计

### 3.1 规则

在 `docs/prompt.md` §6.4 三段式基础上补一条强制条款：

> `family` 与 `variant` 段中，**凡官方名称里的小数点一律写作 `.`**；`-` 只作 token 分隔符，不得用来代替小数点。

- 版本号含小数 → 点：`claude-opus-4.5`、`deepseek-v3.1`、`qwen-3.5-max-preview`、`gemini-2.5-pro`
- 参数量含小数 → 点：`qwen-3-1.7b`、`exaone-3.5-2.4b`、`qwen2.5-1.5b`、`granite-3.0-2b`
- **非小数点的连字符一律保留**：
  - 快照日期：`claude-opus-4-20250514-16k`、`gpt-5.4-mini-2026-03-17-xhigh`、`gemini-2.5-flash-preview-04-17`
  - 整数参数量：`qwen-2-57b-a14b`（`A14B`）、`minimax-m1-40k`、`deepseek-coder-v2-236b`、`nemotron-4-340b`
  - 模型名内嵌数字：`baichuan2-13b`、`telechat2-115b`、`llama-2-70b`、`agentar-fin-r1-32b`、`p1-235b-a22b`

### 3.2 判据（机械可复现，非人工逐条判断）

对 `family` 中每一处「数字-数字」的连字符，取左右两侧**最大连续数字串** `a`、`b`，**仅当字面串 `a.b` 出现在证据文本中**才判为小数点：

```
qwen-3-1-7b   full_name='Qwen3-1.7B'
  ├ '-' 在 3|1 之间 → 查 '3.1'  → 不在证据中 → 保留 '-'
  └ '-' 在 1|7 之间 → 查 '1.7'  → 命中       → 替换 '.'   ⇒ qwen-3-1.7b ✓
```

该判据天然排除全部非小数点场景：
- 日期 `2025-09-23` → `2025.09` 不会出现在原文
- 整数参数量 `r1-32b` → `1.32` 不会出现在原文
- 模型名内嵌 `telechat2-115b` → `2.115` 不会出现在原文
- **反例保护**：`qwen-3-8b`（Qwen3-8B，第 3 代 80 亿参数）的 `full_name` 为 `Qwen3-8B`，不含 `3.8`，故**不会**被误改成 `qwen-3.8b` ✓

### 3.3 证据来源优先级（实现见 `scripts/d42_dots.py`）

1. **`basic_info.full_name`**——库内该字段**完整保留点号**（`Qwen3-1.7B`、`EXAONE 3.5 2.4B`、`abab 6.5`、`BitNet b1.58`），是最主要权威源
2. **`basic_info.version`**——`full_name` 本身也写成连字符时兜底（典型：Anthropic 系列 `full_name='claude-opus-4-5-20251101'` 无点号，但 `version='4.5'` 有）
3. **亲缘继承**——同一模型的截断写法（严格 token 边界扩展关系，如 `claude-3-7-sonnet` ← `claude-3-7-sonnet-20250219-16k`、`grok-4-20` ← `grok-4-20-0309-reasoning`）共享证据，避免「父改子未改」的风格分裂
4. **下划线小数点**——`Qwen-1_8B`、`OpenELM-1_1B` 用 `_` 代替小数点；仅在**两侧均为单个数字**时才认定（该约束排除了 `claude-opus-4-20250514_16K` 这类 `_16K` 变体后缀）
5. **人工补录**——`claude-3-5-sonnet` → `claude-3.5-sonnet`（该家族既无点号证据也无扩展名家族，依据 Anthropic 官方名 `Claude 3.5 Sonnet`）

---

## 四、实施与核验

### 4.1 规模

| 指标 | 值 |
|---|---|
| 记录数 | 937 → **937**（零增删） |
| family 数 | 919 → **917**（见 §六 说明：`glm-4.5`/`glm-4.6` 跨厂商同名，主键不撞） |
| family 含点号 | **6 → 318** |
| 改名记录 | **317**（占 33.8%） |
| 重命名碰撞 | **0** |
| 改名留痕 | 每条 `meta.notes` 追加 `【D42 点号归一】原 model_id: X → Y` |

### 4.2 代表性案例

| 旧 | 新 | 意义 |
|---|---|---|
| `alibaba:qwen-3-1-7b:base` | `alibaba:qwen-3-1.7b:base` | **本轮要解决的核心歧义**：Qwen3-1.7B 不再可能读成 Qwen3.1-7B |
| `alibaba:qwen-3-5-max-preview:base` | `alibaba:qwen-3.5-max-preview:base` | Qwen3.5 世代显式化 |
| `lg:exaone-3-5-2-4b:base` | `lg:exaone-3.5-2.4b:base` | 版本与参数量双小数，此前完全不可切分 |
| `anthropic:claude-opus-4-5:20251101` | `anthropic:claude-opus-4.5:20251101` | 与 `claude-opus-4-20250514-16k`（Opus 4，无小数）区分开 |
| `microsoft:bitnet-b1-58:base` | `microsoft:bitnet-b1.58:base` | 参数量小数（1.58-bit） |
| `qihoo-360:360zhinao3-7b-o1-5:base` | `qihoo-360:360zhinao3-7b-o1.5:base` | 尾部 token 小数 |
| `mahidol-...:openthaigpt-v1-0-0:base` | `mahidol-...:openthaigpt-v1.0.0:base` | 连缀小数（`1.0.0`），需前瞻匹配才能全部还原 |
| `apple:openelm-1-1b:base` | `apple:openelm-1.1b:base` | 下划线小数点还原 |
| `xai:grok-4-20:base` | `xai:grok-4.20:base` | Grok 4.20 |
| `alibaba:qwen-3-8b:base` | **不变** | **反例保护**：Qwen3-8B 是第 3 代 80 亿，不是 Qwen 3.8 |

### 4.3 收尾自检（`scripts/d42_postcheck.py`，5 项全过）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | `model_id` 唯一性 | PASS |
| 2 | 仅点号位变化（317 条逐条比对：`新family.replace('.','-') == 旧family`，且 vendor/variant 段未动） | PASS |
| 3 | 数组缩水取证（对照 `pre-d42-dots` 备份，三数组字段） | PASS（0 处） |
| 4 | 记录数与字段数 | PASS |
| 5 | 可证伪的连字符残留（family 中仍有 `a-b` 而证据含 `a.b`） | PASS（0 处） |

---

## 五、与既有规范的冲突处理

**动手前发现的冲突**：`docs/prompt.md` §6.4 的「执行约束（P1 修复）」原文写着——

> 花名册中 `in_v1` 的模型……**原样沿用花名册中的 model_id**，**严禁「纠正」为点号或营销代号风格**

这条禁令与「小数点用 `.`」直接矛盾，必须显式处理。已按以下方式修订：

- 该禁令**已废止**，并在 §6.4 注明「与旧版 P1 的差异」及其废止理由；
- 但**保留其原本意图**：采集 agent 仍**不得**自行改写 model_id、不得借改名绕过「同模型必须合并而非新建」的约束；
- 新增一句划分职责：**存量归一由主 agent 在专项轮次执行**（含改名留痕、碰撞预检、台账同步），采集期不变。

之所以原文会写成这样，是因为 v1 库存量的 model_id 源自「连字符 family + `:base`」风格，当时点号并非既定规范；D41 已按用户裁定把 Qwen 世代统一为 `qwen-3-*`（连字符），本轮进一步把**小数点**这一独立维度定死。

---

## 六、遗留与下一轮建议

### 6.1 本轮显式排除 1 例（属结构问题，非点号问题）

**`allen-institute-for-ai` 的 s1 家族**三兄弟语义不自洽，转成点号会与兄弟条目读法冲突：

| model_id | full_name | version | 问题 |
|---|---|---|---|
| `allen-institute-for-ai:s1:base` | `s1-32B` | `1.0` | family 未编码版本与参数量 |
| `allen-institute-for-ai:s1-1:base` | `s1.1-1.5B` | `1.1` | `-1` 若读作版本 1.1，则与 `s1-32b` 的读法冲突；若读作参数量则与 full_name 冲突 |
| `allen-institute-for-ai:s1-32b:base` | `s1.1-32B` | `1.1` | family 缺 `.1`（版本），全文 `s1.1` |

**建议**：按 `s1-1.5b` / `s1-32b`（family = 模型名 + 参数量）或 `s1.1-1.5b` / `s1.1-32b`（family 含版本）二选一重命名，需先定 family 语义（是否编码参数量）。

### 6.2 其他结构性命名问题（同属「family 串缺信息或数字语义不唯一」，非点号问题）

| model_id | full_name / version | 建议 |
|---|---|---|
| `saltlux:luxia-21-4b-alignment:base` | `Saltlux Luxia 2.1 4B Alignment` | family 的 `21` 应为 `2-1`（2.1）——缺分隔符，非点号问题 |
| `allen-institute-for-ai:olmo-3-32b-instruct:base` | full_name 明示「官方发布名 Olmo 3.1 Instruct 32B」，version `3.1`（HF 仓库 `allenai/Olmo-3.1-32B-Instruct`） | family 应为 `olmo-3.1-32b-instruct`——缺版本位，非点号问题 |
| `modelbest:minicpm-1-2b:base` | `MiniCPM-1B`（version `2.0`） | family 的 `1-2b` 与 full_name 的 `1B` 矛盾；同族 `minicpm-2-4b`（full `MiniCPM-2B`）同样矛盾。需核对官方命名与参数量后统一 |
| `xai:grok-4-20-0309-reasoning:base` | `Grok 4 (Reasoning)` | 已随父 family 归一为 `grok-4.20-0309-reasoning`，但该条自身证据薄弱（full_name 未写 4.20），建议补信源 |

### 6.3 旁发现的 vendor 别名问题（非本轮范围）

归一只看 `family` 段，本轮不做 vendor 归并，但顺带发现：

- `z-ai-zhipu-ai-tsinghua-university` 与 `zhipu` 两个 vendor 前缀下**同时存在** `glm-4.5` / `glm-4.6`（family 名归一后重合，主键因 vendor 不同而不撞）。这是「同厂多写法」的 vendor 别名问题，与 D41 未合并的多主体联合串属同类，建议后续按 `intermediate/vendor_alias.json` 的口径统一裁定。

### 6.4 残留旧 model_id 引用裁定（活文档扫描）

改完主库后，对全仓活文档做了一次旧 id 反向扫描，逐处裁定如下（沿用 D41 约定：**历史归档与案例引用不改写**，只登记）：

| 位置 | 旧 id | 性质 | 裁定 |
|---|---|---|---|
| `docs/batch_claim_ledger.jsonl`（`b60w1-google-deepmind-google` 批，3 处） | `google-deepmind-google:...` | 该批记录**不在主库**（主库用 `google:` 前缀），属另一条 vendor 漂移问题 | **不动**（`d42_ledger_sync.py` 已正确跳过；另立下一轮议题） |
| `docs/WORKBUDDY_AGENT_GUIDE.md`（7 处） | `alibaba:qwen2-1-5b:base` 等 | §27 历史的探针载体引用 | **不动**（历史案例，非现行数据引用） |
| `docs/prompt.md` L779 | `cognition:swe-1-6:base` | 决策 2 的历史判例引用 | **不动**（历史案例；现行条款已由 §6.4 统一） |
| `docs/增量更新工作流.md` L103 / L164 | `alibaba:qwen-3-8-max:base` | 某轮检测结论的**历史留痕** | **不动**（历史归档） |
| `docs/multi_platform_subagent_guide.md` L166 | `google:gemini-3-5-flash-minimal:base` | 文件命名**格式示例**（"例如"） | **同步改写 + 加注记**（唯一被 agent 照抄的操作型模板） |
| `scripts/d21_fix_qwen_coder_14b.py` / `d41_dola_arena.py` / `d41_normalize.py` | `bytedance:dola-seed-2-0-pro:base` | 一次性历史脚本 | **不动**（脚本即留痕，改了反而失去可复现性） |
| `intermediate/conflicts.json` / `merge_apply_log.txt` | 多处 | 中间态文件 | **不动**（非交付物） |

> 说明：`model_data_v2.jsonl` 内 317 处旧 id 命中**全部**来自本轮写入的 `meta.notes` 变更留痕（"原 model_id: … → …"），属预期。

判据归纳（可复用到后续改名轮）：**「agent 会不会照抄它」**——会被照抄的操作型模板（命名示例、模板变量）同步改写并加注记；历史叙事、判例引用、归档留痕、一次性脚本一律不动。

---

## 七、产物

| 类型 | 文件 |
|---|---|
| 规范 | `docs/prompt.md` §6.4（新增点号条款 + P1 禁令废止说明）、决策表第 6 项 |
| 活文档同步 | `docs/multi_platform_subagent_guide.md` 文件命名示例（1 处，见 §6.4） |
| 脚本 | `scripts/d42_dots.py`（归一，含证据池/亲缘继承/碰撞预检）、`scripts/d42_ledger_sync.py`、`scripts/d42_postcheck.py` |
| 台账 | `docs/batch_claim_ledger.jsonl`（`models` 字段 156 处） |
| 留痕 | `model_data_v2.jsonl` 每条 317 条记录的 `meta.notes` |
| 备份 | `backups/model_data_v2.pre-d42-dots-20260910-170858.jsonl` |
| 日志 | `CHANGELOG.md` [D42] |
