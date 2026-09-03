# model_data 缺口扫描报告（D28 收尾后）

> 撰写于 2026-09-03。基于 `model_data_v2.jsonl` 当时的 933 条记录。

## 1. 数据总体情况

| 维度 | 数值 |
|------|------|
| 总记录数 | 933 条 |
| 厂商数 | 249 家（单模型厂商 145 家，占 58.2%，长尾很长） |
| 跑分条目 | 5,634（自报 4,108 + 独立 1,013 + Arena Elo 513） |
| license 填充率 | 0.9%（8/933，极低） |
| knowledge_cutoff | 18.5%（173/933） |
| pricing.input | 31.3%（292/933） |
| pricing.output | 29.7%（277/933） |
| total_params_b | 69.8%（651/933） |
| context_window_tokens | 76.0%（709/933） |
| modality.input.image | 79.2%（739/933） |
| verification_status | 已验证 54 / 待验证 859 / 已过期 20 |
| 厂商 Top 3 | OpenAI 70 / Alibaba 67 / Anthropic 44 |

## 2. D28 收尾后剩余未探缺口

D28 整轮 17 批已完成，门禁首次清零。已扫描 16 个角度（架构矛盾 / kc vs release_date / arena_elo 范围 / confidence 一致性 / score 异常 / 重复 model_id / source_url 格式 / positioning vs native_multimodal / modality 矛盾 / pricing 单位 / date 空值 / benchmark 拼写 / license 缺失 / context_window 异常 / release_date 格式 / kc 非标准日期）。

剩余 13 个尚未深度扫描的角度，按本次扫描细化：

### 2.1 Arena 子榜覆盖（本次扫描发现）

- **当前覆盖**：text 170 / coding 166 / math 156 / webdev 3 / vision 1 / search 1 / agent 1 / gdpval 1
- **缺口**：webdev / vision / search / agent / gdpval 等子榜覆盖严重不足（1-3 个模型）
- **子榜命名碎片化**：17+ 种写法变体（如 "LMArena (overall, text)" / "Chatbot Arena Overall ELO" / "LMArena Text Generation (Chatbot Arena)" 实际同指 "text" 主榜）
- **可视化已处理**：viz_transform.py `build_arena_subboards` 已用 `SUB_NORM` 映射表归一化展示
- **源数据未修复**：源 JSONL 中仍然是各种碎片化写法，需要在数据层归一

### 2.2 跑分来源 URL 域名分布（本次扫描发现）

- **arena_elo 来源集中度**：datalearner.com 占 481/513 = 93.7%（来源高度集中，单点风险）
- **全库来源 Top 5**：epoch.ai（1,222）、huggingface.co（700）、arxiv.org（596）、m.toutiao.com（432）、github.com（281）
- **Top 5 集中度**：50.5%；**Top 10 集中度**：59.2%
- **域名总数**：744 个
- **可视化已处理**：viz_transform.py `build_source_url_domains` 已展示

### 2.3 active_params vs total_params MoE 稀疏度（本次扫描发现）

- **有参数的模型**：465 个
- **MoE（稀疏度 < 0.95）**：134 个（28.8%）
- **Dense（稀疏度 ≥ 0.95）**：331 个（71.2%）
- **稀疏度分布**：<0.05 (32) / 0.05-0.1 (53) / 0.1-0.3 (47) / 0.3-0.6 (1) / 0.6-0.95 (1) / ≥0.95 (331)
- **极稀疏（< 0.05）的 32 个模型**：典型超稀疏 MoE（如 Qwen3-30B-A3B、DeepSeek-V3 等）
- **可视化已处理**：viz_transform.py `build_moe_sparsity` 已展示

### 2.4 collected_at 时效性（本次扫描发现，需改进判断标准）

- **当前已过期 20 条**：7 条老模型（< 2024，应改"已定死"）+ 13 条新模型（≥ 2024，真正需重审）
- **待验证 859 条**：128 条老模型（< 2024，应改"已定死"）+ 731 条新模型（全部 collected_at < 3 月，时效 fresh）
- **建议新标准**：
  - 老模型（release_date < 2024-01-01）：永久"已定死"，不参与时效性检查 → 影响 135 条
  - 新模型（≥ 2024-01-01）：
    - collected_at < 6 月：fresh（不标记过期）
    - 6-12 月：可重审（仅提示）
    - > 12 月：需重审（可标记过期）

### 2.5 厂商地缘分布（本次扫描发现）

- **中国**：237 模型 / 53 厂商 / 平均 Elo 1346.5 / 平均价 $1.01 / 开源 182
- **美国**：344 模型 / 34 厂商 / 平均 Elo 1375.1 / 平均价 $6.258 / 开源 128
- **欧洲**：47 模型 / 6 厂商 / 平均 Elo 1288.1 / 平均价 $0.82 / 开源 33
- **其他**：305 模型 / 156 厂商 / 平均 Elo 1212.4 / 平均价 $2.048 / 开源 189

**观察**：美国模型数最多但厂商集中度高（少而精），中国厂商多但平均价格最低，欧洲厂商极少但平均价最低。

### 2.6 性价比单位成本（本次扫描发现）

