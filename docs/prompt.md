# 主流大模型静态数据采集任务

利用联网搜索能力、可访问公开网页、技术报告、API 定价页、Hugging Face 模型页、独立评测平台进行调研。你的任务是：**根据以下详细规范，采集主流大模型静态数据，并返回一份尽可能全面、结构化、可校验、可追踪的 JSON 数据集。**

请严格遵守本提示词中的字段定义、可信度分级、采集规则和输出格式。所有数据必须来自公开可查证来源，禁止编造、猜测或使用无法核实的来源。缺失或未披露的数据一律填 `null`。所有记录必须包含来源 URL 和采集日期。

最终输出：**JSON Lines 格式数据**，每行一个模型记录，UTF-8 编码，无 BOM，换行符 `\n`。不要输出分析报告、解释性文字或 Markdown 表格，只输出 JSON Lines 数据。如因响应长度限制无法一次性返回全部记录，请先返回完整的第一批记录，并在最后一行之后用一行独立注释说明剩余记录数量（注释行以 `//` 开头，不计入 JSON 数据）。后续我会要求继续返回剩余部分。

---

## 0. v2 变更摘要（基于 A/B/C 试跑反馈）

本版（v2）已落实全部 7 项决策，包括先行定方向的第 1、2、4、5、7 号，以及经方案设计后落地的第 3 号（定价字段扩展）与第 6 号（版本号命名规范）。

| 决策项 | v2 处理 | 状态 |
|------|---------|------|
| 1. 官方域不可访问降级 | 允许 T3 媒体转述 + T1 独立评测间接引用；每条 `meta.notes` 统一声明「官方域沙盒不可访问，数据经媒体转述间接核实」；`confidence` 按实际来源如实降级，不伪造 T0。**可达性按具体 `source_url` 逐条判定，不做厂商级一刀切**（详见 5.4） | ✅ 已落地 |
| 2. T0-自报 与 媒体转述矛盾 | 官方技术报告不可直访时，自报分改标 `T0-自报-转述`（新增 confidence 枚举值），source_type 记为媒体转述类 | ✅ 已落地 |
| 3. 定价字段扩展 | 结构化子对象扩展：`cache_write`（缓存写入价）、`promotions`（促销价）、`long_context`（长上下文溢价）；`cached_input` 明确为缓存读取价 | ✅ 已落地 |
| 4. Arena 多子榜 | `arena_elo` 由单对象改为**对象数组**，每条含 `sub_benchmark`/`score`/`date` 等 | ✅ 已落地（结构性变更） |
| 5. 退役模型采集范围 | **不区分是否退役，尽可能全量采集**；退役但 API 可用 → `verification_status="已过期"`；完全下线 → 保留记录并 `notes` 标「已下线」 | ✅ 已落地 |
| 6. 版本号命名规范 | 三段式 `vendor:family:variant`：vendor 小写 slug、family 含主版本、variant 放营销代号/快照；`basic_info.version` 只填主版本号 | ✅ 已落地 |
| 7. 执行顺序 / 页面不可读 | 官方页不可读时允许降级或放弃；无 Web 工具的 agent 仅记录可达数据、不伪造；不把「必须读官方页」设为硬性卡死 | ✅ 已落地 |

> **数据 Schema 版本**：`schema_version` 由 `"1.0"` 升为 `"1.1"`，包含三处结构性变更（arena_elo 数组化、定价字段扩展、model_id 三段式），均不另起版本号。

---

## 1. 任务目标

采集全球主流大模型厂商的旗舰与主线模型的静态数据，覆盖以下五大维度：

1. 基础身份
2. 架构规格
3. 能力跑分
4. 定价
5. 多模态

数据类型：**静态、可公开查证的结构化数据**。  
不涉及：推理性能（TTFT/TPS 等）、安全合规、法律条款、社区生态。  
模型范围：仅收录各家厂商的旗舰与主线模型（**含已退役 / 已下线的历史模型**，不区分是否仍在服务），排除量化变体、蒸馏小模型、论文项目、开源社区微调模型。  
> **只收录模型本体**（拍板于 2026-08-31，整改轮 D14）：agent 系统、训练/编排框架、推理基础设施、数据管线**即使由厂商正式对外发布也不建条目**——它们没有「一个模型的架构 / 跑分 / 定价」可填，强行收录只会产出成片 `null`。判据与已移出的 7 条见 `WORKBUDDY_AGENT_GUIDE.md` §23 与 `docs/non_model_records.jsonl`。  
时间范围：**自 GPT-3.5 开放网页使用（2023 年 3 月）至今，所有主流厂商的旗舰与主线模型，含已退役 / 下线的历史模型**。包括 GPT-4、GPT-4o、GPT-5、Claude 系列、Gemini 系列、Llama 系列、Grok 系列、Mistral 系列、DeepSeek 系列、通义千问系列、Kimi 系列、GLM 系列、文心系列、豆包系列、混元系列、盘古系列、百川系列、讯飞星火系列等。  
> 退役 / 下线模型的标记规则见 `meta.verification_status`（决策 5）：退役但 API 仍可调用的统一标 `"已过期"`；完全下线不可调用的保留历史记录并在 `notes` 标「已下线，仅保留历史记录」。

---

## 2. 采集范围：厂商列表

### 国内（文本/代码自研训练厂商）

1. 阿里巴巴
2. 深度求索（DeepSeek）
3. 字节跳动
4. 百度
5. 智谱AI
6. 月之暗面（Moonshot AI）
7. 科大讯飞
8. 百川智能
9. 腾讯
10. 华为
11. 美团
12. 小米
13. 零一万物
14. 面壁智能
15. 思必驰

### 国外（文本/代码自研训练厂商）

1. OpenAI
2. Anthropic
3. Google DeepMind
4. Meta
5. xAI
6. Mistral AI
7. Cohere
8. Inflection AI
9. Aleph Alpha
10. 微软
11. NVIDIA
12. Databricks
13. Cognition AI

**覆盖要求**：  
- 每个厂商至少覆盖其当前旗舰模型、上一代旗舰模型（如仍被广泛使用）、以及重要的主线模型。  
- 若厂商既有闭源 API 模型也有开放权重模型，两类均需采集。  
- 若厂商近期发布过推理增强版、多模态版或工具调用增强版，且属于主线，也需采集。  
- 若某厂商公开信息极少，至少尝试采集旗舰模型，并将无法确认的字段填 `null`，在 `notes` 中说明“未官方确认”。

---

## 3. 五大维度总览

