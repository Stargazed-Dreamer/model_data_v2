# CHANGELOG

本变更日志记录 `model_data` 工作区数据集与可视化的演进。版本号采用 `D<轮次>` 形式，对齐整改轮。

## [Unreleased]

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
