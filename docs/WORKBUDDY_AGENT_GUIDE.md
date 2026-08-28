# WorkBuddy Agent 专属作业规范（model_data v2）

> **本文档读者**：在 WorkBuddy 平台上运行的 agent（主 agent 与它派发的 subagent）。
> **定位**：是 [`multi_platform_subagent_guide.md`](./multi_platform_subagent_guide.md)（跨平台通用规范）的**平台补丁**。通用规范里的认领协议、文件命名、12 条红线、验收 checklist 全部继续有效，本文档只补充 WorkBuddy 环境特有的坑和必须额外执行的动作。
> **冲突时**：以本文档为准（因为它记录的是本平台实测过的环境事实）。
> **建立**：2026-08-28，基于 workbuddy-01 烂尾事故复盘 + 本机 git 弹窗问题。

---

## 0. 30 秒 TL;DR（开工前必读）

```bash
# ① 所有 git 操作必须用【用户本机 git】，绝不能用 WorkBuddy 自带的
export PATH="/e/System_Programes/Git/cmd:$PATH"   # 每个新 Bash 会话都要先执行
git --version        # 必须是 2.46.0.windows.1；若是 2.55.0 说明 PATH 没生效，停下重来

# ② Python 命令统一加 UTF8 前缀（Windows GBK 控制台会崩）
PYTHONUTF8=1 python scripts/validate_model_data.py <file>

# ③ 提交采集文件时必须 -f（.gitignore 第 29 行忽略了 incoming/models/*.jsonl）
git add -f incoming/models/<batch_id>__*.jsonl

# ④ 作业顺序：先收尾自己平台上未提交的批次，再认领新批次
# ⑤ 每批完成后立即 push，不要攒着 —— 烂尾比慢更严重
```

---

## 1. 【红线 A】git 二进制：必须用用户本机的 git

### 1.1 问题现象

WorkBuddy 的 Bash 工具默认 PATH 里排在最前面的是 WorkBuddy 自带的 PortableGit（`/mingw64/bin/git`，v2.55.0）。用它 `git push` 会**弹出交互式凭据窗口**，agent 无法应答，进程挂死，任务烂尾。

### 1.2 根因

两套 git 的 system 级 `credential.helper` 不同，凭据不互通：

| git | 版本 | `credential.helper`(system) | push 行为 |
|---|---|---|---|
| `/e/System_Programes/Git/cmd/git`（用户本机） | 2.46.0.windows.1 | `manager` | 读 Windows 凭据管理器，**静默通过** |
| `/mingw64/bin/git`（WorkBuddy 自带） | 2.55.0.windows.3 | `helper-selector` | **弹交互窗**，agent 卡死 |

用 `type -a git` 可以看到两个都在，PortableGit 排前面。

### 1.3 唯一正确做法

**方式一（推荐，一次设置整会话有效）**：

```bash
export PATH="/e/System_Programes/Git/cmd:$PATH"
git --version    # 校验：必须输出 2.46.0.windows.1
```

**方式二（显式绝对路径，最保险，适合写进脚本）**：

```bash
/e/System_Programes/Git/cmd/git -C <REPO> push
```

> ⚠️ Bash 工具的**每个新会话**都要重新 `export PATH`，shell state 不跨调用保留。
> 每次执行 push 前，先跑一次 `git --version` 自检；看到 2.55.0 就说明 PATH 没生效，**不要用**。

### 1.4 仓库信息

- remote：`https://github.com/Stargazed-Dreamer/model_data_v2.git`
- 默认分支：`main`
- 已配置 user.name / user.email（无需再设）

---

## 2. 【红线 B】采集文件必须 `git add -f`

根 `.gitignore` 第 29 行有：

```
/incoming/models/*.jsonl
!/incoming/models/_samples/
!/incoming/models/_m_context.md
```

即 `incoming/models/` 下只有 `_samples/` 和 `_m_context.md` 入库，**所有采集产出默认被忽略**。

- 提交时必须 `git add -f incoming/models/<batch_id>__*.jsonl`
- 忘记 `-f` 的后果：`git status` 干净，你以为提交成功了，实际只推了 ledger，文件从未进仓库 —— 合并阶段拿不到数据
- 提交后自检：`git ls-files incoming/models/ | grep <batch_id>` 必须能列出你的文件

