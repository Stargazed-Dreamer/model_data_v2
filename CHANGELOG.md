# CHANGELOG

本变更日志记录 `model_data` 工作区数据集与可视化的演进。版本号采用 `D<轮次>` 形式，对齐整改轮。

- **D40 遗留待拍板（D41 全部结清）**：~~5 条 arena 段位错置~~ → **D41 移除 4 条**（实为 4 条，D40 报告标题「5 条」系笔误）；~~`bytedance:dola-seed-2-0-pro:base` 信息过薄是否保留~~ → **D41 裁定保留**并结构化补录 arena 三榜；~~vendor 大小写混乱~~ → **D41 统一为首字母大写品牌式**（229→198 种）；~~Qwen 命名双轨~~ → **D41 统一为 `qwen-3-*`**（40 条）；~~license 余 46 条空白~~ → **D41 留档** `docs/LICENSE_GAP_BACKLOG.md`。本行已无未结项。
- **Wave-1 遗留待拍板（D40 全部结清）**：~~Gemma 4（2026-04-16，5 尺寸，Apache 2.0）与 Step 3.7 Flash（2026-05-28，198B/11B MoE VLM）属漏采待批~~ → **已在库**（`google:gemma-4-*` 6 条 / `stepfun:step-3-7-flash:base` 2026-05-29）；~~Cohere Parse 5 待批~~ → **D38 移除、D39 用户终裁维持移除**；~~Qwen3.7-Plus 思考档仍无独立口径证据~~ → **已在库**（`alibaba:qwen3-7-plus:base` 与 `alibaba:qwen3-7-plus-none:base`，2026-06-01）。本行已无未结项。

- **D42 遗留待拍板（D43 全部结清）**：~~① s1 家族三兄弟语义不自洽~~ → **D43 拍板版本+参数式**（`s1-1`→`s1.1-1.5b`、`s1-32b`→`s1.1-32b`）；~~② luxia-21-4b / olmo-3-32b / minicpm 两类结构问题~~ → **D43 按官方名落改**（`luxia-2.1-4b-alignment`、`olmo-3.1-32b-instruct`、`minicpm-1b`/`minicpm-2b`）；~~③ vendor 别名 z-ai-zhipu-ai-tsinghua-university vs zhipu~~ → **D43 统一为 `zhipu`**（3 条改挂 + glm-4.5/glm-4.6 重复档案合并，937→935）；~~④ 台账 google-deepmind-google 前缀漂移~~ → **D43 台账 models 一次归位 186 处**（86 批次，0 歧义）。本行已无未结项。
- **D44 遗留待拍板（D45+D46 全部结清）**：~~漏采线索 22 条待 S1 拍板~~ → **D45 采 9 / D46 复筛后采 6、排除 7 + dspark 身份核验并入**（22 条全部处置完毕，candidate_diff NEW 6→2 且剩余均为排除项）；~~fillplan 66 条抽验后写 import 落库~~ → **D45 落库 55 条**（ctx 8 / arch 48，只为空值补，抽验与 HF config 一致）；backlog 948 条存量长尾 → **仍开放**（缓采已清零，优先级降低）。
- **D46 遗留待拍板**：r1 同厂商同名 3 组（`qwen2.5-coder-32b` vs `qwen2.5-coder`、minicpm-4 双档、`glm-5.2` vs `glm-5.2-none` 疑似 D34 改名未覆盖 full_name）；r2 基准名大小写异写 14 簇待归一清理；license 待回填 +2（llada-ui / ui-venus-2-9b 官方明示未定）。

## [D46] - 2026-09-13

用户拍板（原文「直接做下一轮，并发加到 3」）：**D44 缓采复筛二批入库 + D34 离群体检器重建**。记录数 **944 → 950**，门禁 **ERROR 0 / WARN 0**。subagent 并发 3（用户放宽），7 个任务分三波。

### Added

- **`scripts/qa_outliers.py`（D34 失传体检器重建版）**：原脚本三处核实不可恢复（回收站系 rm 直删/工作区/git 历史），按 D34 CHANGELOG 留痕口径 + A 类报告方向重建——13 项注册检查 + r1/r2/v3 跨记录检查，`硬错`/`疑点`分级（D34 教训入注：倒挂精度差、知识截止语义均不硬报）。首轮基线：**硬错全 0**，r1=3 组同名簇、r2=13 簇基准名异写、v1=53 缩写对，报告落 `temp/d46_outliers_report.txt`。
- **6 条新模型入库（批次 `b334w1-modelscope`）**：`inclusionai:llada-ui:base`（16.7B MoE **扩散** LLM UI-agent，GitHub release 09-09）、`inclusionai:ui-venus-2-9b:base`（Qwen3.5-9B 微调 GUI agent，arXiv 08-27，license 官方明示待定→null）、`inclusionai:armor-ocr:base`（Qwen3-VL-8B 微调 OCR **权重模型**非管线，三源同日 08-20）、`alibaba:qwen-drive-1.0-4b:base`（驾驶规划 VLM，Qwen3.5-4B 基座+流匹配 expert，发卡 ctx 32K）、`modelbest:mathform-8b:base`（NL→Lean 4 形式化，Qwen3-8B 微调）、`baai:recon2reason-reasoning-4b:base`（**新厂商 BAAI**，空间推理 VLM，Qwen3-VL-4B 微调）。全部过「模型/工具判定」（细则第 10 条 + D37 Parse 教训重点核对 OCR/UI 方向）。

### Changed

- **Ling-3.0-flash-dspark 身份核验后并入不单列**：官方 README 自证为 Ling-3.0-flash 的投机解码 speculator（1.36B/5 层 draft、依附主模型隐状态、无独立能力跑分），按 D35 一行一个测量身份不建条；关键信息 + 「acceptance length 5.29 属吞吐指标」防混淆注记并入 `inclusionai:ling-3.0-flash:base` notes（备份 `backups/model_data_v2.pre-d46-dspark-*.jsonl`）。
- **D44 缓采 13 条复筛**：6 采（上）/ 7 永久排除（MiniCPM5-2B-{SFT,Base,Midtrain}、JustRL-II、Ling-3.0-flash-base-{midtrain,30T} 训练中间产物）。candidate_diff 复扫 **NEW 6 → 2** 且剩余均为排除项——D44 漏采线索 22 条全部处置完毕。

### Note

- 新 6 条零引入硬错（qa_outliers 复扫与基线持平）；r2 基准名大小写簇 13→14（新跑分表带入，入清理清单）。
- license 待回填 +2：llada-ui（官方未披露）、ui-venus-2-9b（官方明示 pending final confirmation）。

## [D45] - 2026-09-13

用户拍板（原文「能继续就继续采集」）：**魔搭补全落库 + D44 漏采线索首批 9 模型采集入库**。记录数 **935 → 944**，门禁 **ERROR 0 / WARN 0**。约束：subagent 并发 ≤2（用户指定），9 个采集 agent 分五波。

### Added

- **9 条新模型入库（批次 `b333w1-modelscope`）**：`deepseek:deepseek-v4.1-flash:base`（552B MoE CED，官方新闻稿 09-10）、`deepseek:deepseek-v4-flash-vision-exp:base`（08-21 发布、09-10 官宣退役→「已过期」）、`inclusionai:ling-3.0-flash:base`（124B/A5.1B KDA+Gated MLA Hybrid）、`inclusionai:ling-3.0-flash-vl:base`（124B/A5.5B 原生视频输入）、`inclusionai:ling-3.0-tiny:base`（7.9B/A1.3B）、`modelbest:minicpm-5-2b:base`（2.52B Dense，GitHub News 09-07）、`nex-agi:nex-n2.5-max:base`（1.6T/A49B，基于 DeepSeek-V4-Pro-Base 后训练，国资委会 09-09 首发文）、`alibaba:qwen-3.8-flash-next:base`（180B=125B LM+51B N-gram+4B MTP /A6B，Gated DeltaNet+QSA Hybrid，原生 262K/YaRN 1M）、`meituan:longcat-flash-lite-sparse:base`（69B/A3B，LSA 稀疏注意力，1M）。
- release_date 全部回官方一手或诚实降级：4 条日级（官方 news 页×2、国资委会文、GitHub News）+ 1 条日级媒体当日转述（标待验证）+ 4 条月级（仅仓库/论文锚点）。2 条 Elo 型绝对分（Codeforces 3471、GDPval-AA 1713）按门禁不入 benchmarks、留 notes。

### Changed

- **魔搭补全落库 55 条（`scripts/d45_import_modelscope.py`，只为空值补）**：`context_window_tokens` 补 8、`architecture_type` 补 48（config.json 结构判据，Hybrid 不导）；抽验 6 条：5 条与 HF config 全等、1 条 gated 按公开规格吻合；MS 仓库 URL 入 source_urls、notes 留痕。
- **口径发现**：config.json `max_position_embeddings` 是**原生标称**，主库口径是**最大可支持**——56 条旁证比对 36 同 / 28 差，差值全为口径差非错误，验证「只为空值补、不覆盖」正确；D44 报告「ctx 可补 64」实为证据可得数，真空值仅 8（详见 `docs/D45_REPORT.md` §一）。
- **D44 候选复扫**：`candidate_diff.py` NEW 11 → 6（入库 9 条全转 EXISTS/CHECK_VARIANT）。

### Note

- N2.5 家族 mini/Pro 的 release_date 仍 null（HF createdAt 09-07/08 属仓库创建日口径，§4 铁律不采，待官方公告）。
- 13 条缓采 + backlog 948 条长尾留存 `temp/d44_msscope_candidates.jsonl` / `d44_msscope_backlog.jsonl`；全库离群体检脚本（D34 31 项口径）待重建，本轮以 9 条新记录针对性体检替代（0 真问题）。
- **subagent 并发 ≤2** 为用户额度约束，后续采集轮沿用。

## [D44] - 2026-09-13

