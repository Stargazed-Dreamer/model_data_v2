# model_data 缺口扫描与可视化报告（D29-D31）

> 撰写于 2026-09-03。承接 `GAP_SCAN_REPORT_D28.md`，覆盖 D29-D31 的工作：可视化改进 3 批 + 缺口扫描 4 个新角度 + 来源去集中化 + 跑分维度候选。

## 1. 数据集当前状态（截至 D31）

| 维度 | 数值 | 备注 |
|---|---|---|
| 总记录 | 933 条 | 全部 model_id 唯一 |
| 厂商 | 233 家（D28 已归一，原 249） | 长尾：单模型厂商 145 家 |
| 跑分条目 | 5,634（自报 4,108 + 独立 1,013 + Arena Elo 513） | arena_elo 来源已去集中化 |
| license 填充率 | 0.9%（8/933） | D30 已扫，未修复 |
| knowledge_cutoff | 18.5%（173/933） | D28 已修关键 5 条 |
| pricing.input | 31.3%（292/933） | |
| total_params_b | 69.8%（651/933） | |
| context_window_tokens | 76.0%（709/933） | D30 扫出 effective vs nominal 矛盾 |
| modality.input.image | 79.2%（739/933） | |
| verification_status | 已验证 54 / 待验证 859 / 已过期 20 | D28 时效性标准已改 |
| arena_elo 来源 | datalearner 481 + lmarena.ai 170 + 其他 11 | 集中度从 93.7% → 仍 93.7%（补充而非替换） |

## 2. D29-D31 累计已扫缺口

### 2.1 D30 新增 4 个扫描角度

| # | 角度 | 扫描结果 | 处置状态 |
|---|------|----------|----------|
| 1 | context_window_effective vs nominal 矛盾 | 倒挂（eff > nom）+ 偏差过大（eff < nom×0.5）共若干条 | 已记录，待修复 |
| 2 | license 填充率（按厂商分布） | 0.9% 极低；Top 厂商中 OpenAI/Anthropic/Alibaba 都几乎全空 | 已记录，需逐厂商补 |
| 3 | 模型代际命名规范（base/large/medium/mini 等） | 大量模型无代际标识；同义异写（mid vs medium） | 已记录，未修复 |
| 4 | 多厂商合作记录归属（vendor 含 + / & / and / /） | 多个 vendor 含分隔符，归属主次未拆 | 已记录，未修复 |

### 2.2 D30 跑分维度缺失扫描

4 个严重缺失维度（独立评测段）：

| 维度 | 覆盖率 | 缺失模型数 | 备注 |
|---|---|---|---|
| HumanEval | 19.4% | 235 / 292 模型缺 | 严重 |
| BBH | 10.2% | 262 / 292 模型缺 | 严重 |
| MuSR | 0.2% | 291 / 292 模型缺 | 几乎全缺 |
| IFEval | 0.6% | 290 / 292 模型缺 | 几乎全缺 |

**4 维全缺模型**：492 个（75.2%）

**Top 5 厂商候选清单**（已过滤 embedding / 预 2023 / 实验性模型）：

- OpenAI: 多个候选（gpt-4o 系列 / o1 系列 / gpt-5 系列等）
- Anthropic: claude-3.5 / claude-4 / claude-opus 系列等
- Alibaba: qwen2.5 / qwen3 系列
- Google / Google DeepMind: gemini-1.5 / gemini-2 系列
- Mistral AI: mistral-large / codestral 系列

候选清单脚本：`temp/d30_top5_filter.py`（输出按厂商分组的可补模型清单）

### 2.3 D30 arena_elo 来源去集中化

- **扫描**：`temp/d30_arena_source_scan.py` 统计 arena_elo 段 source_url 域名分布
- **问题**：datalearner.com 占 481/513 = 93.7%，来源高度集中
- **尝试**：用 WebFetch 抓 lmarena.ai/leaderboard，被 Cloudflare 拦截（SPA tab 切换，无独立子榜 URL）
- **策略 C 落地**：`temp/d30_arena_add_lmarena.py` 为 170 个有 arena_elo 数据的模型在 `meta.source_urls` 数组追加 `https://lmarena.ai/leaderboard` 一手源（幂等，已含则跳过）
- **结果**：170 个模型补充 lmarena.ai 一手源，但条目级 source_url 仍保留 datalearner 镜像

## 3. D29-D31 可视化改进累计

### 3.1 总览：12 页架构 + 全局筛选 + 档案抽屉

12 个页面：总览 / 厂商视角 / 性价比 / 模型对比 / Arena 来源 / 时间演进 / 数据质量 / 数据缺口 / 厂商碎片 / 字段总览 / 图表工坊 / 明细浏览。

全局筛选条：厂商 / 定位 / 开源 / 价格 / 参数 / 日期 / Elo / 跑分 8 维筛选 + URL hash 状态分享。

模型档案抽屉：点任意模型名打开，显示完整档案 + 同厂商兄弟 + 相似推荐。

### 3.2 D29 第一批：缺口分析 + 碎片检测 + 档案抽屉

- 新增 `build_gap_analysis()`：字段组填充率雷达 + 跑分覆盖热力图 + 字段缺口排行 + 无跑分模型清单
- 新增 `build_vendor_fragmentation()`：大小写/空格/连字符变体合并建议 + 厂商气泡图
- 新增 `build_model_details()`：每个模型的完整档案 + 同厂商兄弟 + 相似推荐
- 前端新增「数据缺口」「厂商碎片」2 个页面 + 档案抽屉组件 + sticky 全局筛选条

### 3.3 D30 第二批：价格象限图 + 甘特图

