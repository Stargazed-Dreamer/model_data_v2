# D47 轮次报告：用户四项拍板落地——r1 同名处置 / N2.5 日期 / AA 观测价 / 双源补全

> 日期：2026-09-13。用户拍板（原文「1234都可，按顺序来」）。记录数 **950 → 948**（r1 合并 -2），门禁 **ERROR 0 / WARN 0**（全程保持，AA 导入引起的 24 条 WARN 当轮修正归零）。

## 一、r1 同厂商同名三组处置（950 → 948）

逐组核实后处置（`scripts/d47_merge_r1.py`，dry-run + apply，备份 `backups/model_data_v2.pre-d47-r1-*.jsonl`）：

- **组 A 合并**：`alibaba:qwen2.5-coder:base` → `alibaba:qwen2.5-coder-32b:base`（两侧 full_name/参数/上下文全同，真同物；keeper 取 D43「版本+参数式」命名）。补 null：active_params_b=32.5、version=2.5；independent 数组并集 2+3=5（键 `benchmark,config,date,source_site` 去重 0 撞）；标量冲突留痕：donor 侧 release_date=2024-11-12 取自 epoch Publication date 待核，主档保留 2024-09。
- **组 B 合并**：`openbmb-open-lab-for-big-model-base:minicpm-4-8b:base` → `modelbest:minicpm-4:base`（D41 归并后的正规 vendor 侧为主档，D43 先例）。硬冲突保留主档 + notes 留痕待核：license 主档 MIT (ModelBest) vs donor Apache 2.0；ctx 主档 32768 vs donor 131072。补 null：active_params_b=8.0。
- **组 C 改名不合并**：`zhipu:glm-5.2-none:base` full_name →「GLM-5.2（Non-Think）」。两侧跑分表不同（17+15 vs 2+2，不同基准名），属同模型思考/非思考两档，D34 deepseek-v4-pro 先例：改名消除同名、合并会销毁数据。

## 二、N2.5 mini/Pro 日期月级落位

`nex-agi:nex-n2.5-mini:base` / `nex-agi:nex-n2.5-pro:base` release_date null → **2026-09**（月级）。锚点：HF 官方组织仓库 createdAt 09-07/09-08（仓库创建日口径，§4 铁律不作发布日，仅作月级锚定）+ 姊妹条 Max 的上海市国资委 09-09 发布文；notes 声明官方公告出现后精化。

## 三、AA 观测价准入 pricing（38 条）

`scripts/d47_import_aa_price.py`：D40 快照（735 条 / 435 带价）canon 精确匹配，**只对 pricing.input 为空的记录整套补** input/output/cached_input/cache_write，currency=USD、source_type=独立评测平台、confidence=T2、notes 声明「观测价非官方刊例、滚动更新」。

**四道护栏**（dry-run 拦截实录，56 → 38）：
1. **0/0 占位价跳过**（gemma-3/olmo/north-mini 等开源无 API 模型的 $0 是"无观测"非免费）；
2. **AA 侧同 canon 多条价格不一致 → 该键歧义跳过**（21 键，D39 红线）；
3. **flavor 错配跳过**（seed-oss-36b-**base** ← -instruct slug）；
4. **vendor 等价组校验**（拦下 perplexity:r1:1776 ← deepseek-r1 跨厂错配；alibaba↔inclusionAI 同组放行 ring-2.6-1t；误伤 apertus×2——creator「Swiss AI Initiative」识别不了，留官方价人工）。

**当轮修复的口径冲突**：导入后门禁 WARN 0 → 24（基线纪律触发），两类——18 条旧标签「开源权重模型核对（无官方 API 价）」与新观测价矛盾、6 条缺 effective_date。修正：38 条 source_type 统一改「独立评测平台」（旧标签结论写入 notes 留痕）、effective_date=2026-09-13（观测日）。WARN 归零。

## 四、双源只补空值

**OpenRouter knowledge_cutoff（`scripts/d47_import_openrouter_kc.py`，48 条）**：445 模型清单 canon 精确匹配，T2（供应商申报）。护栏：vendor 等价组（拦 hunyuan-large/yi-large ← mistral-large 的 'large' 残片错配）+ **日期变体护栏**（variant 形如 2402/0528/2507 时 OR id 必须含同数字串，拦下 mistral-large:2402 被现役条目 cutoff=2024-11 污染的错配）。补充教训：z-ai 即 Z.ai（智谱），别名表补 `'z-ai'` 后捡回 2 条。

**HF 版 fillplan（`scripts/d47_fetch_hf.py`，ctx 8 / arch 9）**：19 个 HF 白名单组织，对魔搭覆盖不到的开源权重记录补 config.json 值。落库样例：granite-4.0-h-micro/small 131072、Solar-Open2-250B 1048576、EXAONE-Deep 32768、gpt-oss-120b/20b → MoE、opt-66b → Dense。**gated 仓库 12 条**（meta-llama 全系 + google/gemma 系 401）跳过留人工——这是 open_weights 空 ctx 的主要剩余来源。

## 五、前后对比与遗留

| 指标 | D47 前 | D47 后 |
|---|---|---|
| 记录数 | 950 | 948（r1 合并） |
| knowledge_cutoff 空 | 777 | 727 |
| pricing.input 空 | 637 | 597 |
| open_weights 空 ctx | 59 | 51 |
| ctx 总空 | 204 | 188 |
| qa_outliers r1 同名组 | 3 | **0** |
| 门禁 | ERROR 0 / WARN 0 | ERROR 0 / WARN 0 |

遗留：① gated 12 条（Llama/Gemma 系 ctx）需人工回官方模型卡；② apertus ×2 价格因 creator 识别不了未导；③ 组 B 的 license/ctx 冲突值待核（MIT vs Apache、32K vs 128K）；④ `mistral-large:0324/:2407/:base` 三条同 full_name 仍有版本间 kc 精化空间（本轮保守全拒）；⑤ backlog 948 条长尾仍开放。