用户触发（原文「魔搭社区有很多模型的参数和信息，你看看我们能不能用上」）：**ModelScope（魔搭）以免鉴权结构化 JSON API 接入跟踪源清单 A 层**。S0 探测轮，**主库零改动**（935 条不变，门禁 ERROR 0 / WARN 0），产物全落 `temp/`。

### Added

- **A 层新源（`跟踪源清单.md` §A-1）**：`PUT /api/v1/dolphin/models`（SortBy 枚举 Default/DownloadsCount/StarsCount/GmtModified，Default 实测最新优先）+ 详情接口 + config.json 仓库文件接口，免鉴权 200。**国内厂商版图首次有结构化发现源**（inclusionAI/OpenBMB/openmoss/01ai/nex-agi 等 OpenRouter 缺失厂商均在魔搭有官方组织）。实测三坑：无组织过滤参数（只能 Name 前缀搜索 + Path 客户端过滤）、组织名大小写敏感（openmoss）、列表 item 的 model_size 常空需补拉详情。
- **`scripts/d44_fetch_modelscope.py`**：22 官方组织白名单 → 2,979 仓库快照 → canon 精确匹配 → 漏采线索 22 条（candidate_diff 判定 NEW 11 / CHECK_VARIANT 10 / EXISTS 1，真缺口含 DeepSeek-V4.1-Flash、Ling-3.0 flash/tiny/VL 本体系、Qwen3.8-Flash-Next、MiniCPM5-2B 系、Nex-N2.5-Max、LongCat-Flash-Lite-Sparse）+ open_weights 空字段补全候选 66 条（ctx 可补 64 / arch_type 可判 55，覆盖全库 67 条 open_weights 空 ctx 的 95%）+ backlog 948 条。dry-run 不写库，`--skip-fetch` 可复用快照。

### Changed

- **`modelscope_model_update/SKILL.md`（兄弟工作区）**：阶段 3 增加 JSON API 快速路径（含 Path 过滤/大小写警告），DOM 选择器（`acss-17aobl4`，自标改版风险）降为兜底；风险条目 1 同步。

### Note

- 口径红线沿用并固化进脚本：CreatedTime=仓库创建日非发布日（§4）、镜像/社区组织不收、量化变体并入不单列（§3）、model_size 是字节数非参数量、匹配仅 canon 精确（D40）。详见 `docs/D44_REPORT.md`。

## [D43] - 2026-09-11

用户拍板四项全选推荐项：**D42 四类结构遗留落改 + zhipu 别名归并 + 台账 models 数组一次归位**。门禁 **ERROR 0 / WARN 0**，记录数 **937 → 935**。

### Changed

- **结构改名 6 条**：`allen-institute-for-ai:s1-1:base` → `s1.1-1.5b:base`、`s1-32b:base` → `s1.1-32b:base`（版本+参数式，与全库惯例一致）；`olmo-3-32b-instruct:base` → `olmo-3.1-32b-instruct:base`（官方发布名 Olmo 3.1，version 字段明写）；`saltlux:luxia-21-4b-alignment:base` → `luxia-2.1-4b-alignment:base`（full_name 明写 2.1）；`modelbest:minicpm-1-2b:base` → `minicpm-1b:base`、`minicpm-2-4b:base` → `minicpm-2b:base`（对齐官方名，精确参数量 1.2B/2.7B 本在 `architecture.total_params_b`）。
- **vendor 别名归并**：`z-ai-zhipu-ai-tsinghua-university`（3 条）→ `zhipu`；其中 `glm-4.5`/`glm-4.6` 与 zhipu 侧重复档案**合并**——以 zhipu 侧为主档（benchmark 带 config/date），长前缀侧独有 benchmark 并入（glm-4.6 的 CC-Bench 胜率、Token 效率；glm-4.5 两侧 14 条同名同分零冲突）、null 字段补值、source_urls 并集、标量冲突保留主档并留痕。**937 → 935**。
- **台账 models 数组一次归位 186 处（86 个批次）**：发现漂移是系统性的（多平台 agent 按批次原始 vendor 串登记 vs 主库 D41 归并口径）。解析链三步、每步要求唯一命中（0 歧义）：family+variant 唯一（131，vendor 漂移）、D42/D43 family 映射后唯一（53，连缀漂移）、同 vendor family 唯一（2，variant 漂移如 `claude-3-haiku:20240307`→`:base`）。`status`/`submitted_files`/批次 `vendor` 字段**逐字段核验零改动**。

### Fixed

- 收尾核验全过：model_id 唯一、9 个旧 id 零残留、`z-ai-zhipu` 前缀零残留、glm-4.6 合并内容抽查、台账 66 条真未入库条目保留原登记（远古批未合并/被拒候选/库内缺口）。

### Note（台账暴露的库内真实缺口，下一轮候选）

`google:gemma-4-31b:base`（基座缺，只有 -it）、`lg:exaone-3.5-r-2.4b`（R 系 2.4B 缺）、`google:gemini-3.6-flash-cyber`（3.5 有 3.6 无）、`meituan:longcat-flash`（仅日期 variant，二选一歧义）、`t-bank:t-pro`（库内只有 t-pro-2.0）等，详见 `docs/D43_REPORT.md` §四。

## [D42] - 2026-09-10

用户触发（原文「点号问题有什么解决方案吗，你设计一下然后一起改了」）：**`model_id` 点号口径统一 —— 小数一律写 `.`**。主库 **937 条不变**（零增删），门禁 **ERROR 0 / WARN 0**。

### Added

- **点号规范（`docs/prompt.md` §6.4 新增强制条款）**：`family` / `variant` 段中，凡**官方名称里的小数点一律写作 `.`**；`-` 只作 token 分隔符，不得代替小数点。
  - 版本号含小数 → 点：`claude-opus-4.5`、`deepseek-v3.1`、`qwen-3.5-max-preview`、`gemini-2.5-pro`
  - 参数量含小数 → 点：`qwen-3-1.7b`、`exaone-3.5-2.4b`、`qwen2.5-1.5b`、`granite-3.0-2b`
  - 非小数点的连字符**一律保留**：快照日期（`2025-09-23`）、整数参数量（`qwen-2-57b-a14b` 的 `A14B`、`minimax-m1-40k`、`deepseek-coder-v2-236b`）、模型名内嵌数字（`baichuan2-13b`、`telechat2-115b`、`llama-2-70b`、`agentar-fin-r1-32b`）
- **判据为「证据驱动」而非人工逐条判断**：对 `family` 中每处「数字-数字」连字符，取左右最大连续数字串 `a`、`b`，**仅当字面串 `a.b` 出现在 `basic_info.full_name` 或 `basic_info.version` 原文中**才判为小数点。天然排除日期、整数参数量、模型名内嵌数字。
- **反例保护**：`qwen-3-8b`（Qwen3-8B，第 3 代 80 亿）`full_name` 不含 `3.8`，不会被误改为 `qwen-3.8b`；`gemma-2-2b`（Gemma 2 2B）同理。
- 脚本 `scripts/d42_dots.py`（归一，含证据池 / 亲缘继承 / 下划线小数点 / 隐式排除 / 碰撞预检）、`scripts/d42_ledger_sync.py`（台账同步）、`scripts/d42_postcheck.py`（收尾自检 5 项）。

### Changed

- **`model_id` 改名 314 family / 317 条记录**（占全库 33.8%），family 含点号 **6 → 318**，重命名碰撞 **0**。证据来源：`full_name` 94 ／ `version` 10 ／ 两者兼有 206 ／ 亲缘继承 3 ／ 人工补录 1。
  - 核心歧义消除：`alibaba:qwen-3-1-7b:base` → `alibaba:qwen-3-1.7b:base`（Qwen3-1.7B 不再可能读成 Qwen3.1-7B）；`alibaba:qwen-3-5-max-preview` → `qwen-3.5-max-preview`（Qwen3.5 世代显式化）
  - 双小数还原：`lg:exaone-3-5-2-4b:base` → `lg:exaone-3.5-2.4b:base`
  - 与无小数版本区分：`anthropic:claude-opus-4-5:20251101` → `claude-opus-4.5:20251101`，同族 `claude-opus-4-20250514-16k`（Opus 4）保持无点号
  - 连缀小数：`openthaigpt-v1-0-0` → `openthaigpt-v1.0.0`（需前瞻匹配才能全部还原）
  - 下划线小数点：`apple:openelm-1-1b:base` → `openelm-1.1b`、`alibaba:qwen-1-8b:base` → `qwen-1.8b`
- 每条改名记录 `meta.notes` 追加 `【D42 点号归一】原 model_id: X → Y`。
- `docs/batch_claim_ledger.jsonl`：**`models` 数组同步 156 处**（覆盖 b304–b332 共 20+ 批次，含其他平台登记的批次）；**`submitted_files` 保持历史文件名不改写**。
- **`docs/prompt.md` §6.4「执行约束（P1 修复）」中「严禁把 v1 连字符 id 纠正为点号风格」的禁令已废止**（与新增点号条款直接冲突），并注明废止理由；保留其原本意图——采集 agent 仍不得自行改写 model_id、不得借改名绕过「同模型须合并而非新建」；**存量归一改由主 agent 在专项轮次执行**。决策表第 6 项同步补入口径。
- **活文档残留旧 id 扫描与裁定**（沿用 D41 约定「历史归档与案例引用不改写」）：`docs/multi_platform_subagent_guide.md` 文件命名示例**同步改写**为 `google:gemini-3.5-flash-minimal:base` 并加 D42 注记（唯一被 agent 照抄的操作型模板）；其余 `docs/WORKBUDDY_AGENT_GUIDE.md` 7 处、`docs/prompt.md` L779、`docs/增量更新工作流.md` L103/L164、`scripts/d21_*`/`d41_*`、`intermediate/*` 均为历史案例/归档/中间态，**保持原样**。裁定明细见 `docs/D42_REPORT.md` §6.4。

### Fixed

