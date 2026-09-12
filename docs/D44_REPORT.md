# D44 轮次报告：ModelScope（魔搭）接入跟踪源清单 A 层

> 日期：2026-09-13。用户触发（原文「上一层项目 localagent 的 modelscope 更新 workspace 在工作时，我注意到魔搭社区有很多模型的参数和信息，你看看我们能不能用上」→ 复核后拍板「开工」）。
> 本轮**主库零改动**（935 条不变），门禁复跑 **ERROR 0 / WARN 0**；全部产出为 S0 探测产物（dry-run，落 `temp/`）。

## 一、动机与结论

兄弟工作区 `modelscope_model_update` 靠 CDP 爬 DOM 扫魔搭（选择器 `acss-17aobl4` 自标改版风险），而主库台账恰有大批空字段：`total_params_b` 空 304 条（32%）、`context_window_tokens` 空 204 条（其中 open_weights 67 条）、`architecture_type` Unknown 456 条；且已有 47 条记录零散引用 modelscope.cn 做来源。

**结论：能用上。** 魔搭有免鉴权结构化 JSON API，首轮全量比对即给出：漏采线索 22 条（含 DeepSeek-V4.1-Flash、Ling-3.0 主体系等真缺口）+ open_weights 空字段补全候选 66 条（ctx 可补 64，对全库 open_weights 空 ctx 覆盖率 95%）。

## 二、API 实测发现（2026-09-13）

| 接口 | 说明 |
|---|---|
| `PUT /api/v1/dolphin/models` | 搜索/列表。`SortBy` 合法枚举：`Default`（实测最新优先，首页即 3 天前上架的 DeepSeek-V4.1-Flash）/ `DownloadsCount` / `StarsCount` / `GmtModified`；其余值 400 |
| `GET /api/v1/models/{org}/{name}` | 详情：License、Tasks、CreatedTime/LastUpdatedTime、Architectures、认证组织（含官网）、`ModelInfos.safetensors.model_size`+`tensor_type`、ReadMeContent |
| `GET .../repo?Revision=master&FilePath=config.json` | `max_position_embeddings`（=上下文长度，实测 DeepSeek-V4-Pro-0813 为 1048576=1M）、`n_routed_experts`/`num_experts_per_tok`（MoE 判据）、`quantization_config` |

**三个坑（实测背书）**：

1. **无组织过滤参数**：`Owner`/`Author`/`Namespace`/`Publisher`/`Owners` 全不生效（全站 253,090 不变）。只能 `Name="<org>/"` 前缀搜索 + 客户端按 `Path==org` 过滤——搜索会混入 DevQuasar/mlx-community 等第三方上传，不过滤就会把社区量化当官方新仓库。
2. **组织名大小写敏感**：`OpenMOSS` own=0，`openmoss` 命中 181 仓库。
3. **列表 item 的 `model_size` 常为空**（实测 GLM-5.3 为 None、DeepSeek-V4-Pro-0813 有值 1.65TB），要 model_size 得补拉详情接口。

另有踩坑记录：curl 需 `--ssl-no-revoke`（§5 已载）；Python urllib 无此问题，生产脚本用 urllib。

## 三、首轮全量比对结果

**脚本**：`scripts/d44_fetch_modelscope.py`（22 官方组织白名单 → 快照 → canon 精确匹配 → 四类 dry-run 产物）。

组织命中（own>0 的 21 个，快照共 2,979 仓库）：deepseek-ai 106、Qwen 384、ZhipuAI 172、Shanghai_AI_Laboratory 449、inclusionAI 192、OpenBMB 153、BAAI 199、microsoft 551、PaddlePaddle 193、openmoss 181、Skywork 74、stepfun-ai 57、01ai 28、meituan-longcat 31、XiaomiMiMo 25、baichuan-inc 24、MiniMax 20、moonshotai 19、langboat 15、nex-agi 11、Tencent-Hunyuan 94。
THUDM/InternLM 模型分别在 ZhipuAI / Shanghai_AI_Laboratory 组织下，不重复挂；NVIDIA 魔搭无官方组织（只有 nv-community 等镜像），继续走 HF。

