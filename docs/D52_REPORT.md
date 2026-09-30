# D52 轮次报告：D51 三遗留清账 + S0 口径升级 + 体检器扩容 31 项 + G3/G4 处置

> 日期：2026-10-01。触发方式：用户（原话「A 全 / B 全 / C 前三 / 按序开始做」）。
> 记录数 **977 → 982（+5）**，门禁 **ERROR 0 / WARN 0**；qa_outliers 终态 **r1=0 / r2=0**，硬错为既有存量 `o1=4` / `c4=2`。
> 上轮：D51（2026-09-30）17 天空窗全量 S0 + G1/G2 采集 17 行入库（960 → 977）。本轮处理 D51 全部 3 项遗留 + D50 遗留的体检器扩容。

## 一、本轮工作集（用户拍板）

| 组 | 项 | 内容 | 状态 |
|---|---|---|---|
| A | A | 把 D51 提交推送到 `origin/main` | ✅ |
| B | B1 | xAI → SpaceXAI vendor 归一 | ✅ |
| B | B2 | `muse-spark-1.3` 家族定价复验 | ✅ |
| B | B3 | `glm-5.3-max` 补派立行 | ✅ |
| C | C1 | S0 口径升级为 D39 式全量榜单反推 + 执行补漏 | ✅ |
| C | C2 | `qa_outliers` 扩容至 D31/D34 原 31 项口径 | ✅ |
| C | C3 | G3 立行 + G4 组件并入 | ✅ |
| — | C4（**未选**） | backlog 948 条存量长尾补全 | ⛔ 本轮不做 |

---

## 二、A · 推送 D51 提交

`f6033fc..3b897ff main -> main`，ahead 归零。

**过程坑（已解）**：`git push` 报 `SSL certificate problem: unable to get local issuer certificate`。

- 排查：`unset HTTP_PROXY/HTTPS_PROXY` 后仍失败；curl 直连 github 200 正常；`git config` 显示 `http.sslBackend=openssl` + `http.sslCAInfo=E:/System_Programes/Git/mingw64/etc/ssl/certs/ca-bundle.crt`（2024-07-29 旧包）。
- 试验：`schannel` 后端 `ls-remote` 成功；旧包的 `ca-bundle.trust.crt` 失败。
- **解法**：`git -c http.sslBackend=schannel -c http.schannelCheckRevoke=false push origin main`（走 Windows 证书库）。
- 注：既有记忆 `reference_github_tls_interception_workaround` 称「git 不受本机 TLS 拦截影响」，**本轮回测已不适用**，属新签名，已更新记忆。

---

## 三、B1 · xAI → SpaceXAI vendor 归一（21 条）

**改动范围**：只改 `basic_info.vendor` 显示名 `xAI` → `SpaceXAI`，**`model_id` 前缀 `xai:` 保留不动**。

**判据（为什么不动前缀）**：库内存在 **295 条**「model_id 前缀 ≠ vendor 显示名」的反例（前缀是**短品牌 slug**，不是 vendor 显示名的规范形）。若随厂商改名改前缀，会引发主键/台账/脚本/文档的大范围漂移，收益与风险不匹配。

**执行**：`temp/d52/d52_vendor_norm.py`（dry-run → `--apply`），断言命中 21 条、总条数不变、`model_id` 零漂移，回读自证通过。

**文档同步**（前缀与厂商举例）：`docs/prompt.md` 3 处（厂商清单 / 厂商举例 / vendor 示例）、`docs/跟踪源清单.md` 4 处（两处表格行 + 待办行）。

**台账**：`docs/batch_claim_ledger.jsonl` 的 `vendor` 字段按 D43 约定是「批次登记身份」历史字段，未改 xAI 那几行。

---

## 四、B2 · `muse-spark-1.3` 家族定价改判