| 大类 | 具体字段 | 数据来源 | 主要坑点与绕过方法 |
|------|---------|---------|------------------|
| **1. 基础身份** | 模型全名、版本号、所属厂商、发布日期、定位标签（旗舰/轻量/推理增强）、闭源 or 开放权重 | 各家官方发布页、Model Card | 厂商常用营销代号替代版本号；统一以官方 Model Card 为准，记录采集日期 |
| **2. 架构规格** | 总参数量、激活参数量（MoE 需两者）、架构类型、上下文窗口、知识截止日期 | 技术报告、Hugging Face 页面 | MoE 模型必须标明"总参/激活"两值；"标称上下文"与"有效上下文"差异极大，长上下文选型需单独测试 |
| **3. 能力跑分** | 客观榜（GPQA、SWE-bench、AIME、MMMU、C-Eval 等）、主观榜 | LMArena、OpenCompass、Artificial Analysis | 同一榜单不同版本分数差异可达 5-10 分；务必记录榜版本与评测配置 |
| **4. 定价** | API 输入价、输出价（$/百万 Token） | 各家官方定价页 | 输入/输出价差异大，不能只记均价；缓存价、批量价单独列字段；厂商降价频繁，需标注查询日期 |
| **5. 多模态** | 支持输入（文本/图像/音频/视频）、支持输出（文本/代码/图像） | 官方产品页、API 文档 | "原生多模态"与"外挂拼接"需区分；输出图像/视频与输入理解的模态要分开记录 |

---

## 4. 各维度细项与采集要点

### 维度 1：基础身份

需采集字段：

- **模型全名与版本号**：如 "Claude Opus 4.7"、"DeepSeek V4-Pro"、"GPT-5.2 Preview"。  
- **所属厂商/实验室**：Anthropic、OpenAI、Google DeepMind、DeepSeek、阿里通义、月之暗面、智谱、Meta、xAI、Mistral 等。  
- **发布日期**：精确到月即可，ISO 8601 格式，如 `2026-06`。  
- **定位标签**：旗舰 / 中端 / 轻量 / 推理增强 / 多模态 / 工具调用增强。可多选。  
- **获取方式**：仅 API / 开放权重 / API + 权重。需分别记录 `open_weights`、`api`、`local_deployment` 三个布尔字段。

**坑点与处理**：  
- 厂商常以 "Preview""Experimental""Turbo""Flash""Pro" 等营销代号命名迭代版本，版本号不透明。  
- **绕过方法**：以官方 Model Card 或 Release Note 中的内部代号为唯一标识，并在数据表加“采集日期”字段；若版本不透明，在 `notes` 中说明。  
- 示例：OpenAI 的 "GPT-5.2" 可能包含多个 Preview 版本，需以官方 Model Card 中的版本号为准。

---

### 维度 2：架构规格

需采集字段：

- **总参数量**：如 405B、1T、2.8T，单位：十亿/B，数值型。  
- **激活参数量**：MoE 模型必填，如“总参 397B / 激活 17B”，单位：十亿/B。  
- **架构类型**：Dense Transformer / MoE / Hybrid / Unknown。  
- **上下文窗口**：标称值（如 128K、200K、1M、2M），单位：token。  
- **知识截止日期**：训练数据的时间边界，如 `2026-01`。

**坑点与处理**：  
- **参数量不等于能力**：MoE 架构下“激活参数”才决定推理成本与实际能力下限，直接用总参数对比会得出错误结论。  
- **标称上下文虚高**：许多模型标称 1M token，但超过一定长度后出现“中间遗忘”（Lost-in-the-Middle）。  
- **知识截止日期不透明**：厂商经常不公开，或公开后又通过联网搜索/工具调用绕过。  
- **绕过方法**：  
  - MoE 模型必须同时采集总参数量和激活参数量，在 `architecture` 对象中分别记录 `total_params_b` 和 `active_params_b`。  
  - 上下文窗口必须区分 `context_window_tokens`（标称值）和 `context_window_effective_tokens`（实际可用值）。有效值**不要求独立第三方实测**，厂商标称/自报/社区实测都可填，出处写进 `notes`；无任何依据才填 `null`。有效值不得大于标称值。  
  - 知识截止日期查技术报告附录，或从官方 FAQ 中提取；若未披露填 `null`，并在 `notes` 说明“知识截止日期未披露”。

---

### 维度 3：能力跑分

需采集字段（按类别分组）：

| 类别 | 建议榜单 | 备注 |
|------|---------|------|
| 综合知识 | MMLU-Pro | MMLU 已饱和（头部 88%+），仅作参考基线 |
| 硬推理 | GPQA Diamond | 研究生级科学推理，区分度好 |
| 代码 | SWE-bench Verified | 真实 GitHub Bug 修复率，比 HumanEval 更贴近实际 |
| 数学 | AIME 2025 | GSM8K 已饱和；AIME 具备抗污染性 |
| 多模态理解 | MMMU | 图文混合推理 |
| 中文综合 | C-Eval / SuperCLUE | 国内场景必看 |
| 主观偏好 | LMSYS Chatbot Arena Elo | 用户盲测投票，反映真实体验 |

**采集规则**：  
- 每个 benchmark 分数必须同时记录：`benchmark`、`score`、`score_type`（accuracy / pass@1 / 其他）、`config`（0-shot / few-shot / CoT / 自定义 prompt）、`date`、`source_url`、`source_type`、`confidence`、`notes`。  
- 分数优先使用 0-1 小数；若为百分制，在 `notes` 中注明“原始为百分制，已除以 100”。  
- 同一 benchmark 的厂商自报分与独立评测分必须分开记录在两个数组：`self_reported` 和 `independent`。  
- 若存在第三方独立评测（如 Artificial Analysis、OpenCompass），必须同时采集；若只有厂商自报分，`independent` 数组可为空，但在 `notes` 中标注“无独立评测”。

**坑点与处理**：  
- **数据污染**：公开测试集可能已进入训练数据，导致“虚高”。MMLU、GSM8K、HumanEval 均有不同程度污染证据。  
- **榜单饱和**：MMLU、GSM8K、HumanEval 头部模型分数差距在误差范围内，区分度有限。  
- **厂商自报分 vs 独立评测分**：厂商技术报告常用最优 prompt 配置；独立评测平台更接近默认配置下的真实表现。  
- **Arena Elo 的时效性**：LMArena 榜单变动快，且曾出现厂商定制版本刷分争议。  
- **绕过方法**：  
  - 优先采集动态更新或新题榜单：LiveCodeBench、AIME 2025、GPQA Diamond、SWE-bench Verified。  
  - 每个分数记录“榜版本 + 评测配置 + 数据来源”。  
  - 同时记录 `self_reported` 和 `independent` 两列，并计算 `gap_to_self_reported`（独立评测分 - 自报分）。  
  - Arena Elo 采集时注明快照日期。

---

### 维度 4：定价

需采集字段：

- **API 输入价**（$/百万 token）  
- **API 输出价**（$/百万 token）  
- **缓存价**（如有）  
- **批量价**（如有）  
- **免费额度**（如有）  
- **价格生效日期**：`effective_date`。  
- **来源 URL**：优先官方定价页；官方域不可访问时可为媒体转述 / 独立价格追踪链接，并在 `meta.notes` 声明（决策 1）。  
- **来源类型**：优先“官方定价页”；不可达时记为媒体转述 / 独立价格追踪类。  
- **可信度等级**：官方可直读为 T0；不可达时按实际来源降级为 T3 / T1，**不伪造 T0**（决策 1）。

