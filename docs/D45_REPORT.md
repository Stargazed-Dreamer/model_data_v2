# D45 轮次报告：魔搭补全落库 + D44 漏采线索首批 9 模型采集入库

> 日期：2026-09-13。用户拍板（原文「能继续就继续采集」）。上轮：D44 魔搭接入（漏采线索 22 条 + fillplan 66 条候选）。
> 本轮记录数 **935 → 944**，门禁 **ERROR 0 / WARN 0**；约束：subagent 并发 ≤ 2（用户指定，额度原因），9 个采集 agent 分五波派发。

## 一、魔搭补全落库（fillplan → 主库）

**脚本**：`scripts/d45_import_modelscope.py`（只为空值补，不覆盖任何已有值；备份 `backups/model_data_v2.pre-d45-msfill-*.jsonl`）。

- **抽验**：6 条人工抽验，5 条与 HF 同名仓库 config.json **完全一致**（Qwen2.5-14B / Qwen2-0.5B / Qwen2.5-3B / DeepSeek-R1-Zero / phi-2），1 条 gated（GLM-4-32B-0414）按公开规格吻合。魔搭官方仓库 config 即 HF config 镜像。
- **实际落库**：66 条候选中可补 **55 条记录**——`context_window_tokens` 补 8 条（R1-Distill-Qwen-1.5B 131072、Skywork-OR1-32B 131072、Kimi-Dev-72B 131072、InternLM2/2.5/3、MiMo-7B-Base 等）、`architecture_type` 补 48 条（config.json 结构判据：有专家键=MoE、仅 num_hidden_layers=Dense；Hybrid 不可靠判不导）。MS 仓库 URL 入 `meta.source_urls`，`architecture.notes` 加【D45 魔搭补全】留痕。
- **口径发现（本轮重要产出）**：config.json 的 `max_position_embeddings` 是**原生标称**口径，而主库 `context_window_tokens` 按 prompt.md 收**最大可支持**（含 YaRN 扩展/官方宣传口径）。56 条已有值的记录做了旁证比对：36 条与 config 全等、28 条差值全部是口径差（如 qwen3.5 系库 1,010,000 vs config 262,144；qwen2 小尺寸库 32,768 vs 官方后来把 config 原生提高到 131,072），**非错误**。这验证了「只为空值补、绝不覆盖」的红线正确——否则会把 1M 级大口径压回原生值。D44 报告中「ctx 可补 64」实为"证据可得数"，真实空值仅 8。
- `total_params_b` / `active_params_b` 维持不导（model_size 是字节数，D44 红线）。

## 二、首批采集：S1 拍板 9 采 / 13 缓

S1 三问过筛：13 条缓采——UI/OCR/领域特化（LLaDA-UI、UI-Venus-2-9B、ArmorOCR、Qwen-Drive-1.0-4B、MathForm-8B、Recon2Reason-4B）与训练阶段/中间产物（MiniCPM5-2B-{SFT,Base,Midtrain,DSpark}、JustRL-II、Ling-3.0-flash-{dspark,base,base-midtrain,base-30T}）。名单保留在 `temp/d44_msscope_candidates.jsonl` / `backlog`，后续可捡。

**批次 `b333w1-modelscope`（round D45）**，9 个单模型 subagent（并发 ≤2，五波），全部过单文件门禁后合并（add_record 路径，935→944，无撞键）：

