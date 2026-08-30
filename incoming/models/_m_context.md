# M 型试点共享上下文（2026-08-25）

## 任务
为指定模型产出 M 型单模型深度档案：`incoming/models/<model_id>.jsonl`。
文件名 sanitize：model_id 中 `:` → `__`。JSON 内容里 model_id 保持原样。
每文件 = 单行压缩 JSON，完整 schema 1.1 记录（所有顶层键必须出现，查不到写 null，禁止删键）。

## 待补字段（本批核心目标）
1. `basic_info.positioning`：数组，如 ["旗舰","推理增强"]；依据官方定位描述归纳
2. `architecture.context_window_tokens` / `knowledge_cutoff` / `context_window_effective_tokens`
3. `modality` 三块：input/output/native_multimodal（布尔三态 true/false/null）
4. `benchmarks.self_reported`：官方自报跑分，score 一律 0–1 小数（百分制 ÷100 并在 notes 注明）

## 硬性红线
- 没查到 = null，严禁 false/0/空串冒充"没查到"
- 不伪造 T0。搜索结果转述的官方数据：source_type="行业媒体聚合官方发布"，confidence="T3"，
  source_url 填实际可引用的文章 URL；若能确认转述内容与官方原文一致可标 "T0-自报-转述"
- **定价置 null 的判定基准 = 厂商有无自有官方 API 刊例价，不是「是否开源权重」**（2026-08-29 修订）。
  厂商自营 API 有刊例价就照常采（DeepSeek / Qwen / Kimi / GLM / MiniMax / Mistral 开源权重但也有官方价）；
  确认无自有刊例价才六价键全 null **且 `currency` 一并置 null（无价即无币种，别留 "USD"，门禁规则 4.3 会 WARN）**，
  `source_type="开源权重模型核对（无官方 API 价）"` + `confidence="T0"`
  —— 此处 T0 评的是「已核对官方渠道确认无价」这个核实动作，不是给不存在的价格贴 T0，不算伪造。
  **OpenRouter / NVIDIA hub / 云厂商的转售价不是官方价，禁止填入。**
- 每个 benchmarks.* 条目必须带 source_url
- **benchmarks 条目键名**：`self_reported` / `independent` 的基准名只写 `benchmark`，`arena_elo` 只写 `sub_benchmark`，
  禁止 `name` / `benchmark_name` / `metric_name`（`arena_elo` 也不得写 `benchmark`）——
  合并去重主键认不出非 canonical 写法，同一次测量会静默并存两份。
  存量的 1293 + 57 条老写法已在 2026-08-30 的 D9/D10 全部归一，门禁规则 6.1 现对任何非 canonical 写法报 WARN
- **主键必须唯一标识一次测量**：`benchmark` + `config` 是合并去重主键。同一基准并存多个测量（shot 数 / prompting 方法 /
  脚手架与 turn 预算 / 单次 vs 投票 / pass@k / 一条记录里的多个发布变体）时，**区别写进 `config`，别留 null**；
  子任务各成一条并写进 `benchmark` 名（如 `Russian SuperGLUE (RSG) – MuSeRC`）。
  **`config` 里不要写来源名**（`default（benched.ai）` 这类），来源交给 `source_url` / `source_type`。
  撞车时门禁规则 6.2 会 WARN
- meta.collected_at = **本次采集的当日日期** `"YYYY-MM-DD"`（不要照抄本文或样板里出现过的日期）；meta.verification_status = "待验证"
- 禁止改动 model_data_v2.jsonl（合并由主 agent 统一执行）

## 已核实事实（可直接采用，勿重复搜索定价）
### OpenAI 定价（USD/M tokens，T0，effective 2026-08-25，来源 platform.openai.com/docs/pricing）
- gpt-5.6 家族（sol/sol-max/terra/terra-max/luna/luna-none）：短上下文 $4/$20，缓存读 $0.40，
  缓存写 $5.00，Batch/Flex $2/$10；>272K 输入 $8 / 输出 $30
  （注意 luna 变体例外：$0.20/$1.20，本批不涉及 luna）
- gpt-5.4（2026-03-05 快照）：$5/$30，cutoff 2025-08-31，ctx 1,050,000，max output 128K
- gpt-5.4-mini（2026-03-17 快照）：$0.75/$4.50

### Anthropic 定价（USD/M tokens，T0，effective 2026-08-25，来源 docs.anthropic.com/en/docs/about-claude/pricing）
- claude-opus-4-8 / claude-opus-4-6(max)：$5/$25
- claude-opus-4-5:20251101：$5/$25，ctx 200K，max output 64K
- claude-sonnet-4-5:20250929：$3/$15，ctx 200K（1M beta），max output 64K
- claude-haiku-4-5:base：$1/$5，ctx 200K，max output 64K

## 已知背景（供交叉验证，仍须独立搜索确认）
- GPT-5.4：text+image 输入、不支持音频输入、reasoning_effort none(default)/low/medium/high/xhigh；
  变体 pro（更深推理）/mini（高量编码）/nano（高吞吐）；snapshot gpt-5-4-2026-03-05
- Claude Opus 4.5：定位最强推理编码；Sonnet 4.5：性价比主力；Haiku 4.5：速度最快轻量档
- 本环境 docs.claude.com/docs.anthropic.com/platform.openai.com 直连均不可达，
  信息源以 WebSearch 搜索结果摘要为准，按红线降级标注