**采集规则**：  
- 价格统一为 USD / 百万 token；非 USD 价格需按采集日期汇率换算，并在 `notes` 中记录汇率日期和原始货币。  
- 输入价与输出价必须分别记录，禁止只记均价。  
- 缓存价、批量价单独字段记录，不与标准 API 价混合。  
- **定价是否置 `null`，判定条件是「厂商是否公布自有官方 API 刊例价」，不是「是否开源权重」**（2026-08-29 修订）。  
  - 厂商自营 API 且有刊例价 → 无论是否开源权重都正常采集，`confidence="T0"`。  
  - 确认厂商无自有刊例价 → 六价格键全 `null`，**`currency` 同步置 `null`（无价即无币种，不要留 `"USD"` 默认值）**，  
    `source_type` 按情形取  
    `"开源权重模型核对（无官方 API 价）"` / `"官方定价页核对（无公开定价）"` / `"官方定价页核对（已下架）"`，  
    并在 `notes` 标注「本地部署成本」或「社区/第三方托管价」，不与其他官方 API 价直接比较。  
  - 此时 `confidence="T0"` 评的是**「已核对官方渠道、确认无公开价」这一核实动作**的可信度，不是给不存在的价格贴 T0。  
  - **严禁把第三方托管商报价（OpenRouter / NVIDIA hub / 云厂商转售）当官方价填入**；已误填的剔为 `null`，原观测值留在 `notes` 备查。  
- 每次采集标注查询日期 `collected_at` 和价格生效日期 `effective_date`。

**坑点与处理**：  
- **输入/输出价差异大**：如 Claude Opus 4.6 输入 $15、输出 $75，差 5 倍，只记均价会产生误导。  
- **降价频繁**：新模型发布 3-6 个月内 API 报价平均降 30-50%。  
- **绕过方法**：每次采集标注查询日期，并保留历史版本数据；官方定价页可直读时以官方页最新值为准，官方域不可访问时以可达的 T3/T1 来源为准并在 `meta.notes` 声明，严禁编造官方价。

---

### 维度 5：多模态

需采集字段：

- **输入模态支持**：文本 / 图像 / 音频 / 视频 / PDF / 代码 / 网页。布尔值：`true` 支持，`false` 不支持，`null` 未披露。  
- **输出模态支持**：文本 / 代码 / 图像 / 语音。布尔值同上。  
- **原生 vs 外挂**：模型是否原生支持（端到端训练）还是通过外部工具（如 Whisper + GPT）。需单独记录 `native_multimodal` 对象。

**采集规则**：  
- 输入模态与输出模态分开记录。  
- 原生多模态能力以 `native_multimodal` 为准；外挂拼接能力必须在 `notes` 中标明。  
- 例：模型通过外部 OCR 支持 PDF 输入 → `input.pdf = true`，但 `native_multimodal` 对应字段为 `false` 或 `null`，并在 `notes` 注明“外挂 OCR”。  
- 不得将“视频理解”与“图像理解”混为一谈；两者能力差异大，需分别比较。

**坑点与处理**：  
- **“多模态”定义模糊**：部分模型仅支持图像输入但无图像输出；部分支持音频输入但不支持视频。  
- **绕过方法**：模态支持做成布尔矩阵（行 = 模型，列 = 模态，值 = 支持/不支持/未披露）。  
- 视频理解与图像理解的差异大，不应混为一谈。

---

## 5. 数据来源可信度分级方案

**核心原则：可信度分级不等于“来源等级”，而是“来源类型 × 数据字段”的组合**——同一个来源在不同字段上的可信度不同。例如厂商官网对“API 定价”是最高可信（T0），但其技术报告中的“跑分”虽然是权威来源，却属于“厂商自报”，需与独立评测交叉验证。

### 5.1 五级可信度体系

| 等级 | 名称 | 来源类型 | 更新频率 | 典型字段 |
|------|------|---------|---------|---------|
| **T0** | 一手权威 | 厂商官方技术报告、Model Card、API 定价页、官方 Release Note | 定价月查、规格季查 | 参数量、定价、上下文长度、官方跑分 |
| **T1** | 独立评测 | Artificial Analysis、LMArena（LMSYS）、OpenCompass 等有公开方法论的独立平台 | 季查 | 独立跑分、Arena Elo、效率分 |
| **T2** | 半官方聚合 | Hugging Face 模型页、厂商博客、技术博客（官方性质） | 季查 | 社区跑分、下载量、部分规格补充 |
| **T3** | 行业媒体 | TechCrunch、The Verge、量子位、机器之心等有编辑审核的媒体 | 半年查 | 发布新闻、行业背景、非核心规格 |
| **T4** | 低可信 | Twitter/X 帖子、SEO 内容农场、低质量博客、自媒体 | 不主动采集 | 仅作线索，不作数据源 |

**分级的两个关键判定逻辑：**

1. **来源与数据的“距离”**：越接近数据产生点，可信度越高。API 价格页是价格的产生点（T0），媒体报道价格是二手转述（T3），博客转述媒体报道是三手（T4）。  
2. **是否有利益相关**：厂商对自家定价无修饰动机（T0），但对自家跑分有修饰动机（需交叉验证）；独立评测平台与厂商无直接利益，但可能存在方法论偏差。

### 5.2 字段级可信度映射

同一来源在不同字段上可信度不同，必须按字段单独标注：

| 数据字段 | T0 来源 | T1 来源 | 特殊规则 |
|---------|---------|---------|---------|
| **API 定价** | 厂商官方定价页 | Artificial Analysis 价格追踪 | 媒体报道的降价/涨价仅为线索，须回官方页核实 |
| **参数量 / 架构** | 技术报告、Model Card | — | HF 页面为 T2；媒体报道为 T3 |
| **上下文窗口** | 官方 Model Card | — | 注意区分“标称”与“有效”，有效值需 T1 测试 |
| **官方跑分** | 厂商技术报告 | — | **必须标注“自报”，并列独立评测列**；两者差距大即警示信号 |
| **独立跑分** | — | Artificial Analysis、OpenCompass | 记录方法论版本与评测配置 |
| **Arena Elo** | — | LMArena | 标注快照日期；注意已知刷分争议 |
| **发布日期** | 官方公告 | 厂商博客 | 媒体报道日期常准确，可作 T3 补充 |
| **多模态支持** | 官方产品页、API 文档 | — | 需区分“原生”与“外挂”，仅官方文档明确标注 |

### 5.3 厂商自报数据的特殊处理

**厂商技术报告中的跑分（MMLU、GPQA 等）属于 T0 来源 + “自报”属性**，处理规则如下：