**原疑点（D51 遗留）**：库内该家族 base 行 `$0.10/$0.20/$0.01`，官方域不可达无法复验；数值恰等于 OpenRouter 上 `muse-spark-1.3-contributor` 报价，而 AA/OR 对 `-max` 观测为 `$1.25/$4.25`（差 12.5×）⇒ 疑「当年把 contributor 刊例误读成 base 刊例」。

**本轮证据链闭合**：

| 源 | 观测 | 结论 |
|---|---|---|
| OpenRouter 快照 | `meta/muse-spark-1.3-contributor` = `$0.10/$0.20/$0.01` | 与库内三值**逐一全等** ⇒ 误读成立 |
| OpenRouter 快照 | `meta/muse-spark-1.3` = `$1.25/$4.25/$0.15` | base 的**正确**刊例 |
| Artificial Analysis | slug `muse-spark-1-3` / `1-2` / `1-1` 均 `$1.25/$4.25/$0.15` | 双源互证 |
| 官方域（developer.meta.com / ai.meta.com / www.llama.com） | 2026-10-01 复测仍 443 超时 | 降级，不可作 T0 依据 |

**改动（4 行）**：`temp/d52/d52_musespark_price.py`

- `S13`：`1.3 base` 从 `$0.10/$0.20/$0.01` 改判为 **`$1.25/$4.25/$0.15`**；`confidence T0 → T1`；`source_url` 转 AA；`effective_date 2026-10-01`。硬断言：改前必须精确等于 `0.1 / 0.2 / 0.01`。
- `S11`：`1.1` / `1.2` 的 `confidence T0 → T1` + `source_url` 从 `m.toutiao.com` 转 AA（**金额不变**）。
- `SMAX`：`1.3-max` 追加「裁决②结案留痕」。

**副产品（未批量改，超本轮范围）**：发现库内 **32 条** `pricing.confidence=T0` 却挂评测平台/非官方源的系统性归因缺陷（含 1.1/1.2 两条），已在 notes 留痕，建议下轮专项。

---

## 五、B3 · `glm-5.3-max` 补派立行

**为什么 D51 漏了**：它 09-11 就已在 Arena 榜上，D51 的**差集式** S0 只覆盖「相对基线新增」⇒ 结构性捞不到。本轮直接按已知证据立行（b347w1）。

- `model_id`：`zhipu:glm-5.3-max:base`
- Arena 2026-09-25 三榜独立 elo：text **1480**（r24 / votes 15904 / ci 6）、coding **1522**（r29 / 4034 / ci 10）、math **1497**（r16 / 638 / ci 23）
- `full_name: 'GLM-5.3 (max reasoning effort)'`、`reasoning_model: True`、`thinkingMode=max` ⇒ 按「独立测量身份」立行
- 其余字段继承同族 `zhipu:glm-5.3:base`（753B/40B MoE、ctx 1M、`$1.1255/$3.9394/$0.2814`、MIT）
- 台账追加 `b347w1`（round D52）

---

## 六、C1 · S0 口径升级（差集式 → 双轨）

**根因（方法失传）**：D39 曾用「榜单全量反推」（找出**基线期已上榜但未采**的条目）发现 84 条漏采，但脚本落在 `temp/`、被清理后**方法失传**；D40–D51 因此退回差集式，`glm-5.3-max` 这类漏项反复出现。

**本轮措施**：

1. D39 一次性脚本固化为常驻工具 **`scripts/arena_gap_reverse.py`**（`--raw` / `--out-dir` / `--main`）。
   - 命中判定：先 `modelCode` 再 `modelName`（去变体标记归一）
   - `difflib` 相似度 ≥ 0.72 ⇒ 判「疑似命名差异」；额外自动打标 `ANON`（匿名/实验代号）与 `LEGACY`（老社区模型）
   - 已修 pyright：`importlib.util.spec_from_file_location` 返回值可空 → 加显式 None 检查（3 errors → 0）
