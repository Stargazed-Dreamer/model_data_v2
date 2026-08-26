# 大模型静态数据集 · 采集计划 v2（一模型一 Agent）

> 修订于 2026-08-25，取代 `multi_agent_plan.md` 的「阶段 1 并行采集」分组方式。
> 配套：`prompt.md`（schema 1.1 + 7 项决策）、`执行细则.md`（11 项规则）、
> `model_data_tool.py`（**已修复 add_record，新增记录必出完整骨架**）、
> `validate_model_data.py`（门禁）、`agent_prompt_per_model.md`（单模型 agent 提示词模板）。
> 当前数据库状态：v2 已清理，926 条，ERROR 6（均为已知 p2 未核实站点 source_url 缺口，见第 7 节）。

---

## 0. 为什么改（诚实评估，不粉饰）

v1 计划把模型按厂商分组，一个 agent 扛一组（G4 = alibaba 67 + deepseek 18 + bytedance 4 = **90 条一个 agent**）。
结果（见 DATA_QUALITY_REPORT_v2.md）：

- G1「样板」56 条都漏了 `positioning` 和 `self_reported`，多模态/自报跑分整体缺席；
- 分片补丁（p1 仅 arena）经合并工具 `add_record` 时**直接 deepcopy**，新记录缺 `basic_info/architecture/pricing/modality/meta` → 15 条残缺记录（已删除）；
- 上下文窗口填充率 8.1%、定价 5.3%、多模态 6.0%、定位 0.2%。

**根因**：采集单元太大，agent 上下文被稀释，必然 corner-cutting；且工具不保新增记录结构完整。

**结论**：深度字段（定价 / 多模态 / 定位 / 架构 / 自报跑分 / 上下文）**改为「一个模型一个 subagent」**，
聚焦 = 准确，慢但准（用户明确：慢一点没关系，重准确）。

---

## 1. 新范式：两类 agent，职责分离

| 类型 | 负责字段 | 数据来源特征 | 单元粒度 | 理由 |
|------|----------|--------------|----------|------|
| **M 型（单模型深度档案）** | `basic_info`(含 positioning/access) / `architecture` / `pricing` / `modality` / `benchmarks.self_reported` / `meta` | 每个模型**自己的**官方定价页、Model Card、技术报告、文档 | **1 模型 / 1 agent** | 这些来自各模型自有官方源，聚焦单个模型才能挖深、不漏字段 |
| **P 型（中心化平台跑分）** | `benchmarks.arena_elo` / `benchmarks.independent` | 聚合站：lmarena.ai / Artificial Analysis / OpenCompass（一站列全部模型） | **1 agent / 数据源** | 来自同一榜单，一次性抓全部模型可保证**快照日期一致**、避免 359 个 agent 各自扒同站触发限流、日期漂移 |

> **为什么不把 Arena/独立跑分也拆成一模型一 agent**：Arena 是时间快照数据，集中抓取能保证同一期快照日一致；359 个 agent 各抓各的，快照日必然参差，反而损害准确性与可比性。P 型保持中心化，是"重准确"的延伸而非违背。

---

## 2. M 型单模型 agent：输入 / 输出 / 契约

### 输入（主 agent 派发时附上）
1. `prompt.md` + `执行细则.md`（规范，agent 须遵守）
2. 本模型的 `model_id`（来自花名册 `roster.jsonl`）
3. 该模型在 v2 的**当前状态切片**（若是 `in_v1`，附已有字段 + 待补字段清单；若是 `to_add`，标注"全量新建"）
4. `agent_prompt_per_model.md`（提示词模板，填入 model_id 即可用）

### 输出契约
- 文件：`incoming/models/<model_id>.jsonl`（**每模型一个文件，单行压缩 JSON**）
- **⚠ 文件名 sanitize（重要）**：`model_id` 含冒号 `:`（如 `google:gemini-2.0-flash:base`），**Windows 文件名禁止冒号**。落盘文件名必须把 `:` → `__`（如 `google__gemini-2.0-flash__base.jsonl`）；JSON 内容里的 `model_id` 保持原样。合并工具读内容不读文件名，故无影响。试点已验证此路径。
- 必须是**完整 schema 1.1 记录**（所有顶层键 + modality 三块 + pricing 四必采键务必出现，即使全 `null`）
- 合并工具已修复：即便 agent 只填了部分字段，落库也会自动补全骨架；但**agent 仍须尽力填全**，骨架补全不等于数据补齐
- `meta.collected_at` = **本次真实采集日期**（精确到日，如 `2026-08-25`），禁止写硬编码统一日期（旧 P2 问题，已根治思路：每 agent 各自填真实日期）
- `meta.verification_status` = 诚实值（`待验证` / `已验证` 须带 `verified_at` / `存疑` / `已过期`），**禁止无 `verified_at` 却标"已验证"**（已清理 2 条此类假验证）

