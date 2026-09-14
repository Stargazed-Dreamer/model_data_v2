# D50 轮次报告：三件小事清账 + 全量 S0 扫描（1 新模型入库）

> 日期：2026-09-14。用户指令（原文「先把你说的小的做了，然后扫一轮」）。
> 记录数 **959 → 960**，门禁 **ERROR 0 / WARN 0**，qa_outliers 终态：硬错全 0、r1=0、**r2=0**、c5 批注后归零口径疑点。

## 一、三件小事清账

1. **gpt-6-astra-pro 定论（不采）**：OpenRouter 官方描述明文「same underlying model as GPT-6 Astra，reasoning.mode=pro 服务档」——非独立模型（D35 口径）。库内 `openai:gpt-6-astra:base` notes 已加防重留痕（pro 档 $10/$50、batch 半价）。D49 保留的缓采项就此关闭。
2. **minicpm-4 冲突值核实（D47 遗留清账）**：经魔搭官方仓核实——① license 官方标注 **apache-2.0**，主档原「MIT License (ModelBest)」系采集误读，已改为 Apache 2.0；② ctx 维持主档 32768（config 原生 max_position_embeddings=32768 带 LongRoPE 扩展，扩展上限无官方数字，donor 侧 131072 不采）。
3. **c5 定位口径批注**：13 条「轻量定位 + MoE 大总参」记录（longcat-flash 560B、v4.1-flash 552B、glm-5.3-flash 320B 等）加标准批注「轻量指激活参数/家族档位，非数据矛盾」；4 条「旗舰 + 小模型」（granite/minicpm/mistral-7b 的 family flagship 官方自述）维持不动。

## 二、全量 S0 扫描（A 层 → B 层）

| 层 | 动作 | 结果 |
|---|---|---|
| A 层 | AA/Arena/MS/OR 四源重抓 + leads diff | **无新增**（OR 仅 2 条 `~deepseek` 别名；Arena 快照仍 09-11；MS candidates 8 条全是已排除训练产物） |
| B 层 | 阿里云台账 / DeepSeek news / 智谱发布记录 / Moonshot 文档 | **1 条真线索**：`qwen-flash-character`（已采，见下）；DeepSeek news 页结构已变为文档页（台账式入口失效，下轮直接探测 `/news/news2609xx` 命名或换入口） |
| C/D 层 | 榜单与中文媒体 | 随 A 层快照覆盖，无新增 |

## 三、采集：`alibaba:qwen-flash-character:base`（960 条）

- release_date **2026-01**（修正派发线索：台账 T0 全量显示 01-13 新加坡/北京首发，08-30 仅美区扩展——S0 扫描单区域视角的偏差，采集 agent 已按首次发布口径纠正并双日期留痕）；
- 角色扮演特化（「Qwen 角色扮演模型系列」，与 qwen-plus-character 同系；qwen-flash 特化版为合理推断非官方声明，notes 标明）；动态版 ctx 32,768（快照版 262,144）；美国区定价 $0.034/$0.203/缓存 $0.007（北京区 CNY 入 notes）；纯文本；官方无基准发布 → 三数组按分工留空/空；
- 与 qwen-drive（D46）同为「领域特化可采」先例。

## 四、状态与下一步

- **960 条终态**，门禁绿，qa_outliers：o1=4（历史空日期）/c4=2/r1=0/r2=0，硬错全 0。
- 三件小事与 S0 全部清账；**无待办积压**。下次数据来源 = 厂商新发布（S0 用户触发制）。
- 小遗留：DeepSeek news 入口失效需换探测方式（下轮 S0 时处理）；qa_outliers 扩容至 31 项（可选，未排期）。