- 新增 `build_price_quadrant()`：以中位价格 × 中位 Elo 分割 4 象限 + 线性回归线
  - 高性价比（低价高能）/ 低性价比（高价低能）/ 高端（高价高能）/ 低端（低价低能）
  - 4 个 KPI 卡片显示各象限模型数
  - 点击散点跳模型档案
- 新增 `build_lifecycle_gantt()`：release_date → knowledge_cutoff（缺则用今天兜底）
  - Top 120 模型（优先有 kc 的真实生命周期）
  - 颜色按地缘：中国红 / 美国蓝 / 欧洲紫 / 其他灰
  - dataZoom 双向缩放（X 时间 + Y 模型）
  - 点击条跳模型档案

### 3.4 D31 第三批：缺口矩阵 + 智能诊断 + 导出

- 新增 `build_gap_matrix(rows, top_vendors_n=30)`：返回 3 大块数据
  - **matrix**：31 厂商（Top 30 + 其他聚合）× 19 关键字段 = 438 矩阵数据点（含填充率%）
  - **diagnosis**：每厂商 top_gaps（最缺 Top 3 字段） + 健康度分数（平均填充率）
  - **export**：401 条 todo_items（vendor × field 缺失组合），含具体 model_id 清单
- 前端在「数据缺口」页追加 3 个组件
  - 厂商 × 字段 缺口矩阵热力图：色阶 红 → 黄 → 绿（< 30%/30-70%/> 70%）
  - 厂商智能诊断卡片：健康度最低的 Top 15 厂商，每家显示最缺的 3 字段 chip
  - 一键导出待补清单：JSON / CSV / Markdown 三种格式
- 交互闭环
  - 点击矩阵单元格 → 复制该格缺失 model_id 清单到剪贴板
  - 点厂商名 → 跳转明细页并按该厂商筛选
  - 点字段 chip → 跳转图表工坊用该字段绘图
  - 导出按钮 → Blob 下载文件

## 4. 未深度扫描的剩余角度

D28 + D30 累计已扫 20 个角度。仍未深扫的 8 个角度：

1. **价格策略细分**：cached_input / batch_input vs 普通 input 价的折扣率分布
2. **厂商代际演进**：同厂商不同代次（如 Qwen2→Qwen2.5→Qwen3）能力跃迁图
3. **跑分时间序列**：同 benchmark 在不同 release_date 的分数变化趋势
4. **工具调用 / function calling** 评测分（独立维度，未单独收录）
5. **TTFT / 吞吐量 / 推理时长** 等性能指标（完全无字段）
6. **模型家族关系**：base / instruct / fine-tune 衍生关系图谱
7. **价格历史变化**：同一模型多次调价的轨迹（数据无版本字段，需溯源）
8. **多语种能力**：英文/中文/多语种 benchmark 覆盖对比

## 5. 待推进的修复任务

| # | 任务 | 影响范围 | 优先级 | 状态 |
|---|------|----------|--------|------|
| 1 | 补跑分维度（HumanEval/BBH/MuSR/IFEval） | 168 个 Top 5 厂商候选模型 | 中 | 进行中 |
| 2 | context_window_effective vs nominal 矛盾修复 | D30 已扫，若干条 | 中 | 待修 |
| 3 | license 类型补全（按厂商逐家） | 925 条缺 license | 中 | 待采 |
| 4 | 模型代际命名归一（mid→medium 等） | D30 已扫 | 低 | 待修 |
| 5 | 多厂商合作记录归属主次拆分 | D30 已扫，多个 vendor 含分隔符 | 低 | 待修 |
| 6 | arena_elo 条目级 source_url 替换 | 481 条仍指向 datalearner | 低 | 策略 C 已补一手源兜底 |

## 6. 技术实现要点

### 6.1 后端聚合层（`scripts/viz_transform.py`）

新增聚合函数 4 个：

- `build_gap_matrix(rows, top_vendors_n=30)` — D31 缺口矩阵 + 诊断 + 导出
- `build_price_quadrant(rows)` — D30 价格 × 性能 4 象限 + 线性回归
- `build_lifecycle_gantt(rows, top_n=120)` — D30 模型生命周期甘特图
- D29 已新增的 `build_gap_analysis` / `build_vendor_fragmentation` / `build_model_details` 保持不变

注册入口 `build_extended_aggregates` 共返回 16 个聚合块：

```
vendor_capability / price_brackets / modality_combo / time_trend / data_quality /
arena_subboards / source_domains / cost_effectiveness / moe_sparsity / benchmark_dims /
vendor_geo / model_details / gap_analysis / vendor_fragmentation /
price_quadrant / lifecycle_gantt / gap_matrix
```

### 6.2 前端展示层（`viz/viz_index.html`）

- 全局筛选条 sticky 在顶部（z-index:9），URL hash 状态分享（`#v=OpenAI&p=旗舰&o=yes`）
- 模型档案抽屉：560px 宽右侧抽屉，点任意模型名打开
- D31 新增 3 个组件位于「数据缺口」页末尾
- Toast 反馈组件用于剪贴板复制提示

### 6.3 数据流

```
model_data_v2.jsonl
  ↓ load_rows()
flatten_record(rows)  # 展平 + 派生字段
  ↓
build_extended_aggregates(rows, raw_records)
  ↓ viz_server.py /api/extended
前端 viz_index.html fetch 后渲染
```

## 7. 验证

- D31 后端冒烟通过：31 厂商 / 19 字段 / 438 数据点 / 401 todo_items
- D31 接口 `/api/extended` 通过 PowerShell Invoke-RestMethod 验证返回结构正确
- 最差厂商：China Telecom（健康度 45.1%，7 模型全无 price/kc）
- 最大缺口：「其他」厂商 × HumanEval（337 模型缺）