1. **不可直接与独立评测混排**：自报分常用最优 prompt 配置，独立评测用默认配置，两者可能相差 5-10 分。  
2. **数据表中设置两列**：「厂商自报分」与「独立评测分」，并加一列「差距」。差距超过 5 分的模型，优先采信独立评测。  
3. **污染检测信号**：若自报分显著高于独立评测分，且该模型在公开基准（MMLU、GSM8K）上分数异常高，需标注“可能存在数据污染”。  
4. **结论**：T0 自报分回答“厂商宣称什么”，T1 独立分回答“实际表现什么”——分析时两者都呈现，不可只取其一。  
5. **官方技术报告不可直访时的标签规则（决策 2）**：当厂商自报分是通过行业媒体转述官方发布稿获得、且官方技术报告 / Model Card 无法直接访问时，**不得标 `T0-自报`**，必须改标 **`T0-自报-转述`**，并将 `source_type` 记为媒体转述类（如「行业媒体转述官方发布」），在 `notes` 注明“经媒体转述，官方技术报告不可直访”。`T0-自报-转述` 仍属“自报”性质，分析时与独立评测对比的「差距」信号依旧有效，但可信度低于可直访的 `T0-自报`。

### 5.4 冲突处理规则

| 冲突场景 | 处理规则 |
|---------|---------|
| T0 vs T1 跑分冲突 | 两列并记，差距 > 0.05 标注“存疑”，报告中并列展示 |
| 两个 T0 冲突（如不同版本技术报告） | 取最新发布版本，旧值移入“历史记录” |
| T0 缺失，仅有 T2/T3 | 标注“未官方确认”，优先级降为参考数据，积极寻找 T0 |
| T1 平台间冲突（如 Arena vs Artificial Analysis） | 属正常现象（方法论不同），分别记录，不强行合并 |
| **官方域不可访问（沙盒 / 安全审核拦截）** | **允许降级采集（决策 1）**：跑分以「独立评测 T1 + 行业媒体转述 T3」作为替代双源；定价以「媒体转述 T3 / 独立价格追踪 T1」替代官方页。所有此类记录在 `meta.notes` 统一声明「官方域沙盒不可访问，数据经媒体转述间接核实」，`confidence` 按实际可访问来源如实降级，**严禁伪造 T0**。**判定粒度为具体 `source_url`，不做厂商级开关**：① 同一厂商不同子域可达性可能不同（如主站定价页不可达但 `docs.` 官方文档子域可达），逐条按实际访问结果判定；② 官方注册子域（含官方文档站、API 文档）可达且数据与官方同源 → 该来源仍按官方域计（定价/规格类字段可标 `T0`），并在 `source_type` / `notes` 注明实际取自的官方子域，例如「取自官方文档站（主定价页不可达，同源）」；③ 官方页可达但缺少目标模型数据（如新模型未上架官方定价页）→ 该字段按实际来源（如独立价格追踪）降级标注，不标 `T0`，`notes` 说明「官方页未含该模型」。 |
| T3/T4 与 T0/T1 冲突 | **一律以高等级为准**，T3/T4 仅作线索不作数据源 |
| 定价变动冲突 | 以官方页最新值为准，保留历史价格并记录变更日期 |

### 5.5 可信度与来源使用强制规则

- 任何跑分结论不得仅基于 `T0-自报` 或 `T0-自报-转述`（决策 2）；必须至少伴随一条独立评测（T1）来源，或（官方域不可访问时）伴随一条 T3 媒体转述并已在 `meta.notes` 声明。  
- 若同一 benchmark 同时存在 `self_reported` 和 `independent`：  
  - 计算 gap = independent - self_reported；  
  - gap 绝对值 > 0.05（或 5 个百分点）时，标记“存疑”，优先采信 independent；  
  - 报告中必须两列并记。  
- 价格、参数量、上下文窗口**优先**以 T0 官方页为准；若官方域不可访问（决策 1），允许以 T3 媒体转述 / T1 独立价格追踪替代，并在 `meta.notes` 统一声明，且 `confidence` 如实降级，**严禁伪造 T0 / T0 官方定价**。  
- **降级采集不伪造原则**：任何 agent（无论是否具备 Web 工具）都只能在“实际可访问的来源”基础上标注可信度；读不到官方页就如实标 T3/T1 + notes 声明，绝不臆造 T0 或编造 URL。无 Web 工具的 agent 仅记录其可达数据，缺失项填 `null` + `notes` 说明。  
- 所有结论引用数据时，必须携带 `source_url` 和 `collected_at`。

---

## 6. 数据输出规范：JSON 结构与字段定义

最终输出为 JSON Lines 格式，每行一个模型记录。每个模型记录必须是一个 JSON 对象，包含以下字段。不要删除任何核心字段，允许扩展自定义字段但不要省略以下结构。

### 6.1 顶层结构

```json
{
  "schema_version": "1.1",
  "model_id": "唯一标识",
  "basic_info": { ... },
  "architecture": { ... },
  "benchmarks": { ... },
  "pricing": { ... },
  "modality": { ... },
  "meta": { ... }
}
```

### 6.2 字段详细说明

#### `schema_version`
- 类型：字符串
- 当前值：`"1.1"`
- 变更说明：v1.1 包含三处结构性变更——① `benchmarks.arena_elo` 由单对象改为对象数组（决策 4）；② 定价新增 `cache_write` / `promotions` / `long_context` 结构化字段（决策 3）；③ `model_id` 改为三段式 `vendor:family:variant`（决策 6）。均在同一 1.1 主版本内完成，不另起版本号。

#### `model_id`
- 类型：字符串
- 推荐格式：`厂商英文名:模型名:版本号`
- 示例：`openai:gpt-5.2:preview`、`deepseek:deepseek-v4-pro:2026-06`、`anthropic:claude-opus:4.7`
- 版本号不透明时，以官方 Model Card 或 Release Note 内部代号为准，并在 `basic_info.version` 中记录，`notes` 中说明版本不透明。

#### `basic_info` 对象
必填字段：`full_name`、`vendor`、`release_date`、`access`。

```json
{
  "full_name": "模型全名，如 Claude Opus 4.7",
  "version": "主版本号，如 4.7、5.6（营销代号 Sol/Terra/Luna、快照日期不填入此字段，见 model_id 三段式规则）；若版本不透明则填 null 并在 notes 说明",
  "vendor": "厂商英文名或通用名，如 Anthropic / OpenAI / Google DeepMind / DeepSeek / Alibaba / Moonshot AI / Zhipu AI / Meta / xAI / Mistral AI",
  "release_date": "ISO 8601，精确到月，如 2026-06",
  "positioning": ["旗舰", "推理增强"],
  "access": {
    "open_weights": false,
    "api": true,
    "local_deployment": false,
    "notes": null
  },
  "license": null
}
```

- `positioning` 为数组，可选标签：旗舰 / 中端 / 轻量 / 推理增强 / 多模态 / 工具调用增强。  
- `access` 对象中三个布尔字段：`open_weights`（是否开放权重）、`api`（是否有官方 API）、`local_deployment`（是否支持本地部署）。未知填 `null`。`notes` 可补充说明。
- `license`：权重/使用许可，自由文本，如 `"MIT"`、`"NVIDIA Open Model License + Llama 3.1 Community License"`、`"闭源 API (proprietary, API-only)"`。开放权重模型取官方模型卡/HuggingFace 仓库 LICENSE 原文；闭源模型填「闭源 API」声明。未采集到填 `null`，严禁凭 `open_weights` 反推。

