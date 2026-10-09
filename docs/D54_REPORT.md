# D54 报告：ctx 缺口补缺 + 聚合商别名裁定

> 轮次：**D54** | 日期：**2026-10-10** | 执行：workbuddy-03（主 agent）+ 4 个采集 subagent
> 触发：用户交付清单 `F:\project_temp\localAgent\temp\model_ctx_gap_20261010\GAP_LIST.md`（localAgent 侧 `wip_chat_3directions` 要接「压缩主动触发」，前置是给在用 model 填 `context_window`）
> 清单口径：**先查 model_data 能不能供；供不上的才进清单**。§2 列出的 6 条即「真缺口」。

---

## 一、结论速览

| 指标 | 值 |
|---|---|
| 记录数 | **993 → 995（+2）** |
| 补空字段 | **1 处**（`nvidia:nemotron-3.5-lightning:base` 的 ctx） |
| 新建记录 | **2 条**（`sha-ai-lab:intern-s2-preview:base`、`sapiens-ai:agnes-2.5-flash:base`） |
| 别名裁定 | **3 条**（2 条给出映射、1 条判定无法映射） |
| 门禁 | **ERROR 0 / WARN 0** |
| 体检器 | **r1=0 / r2=0**；硬错 `o1=5`（**4→5**，见 §四）/ `c4=2` |

**6 条清单：5 条解决，1 条（`big-pickle`）无法映射。**

---

## 二、改动明细（3 处落库动作）

### 2.1 补空字段：`nvidia:nemotron-3.5-lightning:base`

- 动作：`architecture.context_window_tokens` **null → 1000000**，并在 `architecture.notes` / `meta.notes` 追加取证段落。
- 证据：NVIDIA 官方 HF 模型卡 `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` 逐字 —— *"| Context Length | Up to 1M tokens (for single H100 deployment, we use 256K) |"*、*"supports up to 1M context length"*。
- 口径：该仓 `config.json` 的 `max_position_embeddings=262144` 是 **BF16 单卡部署默认**（官方 README 明示 1M 需 8×H100/GB200/B200），**不是架构上限**；沿用库内同系列 `nemotron-3-nano/super/ultra` 的 1,000,000 口径（Nano README 有同义逐字句）。
- 技术实现：主库字节级往返可逆已验证（993 行 0 不一致）⇒ 用「解析→改→重转储」脚本，附**单行变更断言 + 备份 + 回读自证**（`temp/d54/fill_nemotron_ctx.py`）。

### 2.2 新建：`sha-ai-lab:intern-s2-preview:base`（35B 科学多模态基座）

- **identity 裁定**：localAgent 在用的裸名 `Shanghai_AI_Laboratory/Intern-S2-Preview` **不是**库内 `intern-s2-397b` 的预览档，而是一个**架构不同的独立 35B 模型**：

  | 仓库 | model_type / arch | hidden / 层 / 专家 | ctx | 建仓日 |
  |---|---|---|---|---|
  | `Intern-S2-Preview` | `intern_s2_preview` | 2048 / 40 / 256 | 262144 | 2026-05-15 |
  | `Intern-S2-Preview-397B` | `intern_s2_preview` | 4096 / 60 / 512 | 262144 | 2026-07-17 |
  | `Intern-S2-397B`（库内已有） | `qwen3_5_moe` | 4096 / 60 / 512 | 262144 | 2026-09-13 |

- 关键字段：rd **2026-05-15**（ModelScope 建仓日）、ctx **262144**、total 35B（官方 README *"an efficient 35B scientific multimodal foundation model"*）、active **null**（官方未披露，不反推）、backbone **Hybrid**（config `layer_types` = linear_attention×3 + full_attention×1）、license **Apache-2.0**、reasoning **true**（`enable_thinking`）。
- 新建文件：`incoming/models/b350w1__sha-ai-lab__intern-s2-preview__base.jsonl`（门禁 ERROR 0 / WARN 0）。
- 命名：`model_id` 前缀 `sha-ai-lab` 是库内 slug（对应官方展示名 `Shanghai AI Laboratory`），与仓库组织名 `Shanghai_AI_Laboratory` 不一致属**既定惯例**，非缺陷；库内 397B 记录的家族注原称本档为「Intern-S2-Preview-35B」，故本条别称 35B 记于笔记。

### 2.3 新建：`sapiens-ai:agnes-2.5-flash:base`

