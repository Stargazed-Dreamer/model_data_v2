# D46 轮次报告：D44 缓采复筛二批入库 + 离群体检器重建

> 日期：2026-09-13。用户拍板（原文「直接做下一轮，并发加到 3」）。上轮：D45 首批 9 模型入库。
> 本轮记录数 **944 → 950**，门禁 **ERROR 0 / WARN 0**；subagent 并发 3（用户放宽），7 个任务分三波。

## 一、d34_scan_outliers.py 处置与重建

用户提示从回收站找（提示正确方向：`scripts/recycle_tool.py` 走 FOF_ALLOWUNDO），实测三处均无：**Windows 回收站**（Shell COM 枚举，只有无关终端日志）、工作区 find、git 历史——原脚本系 `rm` 直删未过回收站，**不可恢复**。

按 D34 CHANGELOG 留痕口径 + `temp/d34_a_class_report.md` 的 A1-A8 方向**重建**为 `scripts/qa_outliers.py`：13 项注册检查（离群 o1-o6 / 矛盾 c1-c6 / 命名 v1）+ 3 项跨记录检查（同厂商同名 r1、基准名大小写异写 r2、字段填充率 v3）。定位**体检不是门禁**：`硬错`=几乎必错，`疑点`=人工判（D34 教训：倒挂 13 条系名义值/精确值精度差、知识截止早于发布系正常语义，均不动）。

**首轮基线（944 条，报告 `temp/d46_outliers_report.txt`）**：硬错全 0；o3=13（全部有精度注，D34 已裁定不动）；v1=53（singapore-ai/allenai 等缩写对，历史命名）；**r1=3 组同厂商同名**（`qwen2.5-coder-32b` vs `qwen2.5-coder`、minicpm-4 双档、`glm-5.2` vs `glm-5.2-none`——后组疑似 D34 思考/非思考改名未彻底，留待拍板）；r2=13 簇基准名大小写异写（D34 修过 5 簇，本轮后 +1=14，源自新入库跑分表，留清理清单）。合并后复扫（950 条）：**硬错仍全 0**，新 6 条零引入。

## 二、D44 缓采 13 条复筛：6 采 / 7 排除

- **永久排除（7，训练中间产物/依附组件，非独立测量身份）**：MiniCPM5-2B-{SFT,Base,Midtrain}、JustRL-II-base-model、Ling-3.0-flash-base-{midtrain,30T}。
- **Ling-3.0-flash-dspark 身份核验**（前置任务）：判定为**投机解码 speculator**（官方 README 原话 "A DSpark speculator for Ling3"，1.36B/5 层 draft，依赖主模型第 1/11/23/29/35 层隐状态、离了主模型无法独立工作，官方 tags 含 speculative-decoding），按 D35 一行一个测量身份**不单列**；关键信息并入 `inclusionai:ling-3.0-flash:base` basic_info.notes（含 acceptance length 5.29 为吞吐指标非能力跑分的防混淆注记）。
- **采集 6 条（批次 `b334w1-modelscope`，round D46）**，全部过「模型/工具判定」（细则第 10 条 + D37 Cohere Parse 教训重点核对 OCR/UI 方向）：

| model_id | vendor | release_date | 关键值 |
|---|---|---|---|
| inclusionai:llada-ui:base | InclusionAI | 2026-09（GitHub initial release 09-09） | **16.7B MoE 扩散 LLM**（backbone Diffusion，LLaDA2.0-mini 基座）UI-agent 特化；8K ctx；license 官方未披露→null；6 条自报 |
| inclusionai:ui-venus-2-9b:base | InclusionAI | 2026-08-27（arXiv:2609.00028） | Qwen3.5-9B 全参微调 GUI agent 基座；9.41B Dense、Hybrid（24 线性+8 全注意力）；256K ctx；license 官方明示「待定」→null；27 条自报 |
| inclusionai:armor-ocr:base | InclusionAI | 2026-08-20（GitHub+HF+arXiv 三处同日） | Qwen3-VL-8B 微调 OCR 权重模型（非管线，两阶段训练法）；8.767B Dense；256K ctx；Apache-2.0；15 条自报 |
| alibaba:qwen-drive-1.0-4b:base | Alibaba | 2026-08（GitHub 08-25/HF 08-27/arXiv 08-31 锚定） | 驾驶规划 VLM（QwenDriveForPlanning），Qwen3.5-4B 基座+BEV 头+流匹配 expert（头参数官方未公布，4.539B 仅 VLM 本体）；发卡 ctx 有意调小至 32K；Apache-2.0 |
| modelbest:mathform-8b:base | ModelBest | 2026-08（GitHub News 08-17 / arXiv 08-14 双口径取月级） | 数学自动形式化（NL→Lean 4），Qwen3-8B 微调；8.19B Dense；40K ctx；Apache-2.0；4 条自报 |
| baai:recon2reason-reasoning-4b:base | **BAAI（新厂商）** | 2026-09（HF 官方仓 09-03，无公告取月级） | 空间推理 VLM，Qwen3-VL-4B 微调；4.438B Dense（官方精确值）；256K ctx；Apache-2.0；官方无数字跑分→三数组空 |

## 三、S4 质检

- 全库门禁 950 条 **ERROR 0 / WARN 0**；
- `qa_outliers.py` 复扫：硬错全 0（o1/o3/c5/v1 与基线持平，均为已知历史项）；
- `candidate_diff.py` 复扫 D44 候选：**NEW 6 → 2**，且剩余 2 条属永久排除名单（训练产物），**D44 漏采线索至此全部处置完毕**。

## 四、遗留

1. **r1 的 glm-5.2 / glm-5.2-none 同名组**：疑似 D34 思考/非思考改名未覆盖到 full_name，建议下轮拍板是否补改名；
2. **r2 基准名大小写 14 簇**：可做一次归一清理（多数派写法），涉及跑分数组主键，需走批处理流程；
3. license 待回填项新增 2 条（llada-ui、ui-venus-2-9b 官方明示未定/待确认），建议挂 `docs/LICENSE_GAP_BACKLOG.md` 同款跟踪；
4. N2.5 mini/Pro 日期、Ling 两系日期待官方公告（沿用 D45 遗留）；
5. D44 遗留的 backlog 948 条长尾仍未过（缓采已清零，长尾多为 embed/经典 NLP，优先级降低）。