---

## 3. 环境差异速查（WorkBuddy 平台实测）

| 项 | 值 / 做法 |
|---|---|
| shell | Git Bash（POSIX），路径用 `/` 正斜杠 |
| 仓库根 `<REPO>` | `F:/project_temp/localAgent/workspace/model_data` |
| Python | 系统 Python 可用；跑脚本一律加 `PYTHONUTF8=1` 前缀 |
| 控制台编码 | GBK，脚本里的 emoji/CJK 输出不加 UTF8 前缀会崩 |
| 网络 | `docs.claude.com` / `platform.openai.com` 直连不可达，信息源以 WebSearch 摘要为准并按红线降级标 T3 |
| 不可调 | 不要调 `cmd.exe` / PowerShell 子进程（安全策略会拦截），用纯 bash |

---

## 4. 平台 ID

- 格式：`workbuddy-<NN>`，NN 为两位序号
- 启动会话时先读 ledger，取一个**当前未被占用**的最小编号（已被 `workbuddy-01` 占用）
- 一个会话内所有批次用同一个 ID，便于留痕和接管判定

---

## 5. 标准作业流程（SOP）

```
S1 环境自检   export PATH=... ; git --version 必须 2.46.0 ; git pull --rebase
S2 收尾      读 ledger，找 claimed_by == 本平台ID 且 status != submitted 的批次
             → 文件已在磁盘：validate → 改 submitted → add -f → push（见 §6）
             → 文件缺失：补齐采集，或按 §7 判定后回退 pending
S3 认领      按通用规范 §2.2 的 CAS 协议，认领 2-4 个 pending 批次，立即 commit+push
S4 采集      每个 model_id 派发一个 subagent（任务书模板见通用规范 §3，须附 §5 全部红线）
S5 门禁      每个文件跑 validate_model_data.py，ERROR 必须 = 0（WARN 可接受）
S6 提交      改 ledger 为 submitted + 填 submitted_files → add -f 文件 → commit → push
S7 复核      git ls-files 确认文件确实入库；git status 干净；主库 model_data_v2.jsonl 无 diff
```

**每批做完就 push**，不要攒。通用规范 §8.3-13 也是这个要求，但本平台要当成硬约束：见 §7 烂尾教训。

---

## 6. 收尾动作的正确姿势（高频场景）

磁盘上已有 `<batch_id>__*.jsonl` 但 ledger 还停在 `claimed` 时：

```bash
# 1) 门禁（每个文件都要跑，ERROR 必须 0）
PYTHONUTF8=1 python scripts/validate_model_data.py \
  "incoming/models/b9w6-openai__openai__text-ada-001__base.jsonl"

# 2) 改 ledger：status=submitted，填 submitted_at / submitted_files / submitted_by
#    （用 Python 原地改写，保持单行压缩 JSON、UTF-8 无 BOM、其余行原样）

# 3) 提交（注意 -f）
export PATH="/e/System_Programes/Git/cmd:$PATH"
git add docs/batch_claim_ledger.jsonl
git add -f incoming/models/b9w6-openai__*.jsonl
git commit -m "submit: b9w6-openai (5/5) by workbuddy-02"
git push

# 4) 自检：文件必须能被 ls-files 列出
git ls-files incoming/models/ | grep b9w6-openai
```

---

## 7. 防烂尾：超时批次的接管规则

### 7.1 事故复盘（务必记住）

2026-08-27 14:26，agent `workbuddy-01` 认领了 3 个批次（b9w6-openai / b9w7-openai / b12w4-anthropic，共 15 个模型），15 个文件**已全部采集落盘**（合计约 100KB），但**从未更新 ledger、从未 push**。后果：

- 其他平台看 ledger 以为这 3 批"有人在做"，不会接管 → 进度虚占
- 文件因 `.gitignore` 未入库 → 远端完全没有这批数据
- 合并阶段按 `status=submitted` 扫描，**这 15 个模型会被整体漏掉**

### 7.2 判定与处理