#### `architecture` 对象
所有字段可空，未知填 `null`。

```json
{
  "total_params_b": null,
  "active_params_b": null,
  "architecture_type": "Unknown",
  "backbone_type": "Unknown",
  "context_window_tokens": 200000,
  "context_window_effective_tokens": null,
  "max_output_tokens": null,
  "reasoning_model": null,
  "knowledge_cutoff": "2026-01",
  "notes": "官方未披露参数量；标称 200K 上下文，有效上下文未测试"
}
```

- `total_params_b`：总参数量，单位十亿/B。Dense 模型等于激活参数。  
- `active_params_b`：激活参数量，单位十亿/B。MoE 模型必填。  
- `architecture_type`：**只填稀疏性**，枚举 `"Dense" / "MoE" / "Hybrid" / "Unknown"`。主干是什么（Transformer / Mamba / RNN…）不写在这一栏，写 `backbone_type`。  
- `backbone_type`：主干结构，枚举 `"Transformer" / "Transformer-Decoder" / "Transformer-Encoder" / "Transformer-Encoder-Decoder" / "Mamba-SSM" / "RNN-LinearAttention" / "Diffusion" / "CNN" / "MLP" / "Hybrid" / "Unknown"`。`Hybrid` 指**两种及以上骨干并存**；稀疏性混合写 `architecture_type="Hybrid"`，别写在这里。  
  两栏都是受控枚举，越界会被门禁规则 1.1 / 1.2 报 WARN（2026-08-31 整改轮 D15 拍板：原来一栏塞了 190 种自由写法，机器没法聚合）。  
  **原文不丢**：来源写法比枚举更具体时（如 `"Decoder-only Transformer (GQA, RoPE, SwiGLU)"`），把原话照抄进 `notes` 结尾的 `；原架构表述：「原话」`。  
  **禁止反推**：不得凭模型名（叫 Llama 就判 Transformer）、也不得参照同系列兄弟条目来填骨干；本条 `architecture_type` 原文和 `notes` 里都没有明文声明，就填 `Unknown`。  
- `context_window_tokens`：标称上下文窗口，单位 token。  
- `context_window_effective_tokens`：实际可用上下文窗口，单位 token。不要求独立第三方实测，但必须在 `notes` 注明数字来源；无任何依据则为 `null`。不得大于 `context_window_tokens`。  
- `max_output_tokens`：官方声明的单次最大输出 token 数（整数），与上下文窗口是不同字段，勿混填。官方未给出则为 `null`。  
- `reasoning_model`：布尔，是否为推理型/思考型模型（有独立思考链/推理档位）。厂商未声明则为 `null`，勿按「能力强」臆断。  
- `knowledge_cutoff`：训练数据时间边界，如 `"2026-01"`。未知填 `null`。  
- `notes`：补充说明，如“标称上下文 200K，但超过 64K 后出现 Lost-in-the-Middle，有效上下文未测试”。

#### `benchmarks` 对象
包含三个子对象：`self_reported`、`independent`、`arena_elo`（**对象数组**，每个 LMArena 子榜一条，支持多子榜）。

```json
{
  "self_reported": [
    {
      "benchmark": "GPQA Diamond",
      "score": 0.82,
      "score_type": "accuracy",
      "config": "0-shot CoT",
      "date": "2026-06",
      "source_url": "https://anthropic.com/claude-opus-4.7-technical-report",
      "source_type": "官方技术报告",
      "confidence": "T0-自报",
      "notes": null
    }
  ],
  "independent": [
    {
      "benchmark": "GPQA Diamond",
      "score": 0.78,
      "score_type": "accuracy",
      "config": "default",
      "date": "2026-07",
      "source_url": "https://artificialanalysis.ai/",
      "source_type": "独立评测平台",
      "confidence": "T1",
      "gap_to_self_reported": -0.04,
      "notes": "独立评测与自报差 4 个百分点，在可接受范围内"
    }
  ],
  "arena_elo": [
    {
      "sub_benchmark": "text",
      "score": 1450,
      "date": "2026-08-20",
      "source_url": "https://lmarena.ai/",
      "source_type": "LMArena",
      "confidence": "T1",
      "is_primary": true,
      "notes": "主榜 text 快照日期 2026-08-20"
    },
    {
      "sub_benchmark": "coding",
      "score": 1520,
      "date": "2026-08-20",
      "source_url": "https://lmarena.ai/",
      "source_type": "LMArena",
      "confidence": "T1",
      "is_primary": false,
      "notes": "CodeArena 子榜，与 text 榜排名差异显著，选型需分维度看"
    }
  ]
}
```

**`self_reported` 和 `independent` 数组中的每个对象必须包含：**  
- `benchmark`：字符串，榜单名称，如 `"MMLU-Pro"`、`"GPQA Diamond"`、`"SWE-bench Verified"`、`"AIME 2025"`、`"MMMU"`、`"C-Eval"`、`"LiveCodeBench"`。
  **同一基准的多个子任务须各成一条并把子任务写进名字**（如 `"Russian SuperGLUE (RSG) – MuSeRC"`），不要挤在同名条目里。
- `score`：数字或字符串，优先数字，0-1 小数；若百分制需在 `notes` 说明。  
- `score_type`：字符串，如 `"accuracy"`、`"pass@1"`、`"其他"`。  
- `config`：字符串，如 `"0-shot"`、`"few-shot"`、`"CoT"`、`"default"`、`"自定义 prompt"`。
  **合并去重主键**是 `benchmark` + `config` + `date`（`independent` 再加 `source_site`），
  这组键必须足以唯一标识一次测量：
  同一基准并存多个测量时（shot 数不同 / prompting 方法不同 / 脚手架或 turn 预算不同 / 单次 vs 投票 / pass@k 不同 /
  一条记录里有多个发布变体），**必须把区别写进 `config`**，留空会撞车。
  **禁止把来源名写进 `config`**（如 `"default（benched.ai）"`）—— 来源站用 `source_site` 记。
- `date`：评测发布日期或快照日期。  
- `source_url`：来源链接。  
- `source_type`：来源类型，如 `"官方技术报告"`、`"独立评测平台"`。  
- `source_site`：**仅 `independent` 使用**。字符串，记这条独立评测出自哪个站，如 `"evals.report"`、
  `"Artificial Analysis"`、`"benched.ai"`。同一基准被多个站各测一次是本表的正常形态，
  `source_site` 就是区分这些测量的主键段 —— 少了它，不同站的分数会被当成「同一次测量记了两遍」而被合并吃掉。
  `self_reported` 不填（来源就是厂商自己，由 `source_type` / `source_url` 表达）。
- `confidence`：可信度等级，可选 `"T0"`、`"T0-自报"`、`"T0-自报-转述"`、`"T1"`、`"T2"`、`"T3"`、`"T4"`（新增 `T0-自报-转述` 见决策 2）。  
- `notes`：补充说明。  
- `independent` 对象额外包含 `gap_to_self_reported`：独立评测分 - 厂商自报分，用于污染/调优检测。