- 修正 317 条记录中 `family` 段「小数点被写成连字符」导致的**数字连串不可机械切分**问题（详见 `docs/D42_REPORT.md` §二）。
- 收尾自检 5 项 ALL PASS：`model_id` 唯一性 / 仅点号位变化（逐条验证 `新family.replace('.','-') == 旧family`，且 vendor 与 variant 段未动）/ 数组无缩水 / 记录数与字段数 / 可证伪的连字符残留 0 处。

### Excluded（另行上报，非点号问题）

- `allen-institute-for-ai:s1-1:base` —— s1 家族三兄弟（`s1` / `s1-1` / `s1-32b`）的 `-1` 语义不自洽：full_name 分别为 `s1-32B`(v1.0) / `s1.1-1.5B` / `s1.1-32B`，转成 `s1.1` 会与 `s1-32b` 的读法冲突。属**结构问题**（family 是否编码参数量未定），本轮显式排除。
- `saltlux:luxia-21-4b-alignment:base`（`21` 应为 `2-1`）、`allen-institute-for-ai:olmo-3-32b-instruct:base`（官方发布名 Olmo **3.1** Instruct，HF 仓库 `allenai/Olmo-3.1-32B-Instruct`）、`modelbest:minicpm-1-2b` / `minicpm-2-4b`（family 与 full_name 的参数量互相矛盾）——均为**缺分隔符 / 缺版本位**，非点号转写问题。

### Note

- 归一后 family 数 919 → 917：`z-ai-zhipu-ai-tsinghua-university` 与 `zhipu` 两个 vendor 前缀下同时出现 `glm-4.5` / `glm-4.6`（family 名归一后重合，主键因 vendor 不同而不撞）。属 vendor 别名问题（D41 未合并的多主体联合串同类），非本轮范围。
- 本轮只动 `family` 段：全库 `variant` 段仅 1 条含「数字-数字」（`cohere:command-r-plus:2024-08`，是月份段而非小数点），无需处理。

## [D41] - 2026-09-10

用户触发，D40 报告 §七 五项遗留一次裁定并执行（原文「1. 移除 2. 保留 3. 统一首字母大写 4. 统一qwen-3 5. 留档后续再做」）：**① 移除 arena 段位错置条目 ② `dola-seed` 保留 ③ vendor 命名统一为首字母大写 ④ Qwen 3 世代命名统一为 `qwen-3-*` ⑤ license 缺口留档**。主库 **937 条不变**（本轮零增删记录，全部是字段级整改），门禁 **ERROR 0 / WARN 0**。

### Removed

- **arena 段位错置条目 4 条**（`sub_benchmark` 取值不属 LMArena 标准段位 text/coding/math/vision/webdev，用户裁定「移除」）：

  | model_id | 被删 sub_benchmark | score | 原判断 |
  |---|---|---|---|
  | `baidu:ernie-5-1:base` | `search` | 1223 | 官方博客转述 Arena Search 榜，非库内标准段位 |
  | `google:gemini-3-1-pro-preview-high:base` | `LiveCodeBench Pro` | 2887 | 第三方竞赛级编程榜，非 arena 榜 |
  | `meta:muse-spark:base` | `gdpval` | 1444 | GDPval 办公任务评估，非 arena 榜 |
  | `zhipu:glm-5-2-none:base` | `agent` | 1524 | 媒体博客转述，未经 LMArena 直证；该条为该记录唯一 arena 条目，删后 `arena_elo` 为空 |

  每条 `meta.notes` 均写有 `【D41 arena 段位错置移除】` 留痕（含「如为独立榜单应迁 independent 段」的备注，本轮按裁定直接移除未迁移）。

  > ⚠ **勘误**：D40 报告 §七.1 标题写「5 条」为笔误，正文表格与说明均为 4 条，实际亦为 4 条（已回填勘误注记）。

### Added

- **`bytedance:dola-seed-2-0-pro:base` 结构化补录 arena 三榜**（用户裁定「保留」）。**勘误**：D40 报告 §七.2 描述该记录「仅 arena 数据（text 1456 / coding 1513 / math 1451）」不准确——D40 采集 agent 把这 3 个 Elo 值**只写进了 `meta.notes` 散文**，`benchmarks.arena_elo` 实为空数组。本轮按同一权威快照结构化落地 3 条：
  | sub_benchmark | score | rank | ci_95 | votes | is_primary |
  |---|---|---|---|---|---|
  | text | 1456.0 | 59 | ±3 | 74,277 | true |
  | coding | 1513.0 | 43 | ±6 | 20,711 | false |
  | math | 1451.0 | 66 | ±10 | 4,083 | false |

  来源 `DataLearner 镜像 LM Arena`，快照 `versionTime=2026-09-02`，`confidence=T1`；三项数值已与 `temp/dl_pg_{text,coding,math}.html` 逐项核对，与采集时写入 notes 的散文值完全一致（**无新增事实，仅为已有事实的结构化落地**）。
- **`docs/LICENSE_GAP_BACKLOG.md`（新建）**：第 ⑤ 项「留档后续再做」的产物。明确口径——「license 空白」不是全库 412 条（多数是闭源模型，本就无开源许可证），真实缺口为 **A 类：`open_weights=true` 但 license 空 46 条** + **B 类：`open_weights=null` 且 license 空 16 条**；并附后续补采方法（HF API `tags` 读 `license:` + 同尺寸一致性校验）。

### Changed

- **`basic_info.vendor` 命名统一（261 条 / 86 种源值）**。规则两层：① 同厂商多写法合并为单一品牌名；② 其余首字符为小写 ASCII 字母的值改为品牌惯用写法。
  - **合并效果（按厂商聚合的漏计被消除）**：`Google DeepMind`→`Google`（37+36→**73**）、`Alibaba` 多写法 5 种→`Alibaba`（88→**98**）、`DeepSeek（深度求索）`→`DeepSeek`（29→**37**）、`Meta AI`/`Meta (Meta AI)`→`Meta`（19→**32**）、`Mistral AI`+`mistral`→`Mistral AI`（→**42**）、Zhipu 多写法 4 种→`Zhipu AI`（→**16**）、`allenai`+`allen-institute-for-ai`→`Allen Institute for AI`（→**19**）、`ByteDance Seed Team`/`ByteDance Seed`/`ByteDance (字节跳动)`→`ByteDance`、`Moonshot`/`Moonshot AI (月之暗面)`→`Moonshot AI`、`Sber（…）`3 种→`Sber`、`华为（…）`2 种+`huawei`→`Huawei`、`Xiaomi`/`xiaomi`→`Xiaomi`、`Meituan`/`meituan`→`Meituan`、`tsinghua`/`tsinghua-university`→`Tsinghua University`、`ModelBest` 4 种→`ModelBest`、`qihoo-360` 2 种→`Qihoo 360`、`4paradigm`→`4Paradigm`。
  - **首字母大写（品牌惯用写法，非机械首字母）**：`lg`→`LG`、`tii`→`TII`、`sdaia`→`SDAIA`、`mbzuai`→`MBZUAI`、`lmsys`→`LMSYS`、`iflytek`→`iFlytek`、`stepfun`→`StepFun`、`sambanova`→`SambaNova`、`lighton`→`LightOn`、`nexusflow`→`NexusFlow`、`character-ai`→`Character.AI`、`sha-ai-lab`→`Shanghai AI Laboratory`、`nous`→`Nous Research`、`kunlun`→`Kunlun Tech`、`singapore-ai`→`AI Singapore`、`stability`→`Stability AI`、`voyage`→`Voyage AI`、`princeton`→`Princeton University`、`sk-telecom`→`SK Telecom`、`unicom`→`China Unicom` 等共 86 种源值。
  - **保留品牌自身的小写首字母**：`xAI` 保持 `xAI`（用户选「保留品牌惯用写法」）。
  - **多主体联合串不合并**：含 `+` / `/` / `,` 的联合研发串（如 `Microsoft + NVIDIA（联合开发）`、`RWKV Foundation / EleutherAI / …`）视为「研发主体描述」而非厂商，保持原文本不做合并与改写。
  - 效果：`vendor` 取值 **229 种 → 198 种**；首字母小写 **62 种 → 2 种**（余 `xAI`、`iFlytek`，均为品牌自身写法）。
  - 全 261 条 `basic_info.notes` 均追加 `【D41 vendor 归一】原 vendor: X→Y`。**脚本内置覆盖率断言**：任何首字母小写的 vendor 值若无显式映射即报错，不留静默兜底（该断言曾拦下漏配的 `huawei` / `salesforce`，及映射不一致的 `qihoo-360`→`Qihoo-360`）。
- **`model_id` 前缀归一为小写 slug（56 条）**。按 `docs/prompt.md` §6 / §6.4「vendor 小写 slug」既有规范执行：`Alibaba`13 / `Google`8 / `Cohere`6 / `DeepSeek`4 / `Meta`3 / `IBM`3 / `Microsoft`3 / `ModelBest`3 / `Hugging Face`2 / `Databricks`2 / `Tencent`2 / `xAI`3 / `NVIDIA`1 / `Deep Cogito`1 / `Baidu`1 → 对应小写 slug（`Hugging Face`→`huggingface`（并入既有同名前缀记录）、`Deep Cogito`→`deep-cogito`）。
  - **附带修正 1 处语义错误前缀**：`unknown:yue-ai:base` → `ireader-technology:yue-ai:base`（该记录 `basic_info.vendor` 本为 `IReader Technology（掌阅科技）`，前缀写 `unknown` 属明显缺陷）。
  - 效果：前缀 **207 种 → 192 种**，首字母大写前缀 **14 种 → 0**；重命名碰撞预检 **0 组**。