| 情况 | 判定 | 动作 |
|---|---|---|
| `claimed` 且 `claimed_by` == 本平台 ID | 自家烂尾 | **直接接管收尾**（§6），`claimed_by` 保持原值，notes 追加 `[recovered by <新ID> @ <now>]` |
| `claimed` 且超时 > 24h（他人平台） | stale | 可接管：`claimed_by` 改本平台 ID，notes 留痕"接管原平台 X 超时未交" |
| `claimed` 且未超时（他人平台，< 24h） | **进行中** | **禁止抢**。可能是对方正在采集或即将 submit，只在报告里提示用户 |
| `claimed` 但磁盘已有完整文件（他人，未超时） | 对方将交 | **不动**，仅报告 |

> 判定超时用 `claimed_at` 与当前时间比较。`claimed_at` 有 `+08:00` 和 `+00:00` 两种写法，**比较前统一转 UTC**。

### 7.3 强制自检（会话结束前必做）

- [ ] 本平台 ID 下**没有任何** `status=claimed` 的残留批次
- [ ] 所有提交过的批次，`git ls-files incoming/models/ | grep <batch_id>` 有输出
- [ ] `git status` 干净（无未提交的 ledger / 文件改动）
- [ ] `git log` 最新 commit 含本轮所有批次号

**"文件写完就报告完成"不算完成。ledger 改完 + push 成功 + ls-files 能查到，才算完成。**

---

## 8. 文件命名与 model 字段（易错点）

- 文件名：`<batch_id>__<vendor>__<model>__<variant>.jsonl`（model_id 的 `:` 全部替换为 `__`，**双下划线**）
- JSON 内的 `model_id` 保持三段式原样（`vendor:model:variant`），**不要**在 JSON 里也替换
- **variant 以 ledger 的 `models` 字段为准**（多为 `base`），不要把 model 名尾段当 variant
  - 例：`microsoft:phi-3-mini-4k-instruct:base` → 文件 `...__phi-3-mini-4k-instruct__base.jsonl`
  - 反例（错误）：把 `phi-3-mini-4k-instruct` 拆成 model=`phi-3-mini` + variant=`4k-instruct`
- `submitted_files` 字段填**相对仓库根的路径**（`incoming/models/<文件名>`），历史记录里两种写法都有，新提交统一用带路径的完整形式

### 8.1 超长文件名降级规则（Windows 路径 260 上限）

多机构联合署名批次的 `batch_id` 可能极长（本库最长 479 字符），且文件名里 `vendor` 段与 `batch_id` 内容重复，导致路径爆表：

```
b56w1-allen-institute-for-ai-...-of-maryland__b56w1-allen-institute-for-ai-...-of-maryland__olmo-3-1-32b-think__base.jsonl
→ 绝对路径 706 字符，Windows 直接抛 OSError [Errno 22] Invalid argument，文件根本写不出来
```

**判定**：若标准命名 `<batch_id>__<vendor>__<model>__<variant>.jsonl` 的**绝对路径长度 > 250 字符**，降级为：

```
incoming/models/<bNNwM>__<model>__<variant>.jsonl
```

其中 `<bNNwM>` 是 `batch_id` 第一个 `-` 之前的部分（如 `b56w1`）。已核验：全库 305 个批次的短标识**两两不冲突（0 冲突）**，降级后最长绝对路径 133 字符，全部安全。

**影响面**：全库 702 个应产出文件中有 **26 个超限，涉及 19 个批次**（最长为 `b97w1-rwkv-foundation-...`，路径 1041 字符）。这些批次**无法用标准命名落盘**，必须走降级。

**注意**：降级后合并阶段照样工作——合并工具按 ledger 的 `submitted_files` 定位文件，不靠文件名反推 batch_id；`bNNwM` 前缀本身仍是有效批次标记。JSON 内的 `model_id` 保持三段式原样，不受影响。

---

## 9. 故障速查

