# CHANGELOG

本变更日志记录 `model_data` 工作区数据集与可视化的演进。版本号采用 `D<轮次>` 形式，对齐整改轮。

## [Unreleased]

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