2. 写进 `docs/增量更新工作流.md`：新增 **§1.1 S0-a 差集式（新面孔）** 与 **§1.2 S0-b 榜单全量反推（必做，不是可选）**，并记录立规起因与三类需剔除项。

**本轮实跑结果**（快照 2026-09-25）：未命中 216 条 → 命名差异 146 / **真漏采 70**（匿名 6 / 社区 19 / 待核 45），明细 `temp/d52/arena_gap_candidates.jsonl`，**待用户点单**。

> 已辨明的两个假阳性：`Opus 4.5`（库内已有 `anthropic:claude-opus-4.5-20251101-32k:base`）、`glm-5.2-max`（落「命名差异」档，库内已有 `zhipu:glm-5.2:base`）。

---

## 七、C2 · `qa_outliers.py` 扩容 16 → 31 项

D50 遗留项。D46 重建时只有 13 项注册检查 + 3 项跨记录（r1/r2/v3）；本轮补回 **D34 原 31 项口径**。

**口径来源**：幸存的 `temp/d34_a_class_report.md`（A1–A8 方向与数值）+ `temp/d34_scan_a_class.py`（800 行，逐条抄回判定实现与阈值）。

**新增 14 项注册检查 + 1 项跨记录（a6）**：`a2` `a3` `a4a` `a4b` `a5` `a7` `a8a` `a8b` `a8c` `p1` `p2` `b1` `b2` `n1` + `a6`（同厂商同代系指纹簇）。

**终态基线（982 条）**：

```
硬错：o1=4 | c4=2 | 其余 o2/o4/o5/o6/c1/c3/c6 全 0
疑点：o3=13 | c5=19 | v1=53 | a2=220 | a3=361 | a4a=41 | a4b=3 | a5=63
      a7=414 | a8a=22 | a8b=73 | a8c=49 | p1=7 | p2=2 | b2=10
跨记录：r1=0 | r2=0 | a6=17
检查项：27 项注册 + r1/r2/a6 三项跨记录 = 30 项缺陷检查，加 v3 覆盖率 ⇒ 共 31 项
```

**判据缺陷三处校准（初版自引入、当轮修正）**：

| 项 | 初版问题 | 校准 |
|---|---|---|
| `p1` 价格半填 | 按「硬错」分级，16 条里 **11 条是 embedding 类**——嵌入模型只按输入 token 计费、**本无输出价**，属行业事实而非缺陷 | 跳过**非生成式模型**（族名/vendor 正则：`embed\|rerank\|colbert\|splade\|bge\|gte-\|e5-\|voyage\|jina-emb`）+ 降为「疑点」⇒ 16 → 7 |
| `p2` batch ≥ 标准 | 用 `>=`，跑出 `bytedance:doubao-function-call-model` 的 batch **等于**标准价 | 官方口径（火山方舟批量推理标价与在线相同）**有 T0 注证** ⇒ 改严格 `>`，3 → 2 |
| `a4b` pdf⇒image | 按「硬错」，跑出 3 条：`deepl-llm`（notes 写明 pdf 指产品文档翻译能力）、mistral 两条（采集缺口） | 属口径差 / 缺口而非不可能值 ⇒ 降为「疑点」 |

**另修两处真缺陷**：

- **`a8a` 的 `NC ` 误报**：原实现对全部模式做大小写不敏感子串匹配，`'NC '` 会命中**域名里的 "inc "**（实测 `sales@perceptron.inc 获取商业许可` 被判「可能含非商用条款」）⇒ `'NC '` 改为**区分大小写的词边界正则** `\bNC\b`。**影响面实测：全库 0 条**记录仅靠该子串命中 ⇒ 纯消误报、不动基线。
- **`r2` 漂移**（见 §九 质检）。

**文档同步**：`docs/增量更新工作流.md` §5 的过时引用 `temp/d34_scan_outliers.py` 更新为 `scripts/qa_outliers.py`，并写明脚本沿革（D34 `rm` 直删不可恢复 → D46 重建为 16 项 → D52 扩容至 31 项）+ 分级基线 + 判读规则。