| 现象 | 原因 | 解法 |
|---|---|---|
| `git push` 卡住不动 / 弹窗 | 用了 WorkBuddy 自带 git | `export PATH="/e/System_Programes/Git/cmd:$PATH"`，校验版本 2.46.0 |
| `git status` 干净但远端没文件 | 漏了 `git add -f` | 重跑 `git add -f` + commit + push，`git ls-files` 验证 |
| Python 报 UnicodeEncodeError | GBK 控制台 | 命令前加 `PYTHONUTF8=1` |
| 门禁报 positioning 越界 | 用了受控词表外的标签 | 六值枚举：`旗舰/中端/轻量/推理增强/多模态/工具调用增强`，越界标签按通用规范 §8.2-9 映射或删除 |
| 门禁报顶层键数量不对 | `access` 被提到顶层 | `access` 必须嵌在 `basic_info.access` 内；8 个顶层键固定 |
| subagent 返回空但疑似已写盘 | Task 结果丢失（发生率约 40%） | **先查磁盘再决定是否重派**，不要盲目重跑 |
| `push` 被拒（远程有新 commit） | 被其他平台抢先 | `git pull --rebase`，检查自己 claim 的批次是否被抢；被抢则放弃该批，取下一批 pending |
| `git ls-files \| grep <batch_id>` 查不到刚提交的文件 | grep 把 `^` 锚在了行首，但输出行首是 `incoming/models/` | 写成 `git ls-files incoming/models/ \| grep "incoming/models/<batch_id>__"` |
| 派发 subagent 返回 `429 queue.userLimit.title` / `429 queue.waiting.title` | 平台级并发 agent 上限，与项目无关，重试无效 | 见下方 §11 |

---

## 11. 并发上限（429）的处理

派发 subagent 采集时可能撞上平台级并发上限，报错形如 `429 queue.userLimit.title` 或 `429 queue.waiting.title`。**这是账号/平台维度的限制，与项目配置无关，立刻重试通常仍失败。**

应对顺序：

1. **降低并发**：一次派 8 个很容易触发，降到一次 3-4 个可正常跑；再降到 1 个若仍 429，说明上限已被占满（可能有上一批 subagent 尚未释放）
2. **不要干等**：等待期间先把已完成批次的验收与 push 做掉
3. **仍无法派发时，必须回退**：已 `claimed` 但采集不出来的批次，**一律改回 `pending` 并清空 `claimed_by` / `claimed_at`**，notes 留痕「平台并发上限，退回待认领」。理由同 §7——留着 claimed 会虚占进度，其他 agent 不会接管 claimed 批次，等于阻塞
4. 回退后向用户报告限流情况，等上限释放后重新认领即可（批次回到 pending 后数据与流程无损）

> 实测：一轮连续派发 8 个 → 陆续出现 429；降到 3 个一组正常；后期完全占满时连 1 个都派不出，此时应回退收尾而非反复重试。

---

## 10. 维护

- 维护者：WorkBuddy 平台主 agent
- 原则：**只增不删**，修改在文末留痕
- 触发修改：发现新的 WorkBuddy 环境坑、git 路径变化、接管判定规则调整

### 留痕

- 2026-08-28 v1 首发。来源：workbuddy-01 三批次烂尾（15 模型未提交未入库）+ 本机 git 与 PortableGit 凭据助手不兼容导致 push 弹窗。确立红线 A（本机 git）、红线 B（`git add -f`）、§7 防烂尾接管规则与结束前强制自检。
- 2026-08-28 v1.1 首次实战验证（agent `workbuddy-02`），三项结论：①红线 A 有效——本机 git 一次性推送 13 个堆积 commit 全程静默无弹窗；②红线 B 的缺口比预想大——除烂尾批次外，另有 5 个已 submitted 批次共 25 个文件因漏 `add -f` 从未入库；③§7.2「未超时他人 claimed 不抢」判断正确——trae-cn-glmm 认领的 b33w1/b44w1 在其 claim 后约 1 小时内自行完成提交，抢工会造成重复劳动。另补 §9 一条 `git ls-files` grep 前缀的实测坑。

> 排查经验补充：判断「磁盘缺失的采集文件是否真丢」时，先查主库 `model_data_v2.jsonl` 是否已含该 model_id。本次 82 个 submitted 批次中有 262 个文件不在磁盘，但逐一比对后确认 **262 个全部已在主库**（0 真丢失），属「采集→合并→文件未保留」的正常链路，无需重采。避免据此误判为数据丢失而重复劳动。
- 2026-08-28 v1.2：新增 §8.1 超长文件名降级规则（Windows 260 上限）与 §11 并发上限（429）处理。本轮（agent `workbuddy-02`）累计完成 18 批 61 模型采集 + 40 个历史文件收尾入库，全程本机 git 零弹窗；末期遇平台 subagent 并发上限，已按 §11 将 8 批回退 pending 并留痕，未留 claimed 残留。