**`arena_elo` 为对象数组，每个 LMArena 子榜一条，每个对象包含：**  
- `sub_benchmark`：子榜名称，如 `"text"`、`"coding"`、`"WebDev"`、`"Vision"`、`"Agent"`、`"CodeArena"`。主榜用 `"text"` 或标注 `is_primary: true`。  
- `score`：Elo 分数，数字。  
- `date`：该子榜快照日期。  
- `is_primary`：布尔值，是否为主榜（用于分析端默认引用）。  
- `source_url`、`source_type`、`confidence`、`notes`。

**键名规则（硬性）**：`self_reported` / `independent` 条目的基准名字段必须写 `benchmark`；`arena_elo` 条目必须写 `sub_benchmark`；**禁止 `name` / `benchmark_name` / `metric_name` 等任何其它写法**（`arena_elo` 也不得写 `benchmark`）。  
- 例：~~`{"name": "GPQA Diamond", "score": 0.82}`~~ → `{"benchmark": "GPQA Diamond", "score": 0.82}`（2026-08-30 分两轮把存量的 1293 + 57 条非 canonical 写法全部归一，门禁规则 6.1 现对**任何**缺 canonical 主键的条目报 WARN）。  
- 代价不是格式问题而是去重失效：合并去重主键 `self_reported` 为 `(benchmark, config, date)`、`independent` 为 `(benchmark, config, source_site, date)`、`arena_elo` 为 `(sub_benchmark, date)`，非 canonical 行读成空键，同一次测量会静默并存两份。  

**注意**：如果某个模型没有某类跑分，对应数组可为空 `[]`；`arena_elo` 可为空数组 `[]`（无子榜数据时）或 `null`（完全无 Arena 数据时）。

#### `pricing` 对象
```json
{
  "currency": "USD",
  "unit": "per_million_tokens",
  "input": 5.0,
  "output": 30.0,
  "cached_input": 0.5,
  "cache_write": 6.25,
  "batch_input": 2.5,
  "batch_output": 15.0,
  "free_tier": null,
  "promotions": {
    "input": 4.0,
    "output": 20.0,
    "ends_on": "2025-11-21",
    "notes": "促销价，原 input 5.0 / output 30.0"
  },
  "long_context": {
    "threshold_tokens": 272000,
    "input_multiplier": 2.0,
    "output_multiplier": 1.5,
    "notes": ">272K tokens 输入 2x、输出 1.5x"
  },
  "effective_date": "2026-08-01",
  "source_url": "https://openai.com/api/pricing",
  "source_type": "官方定价页",
  "confidence": "T0",
  "notes": "输入/输出价差 6 倍；cached_input 为缓存读取价（约 10% 标准输入），cache_write 为缓存写入价（1.25x 标准输入）"
}
```

- `currency`：**有实际价格时**填 `"USD"`（非 USD 价格需换算并在 `notes` 说明）；六个价键  
  （`input` / `output` / `cached_input` / `cache_write` / `batch_input` / `batch_output`）**全为 `null` 时必须填 `null`**。  
  ~~默认 `"USD"`~~ 旧写法作废：无价仍写 USD 会被分析端读成「已按美元核实、确认无价」，属红线 1 的伪造默认值  
  （门禁规则 4.3 会 WARN；2026-08-29 已把存量的 323 条归一为 `null`）。  
- `unit`：默认 `"per_million_tokens"`（纯量纲声明，不携带「已核实」含义，无价时也保留）。  
- `input`：标准 API 输入价，美元/百万 token。  
- `output`：标准 API 输出价，美元/百万 token。  
- `cached_input`：缓存**读取**价（cache read，通常约为标准输入的 10%），如有；无则 `null`。  
- `cache_write`：缓存**写入**价（cache write，通常约为标准输入的 1.25x），如有；无则 `null`。  
- `batch_input`：批量输入价，如有。  
- `batch_output`：批量输出价，如有。  
- `promotions`：促销价对象或 `null`，含 `input`、`output`（促销期输入/输出价）、`ends_on`（ISO 8601 促销截止日）、`notes`（如“原 input 5.0 / output 30.0”）。无促销则 `null`。  
- `long_context`：长上下文溢价对象或 `null`，含 `threshold_tokens`（触发溢价的 token 阈值）、`input_multiplier`、`output_multiplier`（超过阈值后输入/输出价乘数）、`notes`。无则 `null`。  
- `free_tier`：免费额度描述，如 `"每月 100 万 token 免费"`，无则 `null`。  
- `effective_date`：价格生效日期，ISO 8601（OpenAI 类频繁变动须精确到日，采集 30 天后复核）。  
- `source_url`：官方定价页链接（官方域不可访问时可为媒体 / 独立价格追踪链接，并在 `meta.notes` 声明，见决策 1）。  
- `source_type`：`"官方定价页"`（不可达时记为媒体转述 / 独立价格追踪类，并在 `meta.notes` 声明）。  
- `confidence`：官方定价页可直读时为 `"T0"`；官方域不可访问时按实际来源降级为 T3（媒体转述）/ T1（独立价格追踪），**不伪造 T0**。  
- `notes`：补充说明，如“输入/输出价差 6 倍；cached_input 为缓存读取价，cache_write 为缓存写入价”。

> **（v2 已扩展定价字段，见决策 3）** 新增 `cache_write`（缓存写入价）、`promotions`（促销价）、`long_context`（长上下文溢价）三个结构化字段；`cached_input` 明确为**缓存读取价**。字段扩展在 schema_version `1.1` 内完成，不另起版本号。

**如果模型没有官方 API 定价（如开放权重但无官方托管），`pricing` 对象可全部填 `null`，但在 `notes` 中注明“本地部署成本”或“社区托管价”，且 `source_type` 可为 `null`，`confidence` 可为 `null`。**

#### `modality` 对象
```json
{
  "input": {
    "text": true,
    "image": true,
    "audio": false,
    "video": true,
    "pdf": true,
    "code": true,
    "web": false,
    "notes": "PDF 输入经解析为图像，非原生 PDF 解析"
  },
  "output": {
    "text": true,
    "code": true,
    "image": false,
    "audio": false,
    "speech": false,
    "notes": null
  },
  "native_multimodal": {
    "input_image": true,
    "input_audio": false,
    "input_video": true,
    "output_image": false,
    "output_audio": false,
    "notes": "视频理解原生，图像原生；PDF 为工具链支持"
  }
}
```

- `input` 对象：布尔值，支持为 `true`，不支持为 `false`，未披露为 `null`。字段包括：`text`、`image`、`audio`、`video`、`pdf`、`code`、`web`。  
- `output` 对象：布尔值，字段包括：`text`、`code`、`image`、`audio`、`speech`。  
- `native_multimodal` 对象：布尔值，字段包括：`input_image`、`input_audio`、`input_video`、`output_image`、`output_audio`。  
- 每个子对象可带 `notes` 说明。

