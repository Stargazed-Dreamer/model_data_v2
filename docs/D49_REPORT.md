# D49 轮次报告：OC 多来源并集 + 基准名归一续 + 缓采清单拍板

> 日期：2026-09-14（夜）。用户三连拍板（原文「OC 放开为多来源并集 / 基准名归一 / 缓采清单有多少，如果都是小众模型要不就放弃吧」）。

## 一、OC 多来源并集（`--union`，109 个基准条目 / 20 条记录）

`scripts/d48_import_opencompass.py` 新增 `--union` 模式：已有多来源 independent 的记录也追加 OC 条目，与 AA 等来源以 `(benchmark, config, date)` 键共存。护栏全量沿用并新增一条：

- **反向 flavor 护栏（新）**：库内高档变体（`-high` 等）不配 OC 无标注条目（拦下 `gemini-3.7-flash-high`、`o3-...-high` 两条档位混写）；
- **基准名对齐（新）**：OC 列名先对齐库内多数派写法再落（防 r2 回归，如 `GPQA-Diamond`→库内 `GPQA Diamond`）；
- 幂等：同键重跑零写入；歧义组 5 个（qwen3.5-397b 双档、deepseek v4 flash/pro 变体组、LongCat 三变体、kimi-k2.5 双条）维持整组跳过。

落库样例：`zhipu:glm-5.3`、`alibaba:qwen-3.8-max`、`minimax-m2/m2.5/m3`、`deepseek:deepseek-v3.2`、`deepseek-r1:0528`、`step-3.5-flash` 等 20 条记录现同时持有 AA（T1 滚动实测）与 OC（T1/T2 快照重定基）两套独立评测，`config`/`date`/`source_url` 可区分口径。

## 二、r2 基准名归一续

`d48_normalize_bench_names.py` 复跑：**13 处改写**（SWE-Bench Verified 等，均为本晚新采集带入的异写），撞键合并 0。门禁绿。归一脚器现固化为每轮 QA 尾步。

## 三、缓采清单盘点与拍板

**总池**：漏采线索 528 条（AA 301 / OR 227），其中 2026-08-01 后 47 条；已采/折并 12；其余为路由别名（`:batch/:free/-latest` 指向库内已有模型）与 2026-08 前长尾。

**真缓采仅 8 条**（具名，去除别名/已采/折并后）：

| 条目 | 判定 | 处置 |
|---|---|---|
| schematron-v2-turbo / -small（inference-net，09-12） | 小厂商新线，无独立评测 | **放弃** |
| apodex-1-1（Apodex，08-30） | 不知名厂商 | **放弃** |
| g9v3-39a5b（AI9Stars，08-20） | 不知名厂商、代号式命名 | **放弃** |
| quasar-438b（Multiverse Computing，08-10） | 小众（张量压缩系） | **放弃** |
| k-exaone-2-0-0803（LG，08-12） | 库内 k-exaone-2.0 的日期快照变体 | **放弃**（变体不单列，§3） |
| muse-glimmer（Meta，08-10） | 疑似库内 muse-glimmer-30b 的无尺寸条目 | **放弃**（歧义） |
| **gpt-6-astra-pro**（OpenAI，09-04） | **OpenAI 高端档，库内只有 gpt-6-astra**——唯一非小众 | **保留 1 条**，下轮 S0 优先核 |

另有 D46 已永久排除的训练产物 7 条（维持），**backlog 948 条（魔搭 2026-08 前存量）正式关闭**。

**放弃的安全性论证**：以上全部来自 AA/OR 扫描，而 `d48_scan_leads.py` 已固化为可重复管道——任何被放弃的模型若日后真正冒头（上榜、大厂商出品），下次扫描会自动重新出现并按当期口径重新分诊，**放弃没有不可逆代价**。

## 四、收尾状态

- 门禁 ERROR 0 / WARN 0；记录 959 条不变。
- 净变化：+109 OC 基准条目（20 记录）、基准名归一 13 处、缓采清单拍板关闭。
- 遗留：gpt-6-astra-pro 单条待 S0 核（下轮首位）；minicpm-4 冲突值待核（沿用）。