| 产物（temp/） | 条数 | 说明 |
|---|---|---|
| `d44_modelscope_repos.json` | 2,979 | 原始快照（含 org_stat） |
| `d44_msscope_candidates.jsonl` | **22** | 漏采线索（since 2026-08-01），可直喂 candidate_diff.py |
| `d44_msscope_backlog.jsonl` | 948 | 存量未采（<2026-08-01），长尾/变体，人工看 |
| `d44_msscope_fillplan.json` | **66** | open_weights 空字段 ←→ 魔搭 config.json 候选（**ctx 可补 64 / arch_type 可判 55**） |

**漏采线索 22 条经 `candidate_diff.py` 判定：NEW 11 / CHECK_VARIANT 10 / EXISTS 1**。代表性真缺口（主库 grep 证实为 0 命中）：

- `DeepSeek-V4.1-Flash`（09-10 上架，dl 9,971，VL）
- `Ling-3.0-flash` 本体 / `Ling-3.0-tiny` / `Ling-3.0-flash-VL`（库内只有 Fin/Sante 变体——inclusionAI 正是 OpenRouter 揭示的缺失厂商）
- `Qwen3.8-Flash-Next`（含 FP8 变体，主库 0 命中）
- `MiniCPM5-2B` 系（库内最新只有 MiniCPM4）、`Nex-N2.5-Max`、`LongCat-Flash-Lite-Sparse`、`Recon2Reason-Reasoning-4B`、`UI-Venus-2-9B`、`ArmorOCR`、`LLaDA-UI`、`Qwen-Drive-1.0-4B`（领域特化，S1 判定是否在范围）

**补全候选质量**：66 条命中中 ctx 值全部来自官方仓库 config.json（如 `qwen-14b:base` ← `Qwen/Qwen-14B` 8192；`qwen2-0.5b:base` ← 131072）；同 canon 多仓库时按主库 variant 风味选代表仓（`:base` 记录优先无 `-Chat` 仓库）。`model_size`/`tensor_type` 作为参数量**推导参考**单独成段，明确标注不入 `total_params_b`。

## 四、口径红线（写入脚本与 §A-1）

1. `CreatedTime` 是**仓库创建日**（同 HF `createdAt` 性质，§4 铁律适用），候选一律标 T2「待核」，`release_date` 仍回官方公告；
2. 只收 ORGS 白名单官方组织；`AI-ModelScope`/`nv-community`/`FlagRelease` 等镜像/社区组织不收；
3. 量化变体不单列：名字含 gguf/mlx/awq/gptq/nvfp4 直接过滤；canon 相同（-fp8/-chat 被剥）取下载量最高代表仓、其余记 `variants`；剥 `-fp4/-fp8` 后命中主库/其他候选的按 §3 并入；
4. `model_size` 是权重字节数不是参数量（fp8≈1B/byte、bf16≈2B/byte 只给推导范围）；
5. 匹配只走 canon 精确匹配（D40 教训），主库侧索引 family / family-variant / full_name 三键。

## 五、兄弟工作区联动

`modelscope_model_update/SKILL.md` 阶段 3 增加 **JSON API 快速路径**（dolphin 列表 + 详情接口，含 `Path` 过滤与大小写警告，指向 `跟踪源清单.md` §A-1 与本脚本），右侧 API 面板判定等 DOM 操作降为兜底；风险条目 1 同步更新。

## 六、遗留与下一步（非本轮范围）

1. **22 条候选走 S1 拍板**（NEW 11 条是否采集由用户定；`Ling-3.0-flash` 报 EXISTS 是 token 重合的保守建议，人工复核口径）；
2. **fillplan 66 条**：人工抽验（重点：config.json ctx 与线上 API 限制可能不一致）后，写 `d44_import_modelscope.py` 走「只为空值补 + notes 标注来源」落库——参照 d40_aa_import 模式；
3. **backlog 948 条**存量长尾过一遍（预计大量是历史上有意不收的 embed/经典 NLP/变体，但可能藏漏采）；
4. `01ai`/`openmoss` 等新挂组织的存量候选集中在 backlog，首次人工过完后下轮起 candidates 量会回归小水位。

## 七、核验

- 主库 935 条零改动，门禁 `validate_model_data.py` 复跑 **ERROR 0 / WARN 0**；
- candidate_diff.py 退出码 10（存在 NEW，符合其文档约定）；
- 全部产物 dry-run，未触碰 `model_data_v2.jsonl` / `docs/batch_claim_ledger.jsonl`。