**关键规则**：  
- 布尔值 `null` 表示未披露或未采集，不要用 `false` 代替 `null`。  
- 原生多模态能力以 `native_multimodal` 为准；外挂拼接能力在 `notes` 中说明。

#### `meta` 对象
```json
{
  "collected_at": "2026-08-24",
  "verified_at": "2026-08-24",
  "verification_status": "已验证",
  "source_urls": [
    "https://anthropic.com/claude-opus-4.7-technical-report",
    "https://anthropic.com/pricing"
  ],
  "notes": null
}
```

- `collected_at`：采集日期，ISO 8601，必填。  
- `verified_at`：验证日期，可选。  
- `verification_status`：枚举 `"已验证" / "待验证" / "存疑" / "已过期"`。  
  - 退役但 API 仍可调用的模型 → `"已过期"`（决策 5）。  
  - 完全下线不可调用的模型 → 仍收录并保留记录，`notes` 标「已下线，仅保留历史记录」，`verification_status` 可标 `"已过期"` 或 `"待验证"`。  
- `source_urls`：该模型所有数据来源链接的数组，可包含多个。  
- `notes`：整体备注。**凡因官方域不可访问而采用媒体转述（T3）/ 独立评测（T1）降级采集的记录，必须在此统一注明：「官方域沙盒不可访问，数据经媒体转述间接核实」**（决策 1）；并可在同条 notes 中追加具体降级说明（如“定价经媒体转述，非官方页直读”）。

### 6.3 空字段与填写规则

- 所有未知、未采集、不适用、未披露的字段，一律填 `null`。  
- 禁止用 `0`、`""`、`"N/A"`、`"未知"` 代替 `null`。  
- 多模态布尔字段：`true` 明确支持；`false` 明确不支持；`null` 未披露或未采集。  
- 数值类字段如无法确定具体值，填 `null`，并在 `notes` 中说明。  
- 详细描述统一放入相应对象的 `notes` 字段，不强制压缩成枚举或数字。

### 6.4 唯一标识

`model_id` 采用**三段式**：`vendor:family:variant`（决策 6）。  
- `vendor`：厂商小写 slug，如 `openai` / `anthropic` / `google` / `deepseek` / `alibaba` / `moonshot` / `zhipu` / `meta` / `xai` / `mistral`；未知厂商用其英文名小写（去空格）。  
- `family`：模型家族 + 主版本号，如 `gpt-5.6` / `claude-opus` / `gemini-3.1` / `deepseek-v4`。  
- `variant`：子型号 / 营销代号 / 快照日期，如 `sol` / `terra` / `luna` / `preview` / `2025-12-11`；无子型号时常与版本号重合（如 `4.7`）。  

示例：  
- `openai:gpt-5.6:sol`（GPT-5.6 Sol，营销代号 Sol）  
- `openai:gpt-5.6:terra`  
- `openai:gpt-5.2:2025-12-11`（带快照日期）  
- `anthropic:claude-opus:4.7`  
- `deepseek:deepseek-v4-pro:2026-06`  
- `google:gemini-3.1-pro:2026-04`  

`basic_info.version` **只填主版本号**（如 `5.6`、`4.7`）；营销代号（Sol/Terra/Luna）与快照日期写入 `variant` 段及 `notes`，不进入 `version`。版本号不透明时，以官方 Model Card / Release Note 内部代号为准，`notes` 说明。

> **执行约束（P1 修复）**：上述三段式是「新模型如何命名」的生成规则，不是合并时的匹配依据。多 agent 协作时，**`roster.jsonl` / `roster.md` 花名册是 model_id 的唯一权威**：
> - 花名册中 `in_v1` 的模型（v1 库存量，多为 `连字符 family + :base` 风格）：**原样沿用花名册中的 model_id**，严禁「纠正」为点号或营销代号风格——两种风格指向同一模型时必须合并而不是新建记录；
> - 花名册中 `to_add` 的模型：**原样使用花名册分配的 model_id**（本节三段式风格）；
> - 采集 agent 不得自行发明、修改或重命名任何 model_id；发现花名册外的新旗舰/主线模型，先回报主 agent 补录花名册再采集。

---

## 7. 采集执行步骤

按照以下步骤逐项完成采集，确保不遗漏、不编造：

### 步骤 1：确定模型清单

1. 遍历上述 28 家厂商，逐一检索其官方发布页、Model Card、技术报告、API 文档。  
2. 对每家厂商，列出其自 2023 年 3 月以来发布的旗舰与主线模型（**含已退役 / 已下线模型，决策 5：不区分是否退役，尽可能全量采集**）。  
3. 优先覆盖：  
   - 当前旗舰模型（如 GPT-5.2、Claude Opus 4.7、Gemini 3.1 Pro、Llama 4、Grok 4、DeepSeek V4-Pro、Qwen 3.5 Max、Kimi K2.6、GLM 5、文心 5.5、豆包 2.0、混元 Turbo S 等——仅为示例，实际以检索为准）。  
   - 上一代旗舰（如 GPT-5、Claude Opus 4.5、Gemini 2.5 Pro、Llama 3.1 405B 等）。  
   - 重要主线变体（如 GPT-5-mini、Claude Sonnet、Gemini Flash、DeepSeek-V3.2、Qwen-Max、Kimi 等）。  
4. 排除量化变体、蒸馏小模型、论文项目、社区微调模型。

### 步骤 2：逐模型采集五大维度数据

对每个模型，按以下优先级采集：

1. **基础身份**：官方 Model Card、Release Note、产品页。  
2. **架构规格**：技术报告、Hugging Face 模型页（T2）、官方 FAQ。  
3. **能力跑分**：  
   - 厂商自报分：官方技术报告、Model Card。  
   - 独立评测分：Artificial Analysis、OpenCompass、LMArena 等。  
4. **定价**：官方定价页（官方域不可访问时，按决策 1 降级为媒体转述 T3 / 独立价格追踪 T1，并在 `meta.notes` 声明，严禁编造官方价）。  
5. **多模态**：官方产品页、API 文档。

### 步骤 3：标注来源与可信度

每个字段必须标注来源类型、可信度等级、采集日期。  
- 来源类型下拉：官方技术报告 / 官方定价页 / Model Card / 独立评测平台 / Hugging Face / 厂商博客 / 行业媒体 / 行业媒体转述官方发布 / 社交媒体。  
- 可信度等级：T0 / T0-自报 / T0-自报-转述 / T1 / T2 / T3 / T4（新增 `T0-自报-转述`，见决策 2）。  
- 来源 URL 必须完整；确实无法直读官方页时，可用可达的媒体 / 独立评测链接，但须真实存在且非杜撰，并在 `meta.notes` 声明。  
- 采集日期必须为实际采集日期。  
- **无 Web 工具的 agent**：只能基于其可达数据源采集，缺失项填 `null` + `notes` 说明，绝不臆造官方页或 T0（决策 7）。

### 步骤 4：处理冲突

遇到冲突时，按第 5 节冲突处理规则执行：  
- 两列并记，不自行取舍。  
- 标注“存疑”或“未官方确认”。  
- 价格以官方页最新值为准。