- **Qwen 3 世代 `model_id` 统一为 `qwen-3-*` 连字符式（40 条 / 39 个 family）**。按用户裁定「统一 qwen-3」，把 `qwen3-*` 全部改为 `qwen-3-*`：`qwen3-235b-a22b`→`qwen-3-235b-a22b`、`qwen3-5-max-preview`→`qwen-3-5-max-preview`、`qwen3-coder-480b-a35b`→`qwen-3-coder-480b-a35b`、`qwen3-embedding`/`qwen3-reranker`→`qwen-3-embedding`/`qwen-3-reranker` 等，与既有 `qwen-3-5-flash` / `qwen-3-6-27b` / `qwen-3-8-max` 三例合流。
  - **⚠ 这是对 D40 处置的反转**：D40 曾把新入库的 `qwen-3-6-plus-preview` 归一为**紧贴式** `qwen3-6-plus-preview`（当时依「紧贴 36 : 连字符 3」的多数惯例）；本轮按用户终裁改为连字符式，该条随本轮一并改回 `qwen-3-6-plus-preview`。
  - 转换后与既有 `qwen-3-*` 无碰撞（已逐条预检；`qwen3-6-27b-none` → `qwen-3-6-27b-none` 与既有 `qwen-3-6-27b` 为不同 family，不冲突）。
  - **未改动的世代**：`qwen-*`（原始 Qwen：`qwen-7b` / `qwen-1-8b` / `qwen-plus` / `qwen-turbo-*`）、`qwen1-5-*`、`qwen2-*` / `qwen2-5-*` / `qwen2-math-*`、`codeqwen1-5-7b` 均按裁定范围（Qwen 3 世代）保持原样。
  - 全 40 条 `meta.notes` 追加 `【D41 命名归一】原 model_id: X→Y（Qwen 3 世代统一为 qwen-3-* 连字符式）`。

### Docs

- `docs/D41_REPORT.md`（新建，本轮报告）；`docs/D40_REPORT.md` §七 加 D41 处置结论与两处勘误（「5 条」→4 条；`dola-seed` 的 arena 实为散文未结构化）。
- `docs/batch_claim_ledger.jsonl`：7 个批次的 `models` 数组按新 `model_id` 同步（`submitted_files` 保持历史文件名不改写）。共 **15 处** model_id 改写（14 处 `qwen3-*`→`qwen-3-*` + 1 处 `unknown:yue-ai`→`ireader-technology:yue-ai`），涉及 b15w2 / b15w3 / b50w1 / b307w1 / b318w1 / b319w2 / b330w1 共 7 个批次。
- `docs/WORKBUDDY_AGENT_GUIDE.md` §20 案例中的 `alibaba:qwen3-coder-480b-a35b` 加注 D41 已改名后的新 id（保留当时原文）。
- `docs/README.md` 索引补 D41 报告与 license 留档。
- 脚本固化到 `scripts/`（可审计 / 可复跑）：`d41_normalize.py`（vendor + 前缀 + Qwen 命名三项归一，含覆盖率断言与碰撞预检）、`d41_dola_arena.py`（dola-seed arena 结构化补录）、`d41_ledger_sync.py`（台账 model_id 同步）、`d41_license_backlog.py`（生成 license 留档）、`d41_postcheck.py`（收尾六项自检）。

### Notes

- **本轮零记录增删、零跑分/定价改动**：仅 `basic_info.vendor`、`model_id`、`meta.notes`、`benchmarks.arena_elo` 四处变动。数组缩水取证 **0 处**，撞键 **0 组**。
- 备份：`backups/model_data_v2.pre-d41-normalize-*.jsonl`（三项归一前）、`backups/model_data_v2.pre-d41-dola-*.jsonl`（dola 补录前）。
- `docs/archive/**`、`CHANGELOG.md` 历史条目中的旧 `model_id` 属**历史留痕，一律不回改**——归档记录反映当时状态，grep 旧 id 命中属预期。
- `incoming/models/**` **提交快照文件一律不改写**（内容与文件名都保留提交当时状态）：它们记录的是「提交时是什么」，主库才是当前真相；`docs/batch_claim_ledger.jsonl` 的 `submitted_files` 亦保持原文件名与之对应。标识变更只体现在主库与台账 `models` 字段。因此 grep 到 `incoming/models/` 下的 `qwen3-*` 文件名属预期，不是残留。
- D40 报告 §七 五项至此**全部结清**。

## [D40] - 2026-09-10

用户触发，四项拍板一次执行（原文「1.是 2.是 3.看看能不能浏览器去连 4. AB的采集也可以一起做了」）：**① arena 快照瘦身 ② D40 候选开采 ③ Artificial Analysis 独立跑分接入 ④ A 类历史缺口 + B 类增量采集并行**。主库 915 → **937 条**（本轮 +22），门禁 **ERROR 0 / WARN 0**。

### Added

- **Artificial Analysis 免鉴权接入 + 独立跑分大批导入（本轮最大增量）**：
  - **第 ③ 项拍板原话是「看看能不能浏览器去连」**——实测**不需要浏览器**：AA 官方 API `/api/v2/data/llms/models` 返 **401（需 key）**，但榜单页 `https://artificialanalysis.ai/leaderboards/models` 200 / 2.75 MB，**644 个模型的全部评测字段内嵌在 Next.js App Router 的 flight 流里**（`self.__next_f.push([1,"…"])`）。沿用 D39 的 flight 流提取法即可直读，比装 Chromium 更省。采集脚本固化 `scripts/d40_fetch_artificial_analysis.py`，产物 `temp/d40_aa_models.json`（735 条，644 带 `releaseDate`，633 带 `intelligenceIndex`）。
  - **导入口径（保守）**：**仅精确匹配**（270 对；模糊匹配曾把 `command-a-plus` 误配到 `qwen-plus`，已弃用）；**仅对 `independent` 为空的记录写入**；`release_date` 仅在主库为月级且 AA 为同 `YYYY-MM` 的日级时才精化；**`intelligenceIndex` / `omniscience` 等复合指数一律不导入**（量程 3.75–53.37，非 0–1 准确率，混入会污染对比）。
  - **结果**：写入 **99 条记录 / +913 条 independent 条目**，43 条 `release_date` 由月级精化到日。
- **Wave-1 增量采集 22 条入库**（批次 `b329w1-openai` / `b330w1-alibaba` / `b331w1-tencent` / `b332w1-deepseek`，4 批次全部 submitted，22 文件单文件门禁 ERROR 0）：
  - OpenAI/Anthropic/Google 6 条：GPT-5.5 Instant、GPT-4.1 Nano、GPT-5 Nano、Claude Mythos 5.1（Wave-1 遗留）、Gemini Advanced 0514、Gemini Pro Dev API；
  - 阿里 5 条：Qwen3.5/3.6/3.7-Max-Preview、Qwen3.6-Plus-Preview、QwQ-32B-Preview；
  - 腾讯 5 条：Hunyuan-Standard-256K / Hunyuan-Standard-20250210 / Hunyuan-Turbo-0110 / Hunyuan-Vision-1.5-Thinking / Hunyuan-Large-Vision；
  - DeepSeek+Xiaomi+美团+字节 6 条：DeepSeek-V4-Flash/Pro-High-Preview、MiMo-V2-Flash、MiMo-V2-Omni、LongCat-Flash-Chat-2602-Exp、DOLA Seed 2.0 Pro。
- **license 权威补全 36 条（A 类历史缺口 #5）**：改走 **HuggingFace API**（`huggingface.co/api/models/{repo}` 的 `tags` 里读 `license:` 标签）作为权威源，取代此前正则从 notes 抽取文本的做法（正则曾把 `HF`、`Under the MIT` 误判为许可证名）。配套**同尺寸一致性校验**：repo 与记录的参数规模 token 取交集，交集为空则拒写——成功拦下 `g42:jais-70b` ← `inception42/jais-13b` 这类错配。结果：写入 36 条 / 3 条尺寸不符拒写 / 11 条 repo 无 license 标签 / 32 条无 repo 可定位。

### Changed

- **arena_elo 快照瘦身（第 ① 项拍板）**：条目 **809 → 633**，同 `(model_id, sub_benchmark)` 仅保留最新 `date` 一条，历史快照移除（D39 遗留副作用就此清账）；同时归一 `is_primary`（仅 `text` 为 `true`，其余 `false`）——初版脚本曾把所有缺失值置 `true`，与库内惯例（text 266 True / coding·math 全 False）不符，已修正。删除前的全量快照存 `backups/model_data_v2.pre-d40-arena-slim-20260910-152340.jsonl`。
- **日期精度**：`release_date` 到日 665 → **709**，到月 245 → 220，缺失 5 → 6（新增仅 `bytedance:dola-seed-2-0-pro:base` 无信源，见下）。
- **跑分覆盖**：`independent` 340（37.2%）→ **450（48.0%）**；条目数 1,050 → **2,011**；完全无跑分 232 → **210**。`self_reported` 条目 4,256 → 4,284；`arena_elo` 条目 809 → 662（瘦身 -147、新增 +29）。
- **license 填充率** 51.0% → **56.0%**。

### Fixed —— 采集件归一（22 个文件全部 ERROR 0 / WARN 0 后方可合并）

E/F/G 组采集 agent 产出的 22 个文件里有 **7 个未过门禁**，逐类修复（修复脚本 `temp/d40_fix_incoming.py` 等，采集原件留档 `temp/d40_incoming_orig/`）：

| 类 | 处数 | 问题 | 处置 |
|---|---|---|---|
| `source_type` 枚举违规 | 25 | agent 自造 `官方发布页（自报）` / `行业媒体转述官方发布` / `LMArena`，不在受控枚举内（D26 起升 ERROR） | 按库内惯例归正：`confidence=T0-自报-转述` 主流配对 `行业媒体转述官方发布（自报）`（169 例） |
| arena 段来源虚假 | 5 组 | `source_url` 指向新闻站（news.qq.com / ithome.com）或上游 `arena.ai`，`rank/votes/ci` 被塞进 `notes` 文本 | **整段以 DataLearner 本地快照（2026-09-02）权威值重建**，补齐 `rank` / `votes` / `ci_95` 独立字段 |
| 日期格式 | 1 | `gemini-pro-dev-api` 的 `release_date='2024'` 非 ISO | 查证 Google 开发者博客：Gemini API 面向开发者开放日 **2023-12-13**，据此改精确到日，`verification_status` 改「已定死」 |
| 字段键名漂移 | 1 | `pricing.long_context` 用 `input_multiplier`/`output_multiplier` | 改规范键 `input`/`output` 绝对价（$2.00/$12.00 per M），乘数留 notes |
| 定价生效日缺失 | 6 | 有定价但无 `pricing.effective_date`（库内基线为 298/298 全有） | 锚定官方发布/版本标签日补齐；仅知月份用 `YYYY-MM` 并在 notes 注明周期（**不伪造到日**） |
| 命名漂移 | 1 | `qwen-3-6-plus-preview` 与同族 `qwen3-6-plus` 及 qwen3-5/6/7-max-preview 不一致 | 归一为 `qwen3-6-plus-preview`（库内 `qwen3-*` 紧贴式 36 : 连字符式 3），台账同步 |

