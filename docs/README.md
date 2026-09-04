# docs/ 目录索引

> 整理于 2026-09-05（D33 之后）。本文件是 docs 目录的导航。
> **项目当前状态永远以 `CHANGELOG.md` + 门禁 `scripts/validate_model_data.py` 实跑结果为准**，任何文档里的数字都可能过时（截至整理时：891 条 / ERROR 0 / WARN 0）。

## 现行文档（docs/ 根目录）

### 规范类（采集 / 数据作业必读，全平台适用）

| 文档 | 一句话 |
|---|---|
| `prompt.md` | 采集任务总规范：schema 1.1 字段定义、可信度分级（T0–T4）、核心决策与采集红线 |
| `执行细则.md` | 10 项执行层面细则：字段怎么填、冲突怎么记、输出怎么分批 |
| `multi_platform_subagent_guide.md` | 多平台并发采集通用规范：批次认领协议（CAS）、subagent 派发、单文件门禁、落盘 |
| `agent_prompt_per_model.md` | 单模型 subagent 任务书模板（M 型） |

### 平台专属

| 文档 | 受众 |
|---|---|
| `WORKBUDDY_AGENT_GUIDE.md` | **仅 WorkBuddy 平台的 agent 需要**（本机 git 二进制 / 代理 / `add -f` 等平台红线，其他平台无此环境问题，不必遵循）。注意其 §16 起各节同时是 D15–D27 各轮整改的详细实录，属于全平台可读的项目史；其余平台 agent 只读这些章节即可 |

### 现行报告（D 系列整改轮）

| 文档 | 一句话 |
|---|---|
| `GAP_SCAN_REPORT_D28.md` | D28 整改轮（17 批、门禁首次 ERROR 0 / WARN 0）的缺口扫描报告 |
| `GAP_SCAN_REPORT_D31.md` | D31：删 2022 前老模型 + 厂商 × 字段缺口矩阵 |
| `GAP_SCAN_REPORT_D32.md` | D32：8 项数据修复（license 填充 0.9%→51% 等）+ 数据集现状快照（891 条口径） |

### 数据档案（功能性文件，勿动勿删）

| 文件 | 用途 |
|---|---|
| `batch_claim_ledger.jsonl` | 批次认领台账（702 模型名册唯一权威），`scripts/_claim_batch.py` / `scripts/qa_stats.py` 直接读取 |
| `unconfirmed_models.jsonl` | D6 存疑隔离档（10 条，逐字节留存作证据），回流必须走 WB 指南 §17.5 流程 |
| `non_model_records.jsonl` | D14 非模型隔离档（7 条，逐字节留存），回流必须先证明对象是模型 |
| `memory/` | 跨平台记忆副本（`user/` 跨项目 + `project/` 本项目），以仓库这份为准，规矩见 `memory/README.md` |

## archive/（历史快照，20 份）

采集与质检阶段均已完结，当年的采集计划、v1/v2 质检评估、日级状态盘点、D16–D20 交接卡、可视化选型方案统一移入 [`archive/`](./archive/README.md)（`git mv`，内容零改动）。每份归档文档的「是什么、为什么归档」见 `archive/README.md`。

## 维护规矩

- 新一轮缺口扫描报告放 docs/ 根，命名 `GAP_SCAN_REPORT_D<轮次>.md`，轮次结案后在 `CHANGELOG.md` 挂接；
- 新写交接卡时：增量快照只在存活期内放根目录，被取代后移入 `archive/`；完整冷启动信息进 `memory/`（以仓库副本为准）；
- 文档里的数字一律标注实测日期；跨轮引用他人文档的数字前，先跑门禁核对当前基线。