- **identity 裁定**：**独立模型**，非 `agnes-2.5-pro-beta` 的别名/服务档。官方文档把 `Agnes 2.5 Flash` 描述为 *"Generally available upgrade of **Agnes 2.0 Flash**"*，`Agnes 2.5 Pro` 才是 pro-beta 的商业稳定版。
- 关键字段：ctx **512000**、max_output **65536**、定价（list）**$0.05 / $0.15 / cached $0.005**（每 1M tokens；当前价 $0 限时免费）、闭源 API、reasoning true（Thinking mode）、`release_date=null`（官方未公告，AA 亦无此模型页 ⇒ 不伪造）。
- 新建文件：`incoming/models/b350w1__sapiens-ai__agnes-2.5-flash__base.jsonl`（门禁 ERROR 0 / WARN 0）。

---

## 三、别名裁定（不落库，产出映射表）

| 消费方名 | provider | 裁定 | ctx | 依据 |
|---|---|---|---|---|
| `nemotron-3.5-lightning-free` | opencode | → `nvidia:nemotron-3.5-lightning:base`（`-free` 是**服务档**，不立行） | 1000000 | 同 §2.1 |
| `deepseek-flash` | opencode(zen go) | → `deepseek:deepseek-v4.1-flash:base`（置信中高） | 1048576 | OpenRouter `~deepseek/deepseek-flash-latest` 的 `alias_target` = DeepSeek V4.1 Flash |
| `gpt-5.6-luna` | ice(renice) | → `openai:gpt-5.6-luna:base`（兜底 `-max`） | 1050000 | OpenRouter 有同名 base 档；库内四变体 ctx 全同 |
| `big-pickle` | opencode(zen) | **无法映射**（官方匿名 stealth 模型，无 model 目录/模型卡） | **null** | 库内与主流聚合源 0 命中 |

> `-free` / `big-pickle` 的裁定均沿用 D51/D52/D53「独立测量身份」口径（服务档不立行；匿名 stealth 不入库）。

---

## 四、门禁 / 体检器

- 全库门禁：**995 条 ERROR 0 / WARN 0**（单文件与全库两次）。
- 体检器 `qa_outliers.py`：**r1=0 / r2=0**（硬基线）；硬错 `o1=4→5`、`c4=2`。
  - ⚠ **`o1` 增量为 1，须解释**：新增命中 = `sapiens-ai:agnes-2.5-flash:base`（`release_date=null`）。该记录官方页未标注发布/上线日、AA 无模型页 ⇒ 按「查不到=null、不伪造」留空。这正是 `o1` 类别（「release_date 缺失，均为官方未公告的新模型」）的定义内命中，**非数据缺陷**；待官方/媒体给出日期后补。若要求硬错总数零增长，需先取得可用日期再入库。
  - 其余 `疑点` 项的微小增量（v1 53→54、a7 416→417、a8b 82→83）均来自新增的 2 条记录，属正常。

---

## 五、待议 / 后续

1. **`big-pickle` 悬空**：建议消费方从在用清单剔除，或临时套保守值并标注「推定」，**不要当官方值入库**。
2. **`o1` 4→5**：如需维持硬错零增长，需为 `agnes-2.5-flash` 补一个可溯源发布日（官方未公告）。
3. **§4 全库 ctx 缺口未做**：现库 **187/995（18.8%）** 缺 `context_window_tokens`，top 为 `google`(13)/`microsoft`(6)/`alibaba`(5)/`openai`(5)…。清单已标「非本任务必需」，未动；推进需先与用户对齐范围，建议走 `d44_fetch_modelscope.py` + HF `config.json` 批量补。
4. **顺带发现的额外缺口**（本轮未采，仅登记）：`intern-s2-preview-397b`、`agnes-2.5-pro`（GA）、`agnes-3.0-flash` / `agnes-3.0-flash-max`。
5. **采集提示词加固建议**：本机 HF 直连需先 `unset HTTP_PROXY HTTPS_PROXY`，否则 curl 会走死代理返回 000（本轮 1 个 subagent 踩到，改用 hf-mirror 绕过）；建议写入采集 SOP。

---

## 六、本轮工具脚本（本机一次性，`temp/` 不入库）

| 脚本 | 作用 |
|---|---|
| `temp/d54/build_intern_preview.py` | 构建 `intern-s2-preview` 记录（含格式断言） |
| `temp/d54/fill_nemotron_ctx.py` | 定点补 nemotron ctx（备份 + 单行变更断言 + 回读自证） |

> 消费方回填答复另见 `F:\project_temp\localAgent\temp\model_ctx_gap_20261010\GAP_LIST_ANSWER.md`。