**关键发现：采集 agent 写的 arena 分值与真值有偏差**——`qwen3-7-max-preview` coding 档 agent 记 1526（新闻转述），DataLearner 权威值 **1525**；`qwen3-5-max-preview` text 档记 1464，权威值 **1466**。核对后才写入，未沿用新闻口径。

### 待拍板（留给下一轮）

- **5 条 arena `sub_benchmark` 段位错置**：`search` / `LiveCodeBench Pro` / `gdpval` / `agent`（各 1 条）与 `vision`，其 `sub_benchmark` 取值不在库内主流枚举（text/coding/math/vision/webdev），且其中 4 条的 `source_type` 标为 `LMArena 镜像（DataLearner）` 但实际来源存疑。**属跨段位迁移还是移除，需用户裁定**，本轮未自动处置。
- **`bytedance:dola-seed-2-0-pro:base` 信息过薄**：仅 arena 数据，无 `release_date` / 定价 / 架构（AA 与 OpenRouter 均无此模型），采集 agent 自评「可信度偏低」。是否保留待定。
- **vendor 大小写混乱**：库内并存 `Google` / `google`、`Alibaba` / `Alibaba Cloud` / `Alibaba (Qwen Team)` 等写法，`model_id` 前缀与 `basic_info.vendor` 脱钩（D34 扫描 A7：85 条）。已列入 A 类报告，未批量整改。
- **Qwen 命名双轨**：`qwen3-*`（36）vs `qwen-3-*`（3：`qwen-3-5-flash` / `qwen-3-6-27b` / `qwen-3-8-max`），建议下一轮统一。

### 环境坑（建议入清单 §5）

- **Artificial Analysis 的 API 401 不代表数据拿不到**：榜单页 flight 流里就是完整的 644 模型评测矩阵；直接 `curl --ssl-no-revoke` 即可，**无需装 agent-browser（≈500 MB Chromium）**。
- **DataLearner 的 coding / math 榜没有独立 API**：`/api/leaderboards/external/text-generation-coding` 会返回 HTML 而非 JSON（用 `json.load` 会报 `Expecting value: line 1 column 1`），必须存成 `.html` 后解析表格——且**模型名可能只出现在 `<a href>` / `aria-label` 属性里**（如 Qwen3.6-Max-Preview 行），按可见文本匹配会漏掉整行。

## [D39] - 2026-09-10

用户触发。范围：Cohere Parse 5 终裁 + arena 跑分批量补全 + 榜单反推漏采线索。主库仍 **915 条**（本轮未增删记录），门禁 **ERROR 0 / WARN 0**。

### Added

- **arena_elo 批量补全（本轮主目标）**：从 DataLearner 镜像的 LM Arena 榜单（快照 `2026-09-02`，text 400 / coding 395 / math 383 条）批量补入 **296 条** arena 条目，覆盖 **100 个模型**（其中 **43 个此前完全没有 arena 数据**）。arena 覆盖 172（19.1%）→ **215 条（23.5%）**，条目数 513 → **809**。
- **新数据源接入（免鉴权）**：
  - 主榜 API：`https://www.datalearner.com/api/leaderboards/external/text-generation` —— 直返 JSON（`meta` + `columns` + `data` 400 行），含 `rank` / `modelName` / `modelCode` / `score` / `ci` / `votes` / `organization` / `license` / `thinkingMode`。**端点藏在页面 `<script type="application/ld+json">` 的 `distribution.contentUrl` 里**，不在页面导航中出现。
  - 分类榜（coding / math）：**无独立 API**（404），数据内嵌在 Next.js App Router 的 flight 流（`self.__next_f.push([1,"..."])`，420 个块、约 1.1 MB），需拼接后按括号平衡提取。
  - 图像/视频榜（`image-edit` / `text-to-image` / `image-to-video` / `video-generation`）已探到路径，本轮未采（主库以文本模型为主）。
- **榜单反推漏采线索**：榜单 236 条未被主库命中 → 其中 **84 条疑似真漏采**（另有 152 条疑似"库内已有但命名不同"，difflib 模糊判定不可尽信）。真漏采里高价值的：GPT-5.2 Chat / GPT-5.5 Instant / GPT-5.3 Chat、Qwen3.5/3.6/3.7-Max-Preview（阿里）、ERNIE-5.1-Preview / ERNIE 5.0 Preview（百度）、Grok 4.1 Thinking / grok-4.20-multi-agent-beta、DOLA Seed 2.0 Pro（字节）、Kimi K2.5 Instant（月之暗面）、GLM-5V-Turbo（智谱）、mimo-v2-flash（小米）、hunyuan-vision-1.5-thinking（腾讯）、amazon-nova-experimental-chat-*、OpenAI o1/o3/o4-mini。明细落盘 `temp/d40_arena_gap_raw.json`，待 S0/S1 核实（榜单含匿名实验版代号，不可直接当正式模型采）。

### Removed

- `cohere:parse-v5-0:base` —— **D39 用户终裁：维持移除**。理由（用户口径）：**计费方式与主流不符（按页计费 $1.50/1,000 页，token 六键全 null），不像常规模型**。故 D37 Wave-2 二查的"2.3B 文档 VLM＝真模型"结论在"是否收为模型本体"这一判定上不构成保留依据——模型真伪与"是否符合本库收录口径"是两个层次的问题。回滚脚本 `temp/d38_restore_cohere_parse.py` **作废不再执行**；主库不受影响，隔离档 `docs/non_model_records.jsonl` 第 8 条为最终留档。

### 方法学（本轮新增的两道保守过滤）

批量补 arena 时，两类歧义一律**跳过而非猜测**，宁可留空：

| 过滤 | 触发条件 | 跳过条目 | 理由 |
|---|---|---|---|
| 榜单重名 | 同类别下存在多条同名「无变体标记」条目 | 33 | 榜单自身重名（如 `Claude 3.5 Sonnet` 1374/1343），无法确定对应哪条 |
| 版本差异 | 同一榜单条目被多个主库记录引用，且非仅上下文差异 | 63 | 如 `GPT-4` 被 0314/0613/1106/0125 四个快照共用；共用分数等同伪造 |
| （放行）仅上下文差异 | 同一榜单条目被多记录引用，但去掉 `-32k/-64k` 后完全相同 | 6 | 同模型不同上下文窗口，基准分可共享 |

- 变体口径：主库**无 thinking 标记**只取榜单「无变体标记」条目；主库含 `thinking/think/reasoning` 才取 `(thinking)/(high)/(xhigh)` 条目。
- 追加而非覆盖：沿用库内先例（`alibaba:qwen-3-8-max` 已有 2026-08-25 / 08-06 两个快照），同 `sub_benchmark` 保留多快照序列，靠 `date` 区分。**副作用：arena 条目数从 513 涨到 809，若认为历史快照冗余，可另起一轮做快照瘦身。**

### 环境坑（建议入清单 §5）

- DataLearner 页面是 Next.js App Router，`grep "elo"` 命中数为 0——数据在 flight 流里被转义且分片，必须拼接 `self.__next_f.push([1,"…"])` 后再解析；直接正则找 `"elo"` 会误判为"页面无数据"。
- 榜单 API 端点不在导航链接里，只在 `<script type="application/ld+json">` 的 `distribution.contentUrl` 字段。

## [D38] - 2026-09-10

用户触发。范围：新增源实测 + 跟踪清单固化 + 两个模型查证 + 跑分/日期增强 + Wave-2 采集。主库 900 → **915 条**，门禁 **ERROR 0 / WARN 0**。

### Added

- **Wave-2 候选 16 条全部采集入库**（批次 `b319w2`~`b328w2`，10 个批次全部 submitted）：Qwen3.8 Flash、Qwen3.8 2.4T A95B、Hy-MT2 三兄弟（1.8B/7B/30B-A3B）、Seed 2.1 Turbo、Seed-2.0-Code、Ling 3.0 Flash Sante/Fin、Nex-N2.5 Mini/Pro、Muse Glimmer 30B、Granite 4.2 8B、Sakana Namazu、LFM2.5-2.6B、Dots3-Note Preview。16 个文件单文件门禁均 ERROR 0，合并后无重复 model_id。
- **epoch.ai 本地数据批量导入**：`external_sources/epoch_benchmark_data/`（75 CSV / 2,417 行 / 619 模型）→ 补 **30 条**记录的 `independent` 跑分（原计划 34 条，4 条因无任何来源 URL 被门禁挡下）；`epoch_ai_models` 的 `Publication date` → **298 条** `release_date` 由月级补为日级。
- **新增跟踪源实测并固化 `docs/跟踪源清单.md`**：OpenRouter API（435 模型，带 `created`）与 HuggingFace API 均实测可用；新增「官方台账页映射表」（17 个 URL 批量实测，9 个 200 / 4 个连接失败 / 2 个 404 / OpenAI 403 反爬）。

### Changed