- **有性价比数据**：107 个模型
- **Top 5 性价比（$/Elo point）**：
  1. Qwen3.5-35B-A3B (Alibaba) - $0.0000/Elo（极低）
  2. gemini-1.5-flash-8b-001 (Google DeepMind) - $0.0000/Elo
  3. Alibaba Qwen-Plus - $0.0001/Elo
  4. Qwen3-30B-A3B (Alibaba) - $0.0001/Elo
  5. Qwen3.5-122B-A10B (Alibaba) - $0.0001/Elo

### 2.7 跑分维度填充率（本次扫描发现）

- **有跑分数据的模型**：292 个（占总 31.3%）
- **各维度填充率**：
  - MMLU: 144/292 = 49.3%
  - GSM8K: 80/292 = 27.4%
  - GPQA: 190/292 = 65.1%
  - HumanEval: 2/292 = 0.7% **（严重缺失）**
  - MATH: 93/292 = 31.8%
  - BBH: 3/292 = 1.0% **（严重缺失）**
  - MuSR: 1/292 = 0.3% **（严重缺失）**
  - IFEval: 1/292 = 0.3% **（严重缺失）**

**观察**：HumanEval / BBH / MuSR / IFEval 几乎完全缺失，雷达图对比只能用 MMLU / GSM8K / GPQA / MATH 四个维度。

## 3. 待推进的修复任务

| # | 任务 | 影响范围 | 优先级 |
|---|------|----------|--------|
| 1 | 时效性判断标准改进 | 135 条老模型改"已定死"，新模型分级 | 高 |
| 2 | Arena 子榜命名归一（源数据） | 17+ 种子榜写法变体 | 中 |
| 3 | arena_elo 来源集中度风险记录 | 481/513 来自 datalearner.com | 中 |
| 4 | HumanEval/BBH/MuSR/IFEval 跑分补充 | 严重缺失 | 中 |
| 5 | webdev/vision/search/agent 子榜数据补充 | 1-3 个模型覆盖 | 低 |
| 6 | 同模型不同源跑分一致性 | 13 个角度之一 | 低 |
| 7 | context_window_effective vs context_window 矛盾 | 未扫 | 低 |
| 8 | license 类型分布与 GPL/AGPL 合规 | license 填充率仅 0.9% | 低 |
| 9 | 多厂商合作记录归属主次 | 未扫 | 低 |
| 10 | 模型代际命名规范（base/large/medium/mini） | 未扫 | 低 |

## 4. 可视化改进已完成

本次同步推进了 3 批可视化改进（共 10 个新页面/组件）：

### 4.1 联动下钻 + 模型对比页（批1）
- 新增 page-compare（模型对比页）
- 雷达图：8 维跑分对比（MMLU/GSM8K/GPQA/HumanEval/MATH/BBH/MuSR/IFEval）
- 参数对比图：价格 / 参数 / 上下文 / Elo 多 series
- 明细对比表：所有维度并排
- 联动：明细表行点击 / 性价比表行点击 / Arena 子榜 Top5 行点击 → 加入对比列表（最多 4 个）
- 自动跳转到对比页

### 4.2 性价比单位成本 + MoE 稀疏度散点（批2）
- 性价比页扩展：$/Elo point 排行表（点击行加入对比）
- MoE 稀疏度散点：active vs total params（红/灰双色 MoE/Dense 区分）
- symbolSize 按 Elo log 缩放

### 4.3 Arena 子榜覆盖 + 跑分来源可信度（批3）
- 新增 page-arena_source（Arena 子榜 / 来源页）
- 子榜覆盖图：8 个归一化子榜 + 模型数
- 各子榜 Top 5 模型列表（点击加入对比）
- 来源域名分布 Top 10 条形图
- 来源集中度 KPI 卡片（Top 5 / Top 10 占比）

### 4.4 附加：厂商视角页地缘对比图
- 厂商地缘对比：中国/美国/欧洲/其他 × 模型数 + 厂商数
- 地缘平均 Elo + 平均价格双轴图

## 5. 技术实现

- 后端：`scripts/viz_transform.py` 添加 6 个新聚合函数
  - `build_arena_subboards` - 子榜归一 + Top 5
  - `build_source_url_domains` - 来源域名 + 集中度
  - `build_cost_effectiveness` - 性价比排行
  - `build_moe_sparsity` - MoE 稀疏度散点
  - `build_benchmark_dimensions` - 雷达对比维度
  - `build_vendor_geo_stats` - 厂商地缘分组
- 后端：扩展 `flatten_record` 保留 `arena_elo_subs` / `source_urls` 数组
- 后端：新增字段 `cost_per_elo` / `moe_sparsity` / `vendor_geo` / 8 个独立跑分维度
- 前端：`viz/viz_index.html` 新增 2 个页面（compare / arena_source）+ 4 个新图表
- 前端：导航从 8 项扩到 10 项
- 前端：实现联动逻辑（addCompareModel / removeCompareModel / updateCompareList）

## 6. 后续建议

1. **时效性判断标准** 应该把"老模型已定死"的逻辑加入门禁规则或可视化层（如 data_quality 页加"老模型已定死"分类）
2. **Arena 子榜命名归一** 在源数据层修复 17+ 种变体
3. **跑分维度补充** 优先补 HumanEval / BBH / MuSR / IFEval（独立评测已存在但未收录）
4. **arena_elo 来源去集中化** 寻找 lmarena.ai 一手数据替代 datalearner.com 镜像