### 硬性红线（执行细则摘要，agent 必读）
- 没查到 = `null`，**严禁用 `false`/`0`/空串代替"没查到"**
- 不伪造 `T0`；转述来源配 `T0-自报-转述`/`T3`，不自洽直接报错
- 跑分 `score` 一律 0–1 小数，百分制须 ÷100 + notes
- 非 USD 价须按**可查汇率**折算并记来源日期，禁止假设值
- 每个 `benchmarks.*` 条目必须带 `source_url`（采集即记录，不允许为空）

---

## 3. P 型平台 agent（沿用旧计划，保持不变）

| 组 | 数据源 | 写入字段 |
|----|--------|----------|
| P1 Arena | lmarena.ai | `benchmarks.arena_elo`（按子榜 + 快照日，允许月级） |
| P2 独立跑分 | OpenCompass / Artificial Analysis | `benchmarks.independent` |

- 输出 `incoming/agent_p1.jsonl` / `incoming/agent_p2.jsonl`
- 仍须补 `source_url`；`qwq-32b`(4) / `grok-4:0709`(2) 的 6 个 `independent` 条目此前因未核实站点（aiwiki/wiki.hugogu）留空，本伦重采须补齐真实基址 URL，否则校验仍报 ERROR（见第 7 节）

---

## 4. 合并流程（用修复后的工具）

每个 M 型 agent 产出 `incoming/models/<model_id>.jsonl` 后，由主 agent 批量合并：

```bash
# 单模型合并（结构保障已内置，新增记录自动补全骨架）
python model_data_tool.py merge \
  --file model_data_v2.jsonl \
  --incoming incoming/models/<model_id>.jsonl \
  --on-null take_source --on-both conflict \
  --on-array union_by_key \
  --array-key benchmark config date \
  --array-key-override benchmarks.arena_elo:sub_benchmark,date \
  --on-schema upgrade --apply

# 批量合并某厂商目录下所有单模型文件（建议按 vendor 分批，便于回滚）
for f in incoming/models/<vendor>/*.jsonl; do
  python model_data_tool.py merge --file model_data_v2.jsonl --incoming "$f" \
    --on-null take_source --on-both conflict \
    --on-array union_by_key --array-key benchmark config date \
    --array-key-override benchmarks.arena_elo:sub_benchmark,date \
    --on-schema upgrade --apply
done
```

合并前工具自动 `.bak`；每次 `--apply` 后跑一次 `validate_model_data.py` 作门禁，ERROR 必须为 0（除第 7 节已知缺口）方可继续。

---

## 5. 编排与扩容（359 个模型的 fan-out）

花名册：`in_v1` 333 + `to_add` 26 = **359 个待采集模型**，28 家厂商。

- **每模型 = 1 个 M 型 subagent**：聚焦单模型，输出 `incoming/models/<model_id>.jsonl`。
- **并行策略**：按厂商分批，每批 N 个模型并行（N 受运行时/限流约束，建议 5–10）。同厂商模型放同批，便于合并回滚。
- **不跨模型共享上下文**：每个 agent 只看自己那一个模型，杜绝稀释。
- **中心化 P 型**：P1/P2 仍各 1 个 agent 一次性抓全站，独立于 M 型批次。
- **门禁**：每批合并后 `validate_model_data.py` 必须 0 ERROR（已知缺口除外），否则该批退回重采。

---

## 6. 验收标准

1. 合并后全量 `validate_model_data.py`：ERROR = 0（或仅余第 7 节已知 6 项 p2 缺口）。
2. 逐维度填充率较 v1 显著提升：定价、多模态、定位、自报跑分、上下文窗口应从个位数/零提升到合理覆盖。
3. `verification_status` 全部诚实（无"已验证"无 `verified_at`、无 `null`）。
4. `collected_at` 为真实采集日（允许不同模型不同日，这是正确状态）。
5. 占位符 notes（"待补/未含"）占比大幅下降——从 98.4% 降到可接受水平，notes 应是"真实采集说明"而非"没采到"声明。

---

## 7. 已知遗留（非垃圾，阶段 3 待补）

清理后 v2 仍有 **6 ERROR（2 条记录）**，全部是 `qwq-32b`(4) / `grok-4:0709`(2) 的 `independent` 条目 `source_url` 为 null，
来自未核实的第三方登记站（aiwiki / wiki.hugogu）。这是已知数据缺口，非工具缺陷、非垃圾：
- 解决方式 A：P2 重采时补齐这 10 个条目的真实基址 URL；
- 解决方式 B：若确属无法核实站点，在 `notes` 注明"第三方登记站未核实"并放宽校验（需改 `validate_model_data.py` 允许 `source_type=第三方登记站` 且 notes 声明时 null 可豁免）。
- 暂不强行清零，避免编造 URL。

---

## 8. 与 multi_agent_plan.md 的关系

- 本文档**取代** `multi_agent_plan.md` 的「阶段 1 并行采集（6 厂商组 + 2 平台组）」分组方式。
- `multi_agent_plan.md` 的「阶段 0 地基」「阶段 2 合并策略（显式规则 / 无写冲突架构）」「阶段 3 质检」**仍然有效**，合并命令与之完全一致。
- 关键变更只有一处：**采集单元从"一组厂商(几十~上百模型)"改为"单模型"**，并配套修复了 `add_record` 结构保障。