- **日期精度治理**：`release_date` 到日 368 → **665 条**，到月 532 → **245 条**。补日的一律在 `basic_info.notes` 标注「日期取自 epoch.ai Publication date（精度：日），官方发布日待核；原记录精度为月（YYYY-MM）」。
- **跑分覆盖**：`independent` 310（34.4%）→ **340（37.2%）**；完全无跑分 235 → 238（新增 16 条里 3 条暂无跑分）。
- **更新频率**：`docs/增量更新工作流.md` S0 改为**用户触发**，不再写"每周"。

### Removed

- `cohere:parse-v5-0:base` 移出主库、逐字节存入 `docs/non_model_records.jsonl`（第 8 条）。~~**⚠ 存争议**：D37 Wave-2 二查结论为「2.3B 文档 VLM，真模型」，与本轮「文档解析工具→非模型」判定冲突~~ → **D39 用户终裁：维持移除**（理由：计费方式与主流不符，按页计价、token 六键全 null，不像常规模型；见 [D39] Removed）。回滚脚本 `temp/d38_restore_cohere_parse.py` 已作废。

### Fixed

- `bytedance:seed-2-0-code:base` 有定价缺 `pricing.effective_date`（WARN 0 → 1），补 `2026-09-10` 并在 notes 注明"采集观察日，厂商真实调价日未披露"，基线回 WARN 0。

### 环境坑（已入清单 §5）

- 本机 curl 抓 HTTPS 必须加 `--ssl-no-revoke`，否则 `CRYPT_E_NO_REVOCATION_CHECK` 失败（HTTP 000）。此前"huggingface.co 直连必超时"的旧结论系此根因，已修正。
- epoch CSV 分数列名不统一（`Percent correct`/`EM`/`Score`/`Accuracy`…），只认一种会漏掉 97% 数据。
- epoch CSV 的 `Source link` 空时，URL 常藏在 `Source` 列（如 `artificialanalysis.ai`、`arcprize.org`）。

### Added（D37 Wave-2 二查缺口补采，2026-09-06）

用户拍板「二查缺口全补」，并行 8 个采集 agent（分两组、每组 ≤4），原计划 11 条，实际净增 **9 条**，主库 892 → **900 条**，门禁 ERROR 0 / WARN 0 持平：

| model_id | 发布 | 要点 |
|---|---|---|
| `google:gemma-4-e2b:base` | 2026-03-31 | 总 5.1B/有效 2.3B Dense（PLE 有效参数设计）、128K ctx、原生音视频输入、知识截止 2025-01 |
| `google:gemma-4-e4b:base` | 2026-03-31 | 总 8.0B/有效 4.5B，其余同上 |
| `google:gemma-4-12b:base` | 2026-06-03 | 11.95B Dense、256K ctx；官方无"非 Unified 12B"，pre-trained checkpoint |
| `google:gemma-4-12b-unified:base` | 2026-06-03 | **encoder-free** 统一多模态（图像/音频 patch 直投影进 LLM，家族唯一原生音频中尺寸） |
| `stepfun:step-3-7-flash:base` | 2026-05-29 | 198B/11B MoE VLM、256K ctx、三档推理；开源 Apache 2.0 + API ¥1.35/8.1 元折 $0.1992/$1.1949；31 条 T0-自报 |
| `cohere:parse-v5-0:base` | 2026-08-27 | 2.3B 文档 VLM；**按页计价 $1.50/1,000 页**（token 六键 null、unit null，页价存 notes，schema 首例非 token 计价） |
| `google:gemini-3-5-flash-cyber:base` | 2026-07-21 | 安全特化（OSV.dev 700k 漏洞微调）；CodeMender 排他渠道；CyberGym 0.832；定价沿用 3.5 Flash $1.5/$9 |
| `alibaba:qwen3-7-plus:base` | 2026-06 | **思考档**（混合思考单一 API id，enable_thinking 默认 true）；$0.298/$1.192、1M ctx；full_name 加后缀与 -none 行区分 |
| `google:gemma-4-31b:base` | — | **已移除**：主库 init 基线已有 `gemma-4-31b-it`/`-it-minimal`，本采 14 条为 -it 跑分、7 项同名同分构成重复（-it 数据套 base id 身份错配）；采集与既有记录互证一致，留档不提交 |

- **花名册讹误证伪 1 条**：`b317`「Gemini 3.6 Flash Cyber」不存在——7-21 同日发布的 Cyber 实为 **3.5** Flash Cyber（基于 3.5 微调），采集 agent 按「讹误即停」拒绝硬填并给出 DeepMind 官方博客 T0 证据链，批次释放（Wave-1 CHANGELOG 中"3.5/3.6 Cyber 未采"说法据此更正：3.6 Cyber 不存在，3.5 Cyber 本轮已采）。
- **立项盘点失误自纠 1 条**：`b313` gemma-4-26b-a4b 实为 init 基线既有（Wave-2 立项时 Gemma 家族盘点输出截断漏看），本轮独立采集与既有记录全字段互证一致，无需入库。
- **采集侧修正**：Gemma 系 Codeforces Elo/CoVoST BLEU 等 8 条非 0-1 量纲分数按 GDPval 先例撤下进 meta.notes；Parse 的 source_type 归一受控枚举；Step 的 DeepSearchQA 双分数 config 区分（F1/accuracy）；qwen3-7-plus 的 long_context 键名归一。
- **基准名归一（5 处）**：SWE-Bench Verified→**SWE-bench Verified**（Princeton 官方小写 b；与 Scale 官方大写 B 的 SWE-Bench Pro 为两个不同基准、各自官方拼法并存）、GDP.pdf→GDP.PDF。
- 增量质检 d34 扫描与基线持平；台账 `b308w1~b318w1`：9 submitted + b313 互证留档 + b312/b317 释放留痕。

### Added（D37 增量采集轮，2026-09-06）

增量更新工作流（见 `docs/增量更新工作流.md`）首轮实跑，用户拍板 P0+P1 共 **7 个新模型**入库，主库 885 → **892 条**，门禁 ERROR 0 / WARN 0 持平。批次 ledger `b301w1~b307w1`（claimed_by zcode-01，均已 submitted），采集文件已 `add -f` 入库：

| model_id | 发布 | 要点 |
|---|---|---|
| `openai:gpt-6-astra:base` | 2026-09-03 | 新旗舰；$10/$50（cached $1、batch 半价折算）、1.05M ctx/128K out、知识截止 2026-04-30；13 条 T0-自报跑分；首个达 OpenAI Preparedness **Critical** 网络安全阈值的模型 |
| `tencent:hunyuan-hy4-preview:base` | 2026-08-28 | 开源（Apache 2.0）；770B/49B MoE、1M ctx；10 条 T0-自报；API 价 $0.834/$2.501 |
| `anthropic:claude-fable-5-1:base` | 2026-09-01 | $10/$50（cached $0.25）；**Mythos 5.1 = 同一模型权重的宽松护栏 trusted-access 档，经判定不单开记录**，事实写入 notes |
| `google:gemini-3-8-flash:base` | 2026-09-02 | $0.75/$3.75（促销价至 2026-12-31）；1M ctx、知识截止 2026-03；14 条 T0-自报；官方 API 单一 id、thinking 经参数调节（无 -high/-minimal 独立 id） |
| `google:gemini-3-8-flash-cyber:base` | 2026-09-02 | 安全特化变体（专项训练非纯护栏开关，官方称 "2 variants"，判定独立建条，证据链存 notes）；仅 Fairwind 受审渠道；cyber 专属跑分 3 条 |
| `zhipu:glm-5-3-flash:base` | 2026-08-26 | 开源（MIT）+API $0.15/$0.50；320B/18B MoE、1M ctx、原生多模态 |
| `alibaba:qwen3-8-27b:base` | 2026-08 | 开源（Apache 2.0）+百炼 API $0.5/$3.0；27B Dense 原生视觉-语言、262K→YaRN 1M ctx；30 条 T0-自报 |

- **采集侧修正**（门禁拦下后归位）：gemini-3-8-flash 的 GDPval-AA v2 为 Elo 量纲（1545）不适用 0-1 口径，按署不入库、原值留 meta.notes 待口径统一；cyber/glm 的 source_type 用词归一到 D25 受控枚举；gpt-6-astra 的 long_context 键名归一（input_multiplier→input）。
- **基准名大小写归一（26 处）**：SWE-bench Pro→**SWE-Bench Pro**（官方拼法+21 条多数派）、Cybergym→**CyberGym**、GDP.pdf→**GDP.PDF**。
- **增量质检**：d34 扫描 31 项与入库前基线持平（A1/B1/B2/B5 各项无新增）；license 填充率 51.0%→51.3%。
- **Wave-1 遗留待拍板**：P2 二查结果——Gemma 4（2026-04-16，5 尺寸，Apache 2.0）与 Step 3.7 Flash（2026-05-28，198B/11B MoE VLM）均早于采集窗口，属**漏采**待批；Cohere Parse 5 查实为 2.3B 文档 VLM（真模型但按页计价 $1.5/千页）待批；Qwen3.7-Plus 思考档仍无独立口径证据。Cyber 系先例：3.5/3.6 Flash Cyber（2026-07）也在窗口内未采，可并入下一轮。

### Added（增量更新工作流，2026-09-06）

- **`docs/增量更新工作流.md`**：跟进新模型发布的持续循环 SOP——S0 发现（信息源清单）→ S1 范围判定（是否模型/是否新/是否在范围）→ S2 采集（ledger 新批次 + M 型 subagent）→ S3 门禁合并（含三条历史事故硬约束）→ S4 增量质检（门禁基线 + d34 扫描复跑 + 定价量级锚点）→ S5 发布；含每轮固定拍板点与首轮实录。
- **`scripts/candidate_diff.py`**：S1 辅助工具（只读），候选清单 vs 主库差异比对，输出 NEW / CHECK_VARIANT / EXISTS 三档建议（建议不自动处置，处置必经人工）。
- **首轮 Wave-1 发现（窗口 2026-08-20 以来）**：候选 11 条——GPT-6 Astra（09-03，$10/$50）、Hunyuan Hy4 preview（08-28，770B/49B 开源）、Claude Fable 5.1 / Mythos 5.1（09-01）、Gemini 3 系列 9-02 新档、GLM-5.3-Flash、Qwen3.8-27B 等；判定 NEW 2 / CHECK_VARIANT 8 / EXISTS 1。待用户拍板后开 D37 采集轮。

