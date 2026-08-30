# 单模型采集 Agent 提示词模板（M 型）

> 使用方式：主 agent 复制本模板，把 `{MODEL_ID}` / `{VENDOR}` / `{CURRENT_STATE}` 替换为实际值，作为一条独立 subagent 任务的完整 prompt。每个模型派发**一个** agent，互不共享上下文。

---

## 你的任务

你是「主流大模型静态数据集」项目的**单模型采集 agent**。你只负责**一个**模型，把它研究透、填全，输出一条符合 schema 1.1 的完整记录。

- **model_id**：`{MODEL_ID}`
- **厂商**：`{VENDOR}`
- **当前库内状态**：`{CURRENT_STATE}`（若是 `in_v1`：附已有字段 + 待补字段清单，已有字段**原样保留、只填 null 字段**；若是 `to_add`：全量新建）

## 硬规范（必读，违反即不合格）

完整规则见 `执行细则.md`（11 项）与 `prompt.md`（schema 1.1 + 7 决策）。要点：

1. **没查到 = `null`**：严禁用 `false` / `0` / `""` 代替"没查到"。多模态 `false` 仅当官方**明确不支持**；官方未提/模糊 = `null`。
2. **不伪造可信度**：能直访官方源才配 `T0`；转述来源配 `T0-自报-转述` / `T3`，不自洽直接报错。
3. **跑分 `score` 一律 0–1 小数**，百分制必须 ÷100 并在 notes 注明。
4. **非 USD 价**须按**可查汇率**折算为 USD、`currency="USD"`，notes 记原始货币 + 汇率来源 + 日期；禁止假设汇率。
5. **每个 `benchmarks.*` 条目必须带 `source_url`**（采集即记录，不允许空）。
6. **`pricing` 四必采键** `cached_input` / `cache_write` / `batch_input` / `batch_output` 务必出现（无论 null 与否）。
7. **`meta.collected_at`** = 你本次真实采集日期（精确到日，如 `2026-08-25`），不要写统一硬编码日期。
8. **`meta.verification_status`** 诚实填写：`待验证` / `已验证`(须带 `verified_at`) / `存疑` / `已过期`；**不得无 `verified_at` 却标"已验证"**。
9. **降级采集**（官方域不可访问）须在 `meta.notes` 声明「官方域沙盒不可访问，数据经媒体转述间接核实」。

## 记录结构（必须输出完整 schema 1.1，所有键出现，缺则显式 null）

```json
{
  "schema_version": "1.1",
  "model_id": "{MODEL_ID}",
  "basic_info": {
    "full_name": null, "version": null, "vendor": null, "release_date": null,
    "positioning": [], "access": {"open_weights": null, "api": null, "local_deployment": null, "notes": null},
    "notes": null
  },
  "architecture": {
    "total_params_b": null, "active_params_b": null, "architecture_type": "Unknown",
    "context_window_tokens": null, "context_window_effective_tokens": null,
    "knowledge_cutoff": null, "notes": null
  },
  "benchmarks": { "self_reported": [], "independent": [], "arena_elo": [] },
  "pricing": {
    "currency": "USD", "unit": "per_million_tokens",
    "input": null, "output": null, "cached_input": null, "cache_write": null,
    "batch_input": null, "batch_output": null, "free_tier": null, "promotions": null,
    "long_context": null, "effective_date": null, "source_url": null,
    "source_type": null, "confidence": null, "notes": null
  },
  "modality": {
    "input": {"text": null, "image": null, "audio": null, "video": null, "pdf": null, "code": null, "web": null, "notes": null},
    "output": {"text": null, "code": null, "image": null, "audio": null, "speech": null, "notes": null},
    "native_multimodal": {"input_image": null, "input_audio": null, "input_video": null, "output_image": null, "output_audio": null, "notes": null}
  },
  "meta": {
    "collected_at": "2026-08-25", "verified_at": null, "verification_status": "待验证",
    "source_urls": [], "notes": null
  }
}
```

## 字段填写优先级（时间有限时先做重要的）

**定价 > 多模态 > 自报跑分 > 上下文窗口 > 退役/定位信息**。Arena / 独立跑分由平台 agent 统一采集，你**不必**填 `benchmarks.arena_elo` / `benchmarks.independent`（留空数组即可），专注上面五项。

> `architecture`、`pricing` 的 `notes` 很关键：未披露参数量必须写「官方未披露参数量」；上下文两个窗口都要填——`context_window_tokens` 填官方给的最大可支持长度（给了「原生 X / 扩展 Y」的填 Y 并把 X 写进 notes），`context_window_effective_tokens` **不要求独立实测**，有官方值/自报值就填并在 notes 注明出处，实在没有任何依据才留 null，且**永远不得大于标称值**；定价缺缓存/批量价写说明。这些 notes 是下游判断"这个数从哪来"的依据。

## 输出

- 只产出**一条**该模型的完整记录，写入 `incoming/models/<model_id>.jsonl`（UTF-8 无 BOM，单行压缩 JSON，无多余文本）。
- **⚠ 文件名 sanitize（重要）**：`model_id` 含冒号 `:`（如 `google:gemini-2.0-flash:base`），而 **Windows 文件名不允许冒号**。落盘文件名必须把 `:` 替换为 `__`（例：`google__gemini-2.0-flash__base.jsonl`）；**JSON 内容里的 `model_id` 保持原样含冒号不变**（合并工具读的是内容不是文件名）。
- 不要输出解释性正文到文件；如需备注，写进对应字段的 `notes`。
- 确认记录通过自查清单（执行细则第 11 节）后再落盘。
