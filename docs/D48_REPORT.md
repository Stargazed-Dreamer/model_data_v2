# D48 轮次报告：夜间自主批量——双源漏采 11 模型入库 + 双重复折并 + 三项质检基建

> 日期：2026-09-14（凌晨批，03:37–06:30）。用户授权（原文「继续更新和抓取，并发最多4个…直到没数据或早上八点」+ 修订「并发减到3，8:30 开始收尾，绝对 DDL 9 点」）。
> 记录数 **948 → 958**（+11 新模型 −1 dots 同物折并），门禁 **ERROR 0 / WARN 0** 全程保持；subagent 并发 3，五波共 15 个任务。

## 一、榜单刷新与漏采扫描（本地，无 subagent）

- **AA / Arena 双榜重抓**：AA 快照刷新（735 条，价格面无新增可补——D47 已补尽）；DataLearner 快照 **2026-09-02 → 2026-09-11**，`d39_import_arena_elo` 幂等导入 **24 条新 elo**（olmo-3.1-32b-instruct、glm-4.6 等 8 条记录首获 arena 段）。
- **r2 基准名归一落地**（`scripts/d48_normalize_bench_names.py`）：D46 扫出的 14 簇大小写异写按多数派写法改写 **41 处**、撞键合并 0；门禁绿。r2 残留 7 簇（本轮新采集带入的新基准名异写，如 SWE-Bench 系）。
- **双源漏采扫描**（`scripts/d48_scan_leads.py`，新固化脚本）：AA 301 + OpenRouter 227 = **528 条线索**（`temp/d48_leads.jsonl`），其中 2026-08-01 后 47 条。S1 复筛剔除路由别名（`:batch/:free/-latest/~alias` 指向库内已有模型）后拍板 **10 采**，缓采清单（agnes-alpha 权属待考、schematron、apodex、quasar、dots 之外小厂商等）留档线索文件。

## 二、11 模型入库（批次 b335w1/b336w1/b337w1-multi）

| model_id | 亮点（官方一手日期与关键值） |
|---|---|
| sakana:fugu-ultra-v2:base | **库内首条 Sakana AI**；官方博客 09-11；1M ctx；$5/$30（>272K 档翻倍）；"Multi-Agent System as a Model" 编排模型按模型收录先例 |
| sakana:fugu-max:base | 同日同系性价比档 $2/$6 无长文溢价；10 项自报分数自官方图表提取并与博客 "best on six" 互证 |
| meta:muse-spark-1.3:base | 官方博客 09-02；1M ctx；官方刊例 $0.10/$0.20（OR 转售价 $1.25/$4.25 仅 notes 备查） |
| alibaba:qwen-3.8-max-0902:base | 阿里云台账页 T0 直读 09-02 六区域上架；2.4T/A95B；有效上下文 991K 官方明示 |
| mbzuai:k2-horizon-375b-a23b:base | IFM 官方新闻稿 09-03；375B/A23B、192 专家；原生 524,288 ctx；Apache 2.0 |
| inception-labs:mercury-2.5:base | 官方博客 09-08；扩散 LLM（backbone=Diffusion）；260K ctx；$0.20/$0.75 + 发布期 80% 促销 + 1 亿 token 免费档 |
| upstage:solar-pro4:base | 官方博客 08-11；512K ctx（官方口径 vs AA 384K 矛盾按官方并留痕）；$0.30/$1.20 + 70% 促销 |
| ibm:granite-4.2-30b:base / -3b:base | HF 官方卡明示 Release Date 08-25；30B Dense 旗舰推理 + 3B；ctx 标称 512K/原生 128K |
| sapiens-ai:agnes-2.5-pro-beta:base | **身份核验成功**：Agnes 2.5 Pro 系新加坡初创 Sapiens AI 自研（官方文档 T0 直采 $0.10/$0.30、1M ctx），排除「智谱内测代号」传闻（智谱代号史为 Pony/Ox Alpha）；库内新厂商 |
| dots-studio:dots-3-note-preview:base | **身份更正**：Dots Studio 是**小红书旗下**模型工作室（版权行/邮箱/rednotecdn 证据），非韩国初创；280B/A16B MoE 多模态；51 条自报（8+43 折并后） |

另有两次**同物折并**（D35 一行一身份）：
1. `liquid:lfm-2.5-2.6b`（OR slug 拼写）≡ 库内 `liquid:lfm2.5-2.6b`（D42 归一拼写）→ 折入官方博客日期 2026-08-04 + 自报 13 条，重复 id 未建；
2. `dots-3-note-preview` ≡ 库内既有 `dots3-note-preview`（连字符差致 canon 未命中，漏采扫描误报 NEW）→ 折入官方拼写侧（自报 8+43=51），重复 id 删除。