### Fixed（D36 定价错值 + 价格图对数轴，2026-09-06）

用户报告两张价格图被极端值拉爆坐标轴，排查出一处数据错 + 一处图的口径缺陷（备份 `model_data_v2.jsonl.d36bak-20260906-005757`，门禁 ERROR 0 / WARN 0 持平）：

- **gemini-1-0-pro-001 定价千倍错位**：任务给定历史价实为每百万 token 口径（$0.25/M 级），被按「每 1K token」误解再 ×1000 成 $250/$1250（= 8× GPT-4、200× 后继 1.5 Pro，经济上不可能）。input/output/cached_input 三字段除以 1000 归位为 **0.25 / 1.25 / 0.0125**，notes 留网核证据。全库扫描 ×1000 型单位错仅此一条（其余 per-1K 口径记录如 davinci $0.02/1K=$20/M 换算均正确）。
- **价格图对数轴**：象限图（4 象限图）与价格 vs Elo 散点图 x 轴改对数刻度——全库定价中位 $1.1、P95 $15、极值 $75（gpt-4.5-preview，T0 真数据），线性轴把九成点压进左侧 20%。回归同步改为 **Elo ~ log₁₀(price)**（原线性拟合在对数轴上无意义）并标注 R²；免费模型 glm-4-7-flash 对数轴无法绘制，按 $0.01 画并注明。
- **图表工坊对数轴接线修复**：logX/logY 复选框此前从未接到 ECharts 轴类型上（勾选只过滤非正值、轴仍线性），现已真正生效（x/y 轴 type 随勾选切 log/value）。三图均已浏览器实测。

### Changed（D35 同模型双 id 合并，2026-09-06）

D34 体检登记的 7 组「同厂商同名不同 model_id」拍板处置（备份 `model_data_v2.jsonl.d35bak-20260906-001759`）。合并后 891 → **885 条**，门禁 ERROR 0 / WARN 0 持平，C2 扫描（同厂商同名组）清零。

- **6 组合并**（保留 keeper=官方名/数据超集一方；donor 跑分按合并主键只并集不覆盖：self_reported `(benchmark,config,date)`、independent `(benchmark,config,source_site,date)`、arena_elo `(sub_benchmark,date)`；标量字段 donor 只填 null；notes 非空追加「【D35 合并自 …】」段；source_urls 并集）：
  1. `alibaba:qwen2-5-max:base` ← `qwen-max-2025-01-25:base`（并 8 自报 + 3 独立）。⚠️ 上下文冲突网核定案：Qwen2.5-Max API 为 **32,768**（Artificial Analysis / OpenRouter / MCP 文档一致），donor 的 128000 系 datalearner 转述时与 Qwen2.5 开源系列 128K 混淆，弃用并留处置注；
  2. `anthropic:claude-3-haiku:base` ← `:20240307`（并 4 独立评测；填 knowledge_cutoff 2023-08、cache_write 等空字段）；
  3. `anthropic:claude-haiku-4-5:base` ← `:20251001`（并 3 自报 + 3 独立；SWE-bench 0.733 撞键 1 条按 keeper 留用跳过）；
  4. `Cohere:command-r-plus:base` ← `:2024-04`（donor 的首发定价考证与官方博客来源折入 notes；free_tier 等空字段补齐）；
  5. `lg:exaone-deep-2-4b:base` ← `exaone-3-5-r-2-4b:base`（三基准同分实证同模型；并 donor 独有条目）；
  6. `tii:falcon-2-11b:base` ← `falcon-11b:base`（donor notes 自证同物——其 T0 来源即「Falcon 2 11B」官方新闻稿；空骨架 keeper 吸收全部 9 自报 + 2 独立）。
- **1 组改名不合并**：`deepseek:deepseek-v4-pro-none:base` 的 full_name 「DeepSeek-V4-Pro」→「DeepSeek-V4-Pro（Non-Think）」。两记录是同一模型的思考/非思考两种模式（AIME 2025 0.4667 vs 0.9667），合并会销毁数据；-none 后缀即库内 Non-Think 口径（该条 notes 自证），改名仅为消除 full_name 同名混淆。
- 合计并入跑分条目 38（自报 26 + 独立 12），撞键跳过 1，标量填空 15 处，notes 处理 29 处。合并脚本 `temp/d35_merge_dups.py`（dry-run 计划 + 乐观锁断言）。

### Fixed（D34 数据修复，2026-09-05）

用户拍板后对独立体检（`temp/d34_scan_outliers.py`，31 项门禁外检查）发现的 5 类问题修复，备份 `model_data_v2.jsonl.d34bak-20260905-235111`。修复前后门禁均 ERROR 0 / WARN 0 持平；字段级 diff 核对仅预期字段变动（459 处 / 447 条记录）。

- **license 形状拍平（446 条）**：D32 修复项 5 批量补 license 时写成了 `{"name": ...}` 单键 dict（"填充率 51%" 全是该形状），`SCHEMA_BLOCK_KEYS` 只查键不查值类型故门禁静默。全部拍平为字符串。**门禁新增规则 4.5**（WARN）：`basic_info.license` 非 null 且非字符串即报；负对照 ×改前备份命中 446、现库 0。
- **参数量单位硬错（2 条）**：`moonshot:fireworks-kimi-k2p5` total 1.02→1020.0B（notes 自证「总参数1.02T」，T 误写 B）；`deepseek:deepseek-coder-v2-236b` active 21000000000→21.0B（legacy 参数个数写法，同 notes `[原 total_params]` 一类）。
- **MT-Bench 归一错位（1 条）**：`microsoft:wizardlm-2-8x22b` self_reported/MT-Bench 0.0912→0.912（条目 notes 自证 9.12 分，归一误除 100）。
- **qwen3-5 缓存价知情置 null（5 条）**：全家族 `cached_input` 与 output 同值、为 input 的 6~8 倍，作缓存命中单价不可能（阿里云官方规则：缓存命中≈标准输入单价 10%，2026-09-05 网核；全库其余 150+ 条 cached/input 比值均在 0.03~0.5）。采集时计费表第三列语义歧义（"缓存命中/思考同价列"）、存档 raw_pages 未随机器带来，无法核实列归属 → 置 null 知情保留，待官方价格表重核。
- **基准名大小写归一（5 条）**：`Mathvista(mini)`→`MathVista(mini)`（4）、`TAU-Bench Retail`→`TAU-bench Retail`（1，多数派写法）。

**体检中核实后不动的**：release=2022-01 的 2 条属 D31「只要 2022+」边界值；5 条价格早于发布属预发布定价；5 条退役模型无 API 有历史价；llama-4-maverick/hunyuan-large 名字中的参数是激活参数非矛盾；LiveCodeBench Pro Elo 2887 为 D28 知情保留；13 条 Qwen/gemma 系「激活>总参」系名义值 vs 精确值精度差非硬错；160 条「知识截止早于发布」为正常语义（初版判据方向定反，已剔除）。**遗留拍板项**：7 组同厂商同名双 model_id 是否合并（涉及 id 命名空间，未动）。

### Fixed（viz 修复，2026-09-05）

- **可视化 9 个页面空白修复**：`viz/viz_index.html` 甘特图自定义 series 的 `renderItem` 在元素被完全裁剪时返回 `{}`（无 `type`），echarts 内部断言抛 `Error("")`；页面初始化时各分区隐藏（0×0），甘特图矩形必被整体裁剪 → **每次加载必崩**，`refreshAll()` 自第 6 环 `renderTimelinePage()` 起中断，数据质量/数据缺口/厂商碎片/字段总览/图表工坊/明细浏览/跑分排行/Scaling Law/可信度 9 个页面从不渲染。修复两处：`renderItem` 裁剪时改返回合法空组 `{type:'group',children:[]}`；`refreshAll()` 每个渲染函数包 `_safeRender()`（try/catch 隔离，单页失败不再拖垮其他页面）。另修 `scripts/viz_transform.py` `build_lifecycle_gantt()` 重名类目（Claude Haiku 4.5 的 base 与 20251001 两条同 full_name 会互相覆盖 y 轴索引），重名追加 model_id 前缀。
- **echarts.min.js 缺失处置**：`.gitignore` 刻意不入库该文件导致新 clone 上 viz 整页不可用。新增 `scripts/fetch_viz_assets.py` 一键复原（npmmirror→jsdelivr→unpkg 依次尝试），DEPLOY.md §3.5b 补 viz 前置说明。实测 echarts 5.5.1（1.03MB）恢复后 15 个页面全部正常渲染（明细表格 100 行/页、缺口矩阵 345 行、甘特图 120 条）。

### Changed（docs 整理，2026-09-05）

- **docs 目录整理**：20 份已完结阶段的历史文档经 `git mv` 移入 `docs/archive/`（内容零改动）——采集阶段计划 3 份（multi_agent_plan / COLLECTION_PLAN_v2 / TASK_ASSIGNMENT_v2）、v1/v2 时代质检与评估 8 份（TEST_REPORT / clean_v1_log / cleanup_log / validation_v1_baseline / validation_v2_official / DATA_QUALITY_REPORT_v2 / quality_report_20260825 / qa_report）、日级状态快照 3 份（全库状态与下一步_2026-08-25 / 现状盘点_2026-08-27 / 盘点与待改清单）、已结案交接卡 5 份（M型扩容交接 / 收尾状态与交接 / 交接 D16 进行中 / D16 结案 / D19 结案换平台接手卡）、可视化选型方案 1 份（VISUALIZATION_PLAN）。新增 `docs/README.md` 目录索引（含受众标注：WB 平台专属文档单列）与 `docs/archive/README.md` 归档说明；留存文档（WORKBUDDY_AGENT_GUIDE、intermediate/README、.workbuddy 记忆）中指向被移动文档的引用已同步改指 archive 路径。现行规范、GAP_SCAN 报告与数据档案（ledger / 两份隔离档 / memory/）位置不变。