| model_id | vendor | release_date | 关键值（官方一手） |
|---|---|---|---|
| deepseek:deepseek-v4.1-flash:base | DeepSeek | 2026-09-10（官方新闻稿 news260910） | 552B MoE（+Engram 196B 单列）/激活 decode 16B；CED 编码-解码架构；1M ctx；MIT；peak $0.3/$1.2；18 条自报 |
| deepseek:deepseek-v4-flash-vision-exp:base | DeepSeek | 2026-08-21（news260821）；**09-10 已宣布退役**→状态「已过期」 | V4-Flash 视觉实验版；256 专家 MoE；1M ctx；MIT；11 条自报 |
| inclusionai:ling-3.0-flash:base | InclusionAI | 2026-07-24（IT之家当日转述官方，标待验证） | 124B/A5.1B；MoE 512选8+1共享；KDA+Gated MLA 5:1 Hybrid；256K ctx；MIT；5 条自报 |
| inclusionai:ling-3.0-flash-vl:base | InclusionAI | 2026-09-09（多家媒体当日「今日宣布」，标待验证） | 124B/A5.5B；原生图像+视频输入（VideoRoPE）；256K ctx；MIT |
| inclusionai:ling-3.0-tiny:base | InclusionAI | 2026-08（月级，HF/MS 同日首发锚定） | 7.9B/A1.3B；128 专家；3:1 KDA–MLA Hybrid；256K ctx；MIT |
| modelbest:minicpm-5-2b:base | ModelBest | 2026-09-07（GitHub News 官方） | 2.52B Dense；128K ctx；Apache-2.0；混合思考；34 条自报；⚠ WAIC 宣传 512K 与正式 128K 冲突按 T0 取后者 |
| nex-agi:nex-n2.5-max:base | Nex AGI | 2026-09（国资委文 09-09 全球首发） | 1.6T/A49B（官网原值）；基于 DeepSeek-V4-Pro-Base 后训练；1M ctx（config YaRN×16）；Apache-2.0；text-only；6 条自报 |
| alibaba:qwen-3.8-flash-next:base | Alibaba | 2026-08（月级；仓库 08-24/媒体与百炼台账 08-26 分歧无法裁定） | 180B（125B LM+51B N-gram+4B MTP）/A6B；MoE 512 专家；Gated DeltaNet+QSA Hybrid；原生 262K/YaRN 1M；Qwen Community License；22 条自报 |
| meituan:longcat-flash-lite-sparse:base | Meituan | 2026-08（月级，HF 仓 07-31 + arXiv:2608.01662 锚定） | 69B/A3B；LSA 稀疏注意力（Lite=轻量档、Sparse=LSA 替换 MLA，官方原义）；1M ctx；MIT；非思考模型；58 条自报（双推理配置） |

**采集质量口径**：release_date 4 条日级（官方新闻稿×2、国资委会文、GitHub News）+ 1 条日级媒体转述（标待验证）+ 4 条月级（仅仓库/论文锚点，不硬造）；2 条 Elo 型绝对分（Codeforces 3471、GDPval-AA 1713）按门禁「score 0–1」不入 benchmarks、留 notes；新 vendor「Nex AGI」沿用库内 Wave 记录写法。

## 三、S4 增量质检

- 全库门禁：944 条 **ERROR 0 / WARN 0**（基线无上涨）；
- `candidate_diff.py` 复扫 D44 候选：**NEW 11 → 6**（9 条入库记录全部转 EXISTS/CHECK_VARIANT，剩余 NEW 均为缓采名单）；
- 9 条新记录针对性体检（跑分值域/source_url/日期格式/ctx 与参数合理界/pricing 四键/vendor 拼写）：**0 真问题**（原 outlier 全库体检脚本 `temp/d34_scan_outliers.py` 已随 temp 清理失传，本轮以针对性体检替代，脚本待重建）。

## 四、遗留

1. **13 条缓采**与 **948 条 backlog** 长尾待后续轮次（backlog 预计大量是 embed/经典 NLP/变体）；
2. **N2.5 家族 mini/Pro 的 release_date 仍 null**：本轮拿到 HF createdAt 09-07/09-08，但属仓库创建日口径（§4 铁律不采），待官方公告；
3. Ling-3.0-flash / flash-vl 的发布日依赖 T3 媒体当日转述（官方 SPA/GitHub 无 Releases），已标「待验证」，官方一手页面出现后精化；
4. 全库离群体检脚本需按 D34 31 项口径重建（本轮以针对性体检替代）；
5. 用户约束沉淀：**subagent 并发 ≤ 2**（额度原因），已在本轮执行，后续采集轮沿用。