## 三、探路与核查（三个信息任务）

1. **OpenCompass 验证可用**（C 层「待验证」→ 实测）：数据本体在 `cdn.opencompass.org.cn/assets/*.json` 免鉴权直下 + 16 期月度快照；CompassBench v2 覆盖 DeepSeek-V4/GLM-5.3/Kimi-K3/Qwen3.8-Max 正是主库国内旗舰 independent 缺口。**导入待下轮**（约半天：别名表 + 百分制→0-1 + 按月重定基口径）。已写入 `跟踪源清单.md` C 层。探路报告 `temp/d48_opencompass_probe.md`。
2. **gated 14 条核查**：D47 的 gated 名单实为「ctx 或 arch 任一空」的误报——14 条（Llama/Gemma 系）的 ctx **在 8 月采集时已填**；本波 agent 从官方论文/发布文独立复核，14/14 与库内值**全部一致**，等于做了一轮 T1 级交叉验证，零写入。
3. **vision-exp 防重留痕**：AA 的 `deepseek-v4-flash-vision`（无 -Exp）核验为库内 exp 条目的 AA 收录别名（发布日/计费/权重仓三证吻合，无 GA 版），notes 已留痕防重复采集。

## 四、质检与收尾状态

- 门禁 **ERROR 0 / WARN 0**；qa_outliers：硬错全 0，o1=4（4 条已知历史空日期）、r1 折并后归零、r2 残 7 簇（本轮新基准名，下轮归一）、c5=18（定位-参数量级疑点，多为 MoE 大总参轻量定位的口径差）。
- 本轮新记录的定价覆盖好：11 条中 7 条带官方刊例（fugu×2/muse-spark/qwen-0902/mercury/solar/agnes）。
- D48 净变化：记录 948→958；arena_elo +24 条；基准名归一 41 处；新固化脚本 2 个（d48_scan_leads / d48_normalize_bench_names）+1 个归一器复用。

## 五、第二阶段（05:40–06:50）：OpenCompass 落库 + 魔搭重扫收官

1. **OpenCompass 首批落库**（`scripts/d48_import_opencompass.py`）：学术榜 REALTIME + CompassBench v2 26-07，剥 (high)/-Thinking 变体、歧义跳过、只补空 → `tencent:hunyuan-a13b:base` +6 基准（T1）。**深挖版**（`scripts/d48_import_oc_deep.py`，16 期历史快照 + mm 榜，动态列）：再落 5 条（qwen2-7b / minimax-text-01 / glm-4-32b:0414 / yi-1.5-9b / glm-4-plus，含 2024-07 老快照回溯）；LongCat 三日期变体共用一条 OC 评测按歧义红线整组跳过。**收益小的原因是口径正确**：国内旗舰的 independent 已被 AA 填过；管道已固化，后续新模型进来即自动可补。
2. **魔搭重扫（过夜增量）**：candidates 22 → 8（本晚采集消掉了大头）；**Intern-S2-397B**（09-13 建仓，Intern-S2 正式版旗舰，官方文档 T0：397B MoE 512 专家 Hybrid、256K ctx、Apache-2.0）采集入库；其余 7 条均为已排除的训练产物。
3. **fillplan 复核**：qwen-3.5 系等 9 条 ctx 候选全部已有值，0 写入（口径差侧证，与 D47 结论一致）。

**终态统计**：记录 **948 → 959**（+12 新模型 −1 dots 折并）；independent 空 512 → 506；门禁 ERROR 0 / WARN 0；qa_outliers 硬错全 0。

## 六、遗留（按优先级）

1. **OpenCompass 持续导入**（管道已固化 `d48_import_opencompass.py` / `d48_import_oc_deep.py`，后续新模型即自动可补；「OC 作为多来源并集而非只补空」是否放开为口径拍板项）；
2. r2 残留 7 簇基准名归一（同 D46 口径）；
3. 缓采线索：agnes-2-5-pro-alpha（open-weights 权属待考）、dots-3 家族另两成员（jazz/aria）、schematron、apodex、quasar、k-exaone-0803 变体、lfm 小型号等——全部留在 `temp/d48_leads.jsonl`；
4. backlog 948 条长尾（魔搭存量，优先级最低）；
5. c5 疑点 18 条中如 fugu/ling 系「轻量定位 vs 大总参」可考虑在 positioning 口径加「（按激活参数分档）」批注，待拍板。