---

## 八、C3 · G3 立行 + G4 组件并入

### 8.1 G3 工作集澄清（溯源）

D51 报告 §一 写「G3 新厂商 **7 条**」，但其 §七 只列出 **6 个名字**；CHANGELOG D51 的 Note 列出的 7 条含 **`Qwen3.8-27B free`** —— 该条 D51 已按「服务档 `notes` 留痕」处理（不立行）。

⇒ **C3 有效工作集 = 6 条**，与报告 §七 明确列出的名单一致。

### 8.2 S1 身份判定（第 0 步强制）

| 候选 | 判定 | 关键证据（逐字） | 结果 |
|---|---|---|---|
| `BAAI AREX-2` | ✅ 模型本体 | 官方 ModelScope README：「AREX-2 is a 27B-parameter long-horizon **agent model**」；`ModelType=[qwen3_5]`、`Architectures=[Qwen3_5ForConditionalGeneration]`、`BaseModel=Qwen/Qwen3.8-27B`、safetensors 27,356,728,560 | 立行 |
| `Fireworks Ember-1` | ✅ 模型本体 | 官方博客：「**Ember-1 is Fireworks' own model** and the first in a series of models from Fireworks Research」「Built on Kimi K3… the model had to learn to reason more efficiently, and that meant training it」 | 立行 |
| `InclusionAI Realtime-Venus` | ✅ 模型本体 | 官方 README：「This repository hosts two checkpoints… Both directories contain **model weights** and custom Hugging Face Transformers code」；配套 Harness/browser demo 属独立组件，已注明边界 | 立行 |
| `Perceptron Mk1.5` | ✅ 模型本体 | 官方博客：「Today we're releasing Perceptron Mk1.5: **a model built to control embodied agents**」；官方文档给 `Model ID = perceptron-mk1.5` + 规格表 + 定价表 + chat-completions 端点 | 立行 |
| `Unbiased Pareto` | ❌ **非范围** | 官方条款 §1：「**Pareto** means Company's proprietary blended AI model … which **combines outputs from multiple underlying large language models** … and synthesizes such outputs into a single response」；官网：「**Not a router**」+「Pareto runs a mix of frontier and open source models against each other on every request」 | 剔除（§23(b)） |
| `PrismML Ternary-Bonsai-2-27B` | ❌ **非范围** | 官方博客标题：「Introducing Bonsai 2 27B: **Near-Lossless Compression** in a 9x Smaller Footprint」；正文：「**Based on Qwen3.8 27B**」「uses ternary {−1, 0, +1} weights … **applied end to end**」；HF 仓仅 `-gguf`（PTQ1_0 / PQ2_0 / MLX） | 剔除（`prompt.md` L41 排除量化变体） |

### 8.3 采集结果（b348w1，4 条）

| model_id | 厂商 | release_date | 参数量 | ctx | 定价（per 1M） | confidence |
|---|---|---|---|---|---|---|
| `baai:arex-2:base` | BAAI | 2026-09（无发布公告，仓库创建日作月级锚） | 27.36B Dense（混合注意力） | 262144 | 无官方 API 价（null） | T0 |
| `fireworks:ember-1:base` | Fireworks AI | 2026-09-23 | 2.78T MoE（active 未披露） | 1048576 | $3.0 / $15.0 / cached $0.3 | T0 |
| `inclusionai:realtime-venus:base` | InclusionAI | 2026-09-12（arXiv v1） | 9.0B Dense | 40960 | 无官方 API 价（null） | T0 |
| `perceptron:perceptron-mk1.5:base` | Perceptron | 2026-09-25 | 未披露 | 36864 | $0.15 / $1.5 / cached $0.0375 | T0 |

