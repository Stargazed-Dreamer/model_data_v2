# `intermediate/` 文件说明

> 2026-08-29 整理。本目录放**过程产物**，不放交付物（交付物是根目录 `model_data_v2.jsonl`）。

## ⚠️ 首先：采集名册不在这里

**702 条采集名册的唯一来源是 `docs/batch_claim_ledger.jsonl`**（取 `models[].model_id` 去重）。

本目录的 `roster_v1diff_DEPRECATED.jsonl`（原名 `roster.jsonl`，506 行）**不是**采集名册，
而是阶段 0 的 v1 差异清单，且从未随 M 型扩容更新。用它核对覆盖率会得出错误结论。
详见同目录 `roster_v1diff_DEPRECATED.md` 顶部的弃用横幅。

## 现存文件

| 文件 | 大小 | 性质 | 能否再生 |
|---|---|---|---|
| `conflicts.json` | 274 KB | 阶段 3 采集文件 vs 主库的差异扫描明细，`docs/archive/qa_report.md` §4.2 的证据 | 是，`python scripts/diff_incoming_db.py` |
| `qa_stats.json` | 30 KB | 阶段 3 填充率统计明细，`docs/archive/qa_report.md` §3 的证据 | 是，`python scripts/qa_stats.py` |
| `merge_todo.txt` | 24 KB | 277 个补合并文件清单，`docs/archive/qa_report.md` §2.3 合并命令的输入 | 否，对应文件已变动 |
| `merge_apply_log.txt` | 45 KB | 上述合并的执行日志 | 否 |
| `roster_v1diff_DEPRECATED.jsonl` | 92 KB | 阶段 0 v1 差异清单（**已弃用，勿当名册用**） | 否，生成脚本已删除 |
| `roster_v1diff_DEPRECATED.md` | 28 KB | 同上的人读版 | 否 |
| `vendor_alias.json` | 2 KB | 厂商名别名映射，合并 model_id 时归一化用 | 否，手工维护 |
| `_criticgpt_in_v1.json` | 2 KB | 一次性核查产物（CriticGPT 是否已在 v1） | 否，低价值留档 |

## 已删除（2026-08-29）

`hf_org_cache.json`(220 KB)、`hf_lookup_merged.json`(66 KB)、`hf_round3_clean.json`(5 KB)
—— 均为 HuggingFace API 查询缓存，可由采集流程重新生成，不承载独有信息。
