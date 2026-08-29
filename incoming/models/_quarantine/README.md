# 隔离区：存在性未证实的采集成果

这 4 个采集文件**已采集完成并曾入库**，但采集者多轮检索后无法证实其 `model_id` 对应的模型真实公开发布，
故 2026-08-29 与其主库记录一并移入隔离区。主库记录在 `docs/unconfirmed_models.jsonl`（逐字节原样，未改值）。

| 文件 | model_id | 查无依据（摘自记录自身 notes） |
|---|---|---|
| `b236w1-flower-labs__flower-labs__collective-1__base.jsonl` | `flower-labs:collective-1:base` | Flower Labs 官方博客 2025-05～2026-08 全量 30+ 篇无该命名模型 |
| `b187w1-nc-ai__nc-ai__vaetki__base.jsonl` | `nc-ai:vaetki:base` | 自标「占位记录」，9 轮不同关键词组合检索无果 |
| `b215w1-shiyin-intelligent-technology-co-ltd__shiyin-intelligent-technology-co-ltd__skiff-llm__base.jsonl` | `shiyin-intelligent-technology-co-ltd:skiff-llm:base` | 自标「占位记录」，HF 组织页与多组关键词均无果 |
| `b132w1-china-mobile-zero-gravity-labs-0g-ai__china-mobile-zero-gravity-labs-0g-ai__dilocox__base.jsonl` | `china-mobile-zero-gravity-labs-0g-ai:dilocox:base` | 仅有指向同一 arXiv 论文的转述，未见该命名模型发布 |

## 为什么放在子目录而不是删掉

- `model_data_tool.py merge --incoming <目录>` 用 `os.listdir` **非递归**展开目录，
  所以下游照常跑「合并 incoming/models」时**不会**把这些文件重新塞回主库。
  若直接放在 `incoming/models/` 下，一次 `merge --apply` 就会按 `add_record` 把它们复活（见该工具 line 565）。
- 文件本身是多轮检索的负结果留痕，删了就等于把「查过、确实没有」这条证据也扔掉。

## 作业约束

1. **不得**把这些文件移回 `incoming/models/`，也不得对其单跑 `merge --incoming <该文件>`。
2. **不得**把这 4 个 `model_id` 当作「漏采」重新派发采集 —— 已按厂商官方域、HF、ModelScope、arXiv、
   WebArchive 多路查过，重采只会在同一批 UGC 转述上打转。
3. 若日后出现新的官方证据，先改 `docs/unconfirmed_models.jsonl` 里对应记录的
   `meta.verification_status`，再决定是否回流主库。

## 名单完整性

主库共移出 **10** 条存疑记录，本目录只有 4 个文件。另 6 条
（`deepseek:deepseek-llm-1-3b-base:base`、`facebook-ai-research:multi-token-prediction-13b:base`、
`ibm:granite-3-2-2b:base`、`lenovo:tianxi-32b:base`、`t-bank:t-pro:base`、`tsinghua-university:jetfire:base`）
在 `incoming/models/` 下**无对应采集文件**——已按原名、`__` 降级名与 §8.1 缩短名逐一穷举列举核实为 0 命中，
故 `docs/unconfirmed_models.jsonl` 里的那一行是这 6 条的唯一留痕。**不要清理该文件**，否则连负结果证据都会消失。

> 上表 model_id 一律写完整三段式（含 `:base` 版本段），残缺 id 会让后来的 grep 直接漏掉。

## 参考

- 机制、防回灌原理、重新入库流程、以及花名册口径重基线（702 = 主库 692 + 隔离 10）：`docs/WORKBUDDY_AGENT_GUIDE.md` §17
- 不要用 `docs/batch_claim_ledger.jsonl` 的 `submitted_files` 判断文件是否存在：全库 1066 条里 791 条本来就指向不存在路径
  （合并后不保留源文件是历史惯例），本次移动的 4 个也在其中。