### 步骤 5：填写 JSON 记录

按照第 6 节 JSON 结构，将每个模型的所有字段填充完整。确保：  
- `schema_version` 为 `"1.1"`。  
- `model_id` 唯一。  
- `basic_info`、`meta` 必填。  
- 所有缺失字段填 `null`。  
- 每个字段的来源信息完整。

### 步骤 6：质量检查

在输出前，对每行 JSON 进行自查：

- [ ] 是否所有必需字段都存在？  
- [ ] `model_id` 是否唯一？  
- [ ] 所有缺失字段是否填 `null` 而非 `0` 或 `""`？  
- [ ] 跑分是否至少包含一个可信来源（独立评测 T1 优先；官方不可达时 T3 媒体转述须在 `meta.notes` 声明）？  
- [ ] 定价是否来自官方定价页？官方不可达时是否已降级为 T3/T1 并在 `meta.notes` 声明（决策 1）？  
- [ ] 凡官方域不可访问的降级记录，`meta.notes` 是否含「官方域沙盒不可访问，数据经媒体转述间接核实」？
- [ ] 多模态布尔字段是否区分 `true` / `false` / `null`？  
- [ ] `meta.collected_at` 是否填写？  
- [ ] `source_urls` 是否包含所有主要来源链接？  
- [ ] 是否有冲突未标注？  

---

## 8. 输出格式与交付要求

**最终输出格式：JSON Lines 文本块**，每行一个模型 JSON 对象。  
- UTF-8 编码，无 BOM。  
- 换行符 `\n`。  
- 空字段填 `null`。  
- 不要输出 Markdown 表格、解释性文字、分析报告。  
- 如果响应长度受限，先返回完整的第一批记录，并在最后一行之后用一行 `// 剩余记录数: N` 注释说明。  
- 每条 JSON 对象占一行，不要多行展开（除非必要，但建议压缩为单行以便解析）。

**示例输出片段**（仅一条记录）：

```jsonl
{"schema_version":"1.1","model_id":"anthropic:claude-opus:4.7","basic_info":{"full_name":"Claude Opus 4.7","version":"4.7","vendor":"Anthropic","release_date":"2026-06","positioning":["旗舰","推理增强"],"access":{"open_weights":false,"api":true,"local_deployment":false,"notes":null}},"architecture":{"total_params_b":null,"active_params_b":null,"architecture_type":"Unknown","backbone_type":"Unknown","context_window_tokens":200000,"context_window_effective_tokens":null,"knowledge_cutoff":"2026-01","notes":"官方未披露参数量；标称 200K 上下文，有效上下文未测试"},"benchmarks":{"self_reported":[{"benchmark":"GPQA Diamond","score":0.82,"score_type":"accuracy","config":"0-shot CoT","date":"2026-06","source_url":"https://anthropic.com/claude-opus-4.7-technical-report","source_type":"官方技术报告","confidence":"T0-自报","notes":null}],"independent":[{"benchmark":"GPQA Diamond","score":0.78,"score_type":"accuracy","config":"default","date":"2026-07","source_url":"https://artificialanalysis.ai/","source_type":"独立评测平台","confidence":"T1","gap_to_self_reported":-0.04,"notes":"独立评测与自报差 4 个百分点，在可接受范围内"}],"arena_elo":[{"sub_benchmark":"text","score":1450,"date":"2026-08-20","source_url":"https://lmarena.ai/","source_type":"LMArena","confidence":"T1","is_primary":true,"notes":"主榜 text 快照日期 2026-08-20"},{"sub_benchmark":"coding","score":1520,"date":"2026-08-20","source_url":"https://lmarena.ai/","source_type":"LMArena","confidence":"T1","is_primary":false,"notes":"CodeArena 子榜，与 text 榜排名差异显著"}]},"pricing":{"currency":"USD","unit":"per_million_tokens","input":15.0,"output":75.0,"cached_input":1.5,"batch_input":7.5,"batch_output":37.5,"free_tier":null,"effective_date":"2026-08-01","source_url":"https://anthropic.com/pricing","source_type":"官方定价页","confidence":"T0","notes":"输入/输出价差 5 倍，使用时文本输出成本高"},"modality":{"input":{"text":true,"image":true,"audio":false,"video":true,"pdf":true,"code":true,"web":false,"notes":"PDF 输入经解析为图像，非原生 PDF 解析"},"output":{"text":true,"code":true,"image":false,"audio":false,"speech":false,"notes":null},"native_multimodal":{"input_image":true,"input_audio":false,"input_video":true,"output_image":false,"output_audio":false,"notes":"视频理解原生，图像原生；PDF 为工具链支持"}},"meta":{"collected_at":"2026-08-24","verified_at":"2026-08-24","verification_status":"已验证","source_urls":["https://anthropic.com/claude-opus-4.7-technical-report","https://anthropic.com/pricing"],"notes":null}}
```

---

## 9. 执行速查卡（采集时必须遵守）

1. **采集任何数据前，先问**：这个数据的一手来源是什么？能否直接访问？  
2. **优先级顺序**：官方页 > 独立评测 > Hugging Face > 厂商博客 > 媒体（官方域不可访问时按决策 1 降级，不卡死）。  
3. **跑分优先双源**：厂商自报 + 独立评测；官方域不可访问时，以「独立评测 T1 + 行业媒体转述 T3」作为替代双源，并在 `meta.notes` 声明，单源且无可替代时允许但须标「待验证」。  
4. **定价优先官方页**：媒体 / 博客价格一律回官方核实；官方域不可访问时降级为 T3/T1 并 `meta.notes` 声明，**严禁伪造 T0 官方价**（决策 1）。  
5. **采集即记录**：来源 URL、采集日期、来源类型三列不允许为空（无 Web 工具的 agent 可仅记录可达数据，缺失填 `null` + notes，决策 7）。  
6. **空字段填 `null`**，不要把 `null` 当 `0` 或 `false`。  
7. **发现冲突立即标注**：不要自行取舍，记录冲突并在备注中说明，留给分析阶段决策。  
8. **MoE 模型必须同时列出总参数量和激活参数量**。  
9. **上下文窗口区分标称和有效**；有效未经测试填 `null`。  
10. **官方自报分标签规则**：官方技术报告可直访 → `T0-自报`；不可直访、经媒体转述 → `T0-自报-转述`（决策 2），不得混标。  
11. **退役 / 已下线模型全量采集**（决策 5）：退役但 API 可用 → `verification_status="已过期"`；完全下线 → 保留记录 `notes` 标「已下线」。  
12. **最终输出 JSON Lines，不要输出报告**。

---

## 10. 开始执行

请立即开始联网调研。按照上述步骤和规则，采集所有 28 家厂商的旗舰与主线模型静态数据。在响应中直接输出 JSON Lines 数据，最终输出不要包含任务理解、计划、解释等额外文字。如果无法一次完成全部厂商，请先返回已完成的部分，并明确剩余数量。

现在开始。