- 自报跑分：AREX-2 **6 条**（GAIA 0.922 / BrowseComp 0.84 / DeepSearchQA 0.938 / MLE-Lite 0.818 / Frontier-CS 0.707 / HLE 0.526）；ember-1 **5 条**；Realtime-Venus **25 条**（arXiv Table 2–8）；Mk1.5 **17 条**（官方以**图片**发布跑分 ⇒ 经媒体转述，标 `T0-自报-转述`）。
- 新厂商节点 **2 个**：`fireworks`、`perceptron`。
- 单文件门禁逐条复跑（独立复核，不采信 agent 自述）：**4/4 ERROR 0 / WARN 0**。

### 8.4 G4 组件并入（不立行）

| 组件 | 规模 | 官方逐字证据 | 并入目标 |
|---|---|---|---|
| `Nex-N2.5-Max-DSpark` | 77.5B / BF16 / block 5 | 「A DSpark **draft model** for speculative decoding with Nex-N2.5-Max」「This repository contains only the draft model. **It is not a standalone language model** … The output distribution is that of Nex-N2.5-Max; the draft model only reduces latency」（tags: `speculative-decoding` / `dspark` / `sglang`） | `nex-agi:nex-n2.5-max:base` |
| `Nex-N2.5-Pro-DFlash` | 1.29B / BF16 / block 16 | 「A DFlash **draft model** for speculative decoding with Nex-N2.5-Pro」「**not a standalone language model** … The output distribution is that of Nex-N2.5-Pro」（tags: `speculative-decoding` / `dflash` / `sglang`） | `nex-agi:nex-n2.5-pro:base` |

- 旁证：ModelScope API 显示 `Pro-DFlash` 的 `Architectures=["DFlashDraftModel"]`、`model_size=1,291,904,512`；基座 `Nex-N2.5-Max` 为 `1,600,787,478,430`（1.6T），DSpark 仅为其 1/20。
- 执行：`temp/d52/d52_g4_component_notes.py`（dry-run → `--apply`），断言条数不变、非目标行逐字节不变、留痕文本落盘、换行计数自证。
- 判例：同 D46 `inclusionai:ling-3.0-flash:base` ← `Ling-3.0-flash-dspark`（官方称 speculator ⇒ 不单列）。
- ⚠ 防混淆注记已写入 notes：DSpark 的「77.5B」是**草稿模型自身规模**，不是 Nex-N2.5-Max 的规模。

---

## 九、S3/S4 质检

- **合并**：4 条全为 `add_record`（零字段冲突），命令沿用 `增量更新工作流.md` §4 口径（`--on-null take_source --on-both source_wins --on-array replace --on-schema upgrade --tie-breaker keep_target`）；改前基线另存 `temp/d52/premerge_b348w1_model_data_v2.jsonl`。
- **全库门禁**：982 条 **ERROR 0 / WARN 0**（基线保持）。
- **qa_outliers 相对上一轮的变化，全部可解释**：

| 项 | 变化 | 原因 |
|---|---|---|
| `a3` | 359 → 361 | 新增 2 条 Dense 模型（active == total） |
| `a7` | 411 → 414 | 新增 3 条 `version` 与 `full_name` 冗余（库内 411 条的普遍现象） |
| `a8b` | 72 → 73 | ember-1 的闭源 license 与库内 35 条同款，同属「已填未分类」 |
| `a8a` | 22 → 22 | `NC ` 误报修复抵消了新增命中 |
| `r1` / `r2` | 0 / 0 | 见下 |

- **本轮自引入并当轮修复的 `r2` 漂移**：新入库 `inclusionai:realtime-venus` 的基准名 `MMAU-Pro` 与库内 `dots-studio:dots3-note-preview` 的 `MMAU-PRO` 构成「基准名仅大小写异写」簇，使 `r2` 由 0 升至 1。
  - 归一依据（三重）：① 官方名 = `MMAU-Pro`（arXiv:2508.13992 标题 + 项目页 `sonalkum.github.io/mmau-pro`）；② 库内 **188+ 条** `-Pro` 惯例（MMLU-Pro 135 / MMMU-Pro 46 / ScreenSpot-Pro / SWE-Pro / KMMLU-Pro…），`MMAU-PRO` 是全库**唯一**全大写实例；③ 新记录本据 arXiv 原文写作 `MMAU-Pro`。
  - 处置：改**存量**那条为 `MMAU-Pro`（`temp/d52/d52_r2_fix_mmau.py`，带幂等守卫 + 单串断言 + 换行自证），复检 **`r2=0`**。