### Added（D33 新增）

- **D33 可视化三模块**：`scripts/viz_transform.py` 新增 `build_leaderboard()` / `build_scaling_law()` / `build_multi_source_conflict()`，前端 `viz/viz_index.html` 在「跑分」组新增三个页面：
  - **跑分排行**：按 benchmark 维度切换 Top 30 总榜（mmlu / gsm8k / gpqa / math / humaneval / aime2025 / swe_bench 独立评测 + arena_text / arena_coding / arena_math Arena Elo 子榜）。
  - **Scaling Law**：参数量 vs 各 benchmark 分数散点 + log-log 拟合线（含 R²）+ 预测 score@7B/70B/700B。
  - **可信度**：同模型同 benchmark 多源一致性扫描，多源组聚合 + 不一致组（差异 ≥5%）+ 各 benchmark 不一致率。

### Fixed（D32 新增）

- **D32 数据修复 8 项**：扫描 5 个未深探方向后修复，门禁 ERROR 0 / WARN 0 持平。
  - **修复项 1**：`arena_elo` 段 14 条 source_type 错位（"独立评测平台" → "LMArena 镜像（DataLearner），原始来源 LM Arena"），涉及 Alibaba Qwen-3-8-Max / Baidu ERNIE-5-1 / Google Gemini-2-5-Pro / Gemma-3-27B / GLM-5-2 等 14 个模型的子榜分。
  - **修复项 2**：4 条 `open_weights=null` 但 `api=true` → `ow=false`（Google DeepMind gemini-3.6-flash-high / kunlun 天工 4.0 / unisound Shanhai 2.0 / Inflection 3.0）。
  - **修复项 3**：4 条 `ow=null` 但 license="闭源 API" → `ow=false`（gemini-1.5-pro-001/002 / gemini-2.5-pro-exp / Moonshot-v1）。
  - **修复项 4**：API-only 厂商 `ow=null` 改 `false` 共 31 条（OpenAI 21 / Anthropic 9 / Google DeepMind 1）。这些厂商明确闭源，`ow=null` 应是 `false`。
  - **修复项 5**：518 条 `ow=true` 但 license 空的批量补 license（按 vendor 推断），两轮共补 **446 条**，license 填充率从 0.9% → **51.0%**。仍 72 条 vendor 长尾保守保留空（Prime Intellect / Deep Cogito / eth-zurich / salesforce / sambanova 等）。
  - **修复项 6**：686 条 `self_reported` 段 `confidence` 空 → 按 source_type 推断（T0-自报 / T0-自报-转述 / T1 / T3），共修 649 条。
  - **修复项 7**：1301 条 `source_type` 空 → 按 source_url 域名推断，共修 1143 条 + 3 条受控枚举违规补丁（independent 段 huggingface.co/github.com → "独立评测平台"；arxiv.org → "学术独立评测"；arena_elo 段 lmarena.ai/datalearner.com → "LMArena 镜像"）。
  - **修复项 8**：44 条 `ow=true` 但 license="Proprietary" 矛盾改开源协议（Apple OpenELM → CC-BY-NC 4.0 / Google Gemma → Apache 2.0 / Cognition Kevin-32B → Apache 2.0 / Moonshot Kimi K2 系列 → Apache 2.0 / OpenAI gpt-oss → Apache 2.0 / xAI Grok-1 → Apache 2.0 / Perplexity R1-1776 → Apache 2.0 / MiniMax M1/M2 → Apache 2.0）。
- **D32 备份**：`model_data_v2.jsonl.bak.D32`（修复前快照）。

### Added（D29-D31 累计）

- **D31 删除 2022 前老模型**：用户要求"只要 2022+ 数据"，扫描 `release_date < 2022-01-01` 共 42 条记录（最早 1959 Pandemonium、最晚 2021 HyperCLOVA），含 GPT-3/T5/RoBERTa/XLNet/GNMT 等历史名模型。从 `model_data_v2.jsonl` 删除，933 → 891 条。门禁验证 ERROR 0 / WARN 0 持平。原文件备份 `model_data_v2.jsonl.bak.20260903_190631`。
- **D31 厂商 × 字段 缺口矩阵**：`scripts/viz_transform.py` 新增 `build_gap_matrix()`，输出 31 厂商 × 19 关键字段 = 438 矩阵点 + 31 厂商诊断 + 401 条待补 todo 清单。前端 `viz/viz_index.html` 在「数据缺口」页追加缺口矩阵热力图（红→黄→绿色阶）、厂商智能诊断卡片（健康度 Top 15）、一键导出待补清单（JSON/CSV/MD 三种格式）。点击单元格复制该格缺失 model_id 清单到剪贴板，点厂商名跳转明细页筛选，点字段 chip 跳转图表工坊。
- **D30 价格性能象限图**：`scripts/viz_transform.py` 新增 `build_price_quadrant()`，以中位价格 × 中位 Elo 分割 4 象限（高性价比 / 低性价比 / 高端 / 低端）+ 线性回归线。前端在「性价比」页追加 4 象限散点图，点击点跳模型档案。
- **D30 模型生命周期甘特图**：`scripts/viz_transform.py` 新增 `build_lifecycle_gantt()`，按 release_date → knowledge_cutoff（缺则用今天兜底）渲染 Top 120 模型生命周期条。颜色按地缘（中国红/美国蓝/欧洲紫/其他灰）。前端在「时间演进」页追加甘特图，含 dataZoom 缩放 + 点击跳档案。
- **D30 4 个新缺口扫描角度**：`temp/d30_gap_scan4.py` 扫描 context_window_effective vs nominal 矛盾、license 填充率按厂商分布、模型代际命名规范（base/large/medium/mini 等）、多厂商合作记录归属（vendor 含 + / & / and / /）。
- **D30 跑分维度缺失扫描**：`temp/d30_bench_dim_scan.py` 扫描 HumanEval / BBH / MuSR / IFEval 4 个严重缺失维度（覆盖分别 19.4% / 10.2% / 0.2% / 0.6%），按厂商分组输出 168 个候选可补模型清单 `temp/d30_top5_filter.py`。
- **D30 arena_elo 来源去集中化**：`temp/d30_arena_add_lmarena.py` 为 170 个有 arena_elo 数据的模型在 `meta.source_urls` 数组追加 `https://lmarena.ai/leaderboard` 一手源（幂等，已含则跳过），缓解 datalearner.com 占 93.7% 的单点风险。
- **D29 数据缺口分析页**：`scripts/viz_transform.py` 新增 `build_gap_analysis()` 输出字段组填充率雷达 + 跑分覆盖热力图 + 字段缺口排行 + 无跑分模型清单。前端新增「数据缺口」页面。
- **D29 厂商碎片化检测视图**：`scripts/viz_transform.py` 新增 `build_vendor_fragmentation()` 输出大小写/空格/连字符变体合并建议 + 厂商气泡图。前端新增「厂商碎片」页面。
- **D29 模型档案抽屉**：`scripts/viz_transform.py` 新增 `build_model_details()` 输出每个模型的完整档案 + 同厂商兄弟 + 相似推荐。前端添加 sticky 全局筛选条 + 档案抽屉组件，支持厂商/定位/开源/价格/参数/日期/Elo/跑分 8 维筛选 + URL hash 状态分享。

### Changed（D28 累计，已结案）

- **厂商大小写归一**：72 条记录的 vendor 大小写 / 空格 / 连字符变体归一，249 → 233 厂商（D28 第十四批）。
- **score_type 归一**：134 种写法 → 126 种，189 条归一（D28 第十一批）。
- **Arena 子榜命名归一**：源数据 17+ 种子榜写法变体归一为 text/coding/math/webdev/vision/search/agent/gdpval（D28 收尾批）。
- **时效性判断标准**：老模型（release_date < 2024-01-01）永久标记「已定死」不参与过期检查；新模型按 collected_at 分级 fresh（< 6 月）/ 可重审（6-12 月）/ 需重审（> 12 月）。影响 135 条老模型 + 744 条新模型（D28 收尾批）。
- **发布日期异常清理**：9 条老模型（< 2024-01-01）标记「已定死」 + 5 条参数量声明修复。

### Fixed（D28 累计，已结案）

- 17 组主键撞车清零（WARN 33 → 16）。
- 13 条 WARN 处置完成（WARN 13 → 7，剩 7 条均为知情保留）。
- LiveCodeBench Pro 从 independent 段移回 arena_elo 段（独立段门禁要求 0-1/0-100 百分制，Elo 分 2887 越界）。
- positioning vs native_multimodal 自洽性修复 80 条。

### Fixed（D31 新增）

- **子榜区隔修复**：`scripts/viz_transform.py` `flatten_record` 的 `arena_elo_max` 主榜分逻辑修复。旧逻辑 `max(elos)` 会把 agent/coding/math 子榜分误当主榜分（GLM-5.2 agent 子榜 1524 来自 blog.csdn.net 非官方源，被显示为主榜分）。新逻辑：1) 优先 `is_primary=true`；2) 否则 sub_benchmark 归一为 `text`/`overall`/空 的；3) 都无则 `None`（避免子榜虚高）。影响 2 个模型（GLM-5.2 / GLM-5.1）失去主榜分，172/170 模型保持原值。新增 `_norm_sub_benchmark()` 辅助函数。

## [D28] - 2026-09-03

D28 整轮 17 批已完成、门禁首次清零（ERROR 0 / WARN 0）。累计修复 610 条记录、8 个 commit 已推送。详见 `docs/GAP_SCAN_REPORT_D28.md`。

## [D16-D27] - 2026-08-26 ~ 2026-09-02

D16-D27 各轮主要工作：跑分段受控枚举归一、字段一致性核查、潜在缺口排查、WARN 记录处置、新角度缺口扫描、分 commit 提交修复。详见各轮交接文档。