- **格式一致性收尾**（不影响语义，经往返断言）：`perceptron` 采集文件原用紧凑分隔符，归一到库内默认带空格序列化；台账 `b347w1` 行原用带空格分隔符，归一到台账主流的紧凑格式。

---

## 十、遗留与待裁决

1. **C1 反推出的 70 条真漏采候选**（`temp/d52/arena_gap_candidates.jsonl`，快照 2026-09-25）：命名差异 146 / 真漏采 70（匿名 6 / 社区 19 / 待核 45）——**待用户点单**。
2. **`prism-ml:ternary-bonsai-2-27b` 的处置去向待拍板**：已按 `prompt.md` L41「排除量化变体」剔除，但库内存在**反例** `meta:llama-4-maverick-17b-128e-instruct-fp8`（Meta 自家官方 FP8 版当年独立立行）⇒ 是否按 §23 登记入 `docs/non_model_records.jsonl`、以及「自有官方量化版 vs 第三方 PTQ 压缩」的边界是否为现行口径，需用户裁示。本轮按 D51「留痕不擅自处理」惯例**未写入任何 registry**。
3. **`unbiased:pareto` 的登记**：判定为 §23(b) 非模型组合体，同样**未写入** `docs/non_model_records.jsonl`，待一并拍板。
4. **32 条 `pricing.confidence=T0` 归因缺陷**（B2 副产品）：单价取自评测平台/非官方源却标 T0，建议下轮专项批量修正。
5. **backlog 948 条存量长尾**：本轮按用户选择**不做**（C 清单第 4 项未勾选），维持开放。
6. **`baai:arex-2` 的 `backbone_type=Hybrid` 属保守判断**：官方 README 只写「Dense Qwen3.8-compatible multimodal model」，采集 agent 由官方 `config.json` 明见的 linear + full 注意力并存结构判定为 `Hybrid`（未按模型名反推），原架构表述已照抄进 `architecture.notes`；若评审口径更严可下调为 `Unknown`。

---

## 十一、产物清单

| 类型 | 路径 |
|---|---|
| 主库 | `model_data_v2.jsonl`（982 条） |
| 采集文件 | `incoming/models/b347w1__zhipu__glm-5-3-max__base.jsonl`、`incoming/models/b348w1__*__base.jsonl` ×4 |
| 常驻工具 | `scripts/arena_gap_reverse.py`（新）、`scripts/qa_outliers.py`（16 → 31 项） |
| 台账 | `docs/batch_claim_ledger.jsonl`（+`b347w1` / `b348w1`，归一到紧凑格式） |
| 文档 | `docs/增量更新工作流.md`、`docs/prompt.md`、`docs/跟踪源清单.md`、`CHANGELOG.md` |
| 脚本 | `temp/d52/` 下：`d52_vendor_norm.py`、`d52_musespark_price.py`、`d52_build_glm53max.py`、`d52_g4_component_notes.py`、`d52_r2_fix_mmau.py`、`d52_ledger_append.py`、`d52_normalize_incoming_format.py`、`d52_fix_ember1_license.py`、`d52_a8a_nc_impact.py` |
| 备份 | `backups/model_data_v2.jsonl.d52g4-*`、`.d52r2-*`、`backups/batch_claim_ledger.jsonl.d52-*`；`temp/d52/pre_*.jsonl` |
| 报告 | `temp/d52/outliers_report.txt`（31 项体检终态） |
